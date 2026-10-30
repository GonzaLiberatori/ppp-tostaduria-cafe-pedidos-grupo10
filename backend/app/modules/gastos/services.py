"""Reglas de negocio y frontera transaccional del módulo de gastos."""

from sqlalchemy.orm import Session

from app.modules.gastos import crud
from app.modules.gastos.models import Gasto
from app.modules.gastos.schemas import (
    GastoPanelCreate,
    GastoPanelRead,
    GastoPanelUpdate,
)


class GastoNoEncontrado(Exception):
    """El id recibido no corresponde a ningún gasto."""

    def __init__(self, gasto_id: int) -> None:
        self.gasto_id = gasto_id
        super().__init__(f"No existe un gasto con id {gasto_id}.")


def _a_contrato(gasto: Gasto) -> GastoPanelRead:
    return GastoPanelRead(
        id=str(gasto.id),
        categoria=gasto.categoria,
        descripcion=gasto.descripcion,
        monto=float(gasto.monto),
        fecha=gasto.fecha,
    )


def listar_gastos(db: Session) -> list[GastoPanelRead]:
    """Lista todos los gastos del panel."""
    return [_a_contrato(gasto) for gasto in crud.listar_gastos(db)]


def obtener_gasto(db: Session, gasto_id: int) -> GastoPanelRead:
    """Lee un gasto por id."""
    gasto = crud.obtener_gasto(db, gasto_id)
    if gasto is None:
        raise GastoNoEncontrado(gasto_id)
    return _a_contrato(gasto)


def crear_gasto(db: Session, datos: GastoPanelCreate) -> GastoPanelRead:
    """Registra un gasto en una sola transacción."""
    try:
        gasto = Gasto(
            categoria=datos.categoria,
            descripcion=datos.descripcion,
            monto=datos.monto,
            fecha=datos.fecha,
        )
        crud.crear_gasto(db, gasto)
        db.commit()
        db.refresh(gasto)
    except Exception:
        db.rollback()
        raise

    return _a_contrato(gasto)


def actualizar_gasto(
    db: Session, gasto_id: int, datos: GastoPanelUpdate
) -> GastoPanelRead:
    """Aplica solo los campos enviados con valor."""
    gasto = crud.obtener_gasto(db, gasto_id)
    if gasto is None:
        raise GastoNoEncontrado(gasto_id)

    cambios = datos.model_dump(exclude_none=True)
    if not cambios:
        return _a_contrato(gasto)

    try:
        crud.actualizar_gasto(db, gasto, cambios)
        db.commit()
        db.refresh(gasto)
    except Exception:
        db.rollback()
        raise

    return _a_contrato(gasto)


def eliminar_gasto(db: Session, gasto_id: int) -> None:
    """Borra un gasto."""
    gasto = crud.obtener_gasto(db, gasto_id)
    if gasto is None:
        raise GastoNoEncontrado(gasto_id)

    try:
        crud.eliminar_gasto(db, gasto)
        db.commit()
    except Exception:
        db.rollback()
        raise
