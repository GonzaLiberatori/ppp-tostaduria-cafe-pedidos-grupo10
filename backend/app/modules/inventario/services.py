"""Reglas de negocio y frontera transaccional de ``TipoDeCafe``.

Es la única capa que otros módulos pueden importar. No conoce HTTP: lanza
excepciones de dominio y el router las traduce a códigos de estado.

Las validaciones de forma (rango de precio, longitud de los nombres, atributos
desconocidos) las hace Pydantic antes de llegar acá, así que este módulo no las
repite.
"""

from sqlalchemy.orm import Session

from app.modules.inventario import crud
from app.modules.inventario.models import Blend, Lote, TipoDeCafe
from app.modules.inventario.schemas import (
    BlendCreate,
    BlendRead,
    BlendUpdate,
    LoteCreate,
    LoteRead,
    LoteUpdate,
    TipoDeCafeCreate,
    TipoDeCafeRead,
    TipoDeCafeUpdate,
)


class TipoDeCafeNoEncontrado(Exception):
    """El ``id`` recibido no corresponde a ningún tipo de café."""

    def __init__(self, tipo_id: int) -> None:
        self.tipo_id = tipo_id
        super().__init__(f"No existe un tipo de café con id {tipo_id}.")


class TipoDeCafeReferenciado(Exception):
    """El tipo de café no se puede borrar porque otras entidades lo referencian."""

    def __init__(self, entidades: list[str]) -> None:
        self.entidades = entidades
        bloqueantes = ", ".join(entidades)
        super().__init__(f"No se puede eliminar el tipo de café: lo referencian {bloqueantes}.")


class BlendNoEncontrado(Exception):
    """El ``id`` recibido no corresponde a ningún blend."""

    def __init__(self, blend_id: int) -> None:
        self.blend_id = blend_id
        super().__init__(f"No existe un blend con id {blend_id}.")


class BlendReferenciado(Exception):
    """El blend no se puede borrar porque otra entidad lo referencia."""

    def __init__(self, entidades: list[str]) -> None:
        self.entidades = entidades
        bloqueantes = ", ".join(entidades)
        super().__init__(f"No se puede eliminar el blend: lo referencian {bloqueantes}.")


