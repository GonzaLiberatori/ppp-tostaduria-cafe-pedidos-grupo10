"""Reglas de negocio del módulo de envíos programados.

La generación diaria es idempotente por ``(cliente_id, fecha_entrega)``:

1. ``entrega_programada`` tiene una restricción ``UNIQUE`` para esa pareja.
2. El pedido se crea con una ``idempotency_key`` determinística derivada de la
   misma pareja, así que un reintento devuelve el pedido existente sin volver a
   descontar stock.
3. La venta a pagaré se crea al confirmar la entrega, dentro del servicio de
   pedidos, y suma la deuda a la cuenta corriente del cliente B2B.

Un error en un cliente no cancela la corrida de los demás: cada cliente se
procesa y se confirma (o se marca ``ERROR``) por separado.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.modules.clientes import services as clientes_services
from app.modules.envios import crud, models, schemas
from app.modules.pedidos import schemas as pedidos_schemas
from app.modules.pedidos.services import PedidoService
from app.modules.ventas.schemas import CondicionPago

DIAS_DE_LA_SEMANA = schemas.DIAS_DE_LA_SEMANA


class SuscripcionNoEncontrada(Exception):
    """La suscripción solicitada no existe."""

    def __init__(self, suscripcion_id: int) -> None:
        super().__init__(f"No existe la suscripción {suscripcion_id}.")


class ClienteNoHabilitado(Exception):
    """Solo los clientes B2B con cuenta corriente pueden programar envíos."""

    def __init__(self, cliente_id: int) -> None:
        super().__init__(
            f"El cliente {cliente_id} no es B2B: no tiene cuenta corriente "
            "para ventas programadas."
        )


class ProductoInvalido(Exception):
    """El producto configurado no existe en el catálogo."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)


def _nombre_cliente(cliente: object) -> str:
    """Devuelve el nombre visible del cliente."""
    persona = getattr(cliente, "persona", None)
    if persona is None:
        return "Cliente"
    return f"{persona.nombre} {persona.apellido}".strip()


def _variedad(suscripcion: models.SuscripcionEnvio) -> str:
    """Nombre del producto configurado en la suscripción."""
    if suscripcion.tipo_de_cafe is not None:
        return suscripcion.tipo_de_cafe.variedad
    if suscripcion.blend is not None:
        return suscripcion.blend.nombre
    return "Producto"


def _a_suscripcion_read(
    suscripcion: models.SuscripcionEnvio,
) -> schemas.SuscripcionRead:
    """Pasa el ORM al contrato plano del frontend."""
    return schemas.SuscripcionRead(
        id=suscripcion.id,
        clienteId=str(suscripcion.cliente_id),
        clienteNombre=_nombre_cliente(suscripcion.cliente),
        producto=suscripcion.producto,
        productoId=suscripcion.producto_id,
        variedad=_variedad(suscripcion),
        cantidadKg=float(suscripcion.cantidad_kg),
        diaSemana=suscripcion.dia_semana,
        diaNombre=DIAS_DE_LA_SEMANA[suscripcion.dia_semana],
        plazoDias=suscripcion.plazo_dias,
        activa=bool(suscripcion.activa),
        fechaInicio=suscripcion.fecha_inicio,
        observaciones=suscripcion.observaciones or "",
    )


def _a_entrega_read(
    entrega: models.EntregaProgramada,
) -> schemas.EntregaRead:
    """Pasa la entrega al contrato plano del frontend."""
    return schemas.EntregaRead(
        id=entrega.id,
        clienteId=str(entrega.cliente_id),
        clienteNombre=_nombre_cliente(entrega.cliente),
        fechaEntrega=entrega.fecha_entrega,
        estado=getattr(entrega.estado, "value", entrega.estado),
        pedidoId=str(entrega.pedido_id) if entrega.pedido_id else None,
        generadaEn=entrega.generada_en,
        error=entrega.error,
    )


def _validar_producto(
    db: Session, tipo_de_cafe_id: Optional[int], blend_id: Optional[int]
) -> None:
    """Valida que el producto configurado exista en el catálogo."""
    from app.modules.inventario.models import Blend, TipoDeCafe

    if tipo_de_cafe_id is not None:
        if db.get(TipoDeCafe, tipo_de_cafe_id) is None:
            raise ProductoInvalido(
                f"No existe el tipo de café {tipo_de_cafe_id}."
            )
    elif blend_id is not None:
        if db.get(Blend, blend_id) is None:
            raise ProductoInvalido(f"No existe el blend {blend_id}.")


