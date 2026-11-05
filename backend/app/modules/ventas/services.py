"""Reglas de negocio y frontera transaccional del módulo de ventas.

``registrar_venta``, ``cobrar_venta`` y ``anular_venta`` hacen ``commit`` porque
la venta misma es la operación. ``registrar_venta_de_entrega`` no lo hace: la
entrega es un caso de uso de ``pedidos`` y el commit lo cierra
``PedidoService.cambiar_estado_pedido``.

El stock se descuenta al crear el pedido y se devuelve al anular la venta. Si
el pedido se vuelve a vender, se descuenta otra vez. La cuenta corriente solo se
toca en las ventas a pagaré: suma la deuda al registrarse, la descuenta al
cobrarse y la revierte al anularse, siempre a través de
``clientes.services.ajustar_saldo_cuenta_corriente``.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import NoReturn, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.clientes import services as clientes_services
from app.modules.pedidos.models import (
    EstadoPedido,
    Facturacion,
    MetodoPago,
    Moneda,
    Pedido,
)
from app.modules.ventas import crud
from app.modules.ventas.models import (
    PagoVenta,
    VentaComercial,
    VentaComercialHistorial,
    VentaEstado,
)
from app.modules.ventas.schemas import (
    PLAZOS_DE_PAGO,
    CondicionPago,
    PagoVentaRead,
    ResumenPorMetodo,
    VentaAnulacionCreate,
    VentaCobranzaMensualRead,
    VentaCobroCreate,
    VentaCreate,
    VentaDetailRead,
    VentaHistorialRead,
    VentaListRead,
    VentaPorCobrarItemRead,
    VentaPorCobrarRead,
    VentaRead,
    VentaResumenMensualRead,
    VentaResumenRead,
)


# ---------------------------------------------------------------------------
# Errores de dominio (el router los traduce a códigos HTTP)
# ---------------------------------------------------------------------------


class VentaNoEncontrada(Exception):
    """El id o comprobante recibido no corresponde a ninguna venta."""

    def __init__(self, referencia: object) -> None:
        self.referencia = referencia
        super().__init__(f"No existe una venta con la referencia {referencia}.")


class PedidoNoEncontrado(Exception):
    """El pedido indicado no existe."""

    def __init__(self, pedido_id: int) -> None:
        self.pedido_id = pedido_id
        super().__init__(f"No existe un pedido con id {pedido_id}.")


class PedidoNoVendible(Exception):
    """El pedido no está entregado."""

    def __init__(self, pedido_id: int, estado: str) -> None:
        self.pedido_id = pedido_id
        self.estado = estado
        super().__init__(
            f"El pedido {pedido_id} está en estado {estado}: solo se puede "
            "registrar una venta sobre un pedido ENTREGADO."
        )


class VentaDuplicada(Exception):
    """El pedido ya tiene una venta vigente."""

    def __init__(self, pedido_id: int) -> None:
        self.pedido_id = pedido_id
        super().__init__(f"El pedido {pedido_id} ya tiene una venta vigente.")


class PagosNoCuadran(Exception):
    """La suma de los pagos no coincide con el total del pedido."""

    def __init__(self, total: Decimal, pagado: Decimal) -> None:
        self.total = total
        self.pagado = pagado
        self.diferencia = total - pagado
        super().__init__(
            f"Los pagos suman {pagado} y el total del pedido es {total} "
            f"(diferencia {self.diferencia})."
        )


class VentaYaAnulada(Exception):
    """La venta ya está anulada."""

    def __init__(self, venta_id: int) -> None:
        self.venta_id = venta_id
        super().__init__(f"La venta {venta_id} ya está anulada.")


class StockInsuficienteParaVenta(ValueError):
    """No hay stock para volver a vender un pedido cuya venta fue anulada."""

    def __init__(self, detalle: str) -> None:
        super().__init__(
            "No hay stock suficiente para volver a vender el pedido: "
            f"{detalle}"
        )


class ComprobanteDuplicado(Exception):
    """El número de comprobante generado ya estaba asignado a otra venta."""

    def __init__(self, numero_comprobante: Optional[str]) -> None:
        self.numero_comprobante = numero_comprobante
        super().__init__(
            f"El número de comprobante {numero_comprobante} ya está en uso."
        )


class VentaNoPendienteDeCobro(Exception):
    """Solo se puede cobrar una venta que está pendiente de cobro."""

    def __init__(self, venta_id: int, estado: object) -> None:
        self.venta_id = venta_id
        self.estado = estado
        super().__init__(
            f"La venta {venta_id} está en estado {estado}: solo se puede cobrar "
            "una venta PENDIENTE_COBRO."
        )


class PagareNoPermitido(Exception):
    """El cliente no es mayorista y por lo tanto no tiene cuenta corriente."""

    def __init__(self, cliente_id: int) -> None:
        self.cliente_id = cliente_id
        super().__init__(
            f"El cliente {cliente_id} no tiene cuenta corriente: solo los "
            "clientes mayoristas (B2B) pueden comprar a pagaré."
        )


class PlazoInvalido(Exception):
    """El plazo del pagaré no es uno de los admitidos."""

    def __init__(self, plazo_dias: Optional[int]) -> None:
        self.plazo_dias = plazo_dias
        admitidos = ", ".join(str(plazo) for plazo in PLAZOS_DE_PAGO)
        super().__init__(
            f"El plazo del pagaré debe ser uno de estos días: {admitidos} "
            f"(se recibió {plazo_dias})."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _a_decimal(valor: object) -> Decimal:
    """Normaliza a Decimal los valores que SQLite devuelve como número."""
    return Decimal(str(valor or 0))


def _restaurar_stock_de_pedido(db: Session, pedido: Pedido) -> None:
    """Devuelve el stock del pedido al inventario. Sin commit.

    La importación es local para no crear un ciclo: ``pedidos.services``
    importa este módulo al cargarse.
    """
    from app.modules.pedidos import services as pedidos_services

    pedidos_services.restaurar_stock_de_pedido(db, pedido)


def _consumir_stock_de_pedido(db: Session, pedido: Pedido) -> None:
    """Vuelve a descontar el stock si la venta anterior lo había devuelto.

    Se usa al revender un pedido cuya venta fue anulada. Traduce la falta de
    stock a un error de dominio de ventas. Sin commit.
    """
    from app.modules.pedidos import services as pedidos_services

    try:
        pedidos_services.consumir_stock_de_pedido(db, pedido)
    except ValueError as exc:
        raise StockInsuficienteParaVenta(str(exc)) from exc


def _estado_pedido(pedido: object) -> str:
    """Devuelve el estado del pedido como texto, venga como enum o como str."""
    estado = getattr(pedido, "estado", None)
    return getattr(estado, "value", estado)


def _nombre_completo(nombre: Optional[str], apellido: Optional[str]) -> Optional[str]:
    """Une nombre y apellido tolerando datos faltantes."""
    partes = [parte for parte in (nombre, apellido) if parte]
    return " ".join(partes) or None


def _traducir_integrity_error(
    exc: IntegrityError, pedido_id: int, numero_comprobante: Optional[str]
) -> NoReturn:
    """Traduce una violación de integridad al error de dominio que le corresponde.

    Solo el índice parcial ``ux_venta_comercial_pedido_vigente`` delata una
    carrera entre dos altas simultáneas del mismo pedido (SQLite lo reporta por
    columna y otros motores por nombre del índice). Cualquier otra violación se
    propaga tal cual: informar "venta duplicada" cuando el problema fue otro
    (por ejemplo, el comprobante) manda a depurar para el lado equivocado.
    """
    detalle = str(getattr(exc, "orig", exc)).lower()
    if "ux_venta_comercial_pedido_vigente" in detalle or (
        "venta_comercial.pedido_id" in detalle and "unique" in detalle
    ):
        raise VentaDuplicada(pedido_id) from exc
    if "numero_comprobante" in detalle:
        raise ComprobanteDuplicado(numero_comprobante) from exc
    raise exc


def _a_venta_read(venta: VentaComercial) -> VentaRead:
    """Proyecta la venta a su contrato base."""
    return VentaRead(
        id=venta.id,
        pedido_id=venta.pedido_id,
        numero_comprobante=venta.numero_comprobante,
        fecha=venta.fecha,
        facturacion=venta.facturacion,
        estado=venta.estado,
        total=_a_decimal(venta.total),
        creada_en=venta.creada_en,
        anulada_en=venta.anulada_en,
        fecha_vencimiento=venta.fecha_vencimiento,
        cobrada_en=venta.cobrada_en,
    )


def _generar_comprobante(venta: VentaComercial) -> str:
    """Comprobante legible y único: ``V-AAAAMM-######``."""
    return f"V-{venta.fecha:%Y%m}-{venta.id:06d}"


