"""Rutas HTTP del módulo de clientes para el panel."""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.auth.schemas import TokenData
from app.modules.clientes import services
from app.modules.clientes.schemas import (
    ClientePanelCreate,
    ClientePanelRead,
    ClientePanelUpdate,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce las excepciones de dominio a códigos HTTP."""
    if isinstance(exc, services.ClienteNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, (services.EmailDeClienteEnUso, services.TelefonoDeClienteEnUso)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    elif isinstance(exc, services.ClienteConPedidos):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.get("/", response_model=list[ClientePanelRead])
def listar_clientes(
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[ClientePanelRead]:
    """Lista los clientes del panel."""
    return services.listar_clientes(db)


@router.get("/{cliente_id}", response_model=ClientePanelRead)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ClientePanelRead:
    """Devuelve un cliente por id."""
    try:
        return services.obtener_cliente(db, cliente_id)
    except services.ClienteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.post("/", response_model=ClientePanelRead, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    datos: ClientePanelCreate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ClientePanelRead:
    """Crea un cliente y su persona."""
    try:
        return services.crear_cliente(db, datos)
    except (services.EmailDeClienteEnUso, services.TelefonoDeClienteEnUso) as exc:
        _a_codigo_http(exc)


@router.patch("/{cliente_id}", response_model=ClientePanelRead)
def actualizar_cliente(
    cliente_id: int,
    datos: ClientePanelUpdate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ClientePanelRead:
    """Edita los campos enviados de un cliente."""
    try:
        return services.actualizar_cliente(db, cliente_id, datos)
    except (
        services.ClienteNoEncontrado,
        services.EmailDeClienteEnUso,
        services.TelefonoDeClienteEnUso,
    ) as exc:
        _a_codigo_http(exc)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> Response:
    """Elimina un cliente sin pedidos asociados."""
    try:
        services.eliminar_cliente(db, cliente_id)
    except (services.ClienteNoEncontrado, services.ClienteConPedidos) as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
