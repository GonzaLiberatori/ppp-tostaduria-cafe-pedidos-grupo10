"""Rutas HTTP del módulo de gastos."""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.auth.schemas import TokenData
from app.modules.gastos import services
from app.modules.gastos.schemas import (
    GastoPanelCreate,
    GastoPanelRead,
    GastoPanelUpdate,
)

router = APIRouter(prefix="/gastos", tags=["Gastos"])


def _a_codigo_http(exc: Exception) -> NoReturn:
    if isinstance(exc, services.GastoNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise exc


@router.get("/", response_model=list[GastoPanelRead])
def listar_gastos(
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[GastoPanelRead]:
    """Lista los gastos del panel."""
    return services.listar_gastos(db)


@router.get("/{gasto_id}", response_model=GastoPanelRead)
def obtener_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> GastoPanelRead:
    """Devuelve un gasto por id."""
    try:
        return services.obtener_gasto(db, gasto_id)
    except services.GastoNoEncontrado as exc:
        _a_codigo_http(exc)


@router.post("/", response_model=GastoPanelRead, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    datos: GastoPanelCreate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> GastoPanelRead:
    """Registra un gasto."""
    return services.crear_gasto(db, datos)


@router.patch("/{gasto_id}", response_model=GastoPanelRead)
def actualizar_gasto(
    gasto_id: int,
    datos: GastoPanelUpdate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> GastoPanelRead:
    """Edita los campos enviados de un gasto."""
    try:
        return services.actualizar_gasto(db, gasto_id, datos)
    except services.GastoNoEncontrado as exc:
        _a_codigo_http(exc)


@router.delete(
    "/{gasto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def eliminar_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> Response:
    """Elimina un gasto."""
    try:
        services.eliminar_gasto(db, gasto_id)
    except services.GastoNoEncontrado as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