def _persistir_venta(
    db: Session,
    *,
    pedido_id: int,
    total: Decimal,
    facturacion: Facturacion,
    estado: VentaEstado,
    pagos: list[tuple[MetodoPago, Decimal, Moneda, Optional[str]]],
    cuenta_id: Optional[int],
    fecha: Optional[datetime] = None,
    fecha_vencimiento: Optional[datetime] = None,
    cobrada_en: Optional[datetime] = None,
    motivo: str = "Registro de la venta",
) -> VentaComercial:
    """Crea la venta con su comprobante, historial y pagos. Sin commit.

    Es el camino de persistencia compartido por el alta manual (``POST
    /ventas/``) y la venta que nace al entregar un pedido. Traduce la violación
    del índice de venta vigente a ``VentaDuplicada``; el llamador decide si
    revierte la transacción.

    ``fecha`` permite que el vencimiento se calcule sobre la misma marca de
    tiempo que la venta: si se dejara al valor por defecto, la diferencia de
    microsegundos haría que ``fecha_vencimiento - fecha`` no sea el plazo exacto.
    """
    ahora = fecha or datetime.now()
    numero_comprobante: Optional[str] = None

    try:
        venta = VentaComercial(
            pedido_id=pedido_id,
            fecha=ahora,
            facturacion=facturacion,
            estado=estado,
            total=total,
            cuenta_id=cuenta_id,
            creada_en=ahora,
            fecha_vencimiento=fecha_vencimiento,
            cobrada_en=cobrada_en,
        )
        crud.crear_venta(db, venta)
        numero_comprobante = _generar_comprobante(venta)
        venta.numero_comprobante = numero_comprobante
        crud.actualizar_venta(db, venta)

        crud.crear_historial(
            db,
            VentaComercialHistorial(
                venta_id=venta.id,
                estado_anterior=None,
                estado_nuevo=estado,
                motivo=motivo,
                cuenta_id=cuenta_id,
                timestamp=ahora,
            ),
        )

        for metodo, monto, moneda, aclaracion in pagos:
            crud.crear_pago(
                db,
                PagoVenta(
                    venta_id=venta.id,
                    metodo_de_pago=metodo,
                    monto=monto,
                    moneda=moneda,
                    aclaracion=aclaracion,
                    creado_en=ahora,
                ),
            )
    except IntegrityError as exc:
        _traducir_integrity_error(exc, pedido_id, numero_comprobante)

    return venta


