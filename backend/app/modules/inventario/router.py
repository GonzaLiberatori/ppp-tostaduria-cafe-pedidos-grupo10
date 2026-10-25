"""Rutas HTTP de ``TipoDeCafe``.

Solo capa de presentación: valida la entrada con los schemas, devuelve los
códigos de estado y pide la sesión con ``Depends``. No abre sesiones por su
cuenta ni decide reglas de negocio; esas viven en ``services``.

El ``id`` que identifica al registro va siempre por la ruta.
"""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.inventario import services
from app.modules.inventario.schemas import TipoDeCafeCreate, TipoDeCafeRead, TipoDeCafeUpdate

router = APIRouter(prefix="/tipos-de-cafe", tags=["Tipo de café"])


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce una excepción de dominio al código HTTP que le corresponde."""
    if isinstance(exc, services.TipoDeCafeNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.TipoDeCafeReferenciado):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=TipoDeCafeRead, status_code=status.HTTP_201_CREATED)
def crear_tipo_de_cafe(datos: TipoDeCafeCreate, db: Session = Depends(get_db)) -> TipoDeCafeRead:
    """Da de alta un tipo de café."""
    return services.crear_tipo_de_cafe(db, datos)


@router.get("/{tipo_id}", response_model=TipoDeCafeRead)
def leer_tipo_de_cafe(tipo_id: int, db: Session = Depends(get_db)) -> TipoDeCafeRead:
    """Devuelve el tipo de café con el ``id`` indicado."""
    try:
        return services.obtener_tipo_de_cafe(db, tipo_id)
    except services.TipoDeCafeNoEncontrado as exc:
        _a_codigo_http(exc)


@router.patch("/{tipo_id}", response_model=TipoDeCafeRead)
def editar_tipo_de_cafe(
    tipo_id: int,
    datos: TipoDeCafeUpdate,
    db: Session = Depends(get_db),
) -> TipoDeCafeRead:
    """Modifica solo los atributos enviados con valor."""
    try:
        return services.actualizar_tipo_de_cafe(db, tipo_id, datos)
    except services.TipoDeCafeNoEncontrado as exc:
        _a_codigo_http(exc)


@router.delete("/{tipo_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def eliminar_tipo_de_cafe(tipo_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra el tipo de café, salvo que otra entidad lo esté usando."""
    try:
        services.eliminar_tipo_de_cafe(db, tipo_id)
    except (services.TipoDeCafeNoEncontrado, services.TipoDeCafeReferenciado) as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
