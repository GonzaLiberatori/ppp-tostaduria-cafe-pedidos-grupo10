"""Rutas HTTP del módulo de envíos programados.

La autorización se resuelve acá: el token solo transporta el correo, así que el
rol y el ``cliente_id`` se leen de la cuenta en la base. Un usuario ``Cliente``
solo puede operar sobre sus propias suscripciones y entregas.
"""

from datetime import date
from typing import List, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.auth.models import Cuenta, UserRole
from app.modules.auth.schemas import TokenData
from app.modules.clientes.models import Cliente, Persona
from app.modules.envios import schemas, services

router = APIRouter(prefix="/envios", tags=["Envíos Programados"])

ROLES_GESTION = (UserRole.ADMINISTRADOR, UserRole.CAJERO)
ROLES_LOGISTICA = (
    UserRole.ADMINISTRADOR,
    UserRole.CAJERO,
    UserRole.OPERARIO,
)
ROLES_PROPIOS = (UserRole.CLIENTE,)


def get_cuenta_actual(
    token: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Cuenta:
    """Devuelve la cuenta autenticada, con su rol."""
    cuenta = db.query(Cuenta).filter(Cuenta.correo == token.email).first()
    if cuenta is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario del token no existe",
        )
    return cuenta


def get_envio_service(db: Session = Depends(get_db)) -> services.EnvioService:
    return services.EnvioService(db)


def _rol(cuenta: Cuenta) -> str:
    return getattr(cuenta.rol, "value", cuenta.rol)


def _es_cliente(cuenta: Cuenta) -> bool:
    return _rol(cuenta) == UserRole.CLIENTE.value


def _exigir_rol(cuenta: Cuenta, roles: tuple[UserRole, ...]) -> None:
    if _rol(cuenta) not in {rol.value for rol in roles}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para esta operación",
        )


def _cliente_id_de_cuenta(db: Session, cuenta: Cuenta) -> Optional[int]:
    """Resuelve el ``persona_id`` del cliente vinculado a la cuenta."""
    persona = (
        db.query(Persona).filter(Persona.cuenta_id == cuenta.id).first()
    )
    if persona is None:
        return None
    cliente = (
        db.query(Cliente)
        .filter(Cliente.persona_id == persona.id)
        .first()
    )
    return cliente.persona_id if cliente is not None else None


def _cliente_id_permitido(
    db: Session, cuenta: Cuenta, cliente_id: Optional[int]
) -> Optional[int]:
    """Fuerza el propio cliente cuando el usuario es de rol Cliente."""
    if not _es_cliente(cuenta):
        return cliente_id

    propio = _cliente_id_de_cuenta(db, cuenta)
    if propio is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está vinculada a un cliente.",
        )
    if cliente_id is not None and cliente_id != propio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo podés consultar tus propias entregas.",
        )
    return propio


def _a_entero(valor: Optional[str], nombre: str) -> Optional[int]:
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{nombre} inválido.",
        ) from None


def _traducir_error(exc: Exception) -> NoReturn:
    if isinstance(exc, services.SuscripcionNoEncontrada):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if isinstance(exc, (services.ClienteNoHabilitado, services.ProductoInvalido)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    raise exc


@router.post(
    "/suscripciones",
    response_model=schemas.SuscripcionRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_suscripcion(
    datos: schemas.SuscripcionCreate,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
    db: Session = Depends(get_db),
):
    _exigir_rol(cuenta, ROLES_GESTION + ROLES_PROPIOS)

    if _es_cliente(cuenta):
        propio = _cliente_id_permitido(db, cuenta, None)
        datos = datos.model_copy(update={"clienteId": str(propio)})

    try:
        return service.crear_suscripcion(datos)
    except Exception as exc:
        _traducir_error(exc)


@router.get("/suscripciones", response_model=List[schemas.SuscripcionRead])
def listar_suscripciones(
    clienteId: Optional[str] = Query(default=None),
    soloActivas: Optional[bool] = Query(default=None),
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
    db: Session = Depends(get_db),
):
    _exigir_rol(cuenta, ROLES_GESTION + ROLES_LOGISTICA + ROLES_PROPIOS)
    cliente_id = _cliente_id_permitido(
        db, cuenta, _a_entero(clienteId, "clienteId")
    )
    return service.listar_suscripciones(
        cliente_id=cliente_id, solo_activas=soloActivas
    )


@router.patch(
    "/suscripciones/{suscripcion_id}",
    response_model=schemas.SuscripcionRead,
)
def actualizar_suscripcion(
    suscripcion_id: int,
    datos: schemas.SuscripcionUpdate,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
    db: Session = Depends(get_db),
):
    _exigir_rol(cuenta, ROLES_GESTION + ROLES_PROPIOS)

    if _es_cliente(cuenta):
        propio = _cliente_id_permitido(db, cuenta, None)
        suscripcion = next(
            (
                item
                for item in service.listar_suscripciones(cliente_id=propio)
                if item.id == suscripcion_id
            ),
            None,
        )
        if suscripcion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe la suscripción.",
            )

    try:
        return service.actualizar_suscripcion(suscripcion_id, datos)
    except Exception as exc:
        _traducir_error(exc)


@router.delete(
    "/suscripciones/{suscripcion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def desactivar_suscripcion(
    suscripcion_id: int,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
    db: Session = Depends(get_db),
):
    _exigir_rol(cuenta, ROLES_GESTION + ROLES_PROPIOS)

    if _es_cliente(cuenta):
        propio = _cliente_id_permitido(db, cuenta, None)
        suscripcion = next(
            (
                item
                for item in service.listar_suscripciones(cliente_id=propio)
                if item.id == suscripcion_id
            ),
            None,
        )
        if suscripcion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe la suscripción.",
            )

    try:
        service.desactivar_suscripcion(suscripcion_id)
    except Exception as exc:
        _traducir_error(exc)


@router.get("/entregas", response_model=List[schemas.EntregaRead])
def listar_entregas(
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    clienteId: Optional[str] = Query(default=None),
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
    db: Session = Depends(get_db),
):
    _exigir_rol(cuenta, ROLES_GESTION + ROLES_LOGISTICA + ROLES_PROPIOS)
    cliente_id = _cliente_id_permitido(
        db, cuenta, _a_entero(clienteId, "clienteId")
    )
    return service.listar_entregas(
        desde=desde, hasta=hasta, cliente_id=cliente_id
    )


@router.post("/generar", response_model=schemas.GeneracionResultadoRead)
def generar_del_dia(
    fecha: Optional[date] = Query(default=None),
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
):
    _exigir_rol(cuenta, ROLES_GESTION + (UserRole.OPERARIO,))
    try:
        return service.generar_del_dia(fecha)
    except Exception as exc:
        _traducir_error(exc)


@router.get("/hoja-de-ruta", response_model=List[schemas.HojaDeRutaRead])
def hoja_de_ruta(
    fecha: Optional[date] = Query(default=None),
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.EnvioService = Depends(get_envio_service),
):
    _exigir_rol(cuenta, ROLES_LOGISTICA)
    try:
        return service.hoja_de_ruta(fecha)
    except Exception as exc:
        _traducir_error(exc)