class EnvioService:
    """Casos de uso de suscripciones y generación diaria de despachos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Suscripciones
    # ------------------------------------------------------------------
    def crear_suscripcion(
        self, datos: schemas.SuscripcionCreate
    ) -> schemas.SuscripcionRead:
        """Da de alta una suscripción B2B en una sola transacción."""
        try:
            cliente_id = int(datos.clienteId)
        except (TypeError, ValueError):
            raise ProductoInvalido("Cliente inválido.") from None

        cliente = clientes_services.obtener_cliente(self.db, cliente_id)
        if cliente.tipo != "B2B":
            raise ClienteNoHabilitado(cliente_id)

        _validar_producto(self.db, datos.tipoDeCafeId, datos.blendId)

        try:
            suscripcion = crud.crear_suscripcion(
                self.db,
                {
                    "cliente_id": cliente_id,
                    "tipo_de_cafe_id": datos.tipoDeCafeId,
                    "blend_id": datos.blendId,
                    "cantidad_kg": datos.cantidadKg,
                    "dia_semana": datos.diaSemana,
                    "plazo_dias": datos.plazoDias,
                    "fecha_inicio": datos.fechaInicio or date.today(),
                    "observaciones": datos.observaciones or None,
                    "activa": True,
                },
            )
            self.db.commit()
            self.db.refresh(suscripcion)
        except Exception:
            self.db.rollback()
            raise

        return _a_suscripcion_read(suscripcion)

    def listar_suscripciones(
        self,
        cliente_id: Optional[int] = None,
        solo_activas: Optional[bool] = None,
    ) -> List[schemas.SuscripcionRead]:
        """Lista las suscripciones visibles para el usuario."""
        return [
            _a_suscripcion_read(suscripcion)
            for suscripcion in crud.listar_suscripciones(
                self.db, cliente_id=cliente_id, solo_activas=solo_activas
            )
        ]

    def actualizar_suscripcion(
        self, suscripcion_id: int, datos: schemas.SuscripcionUpdate
    ) -> schemas.SuscripcionRead:
        """Aplica los cambios enviados y confirma en una transacción."""
        suscripcion = crud.obtener_suscripcion(self.db, suscripcion_id)
        if suscripcion is None:
            raise SuscripcionNoEncontrada(suscripcion_id)

        try:
            if datos.cantidadKg is not None:
                suscripcion.cantidad_kg = datos.cantidadKg
            if datos.diaSemana is not None:
                suscripcion.dia_semana = datos.diaSemana
            if datos.plazoDias is not None:
                suscripcion.plazo_dias = datos.plazoDias
            if datos.activa is not None:
                suscripcion.activa = datos.activa
            if datos.observaciones is not None:
                suscripcion.observaciones = datos.observaciones or None

            self.db.commit()
            self.db.refresh(suscripcion)
        except Exception:
            self.db.rollback()
            raise

        return _a_suscripcion_read(suscripcion)

    def desactivar_suscripcion(self, suscripcion_id: int) -> None:
        """Baja lógica: deja de generar entregas sin borrar el historial."""
        suscripcion = crud.obtener_suscripcion(self.db, suscripcion_id)
        if suscripcion is None:
            raise SuscripcionNoEncontrada(suscripcion_id)

        try:
            suscripcion.activa = False
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # Generación diaria
    # ------------------------------------------------------------------
    def listar_entregas(
        self,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        cliente_id: Optional[int] = None,
    ) -> List[schemas.EntregaRead]:
        """Lista las entregas programadas en el rango indicado."""
        return [
            _a_entrega_read(entrega)
            for entrega in crud.listar_entregas(
                self.db, desde=desde, hasta=hasta, cliente_id=cliente_id
            )
        ]

    def generar_del_dia(self, fecha: Optional[date] = None) -> schemas.GeneracionResultadoRead:
        """Genera los pedidos de todas las suscripciones del día.

        Idempotente: si la entrega ya está ``GENERADA`` o ``CANCELADA`` se
        omite. Si quedó en ``ERROR``, se reintenta reutilizando el pedido que
        ya exista con la misma clave determinística.
        """
        fecha = fecha or date.today()
        suscripciones = crud.suscripciones_del_dia(self.db, fecha)

        por_cliente: Dict[int, List[models.SuscripcionEnvio]] = {}
        for suscripcion in suscripciones:
            por_cliente.setdefault(suscripcion.cliente_id, []).append(suscripcion)

        detalle: List[schemas.GeneracionDetalle] = []

        for cliente_id, grupo in por_cliente.items():
            nombre = _nombre_cliente(grupo[0].cliente)
            try:
                resultado = self._generar_cliente(cliente_id, fecha, grupo)
            except Exception as exc:
                self.db.rollback()
                resultado = self._marcar_error(cliente_id, fecha, nombre, exc)
            detalle.append(resultado)

        generadas = sum(1 for item in detalle if item.estado == "GENERADA")
        omitidas = sum(1 for item in detalle if item.estado == "OMITIDA")
        errores = sum(1 for item in detalle if item.estado == "ERROR")

        return schemas.GeneracionResultadoRead(
            fecha=fecha,
            procesadas=len(detalle),
            generadas=generadas,
            omitidas=omitidas,
            errores=errores,
            detalle=detalle,
        )

    def _generar_cliente(
        self,
        cliente_id: int,
        fecha: date,
        suscripciones: List[models.SuscripcionEnvio],
    ) -> schemas.GeneracionDetalle:
        """Genera el pedido de un cliente para una fecha."""
        entrega = crud.obtener_entrega(self.db, cliente_id, fecha)
        if entrega is not None and entrega.estado in (
            models.EstadoEntrega.GENERADA,
            models.EstadoEntrega.CANCELADA,
        ):
            return schemas.GeneracionDetalle(
                clienteId=str(cliente_id),
                clienteNombre=_nombre_cliente(entrega.cliente),
                estado="OMITIDA",
                pedidoId=str(entrega.pedido_id) if entrega.pedido_id else None,
                mensaje=f"La entrega ya está {entrega.estado.value}.",
            )

        if entrega is None:
            entrega = crud.crear_entrega(
                self.db,
                {
                    "cliente_id": cliente_id,
                    "fecha_entrega": fecha,
                    "estado": models.EstadoEntrega.PROGRAMADA,
                    "suscripcion_id": suscripciones[0].id,
                },
            )
        else:
            entrega.estado = models.EstadoEntrega.PROGRAMADA
            entrega.error = None

        detalles = [
            pedidos_schemas.DetallePedidoCreate(
                cantidad_kg=suscripcion.cantidad_kg,
                tipo_de_cafe_id=suscripcion.tipo_de_cafe_id,
                blend_id=suscripcion.blend_id,
            )
            for suscripcion in suscripciones
        ]

        pedido_in = pedidos_schemas.PedidoCreate(
            fecha=datetime.combine(fecha, datetime.min.time()),
            metodo_de_despacho="Envio propio",
            estado="PENDIENTE",
            idempotency_key=self._clave_idempotencia(cliente_id, fecha),
            medio_contacto="Email",
            observaciones="Generado automáticamente por envío programado",
            cliente_persona_id=cliente_id,
            empleado_persona_id=None,
            detalles=detalles,
        )

        servicio_pedidos = PedidoService(self.db)
        pedido = servicio_pedidos.crear_pedido_completo(pedido_in)

        plazo = suscripciones[0].plazo_dias or 30
        if pedido.estado == "PENDIENTE":
            servicio_pedidos.cambiar_estado_pedido(pedido.id, "LISTO")
        if pedido.estado == "LISTO":
            servicio_pedidos.cambiar_estado_pedido(
                pedido.id,
                "ENTREGADO",
                condicion_pago=CondicionPago.PAGARE,
                plazo_dias=plazo,
            )

        entrega = crud.obtener_entrega(self.db, cliente_id, fecha)
        if entrega is None:
            raise ValueError("No se pudo registrar la entrega programada.")

        entrega.pedido_id = pedido.id
        entrega.estado = models.EstadoEntrega.GENERADA
        entrega.generada_en = datetime.utcnow()
        entrega.error = None
        self.db.commit()

        return schemas.GeneracionDetalle(
            clienteId=str(cliente_id),
            clienteNombre=_nombre_cliente(entrega.cliente),
            estado="GENERADA",
            pedidoId=str(pedido.id),
            mensaje=f"Pedido entregado a pagaré con vencimiento a {plazo} días.",
        )

    def _marcar_error(
        self,
        cliente_id: int,
        fecha: date,
        nombre: str,
        exc: Exception,
    ) -> schemas.GeneracionDetalle:
        """Registra el error de un cliente sin abortar la corrida.

        Si otro proceso ya generó la entrega (carrera entre workers), no se
        pisa el resultado: se informa ``OMITIDA`` en lugar de marcar ``ERROR``.
        """
        mensaje = str(exc)[:255]
        try:
            entrega = crud.obtener_entrega(self.db, cliente_id, fecha)
            if entrega is not None and entrega.estado in (
                models.EstadoEntrega.GENERADA,
                models.EstadoEntrega.CANCELADA,
            ):
                return schemas.GeneracionDetalle(
                    clienteId=str(cliente_id),
                    clienteNombre=nombre,
                    estado="OMITIDA",
                    pedidoId=(
                        str(entrega.pedido_id) if entrega.pedido_id else None
                    ),
                    mensaje=(
                        "Otro proceso ya generó la entrega para esta fecha."
                    ),
                )

            if entrega is None:
                entrega = crud.crear_entrega(
                    self.db,
                    {
                        "cliente_id": cliente_id,
                        "fecha_entrega": fecha,
                        "estado": models.EstadoEntrega.ERROR,
                        "error": mensaje,
                    },
                )
            else:
                entrega.estado = models.EstadoEntrega.ERROR
                entrega.error = mensaje
            self.db.commit()
        except Exception:
            self.db.rollback()

        return schemas.GeneracionDetalle(
            clienteId=str(cliente_id),
            clienteNombre=nombre,
            estado="ERROR",
            mensaje=mensaje,
        )

    @staticmethod
    def _clave_idempotencia(cliente_id: int, fecha: date) -> str:
        """Clave determinística por cliente y fecha (máx. 64 caracteres)."""
        return f"envio-{cliente_id}-{fecha.isoformat()}"

    # ------------------------------------------------------------------
    # Hoja de ruta
    # ------------------------------------------------------------------
    def hoja_de_ruta(self, fecha: Optional[date] = None) -> List[schemas.HojaDeRutaRead]:
        """Devuelve los pedidos generados para el reparto de una fecha."""
        from app.modules.pedidos.models import DetallePedido, Pedido
        from app.modules.ventas.models import VentaComercial

        fecha = fecha or date.today()
        pedidos = (
            self.db.query(Pedido)
            .join(
                models.EntregaProgramada,
                models.EntregaProgramada.pedido_id == Pedido.id,
            )
            .filter(
                models.EntregaProgramada.fecha_entrega == fecha,
                models.EntregaProgramada.estado == models.EstadoEntrega.GENERADA,
            )
            .order_by(Pedido.id)
            .all()
        )

        resultado: List[schemas.HojaDeRutaRead] = []
        for pedido in pedidos:
            cliente = pedido.cliente
            persona = cliente.persona if cliente is not None else None
            items: List[schemas.HojaDeRutaItemRead] = []

            for detalle in pedido.detalles:
                tipo = detalle.tipo_de_cafe
                blend = detalle.blend
                if tipo is not None:
                    stock_id = f"tc-{tipo.id}-TOSTADO"
                    variedad = tipo.variedad
                elif blend is not None:
                    stock_id = f"bl-{blend.id}-TOSTADO"
                    variedad = blend.nombre
                else:
                    stock_id = "desconocido"
                    variedad = "Producto"

                kilos = Decimal(detalle.cantidad_kg)
                subtotal = Decimal(detalle.subtotal)
                items.append(
                    schemas.HojaDeRutaItemRead(
                        stockId=stock_id,
                        variedad=variedad,
                        kilos=float(kilos),
                        precioKg=float(subtotal / kilos) if kilos else 0.0,
                        subtotal=float(subtotal),
                    )
                )

            venta = (
                self.db.query(VentaComercial)
                .filter(VentaComercial.pedido_id == pedido.id)
                .order_by(VentaComercial.id.desc())
                .first()
            )
            condicion = "PAGARE" if venta and venta.fecha_vencimiento else "CONTADO"

            resultado.append(
                schemas.HojaDeRutaRead(
                    pedidoId=str(pedido.id),
                    clienteId=str(pedido.cliente_persona_id),
                    clienteNombre=(
                        f"{persona.nombre} {persona.apellido}".strip()
                        if persona is not None
                        else "Cliente"
                    ),
                    direccion=(
                        cliente.direccion_de_entrega
                        if cliente is not None and cliente.direccion_de_entrega
                        else ""
                    ),
                    telefono=persona.telefono if persona is not None else "",
                    estado=getattr(pedido.estado, "value", pedido.estado),
                    condicionPago=condicion,
                    total=float(pedido.total),
                    items=items,
                )
            )

        return resultado
