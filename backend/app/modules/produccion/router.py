"""Rutas HTTP del módulo de producción.

Solo capa de presentación: valida la entrada con los schemas, traduce las
excepciones de dominio a códigos de estado y pide la sesión con ``Depends``.
"""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.produccion import services
from app.modules.produccion.schemas import TuesteCreate, TuesteRead

router = APIRouter(tags=["Producción"])

RUTA_TUESTES = "/tuestes"


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce una excepción de dominio al código HTTP que le corresponde."""
    if isinstance(exc, services.TuesteNoEncontrado):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    elif isinstance(exc, services.TipoDeCafeNoEncontradoParaTueste):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    elif isinstance(exc, services.StockVerdeInsuficienteParaTueste):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    raise exc


@router.post(
    RUTA_TUESTES,
    response_model=TuesteRead,
    status_code=status.HTTP_201_CREATED,
)
def registrar_tueste(
    datos: TuesteCreate, db: Session = Depends(get_db)
) -> TuesteRead:
    """Registra un tueste y convierte stock verde en stock tostado."""
    try:
        return services.registrar_tueste(db, datos)
    except (
        services.TipoDeCafeNoEncontradoParaTueste,
        services.StockVerdeInsuficienteParaTueste,
    ) as exc:
        _a_codigo_http(exc)


@router.get(RUTA_TUESTES, response_model=list[TuesteRead])
def listar_tuestes(db: Session = Depends(get_db)) -> list[TuesteRead]:
    """Lista las órdenes de tueste registradas."""
    return services.listar_tuestes(db)


@router.get(f"{RUTA_TUESTES}/{{orden_id}}", response_model=TuesteRead)
def leer_tueste(
    orden_id: int, db: Session = Depends(get_db)
) -> TuesteRead:
    """Devuelve la orden de tueste con el ``id`` indicado."""
    try:
        return services.obtener_tueste(db, orden_id)
    except services.TuesteNoEncontrado as exc:
        _a_codigo_http(exc)
