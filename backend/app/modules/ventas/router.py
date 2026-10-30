"""Rutas HTTP del módulo de ventas.

La autorización se resuelve acá: el token solo transporta el correo, así que el
rol se lee de la cuenta en la base. No se modifica ``core/deps.py``.
"""

from datetime import datetime
from typing import NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.auth.models import Cuenta, UserRole
from app.modules.auth.schemas import TokenData
from app.modules.pedidos.models import MetodoPago
from app.modules.ventas import schemas, services
from app.modules.ventas.models import VentaEstado

router = APIRouter(prefix="/ventas", tags=["Ventas"])

ROLES_REGISTRO = (UserRole.ADMINISTRADOR, UserRole.CAJERO)
ROLES_ANULACION = (UserRole.ADMINISTRADOR,)
ROLES_CONSULTA = (UserRole.ADMINISTRADOR, UserRole.CAJERO, UserRole.OPERARIO)


# ---------------------------------------------------------------------------
# Dependencias propias del módulo
# ---------------------------------------------------------------------------


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


def get_venta_service(db: Session = Depends(get_db)) -> services.VentaService:
    """Instancia el servicio con la sesión del request."""
    return services.VentaService(db)


# ---------------------------------------------------------------------------
# Helpers de autorización y errores
# ---------------------------------------------------------------------------


def _rol(cuenta: Cuenta) -> str:
    """Normaliza el rol a texto, venga como enum o como str."""
    return getattr(cuenta.rol, "value", cuenta.rol)


def _exigir_rol(cuenta: Cuenta, roles: tuple[UserRole, ...]) -> None:
    """Rechaza con 403 si el rol de la cuenta no está habilitado."""
    if _rol(cuenta) not in {rol.value for rol in roles}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para esta operación",
        )


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce las excepciones de dominio a códigos HTTP."""
    if isinstance(exc, (services.VentaNoEncontrada, services.PedidoNoEncontrado)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if isinstance(
        exc,
        (
            services.PedidoNoVendible,
            services.VentaDuplicada,
            services.PagosNoCuadran,
            services.VentaYaAnulada,
            services.ComprobanteDuplicado,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    raise exc


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=schemas.VentaDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def registrar_venta(
    datos: schemas.VentaCreate,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> schemas.VentaDetailRead:
    """Registra el cobro de un pedido entregado."""
    _exigir_rol(cuenta, ROLES_REGISTRO)
    try:
        return service.registrar_venta(datos, cuenta_id=cuenta.id)
    except Exception as exc:
        _a_codigo_http(exc)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
# ``/resumen`` y ``/comprobante/...`` van antes de ``/{venta_id}`` para que no
# se interpreten como identificadores.


@router.get("/", response_model=list[schemas.VentaListRead])
def listar_ventas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado: Optional[VentaEstado] = None,
    metodo_de_pago: Optional[MetodoPago] = None,
    cliente_persona_id: Optional[int] = None,
    q: Optional[str] = None,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> list[schemas.VentaListRead]:
    """Lista las ventas con filtros y paginación."""
    _exigir_rol(cuenta, ROLES_CONSULTA)
    return service.listar_ventas(
        skip=skip,
        limit=limit,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        metodo_de_pago=metodo_de_pago,
        cliente_persona_id=cliente_persona_id,
        q=q,
    )


@router.get("/resumen", response_model=schemas.VentaResumenRead)
def resumen_de_ventas(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> schemas.VentaResumenRead:
    """Arqueo de caja por método de pago."""
    _exigir_rol(cuenta, ROLES_CONSULTA)
    return service.resumen_arqueo(fecha_desde, fecha_hasta)


@router.get(
    "/comprobante/{numero_comprobante}",
    response_model=schemas.VentaDetailRead,
)
def obtener_venta_por_comprobante(
    numero_comprobante: str,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> schemas.VentaDetailRead:
    """Detalle de una venta por número de comprobante."""
    _exigir_rol(cuenta, ROLES_CONSULTA)
    try:
        return service.obtener_por_comprobante(numero_comprobante)
    except Exception as exc:
        _a_codigo_http(exc)


@router.get("/{venta_id}", response_model=schemas.VentaDetailRead)
def obtener_venta(
    venta_id: int,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> schemas.VentaDetailRead:
    """Detalle de una venta por id."""
    _exigir_rol(cuenta, ROLES_CONSULTA)
    try:
        return service.obtener_venta(venta_id)
    except Exception as exc:
        _a_codigo_http(exc)


# ---------------------------------------------------------------------------
# Anulación
# ---------------------------------------------------------------------------


@router.post("/{venta_id}/anular", response_model=schemas.VentaDetailRead)
def anular_venta(
    venta_id: int,
    datos: schemas.VentaAnulacionCreate,
    cuenta: Cuenta = Depends(get_cuenta_actual),
    service: services.VentaService = Depends(get_venta_service),
) -> schemas.VentaDetailRead:
    """Anula la venta de forma lógica, con motivo y usuario."""
    _exigir_rol(cuenta, ROLES_ANULACION)
    try:
        return service.anular_venta(venta_id, datos, cuenta_id=cuenta.id)
    except Exception as exc:
        _a_codigo_http(exc)
