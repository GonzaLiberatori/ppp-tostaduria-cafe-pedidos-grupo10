"""Reglas de negocio y frontera transaccional del módulo de ventas.

``registrar_venta`` y ``anular_venta`` son los únicos puntos que hacen
``commit``. Ninguna operación de este módulo modifica stock ni el saldo de la
cuenta corriente: eso sigue siendo responsabilidad del módulo de pedidos.
"""

from datetime import datetime
from decimal import Decimal
from typing import NoReturn, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.pedidos.models import EstadoPedido
from app.modules.ventas import crud
from app.modules.ventas.models import (
    PagoVenta,
    VentaComercial,
    VentaComercialHistorial,
    VentaEstado,
)
from app.modules.ventas.schemas import (
    PagoVentaRead,
    ResumenPorMetodo,
    VentaAnulacionCreate,
    VentaCreate,
    VentaDetailRead,
    VentaHistorialRead,
    VentaListRead,
    VentaRead,
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


class ComprobanteDuplicado(Exception):
    """El número de comprobante generado ya estaba asignado a otra venta."""

    def __init__(self, numero_comprobante: Optional[str]) -> None:
        self.numero_comprobante = numero_comprobante
        super().__init__(
            f"El número de comprobante {numero_comprobante} ya está en uso."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _a_decimal(valor: object) -> Decimal:
    """Normaliza a Decimal los valores que SQLite devuelve como número."""
    return Decimal(str(valor or 0))


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
        numero_comprobante: Optional[str] = None
        try:
            venta = VentaComercial(
                pedido_id=pedido.id,
                fecha=ahora,
                facturacion=datos.facturacion,
                estado=VentaEstado.CONFIRMADA,
                total=total,
                cuenta_id=cuenta_id,
                creada_en=ahora,
            )
            crud.crear_venta(self.db, venta)
            numero_comprobante = self._generar_comprobante(venta)
            venta.numero_comprobante = numero_comprobante
            crud.actualizar_venta(self.db, venta)

            crud.crear_historial(
                self.db,
                VentaComercialHistorial(
                    venta_id=venta.id,
                    estado_anterior=None,
                    estado_nuevo=VentaEstado.CONFIRMADA,
                    motivo="Registro de la venta",
                    cuenta_id=cuenta_id,
                    timestamp=ahora,
                ),
            )

            for pago in datos.pagos:
                crud.crear_pago(
                    self.db,
                    PagoVenta(
                        venta_id=venta.id,
                        metodo_de_pago=pago.metodo_de_pago,
                        monto=pago.monto,
                        moneda=pago.moneda,
                        aclaracion=pago.aclaracion,
                        creado_en=ahora,
                    ),
                )

            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            _traducir_integrity_error(exc, pedido.id, numero_comprobante)
        except Exception:
            self.db.rollback()
            raise

        return self.obtener_venta(venta.id)

    # -- Anulación --------------------------------------------------------

    def anular_venta(
        self,
        venta_id: int,
        datos: VentaAnulacionCreate,
        cuenta_id: Optional[int] = None,
    ) -> VentaDetailRead:
        """Anula la venta de forma lógica, sin tocar stock ni cuenta corriente."""
        venta = crud.obtener_por_id(self.db, venta_id)
        if venta is None:
            raise VentaNoEncontrada(venta_id)
        if venta.estado == VentaEstado.ANULADA:
            raise VentaYaAnulada(venta_id)

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

    # -- Internos ---------------------------------------------------------

    def _generar_comprobante(self, venta: VentaComercial) -> str:
        """Comprobante legible y único: ``V-AAAAMM-######``."""
        return f"V-{venta.fecha:%Y%m}-{venta.id:06d}"

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
