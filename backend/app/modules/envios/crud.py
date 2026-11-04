"""Acceso a datos del módulo de envíos programados.

Sin reglas de negocio y sin ``commit``: el servicio es la frontera transaccional.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.clientes.models import Cliente
from app.modules.envios import models


def listar_suscripciones(
    db: Session,
    cliente_id: Optional[int] = None,
    solo_activas: Optional[bool] = None,
) -> List[models.SuscripcionEnvio]:
    """Lista suscripciones, con filtros opcionales."""
    consulta = db.query(models.SuscripcionEnvio).options(
        joinedload(models.SuscripcionEnvio.cliente).joinedload(Cliente.persona),
        joinedload(models.SuscripcionEnvio.tipo_de_cafe),
        joinedload(models.SuscripcionEnvio.blend),
    )
    if cliente_id is not None:
        consulta = consulta.filter(
            models.SuscripcionEnvio.cliente_id == cliente_id
        )
    if solo_activas is not None:
        consulta = consulta.filter(
            models.SuscripcionEnvio.activa.is_(solo_activas)
        )
    return consulta.order_by(models.SuscripcionEnvio.id.desc()).all()


def obtener_suscripcion(
    db: Session, suscripcion_id: int
) -> Optional[models.SuscripcionEnvio]:
    """Busca una suscripción por id."""
    return db.get(models.SuscripcionEnvio, suscripcion_id)


def crear_suscripcion(
    db: Session, datos: dict
) -> models.SuscripcionEnvio:
    """Agrega la suscripción a la sesión y hace flush (sin commit)."""
    suscripcion = models.SuscripcionEnvio(**datos)
    db.add(suscripcion)
    db.flush()
    return suscripcion


def suscripciones_del_dia(
    db: Session, fecha: date
) -> List[models.SuscripcionEnvio]:
    """Suscripciones activas que corresponden al día de la semana de ``fecha``."""
    return (
        db.query(models.SuscripcionEnvio)
        .options(
            joinedload(models.SuscripcionEnvio.cliente).joinedload(Cliente.persona),
            joinedload(models.SuscripcionEnvio.tipo_de_cafe),
            joinedload(models.SuscripcionEnvio.blend),
        )
        .filter(
            models.SuscripcionEnvio.activa.is_(True),
            models.SuscripcionEnvio.dia_semana == fecha.weekday(),
            models.SuscripcionEnvio.fecha_inicio <= fecha,
        )
        .order_by(models.SuscripcionEnvio.cliente_id, models.SuscripcionEnvio.id)
        .all()
    )


def obtener_entrega(
    db: Session, cliente_id: int, fecha_entrega: date
) -> Optional[models.EntregaProgramada]:
    """Busca la entrega de un cliente para una fecha (clave de idempotencia)."""
    return (
        db.query(models.EntregaProgramada)
        .filter(
            models.EntregaProgramada.cliente_id == cliente_id,
            models.EntregaProgramada.fecha_entrega == fecha_entrega,
        )
        .first()
    )


def crear_entrega(
    db: Session, datos: dict
) -> models.EntregaProgramada:
    """Agrega la entrega a la sesión y hace flush (sin commit)."""
    entrega = models.EntregaProgramada(**datos)
    db.add(entrega)
    db.flush()
    return entrega


def listar_entregas(
    db: Session,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    cliente_id: Optional[int] = None,
) -> List[models.EntregaProgramada]:
    """Lista entregas programadas con filtros por rango y cliente."""
    consulta = db.query(models.EntregaProgramada).options(
        joinedload(models.EntregaProgramada.cliente).joinedload(Cliente.persona),
    )
    if desde is not None:
        consulta = consulta.filter(
            models.EntregaProgramada.fecha_entrega >= desde
        )
    if hasta is not None:
        consulta = consulta.filter(
            models.EntregaProgramada.fecha_entrega <= hasta
        )
    if cliente_id is not None:
        consulta = consulta.filter(
            models.EntregaProgramada.cliente_id == cliente_id
        )
    return consulta.order_by(
        models.EntregaProgramada.fecha_entrega,
        models.EntregaProgramada.cliente_id,
    ).all()


__all__ = [
    "listar_suscripciones",
    "obtener_suscripcion",
    "crear_suscripcion",
    "suscripciones_del_dia",
    "obtener_entrega",
    "crear_entrega",
    "listar_entregas",
]
