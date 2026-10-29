"""Rutas HTTP de ``TipoDeCafe`` y ``Blend``.

Solo capa de presentación: valida la entrada con los schemas, devuelve los
códigos de estado y pide la sesión con ``Depends``. No abre sesiones por su
cuenta ni decide reglas de negocio; esas viven en ``services``.

El ``id`` que identifica al registro va siempre por la ruta. Un solo router por
módulo, con los prefijos escritos en cada ruta, para que quien lo incluya no
tenga que acordarse de dos routers.
"""

from typing import NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.inventario import services
from app.modules.inventario.schemas import (
    BlendCreate,
    BlendRead,
    BlendUpdate,
    LoteCreate,
    LoteEstadoUpdate,
    LoteKgDisponiblesUpdate,
    LoteKgRealesUpdate,
    LoteRead,
    LoteUpdate,
    TipoDeCafeCreate,
    TipoDeCafeRead,
    TipoDeCafeUpdate,
)

router = APIRouter(tags=["Inventario"])

RUTA_TIPOS_DE_CAFE = "/tipos-de-cafe"
RUTA_BLENDS = "/blends"
RUTA_LOTES = "/lotes"


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
    elif isinstance(exc, services.LoteNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.OrigenDeLoteNoEncontrado):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elif isinstance(exc, services.KgDisponiblesExcedeKgReales):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    elif isinstance(exc, services.FiltroLotesInvalido):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


# ---------------------------------------------------------------------------
# TipoDeCafe
# ---------------------------------------------------------------------------
@router.post(RUTA_TIPOS_DE_CAFE, response_model=TipoDeCafeRead, status_code=status.HTTP_201_CREATED)
def crear_tipo_de_cafe(datos: TipoDeCafeCreate, db: Session = Depends(get_db)) -> TipoDeCafeRead:
    """Da de alta un tipo de café."""
    return services.crear_tipo_de_cafe(db, datos)


@router.get(RUTA_TIPOS_DE_CAFE, response_model=list[TipoDeCafeRead])
def listar_tipos_de_cafe(db: Session = Depends(get_db)) -> list[TipoDeCafeRead]:
    """Lista todos los tipos de café registrados."""
    return services.listar_tipos_de_cafe(db)


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


@router.get(RUTA_BLENDS, response_model=list[BlendRead])
def listar_blends(db: Session = Depends(get_db)) -> list[BlendRead]:
    """Lista todos los blends registrados con sus composiciones."""
    return services.listar_blends(db)


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


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------
@router.post(RUTA_LOTES, response_model=LoteRead, status_code=status.HTTP_201_CREATED)
def crear_lote(datos: LoteCreate, db: Session = Depends(get_db)) -> LoteRead:
    """Da de alta un lote. Los kilos disponibles se derivan de los reales."""
    try:
        return services.crear_lote(db, datos)
    except services.OrigenDeLoteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.get(RUTA_LOTES, response_model=list[LoteRead])
def listar_lotes(
    tipo_de_cafe_id: Optional[int] = None,
    blend_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[LoteRead]:
    """Lista los lotes filtrados por tipo_de_cafe_id o blend_id (XOR)."""
    try:
        return services.listar_lotes(
            db, tipo_de_cafe_id=tipo_de_cafe_id, blend_id=blend_id
        )
    except services.FiltroLotesInvalido as exc:
        _a_codigo_http(exc)


@router.get(f"{RUTA_LOTES}/{{lote_id}}", response_model=LoteRead)
def leer_lote(lote_id: int, db: Session = Depends(get_db)) -> LoteRead:
    """Devuelve el lote con el `id` indicado, con sus claves foráneas."""
    try:
        return services.obtener_lote(db, lote_id)
    except services.LoteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.patch(f"{RUTA_LOTES}/{{lote_id}}", response_model=LoteRead)
def editar_lote(
    lote_id: int,
    datos: LoteUpdate,
    db: Session = Depends(get_db),
) -> LoteRead:
    """Modifica solo los atributos enviados con valor."""
    try:
        return services.actualizar_lote(db, lote_id, datos)
    except services.LoteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.delete(
    f"{RUTA_LOTES}/{{lote_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def eliminar_lote(lote_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra únicamente el lote; lo que referencie permanece intacto."""
    try:
        services.eliminar_lote(db, lote_id)
    except services.LoteNoEncontrado as exc:
        _a_codigo_http(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(f"{RUTA_LOTES}/{{lote_id}}/kg-reales", response_model=LoteRead)
def actualizar_kg_reales(
    lote_id: int,
    datos: LoteKgRealesUpdate,
    db: Session = Depends(get_db),
) -> LoteRead:
    """Actualiza los kilos reales de un lote.

    Propaga la diferencia a kg_disponibles si el nuevo valor es mayor.
    """
    try:
        return services.actualizar_kg_reales(db, lote_id, datos)
    except services.LoteNoEncontrado as exc:
        _a_codigo_http(exc)


@router.patch(f"{RUTA_LOTES}/{{lote_id}}/kg-disponibles", response_model=LoteRead)
def actualizar_kg_disponibles(
    lote_id: int,
    datos: LoteKgDisponiblesUpdate,
    db: Session = Depends(get_db),
) -> LoteRead:
    """Actualiza los kilos disponibles de un lote.

    Valida que kg_disponibles no exceda kg_reales.
    """
    try:
        return services.actualizar_kg_disponibles(db, lote_id, datos)
    except (services.LoteNoEncontrado, services.KgDisponiblesExcedeKgReales) as exc:
        _a_codigo_http(exc)


@router.patch(f"{RUTA_LOTES}/{{lote_id}}/estado", response_model=LoteRead)
def actualizar_estado(
    lote_id: int,
    datos: LoteEstadoUpdate,
    db: Session = Depends(get_db),
) -> LoteRead:
    """Actualiza el estado de un lote."""
    try:
        return services.actualizar_estado(db, lote_id, datos)
    except services.LoteNoEncontrado as exc:
        _a_codigo_http(exc)
