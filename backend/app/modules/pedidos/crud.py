from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Tuple
from hashlib import sha256
import json

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session, selectinload

from app.modules.pedidos.models import Pedido, PedidoItem, PedidoEstadoHistorial, EstadoPedidoEnum
from app.modules.pedidos.schemas import PedidoCreate, PedidoUpdate, PedidoItemCreate


def generate_idempotency_key(cliente_id: int, items: List[PedidoItemCreate], fecha: date) -> str:
    """Genera una clave de idempotencia única basada en cliente, items y fecha."""
    items_json = json.dumps(
        [
            {"stock_id": item.stock_id, "kilos": str(item.kilos), "precio_kg": str(item.precio_kg)}
            for item in items
        ],
        sort_keys=True,
    )
    data = f"{cliente_id}|{items_json}|{fecha.isoformat()}"
    return sha256(data.encode()).hexdigest()


def create_pedido(
    db: Session,
    *,
    cliente_id: int,
    estado: EstadoPedidoEnum,
    medio_contacto: str,
    observaciones: Optional[str],
    items: List[dict],
    total: Decimal,
    idempotency_key: str,
) -> Pedido:
    """Crea un pedido con sus items."""
    pedido = Pedido(
        cliente_id=cliente_id,
        estado=estado,
        medio_contacto=medio_contacto,
        observaciones=observaciones,
        total=total,
        idempotency_key=idempotency_key,
    )
    db.add(pedido)
    db.flush()

    for item_data in items:
        item = PedidoItem(
            pedido_id=pedido.id,
            stock_id=item_data["stock_id"],
            variedad=item_data["variedad"],
            kilos=item_data["kilos"],
            precio_kg=item_data["precio_kg"],
            subtotal=item_data["kilos"] * item_data["precio_kg"],
        )
        db.add(item)

    db.flush()
    return pedido


def get_pedido(db: Session, pedido_id: int) -> Optional[Pedido]:
    """Obtiene un pedido por ID con sus items."""
    stmt = (
        select(Pedido)
        .options(selectinload(Pedido.items))
        .where(Pedido.id == pedido_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_pedido_by_idempotency_key(db: Session, idempotency_key: str) -> Optional[Pedido]:
    """Obtiene un pedido por su clave de idempotencia."""
    stmt = select(Pedido).where(Pedido.idempotency_key == idempotency_key)
    return db.execute(stmt).scalar_one_or_none()


def get_pedidos_con_filtros(
    db: Session,
    *,
    estado: Optional[EstadoPedidoEnum] = None,
    cliente_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Pedido], int]:
    """Lista pedidos con filtros y paginación."""
    stmt = (
        select(Pedido)
        .options(selectinload(Pedido.items))
        .order_by(desc(Pedido.fecha))
    )

    conditions = []
    if estado:
        conditions.append(Pedido.estado == estado)
    if cliente_id:
        conditions.append(Pedido.cliente_id == cliente_id)
    if fecha_desde:
        conditions.append(func.date(Pedido.fecha) >= fecha_desde)
    if fecha_hasta:
        conditions.append(func.date(Pedido.fecha) <= fecha_hasta)
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Pedido.medio_contacto.ilike(search_term),
                Pedido.observaciones.ilike(search_term),
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    pedidos = db.execute(stmt).scalars().all()
    return list(pedidos), total


def update_pedido(
    db: Session,
    *,
    pedido: Pedido,
    medio_contacto: Optional[str] = None,
    observaciones: Optional[str] = None,
    estado: Optional[EstadoPedidoEnum] = None,
) -> Pedido:
    """Actualiza campos editables de un pedido."""
    if medio_contacto is not None:
        pedido.medio_contacto = medio_contacto
    if observaciones is not None:
        pedido.observaciones = observaciones
    if estado is not None:
        pedido.estado = estado
    db.flush()
    return pedido


def delete_pedido(db: Session, pedido: Pedido) -> None:
    """Elimina un pedido (y sus items por cascade)."""
    db.delete(pedido)
    db.flush()


def create_pedido_items_bulk(db: Session, pedido_id: int, items: List[dict]) -> List[PedidoItem]:
    """Crea múltiples items para un pedido."""
    created_items = []
    for item_data in items:
        item = PedidoItem(
            pedido_id=pedido_id,
            stock_id=item_data["stock_id"],
            variedad=item_data["variedad"],
            kilos=item_data["kilos"],
            precio_kg=item_data["precio_kg"],
            subtotal=item_data["kilos"] * item_data["precio_kg"],
        )
        db.add(item)
        created_items.append(item)
    db.flush()
    return created_items


def create_estado_historial(
    db: Session,
    *,
    pedido_id: int,
    estado_anterior: Optional[EstadoPedidoEnum],
    estado_nuevo: EstadoPedidoEnum,
    usuario_id: Optional[int] = None,
) -> PedidoEstadoHistorial:
    """Registra un cambio de estado en el historial."""
    historial = PedidoEstadoHistorial(
        pedido_id=pedido_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_id=usuario_id,
    )
    db.add(historial)
    db.flush()
    return historial


def get_pedidos_by_cliente(db: Session, cliente_id: int) -> List[Pedido]:
    """Obtiene todos los pedidos de un cliente."""
    stmt = (
        select(Pedido)
        .options(selectinload(Pedido.items))
        .where(Pedido.cliente_id == cliente_id)
        .order_by(desc(Pedido.fecha))
    )
    return list(db.execute(stmt).scalars().all())


def get_pedidos_by_estado(db: Session, estado: EstadoPedidoEnum) -> List[Pedido]:
    """Obtiene todos los pedidos con un estado específico."""
    stmt = (
        select(Pedido)
        .options(selectinload(Pedido.items))
        .where(Pedido.estado == estado)
        .order_by(desc(Pedido.fecha))
    )
    return list(db.execute(stmt).scalars().all())