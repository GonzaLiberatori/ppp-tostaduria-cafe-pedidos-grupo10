"""Acceso a datos del módulo de gastos. Consultas puras, sin commits."""

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.gastos.models import Gasto


def listar_gastos(db: Session) -> list[Gasto]:
    """Devuelve los gastos ordenados del más reciente al más antiguo."""
    return db.query(Gasto).order_by(Gasto.fecha.desc(), Gasto.id.desc()).all()


def obtener_gasto(db: Session, gasto_id: int) -> Optional[Gasto]:
    """Devuelve el gasto con ese id, o ``None``."""
    return db.get(Gasto, gasto_id)


def crear_gasto(db: Session, gasto: Gasto) -> Gasto:
    """Agrega el gasto a la sesión y hace flush. No hace commit."""
    db.add(gasto)
    db.flush()
    return gasto


def actualizar_gasto(db: Session, gasto: Gasto, cambios: dict) -> Gasto:
    """Aplica los campos recibidos y hace flush. No hace commit."""
    for atributo, valor in cambios.items():
        setattr(gasto, atributo, valor)
    db.flush()
    return gasto


def eliminar_gasto(db: Session, gasto: Gasto) -> None:
    """Marca el gasto para borrado. No hace commit."""
    db.delete(gasto)
    db.flush()
