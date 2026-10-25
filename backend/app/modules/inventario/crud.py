"""Acceso a datos del módulo de inventario sobre ``TipoDeCafe``.

Consultas puras: sin reglas de negocio y sin commits. Tanto la decisión de qué
operaciones proceden como la frontera transaccional viven en ``services.py``.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventario.models import BlendHasTipoDeCafe, Lote, TipoDeCafe
from app.modules.inventario.schemas import TipoDeCafeCreate

# Entidades que impiden el borrado de un TipoDeCafe. El guard las recorre TODAS
# en lugar de elegir una: un tipo de café puede estar en un blend y tener lotes
# a la vez, y el aviso de bloqueo debe poder nombrar a las dos.
#
# Cuando `pedidos` defina `detalle_pedido` con `tipo_de_cafe_id` como FK, basta
# con agregarla a esta tupla: `cuentas_de_referencias` la cubre sin más cambios.
REFERENCIAS_PROHIBIDAS: tuple[type, ...] = (BlendHasTipoDeCafe, Lote)

# Nombre de la columna FK en todas las entidades referenciadoras.
_COLUMNA_TIPO_DE_CAFE = "tipo_de_cafe_id"


def obtener_tipo_de_cafe(db: Session, tipo_id: int) -> TipoDeCafe | None:
    """Devuelve el tipo de café con ese ``id``, o ``None`` si no existe."""
    return db.get(TipoDeCafe, tipo_id)


def crear_tipo_de_cafe(db: Session, datos: TipoDeCafeCreate) -> TipoDeCafe:
    """Da de alta un tipo de café y lo devuelve con el ``id`` ya asignado."""
    tipo = TipoDeCafe(
        organico=datos.organico,
        precio_por_kg_verde=datos.precio_por_kg_verde,
        variedad=datos.variedad,
        region=datos.region,
        pais=datos.pais,
    )
    db.add(tipo)
    db.flush()
    return tipo


def actualizar_tipo_de_cafe(db: Session, tipo: TipoDeCafe, cambios: dict[str, Any]) -> TipoDeCafe:
    """Aplica solo las claves recibidas, en el orden en que vengan.

    No hace commit: quién decide qué se modifica es el servicio.
    """
    for atributo, valor in cambios.items():
        setattr(tipo, atributo, valor)
    db.flush()
    return tipo


def eliminar_tipo_de_cafe(db: Session, tipo: TipoDeCafe) -> None:
    """Marca el registro para borrado. No hace commit."""
    db.delete(tipo)
    db.flush()


def cuentas_de_referencias(db: Session, tipo_id: int) -> dict[str, int]:
    """Cuenta cuántas filas de cada entidad referenciadora bloquean el borrado.

    Devuelve un contador por entidad, con ceros incluidos, para que quien llama
    pueda distinguir "no lo referencia nadie" de "solo lo referencia uno".
    """
    cuentas: dict[str, int] = {}

    for entidad in REFERENCIAS_PROHIBIDAS:
        columna = entidad.__table__.c[_COLUMNA_TIPO_DE_CAFE]
        total = db.scalar(select(func.count()).select_from(entidad).where(columna == tipo_id))
        cuentas[entidad.__name__] = int(total or 0)

    return cuentas
