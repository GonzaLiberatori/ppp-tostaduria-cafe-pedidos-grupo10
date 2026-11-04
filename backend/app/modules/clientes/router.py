"""Rutas HTTP del módulo de clientes para el panel y el portal."""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_account, get_db
from app.modules.auth.models import Cuenta, UserRole
from app.modules.clientes import services
from app.modules.clientes.schemas import (
    ClientePanelCreate,
    ClientePanelRead,
    ClientePanelUpdate,
    ClientePerfilUpdate,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])

# El personal interno puede consultar el padrón; solo Administrador y Cajero
# pueden modificarlo. Un Cliente únicamente accede a su propio perfil.
ROLES_LECTURA = (UserRole.ADMINISTRADOR, UserRole.CAJERO, UserRole.OPERARIO)
ROLES_GESTION = (UserRole.ADMINISTRADOR, UserRole.CAJERO)
ROLES_ELIMINACION = (UserRole.ADMINISTRADOR,)


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce las excepciones de dominio a códigos HTTP."""
    if isinstance(exc, services.ClienteNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.CuentaSinCliente):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, (services.EmailDeClienteEnUso, services.TelefonoDeClienteEnUso)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    elif isinstance(exc, services.ClienteConPedidos):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    elif isinstance(exc, services.AccesoPortalInvalido):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _exigir_rol(cuenta: Cuenta, roles: tuple[UserRole, ...]) -> None:
    """Corta con 403 si la cuenta no tiene uno de los roles permitidos."""
    if cuenta.rol not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para esta operación.",
        )


def _exigir_acceso_cliente(
    db: Session, cuenta: Cuenta, cliente_id: int
) -> None:
    """Un Cliente solo puede operar sobre su propio ``persona_id``."""
    if cuenta.rol is not UserRole.CLIENTE:
        return

    propio_id = services.cliente_id_de_cuenta(db, cuenta)
    if propio_id != cliente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para acceder a otro cliente.",
        )


@router.get("/me", response_model=ClientePanelRead)
def obtener_mi_perfil(
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> ClientePanelRead:
    """Devuelve el perfil del cliente vinculado a la cuenta autenticada."""
    try:
        return services.obtener_cliente_por_cuenta(db, cuenta)
    except services.CuentaSinCliente as exc:
        _a_codigo_http(exc)


@router.patch("/me", response_model=ClientePanelRead)
def actualizar_mi_perfil(
    datos: ClientePerfilUpdate,
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> ClientePanelRead:
    """Permite al cliente editar sus propios datos de contacto y entrega."""
    try:
        return services.actualizar_cliente_por_cuenta(db, cuenta, datos)
    except (
        services.CuentaSinCliente,
        services.EmailDeClienteEnUso,
        services.TelefonoDeClienteEnUso,
        services.AccesoPortalInvalido,
    ) as exc:
        _a_codigo_http(exc)


@router.get("/", response_model=list[ClientePanelRead])
def listar_clientes(
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> list[ClientePanelRead]:
    """Lista los clientes del panel. Reservado al personal interno."""
    _exigir_rol(cuenta, ROLES_LECTURA)
    return services.listar_clientes(db)


@router.get("/{cliente_id}", response_model=ClientePanelRead)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> ClientePanelRead:
    """Devuelve un cliente por id; el Cliente solo puede ver el propio."""
    _exigir_acceso_cliente(db, cuenta, cliente_id)
    try:
        return services.obtener_cliente(db, cliente_id)
    except services.ClienteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.post("/", response_model=ClientePanelRead, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    datos: ClientePanelCreate,
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> ClientePanelRead:
    """Crea un cliente y su persona (y su acceso al portal si se envía password)."""
    _exigir_rol(cuenta, ROLES_GESTION)
    try:
        return services.crear_cliente(db, datos)
    except (
        services.EmailDeClienteEnUso,
        services.TelefonoDeClienteEnUso,
        services.AccesoPortalInvalido,
    ) as exc:
        _a_codigo_http(exc)


@router.patch("/{cliente_id}", response_model=ClientePanelRead)
def actualizar_cliente(
    cliente_id: int,
    datos: ClientePanelUpdate,
    db: Session = Depends(get_db),
    cuenta: Cuenta = Depends(get_current_account),
) -> ClientePanelRead:
    """Edita los campos enviados de un cliente desde el panel."""
    _exigir_rol(cuenta, ROLES_GESTION)
    try:
        return services.actualizar_cliente(db, cliente_id, datos)
    except (
        services.ClienteNoEncontrado,
        services.EmailDeClienteEnUso,
        services.TelefonoDeClienteEnUso,
        services.AccesoPortalInvalido,
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
    cuenta: Cuenta = Depends(get_current_account),
) -> Response:
    """Elimina un cliente sin pedidos asociados."""
    _exigir_rol(cuenta, ROLES_ELIMINACION)
    try:
        services.eliminar_cliente(db, cliente_id)
    except (services.ClienteNoEncontrado, services.ClienteConPedidos) as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