def _validar_plazo(plazo_dias: Optional[int]) -> int:
    """Devuelve el plazo si es uno de los admitidos; si no, ``PlazoInvalido``."""
    if plazo_dias not in PLAZOS_DE_PAGO:
        raise PlazoInvalido(plazo_dias)
    return plazo_dias


def _sumar_deuda_de_pagare(
    db: Session, pedido: Pedido, total: Decimal
) -> None:
    """Valida que el cliente sea mayorista y suma la deuda a su cuenta corriente.

    La cuenta corriente es un atributo comercial del cliente B2B, así que la
    validación se hace acá, en el alta de la venta, y no en el ajuste de saldo:
    las reversiones posteriores tienen que funcionar aunque el cliente cambie
    de tipo.
    """
    cliente = clientes_services.obtener_cliente(db, pedido.cliente_persona_id)
    if cliente.tipo != "B2B":
        raise PagareNoPermitido(pedido.cliente_persona_id)

    clientes_services.ajustar_saldo_cuenta_corriente(
        db, pedido.cliente_persona_id, total
    )


def tiene_venta_vigente(db: Session, pedido_id: int) -> bool:
    """Indica si el pedido tiene una venta ``CONFIRMADA`` o ``PENDIENTE_COBRO``.

    Lo consulta ``pedidos`` para impedir que se revierta una entrega ya vendida.
    """
    return crud.obtener_vigente_por_pedido(db, pedido_id) is not None


