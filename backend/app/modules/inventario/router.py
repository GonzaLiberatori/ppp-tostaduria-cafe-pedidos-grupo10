"""Rutas HTTP de ``TipoDeCafe`` y ``Blend``.

Solo capa de presentación: valida la entrada con los schemas, devuelve los
códigos de estado y pide la sesión con ``Depends``. No abre sesiones por su
cuenta ni decide reglas de negocio; esas viven en ``services``.

El ``id`` que identifica al registro va siempre por la ruta. Un solo router por
módulo, con los prefijos escritos en cada ruta, para que quien lo incluya no
tenga que acordarse de dos routers.
"""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.inventario import services
from app.modules.inventario.schemas import (
    BlendCreate,
    BlendRead,
    BlendUpdate,
    TipoDeCafeCreate,
    TipoDeCafeRead,
    TipoDeCafeUpdate,
)

router = APIRouter(tags=["Inventario"])

RUTA_TIPOS_DE_CAFE = "/tipos-de-cafe"
RUTA_BLENDS = "/blends"


def _a_codigo_http(exc: Exception) -> NoReturn:
    """Traduce una excepción de dominio al código HTTP que le corresponde.

    Cadena de `if / elif / else`: los casos son mutuamente excluyentes sobre el
    mismo sujeto, que es el tipo de la excepción.
    """
    if isinstance(exc, services.TipoDeCafeNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.TipoDeCafeReferenciado):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    elif isinstance(exc, services.BlendNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.BlendReferenciado):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    elif isinstance(exc, services.NombreDeBlendEnUso):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


# ---------------------------------------------------------------------------
# TipoDeCafe
# ---------------------------------------------------------------------------
@router.post(RUTA_TIPOS_DE_CAFE, response_model=TipoDeCafeRead, status_code=status.HTTP_201_CREATED)
def crear_tipo_de_cafe(datos: TipoDeCafeCreate, db: Session = Depends(get_db)) -> TipoDeCafeRead:
    """Da de alta un tipo de café."""
    return services.crear_tipo_de_cafe(db, datos)


@router.get(f"{RUTA_TIPOS_DE_CAFE}/{{tipo_id}}", response_model=TipoDeCafeRead)
def leer_tipo_de_cafe(tipo_id: int, db: Session = Depends(get_db)) -> TipoDeCafeRead:
    """Devuelve el tipo de café con el ``id`` indicado."""
    try:
        return services.obtener_tipo_de_cafe(db, tipo_id)
    except services.TipoDeCafeNoEncontrado as exc:
        _a_codigo_http(exc)


@router.patch(f"{RUTA_TIPOS_DE_CAFE}/{{tipo_id}}", response_model=TipoDeCafeRead)
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


@router.delete(
    f"{RUTA_TIPOS_DE_CAFE}/{{tipo_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def eliminar_tipo_de_cafe(tipo_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra el tipo de café, salvo que otra entidad lo esté usando."""
    try:
        services.eliminar_tipo_de_cafe(db, tipo_id)
    except (services.TipoDeCafeNoEncontrado, services.TipoDeCafeReferenciado) as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Blend
# ---------------------------------------------------------------------------
@router.post(RUTA_BLENDS, response_model=BlendRead, status_code=status.HTTP_201_CREATED)
def crear_blend(datos: BlendCreate, db: Session = Depends(get_db)) -> BlendRead:
    """Da de alta un blend con su composición de tipos de café."""
    try:
        return services.crear_blend(db, datos)
    except services.NombreDeBlendEnUso as exc:
        _a_codigo_http(exc)


@router.get(f"{RUTA_BLENDS}/{{blend_id}}", response_model=BlendRead)
def leer_blend(blend_id: int, db: Session = Depends(get_db)) -> BlendRead:
    """Devuelve el blend con el ``id`` indicado y su composición."""
    try:
        return services.obtener_blend(db, blend_id)
    except services.BlendNoEncontrado as exc:
        _a_codigo_http(exc)


@router.patch(f"{RUTA_BLENDS}/{{blend_id}}", response_model=BlendRead)
def editar_blend(
    blend_id: int,
    datos: BlendUpdate,
    db: Session = Depends(get_db),
) -> BlendRead:
    """Modifica solo los atributos enviados con valor y reemplaza la composición."""
    try:
        return services.actualizar_blend(db, blend_id, datos)
    except (services.BlendNoEncontrado, services.NombreDeBlendEnUso) as exc:
        _a_codigo_http(exc)


@router.delete(
    f"{RUTA_BLENDS}/{{blend_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def eliminar_blend(blend_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra el blend y su composición, salvo que otra entidad lo esté usando."""
    try:
        services.eliminar_blend(db, blend_id)
    except (services.BlendNoEncontrado, services.BlendReferenciado) as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
