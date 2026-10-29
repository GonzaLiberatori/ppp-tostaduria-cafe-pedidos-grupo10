from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.modules.auth.models import Rol, Usuario
from app.modules.clientes import services
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
)

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    dependencies=[Depends(require_roles(Rol.ADMIN, Rol.EMPLEADO))],
)

CAMPOS_DEUDA = {
    "montoDeuda",
    "monto_deuda",
    "deudaPendiente",
    "deuda_pendiente",
}

CLIENTE_NO_ENCONTRADO = "Cliente no encontrado"
SIN_PERMISO_DEUDA = "No tiene permiso para modificar la deuda pendiente"
CLIENTE_CON_RELACIONES = (
    "No se puede eliminar el cliente porque tiene registros asociados"
)


def _es_admin(usuario: Usuario = Depends(get_current_user)) -> bool:
    return usuario.rol == Rol.ADMIN


async def prohibir_campos_sensibles(
    request: Request,
    usuario: Usuario = Depends(get_current_user),
) -> None:
    """Bloquea la deuda pendiente en el body antes de la validación Pydantic.

    Se inspecciona el JSON crudo para que un error de validación nunca
    devuelva el valor enviado por un usuario sin permisos.
    """
    if usuario.rol == Rol.ADMIN:
        return

    if request.method not in {"POST", "PUT", "PATCH"}:
        return

    try:
        cuerpo = await request.json()
    except Exception:
        return

    if isinstance(cuerpo, dict) and CAMPOS_DEUDA.intersection(cuerpo.keys()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SIN_PERMISO_DEUDA,
        )


def _manejar_errores_comunes(exc: Exception) -> None:
    if isinstance(exc, services.ClienteNoEncontradoError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLIENTE_NO_ENCONTRADO,
        ) from exc

    if isinstance(exc, services.ClienteConRelacionesError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CLIENTE_CON_RELACIONES,
        ) from exc

    if isinstance(exc, services.ModificacionDeudaNoPermitidaError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SIN_PERMISO_DEUDA,
        ) from exc

    if isinstance(exc, services.DatosInvalidosError):
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    raise exc


@router.get(
    "",
    response_model=list[ClienteOut],
    response_model_exclude_none=True,
)
def listar_clientes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    es_admin: bool = Depends(_es_admin),
) -> list[ClienteOut]:
    clientes = services.listar_clientes(db, skip=skip, limit=limit)
    return [
        ClienteOut.desde_modelo(cliente, incluir_deuda=es_admin)
        for cliente in clientes
    ]


@router.get(
    "/{cliente_id}",
    response_model=ClienteOut,
    response_model_exclude_none=True,
)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    es_admin: bool = Depends(_es_admin),
) -> ClienteOut:
    try:
        cliente = services.obtener_cliente(db, cliente_id)
    except Exception as exc:
        _manejar_errores_comunes(exc)

    return ClienteOut.desde_modelo(cliente, incluir_deuda=es_admin)


@router.post(
    "",
    response_model=ClienteOut,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
    dependencies=[Depends(prohibir_campos_sensibles)],
)
def crear_cliente(
    payload: ClienteCreate,
    db: Session = Depends(get_db),
    es_admin: bool = Depends(_es_admin),
) -> ClienteOut:
    try:
        cliente = services.crear_cliente(db, payload)
    except Exception as exc:
        _manejar_errores_comunes(exc)

    return ClienteOut.desde_modelo(cliente, incluir_deuda=es_admin)


@router.put(
    "/{cliente_id}",
    response_model=ClienteOut,
    response_model_exclude_none=True,
    dependencies=[Depends(prohibir_campos_sensibles)],
)
def actualizar_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    db: Session = Depends(get_db),
    es_admin: bool = Depends(_es_admin),
) -> ClienteOut:
    try:
        cliente = services.actualizar_cliente(
            db,
            cliente_id,
            payload,
            es_admin=es_admin,
        )
    except Exception as exc:
        _manejar_errores_comunes(exc)

    return ClienteOut.desde_modelo(cliente, incluir_deuda=es_admin)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
) -> None:
    try:
        services.eliminar_cliente(db, cliente_id)
    except Exception as exc:
        _manejar_errores_comunes(exc)
