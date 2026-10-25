"""Reglas de negocio y frontera transaccional de ``TipoDeCafe``.

Es la única capa que otros módulos pueden importar. No conoce HTTP: lanza
excepciones de dominio y el router las traduce a códigos de estado.

Las validaciones de forma (rango de precio, longitud de los nombres, atributos
desconocidos) las hace Pydantic antes de llegar acá, así que este módulo no las
repite.
"""

from sqlalchemy.orm import Session

from app.modules.inventario import crud
from app.modules.inventario.schemas import TipoDeCafeCreate, TipoDeCafeRead, TipoDeCafeUpdate


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

    cuentas = crud.cuentas_de_referencias(db, tipo_id)
    bloqueantes = [nombre for nombre, total in cuentas.items() if total > 0]

    if bloqueantes:
        raise TipoDeCafeReferenciado(bloqueantes)

    try:
        crud.eliminar_tipo_de_cafe(db, tipo)
        db.commit()
    except Exception:
        db.rollback()
        raise