class NombreDeBlendEnUso(Exception):
    """El nombre enviado ya pertenece a otro blend."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        super().__init__(f"Ya existe un blend con el nombre '{nombre}'.")


class LoteNoEncontrado(Exception):
    """El ``id`` recibido no corresponde a ningún lote."""

    def __init__(self, lote_id: int) -> None:
        self.lote_id = lote_id
        super().__init__(f"No existe un lote con id {lote_id}.")


class OrigenDeLoteNoEncontrado(Exception):
    """El origen indicado no corresponde a ningún registro."""

    def __init__(self, entidad: str, entidad_id: int) -> None:
        self.entidad = entidad
        self.entidad_id = entidad_id
        super().__init__(f"No existe {entidad} con id {entidad_id}.")


def crear_tipo_de_cafe(db: Session, datos: TipoDeCafeCreate) -> TipoDeCafeRead:
    """Da de alta un tipo de café en una sola transacción."""
    try:
        tipo = crud.crear_tipo_de_cafe(db, datos)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TipoDeCafeRead.model_validate(tipo)


def obtener_tipo_de_cafe(db: Session, tipo_id: int) -> TipoDeCafeRead:
    """Lee un tipo de café por su ``id``."""
    tipo = crud.obtener_tipo_de_cafe(db, tipo_id)

    if tipo is None:
        raise TipoDeCafeNoEncontrado(tipo_id)

    return TipoDeCafeRead.model_validate(tipo)


def actualizar_tipo_de_cafe(db: Session, tipo_id: int, datos: TipoDeCafeUpdate) -> TipoDeCafeRead:
    """Aplica los atributos con valor, dejando intactos los nulos y los ausentes.

    La existencia se comprueba ANTES de aplicar cambios: con un cuerpo vacío
    sobre un ``id`` inexistente, el orden inverso devolvería un registro
    inexistente en lugar de ``TipoDeCafeNoEncontrado``.
    """
    tipo = crud.obtener_tipo_de_cafe(db, tipo_id)

    if tipo is None:
        raise TipoDeCafeNoEncontrado(tipo_id)

    cambios = datos.model_dump(exclude_none=True)

    if not cambios:
        return TipoDeCafeRead.model_validate(tipo)

    try:
        crud.actualizar_tipo_de_cafe(db, tipo, cambios)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TipoDeCafeRead.model_validate(tipo)


def eliminar_tipo_de_cafe(db: Session, tipo_id: int) -> None:
    """Borra un tipo de café, salvo que otra entidad lo esté usando."""
    tipo = crud.obtener_tipo_de_cafe(db, tipo_id)

    if tipo is None:
        raise TipoDeCafeNoEncontrado(tipo_id)

    cuentas = crud.cuentas_de_referencias(db, TipoDeCafe, tipo_id)
    bloqueantes = [nombre for nombre, total in cuentas.items() if total > 0]

    if bloqueantes:
        raise TipoDeCafeReferenciado(bloqueantes)

    try:
        crud.eliminar_tipo_de_cafe(db, tipo)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Blend
# ---------------------------------------------------------------------------
def crear_blend(db: Session, datos: BlendCreate) -> BlendRead:
    """Da de alta un blend y su composición en una sola transacción."""
    if crud.nombre_de_blend_ya_en_usado(db, datos.nombre):
        raise NombreDeBlendEnUso(datos.nombre)

    try:
        blend = crud.crear_blend(db, datos)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return BlendRead.desde_orm(blend)


def obtener_blend(db: Session, blend_id: int) -> BlendRead:
    """Lee un blend por su ``id``, junto con su composición."""
    blend = crud.obtener_blend(db, blend_id)

    if blend is None:
        raise BlendNoEncontrado(blend_id)

    return BlendRead.desde_orm(blend)


def actualizar_blend(db: Session, blend_id: int, datos: BlendUpdate) -> BlendRead:
    """Aplica los atributos con valor y reemplaza la composición si viene lista.

    La existencia se comprueba ANTES de aplicar cambios: con un cuerpo vacío
    sobre un ``id`` inexistente, el orden inverso devolvería un registro
    inexistente en lugar de ``BlendNoEncontrado``.
    """
    blend = crud.obtener_blend(db, blend_id)

    if blend is None:
        raise BlendNoEncontrado(blend_id)

    composicion = datos.tipos_de_cafe
    cambios = datos.model_dump(exclude_none=True, exclude={"tipos_de_cafe"})

    if not cambios and composicion is None:
        return BlendRead.desde_orm(blend)

    # `excluir_id` es imprescindible: editar sin cambiarle el nombre no es
    # un conflicto del blend consigo mismo.
    if "nombre" in cambios and crud.nombre_de_blend_ya_en_usado(
        db, cambios["nombre"], excluir_id=blend_id
    ):
        raise NombreDeBlendEnUso(cambios["nombre"])

    try:
        if cambios:
            crud.actualizar_blend(db, blend, cambios)

        if composicion is not None:
            crud.reemplazar_composicion(db, blend, composicion)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return BlendRead.desde_orm(blend)


def eliminar_blend(db: Session, blend_id: int) -> None:
    """Borra un blend y su composición, salvo que una entidad externa lo use.

    La composición propia no bloquea: son los hijos del blend, se borran juntos.
    """
    blend = crud.obtener_blend(db, blend_id)

    if blend is None:
        raise BlendNoEncontrado(blend_id)

    cuentas = crud.cuentas_de_referencias(db, Blend, blend_id)
    bloqueantes = [nombre for nombre, total in cuentas.items() if total > 0]

    if bloqueantes:
        raise BlendReferenciado(bloqueantes)

    try:
        crud.eliminar_composicion(db, blend)
        crud.eliminar_blend(db, blend)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------
def crear_lote(db: Session, datos: LoteCreate) -> LoteRead:
    """Da de alta un lote en una sola transacción.

    El schema ya garantizó que viene exactamente un origen; acá solo falta
    comprobar que ese registro exista. Y de paso se deriva el campo que el
    contrato no pide: `kg_disponibles` arranca igual que `kg_reales`.
    """
    if datos.tipo_de_cafe_id is not None:
        entidad_origen, origen_id = TipoDeCafe, datos.tipo_de_cafe_id
    else:
        entidad_origen, origen_id = Blend, datos.blend_id

    if not crud.existe_registro(db, entidad_origen, origen_id):
        raise OrigenDeLoteNoEncontrado(entidad_origen.__name__, origen_id)

    try:
        lote = crud.crear_lote(db, datos, kg_disponibles=datos.kg_reales)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


def obtener_lote(db: Session, lote_id: int) -> LoteRead:
    """Lee un lote por su ``id``, con las claves foráneas sin resolver."""
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    return LoteRead.model_validate(lote)


def actualizar_lote(db: Session, lote_id: int, datos: LoteUpdate) -> LoteRead:
    """Aplica los atributos con valor.

    La existencia se comprueba ANTES de aplicar cambios: con un cuerpo vacío
    sobre un ``id`` inexistente, el orden inverso devolvería un registro
    inexistente en lugar de ``LoteNoEncontrado``.
    """
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    cambios = datos.model_dump(exclude_none=True)

    if not cambios:
        return LoteRead.model_validate(lote)

    try:
        crud.actualizar_lote(db, lote, cambios)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


def eliminar_lote(db: Session, lote_id: int) -> None:
    """Borra un lote. Nadie lo referencia, así que no hay bloqueos."""
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    try:
        crud.eliminar_lote(db, lote)
        db.commit()
    except Exception:
        db.rollback()
        raise
