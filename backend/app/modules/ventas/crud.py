"""Acceso a datos del módulo de ventas. Consultas puras, sin commits."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.modules.clientes.models import Persona
from app.modules.pedidos.models import MetodoPago, Pedido
from app.modules.ventas.models import (
    PagoVenta,
    VentaComercial,
    VentaComercialHistorial,
    VentaEstado,
)


# ---------------------------------------------------------------------------
# Escritura (siempre dentro de la transacción que abre el servicio)
# ---------------------------------------------------------------------------


def crear_venta(db: Session, venta: VentaComercial) -> VentaComercial:
    """Agrega la venta a la sesión y hace flush para obtener el id."""
    db.add(venta)
    db.flush()
    return venta


def actualizar_venta(db: Session, venta: VentaComercial) -> VentaComercial:
    """Aplica los cambios pendientes de la venta y hace flush."""
    db.flush()
    return venta


def crear_pago(db: Session, pago: PagoVenta) -> PagoVenta:
    """Agrega un pago a la sesión y hace flush."""
    db.add(pago)
    db.flush()
    return pago


def crear_historial(
    db: Session, historial: VentaComercialHistorial
) -> VentaComercialHistorial:
    """Agrega una entrada de auditoría a la sesión y hace flush."""
    db.add(historial)
    db.flush()
    return historial


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def obtener_por_id(db: Session, venta_id: int) -> Optional[VentaComercial]:
    """Devuelve la venta con ese id, o ``None``."""
    return db.get(VentaComercial, venta_id)


def obtener_por_comprobante(
    db: Session, numero_comprobante: str
) -> Optional[VentaComercial]:
    """Devuelve la venta con ese comprobante, o ``None``."""
    return (
        db.query(VentaComercial)
        .filter(VentaComercial.numero_comprobante == numero_comprobante)
        .first()
    )


def obtener_vigente_por_pedido(
    db: Session, pedido_id: int
) -> Optional[VentaComercial]:
    """Devuelve la venta CONFIRMADA del pedido, o ``None``."""
    return (
        db.query(VentaComercial)
        .filter(
            VentaComercial.pedido_id == pedido_id,
            VentaComercial.estado == VentaEstado.CONFIRMADA,
        )
        .first()
    )


def obtener_pedido(db: Session, pedido_id: int) -> Optional[Pedido]:
    """Lee el pedido asociado. El módulo de ventas nunca lo modifica."""
    return db.get(Pedido, pedido_id)


def obtener_persona(db: Session, persona_id: int) -> Optional[Persona]:
    """Lee la persona del cliente para mostrar el nombre en el detalle."""
    return db.get(Persona, persona_id)


def _filtrar_por_fechas(
    consulta: Query,
    fecha_desde: Optional[datetime],
    fecha_hasta: Optional[datetime],
) -> Query:
    """Aplica el rango de fechas sobre la fecha de la venta."""
    if fecha_desde is not None:
        consulta = consulta.filter(VentaComercial.fecha >= fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.filter(VentaComercial.fecha <= fecha_hasta)
    return consulta


def listar(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado: Optional[VentaEstado] = None,
    metodo_de_pago: Optional[str] = None,
    cliente_persona_id: Optional[int] = None,
    q: Optional[str] = None,
) -> list[tuple[VentaComercial, Optional[int], Optional[str], Optional[str]]]:
    """Lista ventas con filtros y paginación, de la más reciente a la más vieja.

    Devuelve tuplas ``(venta, cliente_persona_id, nombre, apellido)``. Los
    joins son externos para que una venta cuyo pedido o cliente ya no exista
    siga apareciendo en el listado, igual que en el detalle, en lugar de
    desaparecer sin aviso.
    """
    consulta = (
        db.query(
            VentaComercial,
            Pedido.cliente_persona_id,
            Persona.nombre,
            Persona.apellido,
        )
        .outerjoin(Pedido, Pedido.id == VentaComercial.pedido_id)
        .outerjoin(Persona, Persona.id == Pedido.cliente_persona_id)
    )

    consulta = _filtrar_por_fechas(consulta, fecha_desde, fecha_hasta)

    if estado is not None:
        consulta = consulta.filter(VentaComercial.estado == estado)
    if cliente_persona_id is not None:
        consulta = consulta.filter(Pedido.cliente_persona_id == cliente_persona_id)
    if metodo_de_pago is not None:
        consulta = consulta.filter(
            VentaComercial.pagos.any(PagoVenta.metodo_de_pago == metodo_de_pago)
        )
    if q:
        patron = f"%{q}%"
        consulta = consulta.filter(
            or_(
                VentaComercial.numero_comprobante.ilike(patron),
                Persona.nombre.ilike(patron),
                Persona.apellido.ilike(patron),
            )
        )

    consulta = consulta.order_by(
        VentaComercial.fecha.desc(), VentaComercial.id.desc()
    )
    return consulta.offset(skip).limit(limit).all()


def metodos_por_venta(
    db: Session, venta_ids: list[int]
) -> dict[int, list[MetodoPago]]:
    """Devuelve los métodos de pago usados por cada venta."""
    if not venta_ids:
        return {}

    filas = (
        db.query(PagoVenta.venta_id, PagoVenta.metodo_de_pago)
        .filter(PagoVenta.venta_id.in_(venta_ids))
        .order_by(PagoVenta.id)
        .all()
    )

    metodos: dict[int, list[MetodoPago]] = {}
    for venta_id, metodo in filas:
        metodos.setdefault(venta_id, []).append(metodo)
    return metodos


def totales_generales(
    db: Session,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
) -> tuple[int, Decimal]:
    """Cantidad de ventas vigentes y total facturado del rango."""
    consulta = db.query(
        func.count(VentaComercial.id),
        func.coalesce(func.sum(VentaComercial.total), 0),
    ).filter(VentaComercial.estado == VentaEstado.CONFIRMADA)
    consulta = _filtrar_por_fechas(consulta, fecha_desde, fecha_hasta)

    cantidad, total = consulta.one()
    return int(cantidad or 0), Decimal(str(total or 0))


def totales_por_metodo(
    db: Session,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
) -> list[tuple[str, Decimal]]:
    """Total cobrado por método de pago, excluyendo las ventas anuladas."""
    consulta = (
        db.query(
            PagoVenta.metodo_de_pago,
            func.coalesce(func.sum(PagoVenta.monto), 0),
        )
        .join(VentaComercial, VentaComercial.id == PagoVenta.venta_id)
        .filter(VentaComercial.estado == VentaEstado.CONFIRMADA)
    )
    consulta = _filtrar_por_fechas(consulta, fecha_desde, fecha_hasta)

    filas = consulta.group_by(PagoVenta.metodo_de_pago).all()
    return [(metodo, Decimal(str(total or 0))) for metodo, total in filas]
