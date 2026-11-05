"""Acceso a datos del módulo de producción.

Consultas puras: sin reglas de negocio y sin commits. La frontera transaccional
y las validaciones de stock viven en ``services.py``.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.modules.produccion.models import ConsumoTueste, OrdenTueste


def crear_orden_tueste(
    db: Session,
    *,
    fecha_tueste: datetime,
    kg_gastados: Decimal,
    kg_obtenidos: Decimal,
    tipo_de_cafe_id: int,
) -> OrdenTueste:
    """Crea una orden de tueste y la deja flusheada, sin commit."""
    orden = OrdenTueste(
        fecha_tueste=fecha_tueste,
        kg_gastados=kg_gastados,
        kg_obtenidos=kg_obtenidos,
        tipo_de_cafe_id=tipo_de_cafe_id,
    )
    db.add(orden)
    db.flush()
    return orden


def registrar_consumo(
    db: Session,
    *,
    orden: OrdenTueste,
    lote_id: int,
    kg_consumidos: Decimal,
) -> ConsumoTueste:
    """Registra el consumo de un lote verde y lo deja flusheado, sin commit."""
    consumo = ConsumoTueste(
        orden_tueste_id=orden.id,
        lote_id=lote_id,
        kg_consumidos=kg_consumidos,
    )
    db.add(consumo)
    db.flush()
    return consumo


def _consulta_con_relaciones() -> Select[tuple[OrdenTueste]]:
    """Consulta base de órdenes con consumos y lotes precargados."""
    return select(OrdenTueste).options(
        selectinload(OrdenTueste.consumos),
        selectinload(OrdenTueste.lotes),
    )


def obtener_orden(db: Session, orden_id: int) -> OrdenTueste | None:
    """Devuelve la orden con ese ``id`` y sus relaciones, o ``None``."""
    return db.execute(
        _consulta_con_relaciones().where(OrdenTueste.id == orden_id)
    ).scalar_one_or_none()


def listar_ordenes(db: Session) -> list[OrdenTueste]:
    """Devuelve todas las órdenes, de la más reciente a la más antigua."""
    return list(
        db.execute(
            _consulta_con_relaciones().order_by(OrdenTueste.id.desc())
        ).scalars().all()
    )