def _facturacion_por_defecto(db: Session, pedido: Pedido) -> Facturacion:
    """Factura A para mayoristas y consumidor final para el resto.

    El panel no elige la facturación al confirmar la entrega, así que se deduce
    del tipo de cliente con el mismo criterio que el resto del sistema.
    """
    cliente = clientes_services.obtener_cliente(db, pedido.cliente_persona_id)
    return (
        Facturacion.FACTURA_A
        if cliente.tipo == "B2B"
        else Facturacion.CONSUMIDOR_FINAL
    )


def registrar_venta_de_entrega(
    db: Session,
    pedido: Pedido,
    condicion_pago: CondicionPago,
    metodo_de_pago: Optional[MetodoPago] = None,
    plazo_dias: Optional[int] = None,
    cuenta_id: Optional[int] = None,
) -> VentaComercial:
    """Crea la venta que nace al confirmar la entrega de un pedido. Sin commit.

    Participa de la transacción de ``PedidoService.cambiar_estado_pedido``, que
    es la que valida la transición, aplica el estado ``ENTREGADO`` y cierra el
    commit. Por eso acá no se exige que el pedido ya esté entregado ni se
    revierte nada: si algo falla, el llamador hace el ``rollback`` completo.

    Al contado la venta nace ``CONFIRMADA`` con la fecha de cobro y el método
    informado. A pagaré nace ``PENDIENTE_COBRO``, con el vencimiento calculado y
    un pago ``CREDITO`` que representa la deuda, y suma esa deuda a la cuenta
    corriente del cliente mayorista.
    """
    if crud.obtener_vigente_por_pedido(db, pedido.id) is not None:
        raise VentaDuplicada(pedido.id)

    total = _a_decimal(pedido.total)
    ahora = datetime.now()

    if condicion_pago is CondicionPago.PAGARE:
        plazo = _validar_plazo(plazo_dias)
        estado = VentaEstado.PENDIENTE_COBRO
        fecha_vencimiento = ahora + timedelta(days=plazo)
        cobrada_en = None
        pagos = [(MetodoPago.CREDITO, total, Moneda.ARS, None)]
        motivo = "Venta a pagaré generada al confirmar la entrega"
        _sumar_deuda_de_pagare(db, pedido, total)
    else:
        if metodo_de_pago is None:
            raise ValueError(
                "Una venta al contado necesita el método de pago con el que se "
                "cobró."
            )
        estado = VentaEstado.CONFIRMADA
        fecha_vencimiento = None
        cobrada_en = ahora
        pagos = [(metodo_de_pago, total, Moneda.ARS, None)]
        motivo = "Venta al contado generada al confirmar la entrega"

    _consumir_stock_de_pedido(db, pedido)

    return _persistir_venta(
        db,
        pedido_id=pedido.id,
        total=total,
        facturacion=_facturacion_por_defecto(db, pedido),
        estado=estado,
        pagos=pagos,
        cuenta_id=cuenta_id,
        fecha=ahora,
        fecha_vencimiento=fecha_vencimiento,
        cobrada_en=cobrada_en,
        motivo=motivo,
    )



# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------


class VentaService:
    """Casos de uso del módulo de ventas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Registro ---------------------------------------------------------

    def registrar_venta(
        self, datos: VentaCreate, cuenta_id: Optional[int] = None
    ) -> VentaDetailRead:
        """Registra el cobro de un pedido entregado en una sola transacción."""
        pedido = crud.obtener_pedido(self.db, datos.pedido_id)
        if pedido is None:
            raise PedidoNoEncontrado(datos.pedido_id)

        estado = _estado_pedido(pedido)
        if estado != EstadoPedido.ENTREGADO.value:
            raise PedidoNoVendible(pedido.id, str(estado))

        if crud.obtener_vigente_por_pedido(self.db, pedido.id) is not None:
            raise VentaDuplicada(pedido.id)

        total = _a_decimal(pedido.total)
        pagado = sum((pago.monto for pago in datos.pagos), Decimal("0"))
        if pagado != total:
            raise PagosNoCuadran(total, pagado)

        ahora = datetime.now()
        es_pagare = datos.condicion_pago is CondicionPago.PAGARE
        if es_pagare:
            plazo = _validar_plazo(datos.plazo_dias)
            estado = VentaEstado.PENDIENTE_COBRO
            fecha_vencimiento: Optional[datetime] = ahora + timedelta(days=plazo)
            cobrada_en: Optional[datetime] = None
            _sumar_deuda_de_pagare(self.db, pedido, total)
        else:
            estado = VentaEstado.CONFIRMADA
            fecha_vencimiento = None
            cobrada_en = ahora

        pagos = [
            (pago.metodo_de_pago, pago.monto, pago.moneda, pago.aclaracion)
            for pago in datos.pagos
        ]

        try:
            _consumir_stock_de_pedido(self.db, pedido)
            venta = _persistir_venta(
                self.db,
                pedido_id=pedido.id,
                total=total,
                facturacion=datos.facturacion,
                estado=estado,
                pagos=pagos,
                cuenta_id=cuenta_id,
                fecha=ahora,
                fecha_vencimiento=fecha_vencimiento,
                cobrada_en=cobrada_en,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.obtener_venta(venta.id)

    # -- Cobro ------------------------------------------------------------

    def cobrar_venta(
        self,
        venta_id: int,
        datos: VentaCobroCreate,
        cuenta_id: Optional[int] = None,
    ) -> VentaDetailRead:
        """Marca cobrada una venta a pagaré en una sola transacción.

        Actualiza el método de los pagos que representaban la deuda en lugar de
        agregar uno nuevo: así la suma de los pagos sigue siendo igual al total
        y el arqueo por método refleja el dinero que realmente entró.
        """
        venta = crud.obtener_por_id(self.db, venta_id)
        if venta is None:
            raise VentaNoEncontrada(venta_id)
        if venta.estado != VentaEstado.PENDIENTE_COBRO:
            raise VentaNoPendienteDeCobro(venta_id, venta.estado)

        pedido = crud.obtener_pedido(self.db, venta.pedido_id)
        if pedido is None:
            raise PedidoNoEncontrado(venta.pedido_id)

        ahora = datetime.now()
        try:
            venta.estado = VentaEstado.CONFIRMADA
            venta.cobrada_en = ahora
            crud.actualizar_venta(self.db, venta)

            for pago in venta.pagos:
                pago.metodo_de_pago = datos.metodo_de_pago
                pago.aclaracion = datos.aclaracion

            crud.crear_historial(
                self.db,
                VentaComercialHistorial(
                    venta_id=venta.id,
                    estado_anterior=VentaEstado.PENDIENTE_COBRO,
                    estado_nuevo=VentaEstado.CONFIRMADA,
                    motivo="Cobro de la venta a pagaré",
                    cuenta_id=cuenta_id,
                    timestamp=ahora,
                ),
            )

            clientes_services.ajustar_saldo_cuenta_corriente(
                self.db,
                pedido.cliente_persona_id,
                -_a_decimal(venta.total),
            )

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.obtener_venta(venta_id)

    # -- Anulación --------------------------------------------------------

    def anular_venta(
        self,
        venta_id: int,
        datos: VentaAnulacionCreate,
        cuenta_id: Optional[int] = None,
    ) -> VentaDetailRead:
        """Anula la venta de forma lógica y devuelve el stock del pedido.

        Si la venta estaba ``PENDIENTE_COBRO`` revierte la deuda que había
        generado en la cuenta corriente del cliente; una venta al contado no
        toca el saldo. El stock se devuelve una sola vez por pedido.
        """
        venta = crud.obtener_por_id(self.db, venta_id)
        if venta is None:
            raise VentaNoEncontrada(venta_id)
        if venta.estado == VentaEstado.ANULADA:
            raise VentaYaAnulada(venta_id)

        pedido = crud.obtener_pedido(self.db, venta.pedido_id)
        if pedido is None:
            raise PedidoNoEncontrado(venta.pedido_id)

        ahora = datetime.now()
        try:
            estado_anterior = venta.estado
            venta.estado = VentaEstado.ANULADA
            venta.anulada_en = ahora
            crud.actualizar_venta(self.db, venta)

            crud.crear_historial(
                self.db,
                VentaComercialHistorial(
                    venta_id=venta.id,
                    estado_anterior=estado_anterior,
                    estado_nuevo=VentaEstado.ANULADA,
                    motivo=datos.motivo,
                    cuenta_id=cuenta_id,
                    timestamp=ahora,
                ),
            )

            if estado_anterior == VentaEstado.PENDIENTE_COBRO:
                clientes_services.ajustar_saldo_cuenta_corriente(
                    self.db,
                    pedido.cliente_persona_id,
                    -_a_decimal(venta.total),
                )

            _restaurar_stock_de_pedido(self.db, pedido)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.obtener_venta(venta_id)

    # -- Consultas --------------------------------------------------------

    def obtener_venta(self, venta_id: int) -> VentaDetailRead:
        """Detalle de una venta por id."""
        venta = crud.obtener_por_id(self.db, venta_id)
        if venta is None:
            raise VentaNoEncontrada(venta_id)
        return self._a_detalle(venta)

    def obtener_por_comprobante(self, numero_comprobante: str) -> VentaDetailRead:
        """Detalle de una venta por número de comprobante."""
        venta = crud.obtener_por_comprobante(self.db, numero_comprobante)
        if venta is None:
            raise VentaNoEncontrada(numero_comprobante)
        return self._a_detalle(venta)

    def listar_ventas(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        estado: Optional[VentaEstado] = None,
        metodo_de_pago: Optional[str] = None,
        cliente_persona_id: Optional[int] = None,
        q: Optional[str] = None,
    ) -> list[VentaListRead]:
        """Listado filtrable y paginado."""
        filas = crud.listar(
            self.db,
            skip=skip,
            limit=limit,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=estado,
            metodo_de_pago=metodo_de_pago,
            cliente_persona_id=cliente_persona_id,
            q=q,
        )
        metodos = crud.metodos_por_venta(self.db, [fila[0].id for fila in filas])

        return [
            VentaListRead(
                **_a_venta_read(venta).model_dump(),
                cliente_persona_id=persona_id,
                cliente_nombre=_nombre_completo(nombre, apellido),
                metodos_de_pago=metodos.get(venta.id, []),
            )
            for venta, persona_id, nombre, apellido in filas
        ]

    def resumen_arqueo(
        self,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> VentaResumenRead:
        """Arqueo de caja del rango, sin las ventas anuladas."""
        cantidad, total = crud.totales_generales(
            self.db, fecha_desde, fecha_hasta
        )
        por_metodo = [
            ResumenPorMetodo(metodo_de_pago=metodo, monto=monto)
            for metodo, monto in crud.totales_por_metodo(
                self.db, fecha_desde, fecha_hasta
            )
        ]
        return VentaResumenRead(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            cantidad_ventas=cantidad,
            total_facturado=total,
            totales_por_metodo=por_metodo,
        )

    def resumen_mensual(
        self,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> list[VentaResumenMensualRead]:
        """Serie mensual de ventas confirmadas, de la más reciente a la más vieja."""
        filas = crud.resumen_por_mes(self.db, fecha_desde, fecha_hasta)

        metodos_por_mes: dict[str, list[ResumenPorMetodo]] = {}
        for mes, metodo, monto in crud.totales_por_mes_y_metodo(
            self.db, fecha_desde, fecha_hasta
        ):
            metodos_por_mes.setdefault(mes, []).append(
                ResumenPorMetodo(metodo_de_pago=metodo, monto=monto)
            )

        return [
            VentaResumenMensualRead(
                mes=mes,
                cantidad_ventas=cantidad,
                total_facturado=total,
                totales_por_metodo=metodos_por_mes.get(mes, []),
            )
            for mes, cantidad, total in filas
        ]

    def cobranza_mensual(
        self,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> list[VentaCobranzaMensualRead]:
        """Serie de cobranza por mes de cobro, de la más reciente a la más vieja.

        Es el complemento del resumen de facturación: mide el dinero que entró,
        agrupado por ``cobrada_en`` y no por la fecha de la venta.
        """
        filas = crud.cobranza_por_mes(self.db, fecha_desde, fecha_hasta)

        metodos_por_mes: dict[str, list[ResumenPorMetodo]] = {}
        for mes, metodo, monto in crud.totales_de_cobranza_por_metodo(
            self.db, fecha_desde, fecha_hasta
        ):
            metodos_por_mes.setdefault(mes, []).append(
                ResumenPorMetodo(metodo_de_pago=metodo, monto=monto)
            )

        return [
            VentaCobranzaMensualRead(
                mes=mes,
                cantidad_cobros=cantidad,
                total_cobrado=total,
                totales_por_metodo=metodos_por_mes.get(mes, []),
            )
            for mes, cantidad, total in filas
        ]

    def por_cobrar(self) -> VentaPorCobrarRead:
        """Saldo por cobrar: pendientes ordenadas por vencimiento y su total.

        La marca de vencida se calcula acá con ``datetime.now()`` para que el
        contrato no dependa de la zona horaria con la que SQLite guardó las
        fechas. Un pendiente sin vencimiento (dato heredado) no se marca vencido.
        """
        ahora = datetime.now()
        items: list[VentaPorCobrarItemRead] = []

        for venta, persona_id, nombre, apellido in crud.pendientes_de_cobro(self.db):
            vencimiento = venta.fecha_vencimiento
            items.append(
                VentaPorCobrarItemRead(
                    venta_id=venta.id,
                    pedido_id=venta.pedido_id,
                    numero_comprobante=venta.numero_comprobante,
                    cliente_persona_id=persona_id,
                    cliente_nombre=_nombre_completo(nombre, apellido),
                    fecha=venta.fecha,
                    fecha_vencimiento=vencimiento,
                    total=_a_decimal(venta.total),
                    vencida=vencimiento is not None and vencimiento < ahora,
                )
            )

        return VentaPorCobrarRead(
            items=items,
            total_por_cobrar=sum((item.total for item in items), Decimal("0")),
            cantidad_vencidas=sum(1 for item in items if item.vencida),
        )

    # -- Internos ---------------------------------------------------------

    def _a_detalle(self, venta: VentaComercial) -> VentaDetailRead:
        """Arma el detalle leyendo el pedido y el cliente en modo lectura."""
        pedido = crud.obtener_pedido(self.db, venta.pedido_id)
        persona = (
            crud.obtener_persona(self.db, pedido.cliente_persona_id)
            if pedido is not None
            else None
        )

        return VentaDetailRead(
            **_a_venta_read(venta).model_dump(),
            cuenta_id=venta.cuenta_id,
            cliente_persona_id=pedido.cliente_persona_id if pedido else None,
            cliente_nombre=(
                _nombre_completo(persona.nombre, persona.apellido)
                if persona
                else None
            ),
            pedido_estado=_estado_pedido(pedido) if pedido is not None else None,
            pedido_total=_a_decimal(pedido.total) if pedido is not None else None,
            pagos=[
                PagoVentaRead(
                    metodo_de_pago=pago.metodo_de_pago,
                    monto=_a_decimal(pago.monto),
                    moneda=pago.moneda,
                    aclaracion=pago.aclaracion,
                )
                for pago in venta.pagos
            ],
            historial=[
                VentaHistorialRead(
                    estado_anterior=entrada.estado_anterior,
                    estado_nuevo=entrada.estado_nuevo,
                    motivo=entrada.motivo,
                    cuenta_id=entrada.cuenta_id,
                    timestamp=entrada.timestamp,
                )
                for entrada in venta.historial
            ],
        )
