"""Acceso a datos del módulo de inventario sobre ``TipoDeCafe`` y ``Blend``.

Consultas puras: sin reglas de negocio y sin commits. Tanto la decisión de qué
operaciones proceden como la frontera transaccional viven en ``services.py``.
"""

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventario.models import (
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    TipoDeCafe,
)
from app.modules.inventario.schemas import (
    BlendComposicionItem,
    BlendCreate,
    LoteCreate,
    TipoDeCafeCreate,
)

# Entidades que impiden el borrado de cada entidad borrable, con la columna FK
# de la que cuelgan. La clave es la pareja (referenciadora, columna): `Lote`
# bloquea a `TipoDeCafe` por `tipo_de_cafe_id` y a `Blend` por `blend_id`, así
# que no alcanza una sola constante de columna.
#
# `BlendHasTipoDeCafe` NO figura en la lista de `Blend`: es la composición
# propia del blend, no un tercero que la use, y se borra antes que él.
#
# Cuando `pedidos` defina `detalle_pedido`, se agrega la pareja correspondiente
# a cada lista sin tocar la lógica.
REFERENCIAS_PROHIBIDAS: dict[type, tuple[tuple[type, str], ...]] = {
    TipoDeCafe: ((BlendHasTipoDeCafe, "tipo_de_cafe_id"), (Lote, "tipo_de_cafe_id")),
    Blend: ((Lote, "blend_id"),),
}


# ---------------------------------------------------------------------------
# TipoDeCafe
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Referencias: compartidas por todas las entidades borrables
# ---------------------------------------------------------------------------
def cuentas_de_referencias(db: Session, entidad_borrable: type, entidad_id: int) -> dict[str, int]:
    """Cuenta cuántas filas de cada entidad referenciadora bloquean el borrado.

    Devuelve un contador por entidad, con ceros incluidos, para que quien llama
    pueda distinguir "no lo referencia nadie" de "solo lo referencia uno".
    """
    cuentas: dict[str, int] = {}

    for referenciadora, columna in REFERENCIAS_PROHIBIDAS.get(entidad_borrable, ()):
        clave_ajena = referenciadora.__table__.c[columna]
        total = db.scalar(select(func.count()).select_from(referenciadora).where(clave_ajena == entidad_id))
        cuentas[referenciadora.__name__] = int(total or 0)

    return cuentas


# ---------------------------------------------------------------------------
# Blend
# ---------------------------------------------------------------------------
def obtener_blend(db: Session, blend_id: int) -> Blend | None:
    """Devuelve el blend con ese ``id``, o ``None`` si no existe."""
    return db.get(Blend, blend_id)


def nombre_de_blend_ya_en_usado(db: Session, nombre: str, excluir_id: Optional[int] = None) -> bool:
    """Consulta si otro blend ya usa ese nombre.

    En edición hay que pasar el ``id`` propio, o editar un blend sin cambiarle
    el nombre se declararía conflicto consigo mismo.
    """
    consulta = select(Blend.id).where(Blend.nombre == nombre)

    if excluir_id is not None:
        consulta = consulta.where(Blend.id != excluir_id)

    return db.scalar(consulta) is not None


def crear_blend(db: Session, datos: BlendCreate) -> Blend:
    """Da de alta un blend y su composición, en esa orden.

    El ``flush`` del blend es obligatorio: sin su ``id`` no hay con qué poblar
    las filas de composición.
    """
    blend = Blend(
        nombre=datos.nombre,
        precio_por_kg_verde=datos.precio_por_kg_verde,
        descripcion=datos.descripcion,
    )
    db.add(blend)
    db.flush()

    _escribir_composicion(db, blend, datos.tipos_de_cafe)
    return blend


def actualizar_blend(db: Session, blend: Blend, cambios: dict[str, Any]) -> Blend:
    """Aplica solo las claves escalares recibidas, sin commit.

    La lista de composición no se pasa por acá: quien la reemplaza es
    ``reemplazar_composicion``.
    """
    for atributo, valor in cambios.items():
        setattr(blend, atributo, valor)
    db.flush()
    return blend


def reemplazar_composicion(db: Session, blend: Blend, items: list[BlendComposicionItem]) -> None:
    """Borra la composición previa y crea una por cada item recibido.

    Se borra antes de crear para no dejar dos composiciones conviviendo si algo
    falla a mitad de camino.
    """
    eliminar_composicion(db, blend)
    _escribir_composicion(db, blend, items)


def eliminar_composicion(db: Session, blend: Blend) -> None:
    """Borra los registros de composición del blend. No hace commit."""
    for fila in list(blend.tipos_de_cafe):
        db.delete(fila)
    db.flush()

    # El SQL borró las filas, pero la colección sigue cargada en memoria con los
    # objetos. Sin este expire, `eliminar_blend` ve hijos "vivos" y SQLAlchemy
    # intenta anular `blend_id` — que forma parte de la clave primaria — y lanza
    # `AssertionError: Dependency rule ... tried to blank-out primary key`.
    db.expire(blend, ["tipos_de_cafe"])


def eliminar_blend(db: Session, blend: Blend) -> None:
    """Marca el blend para borrado. No hace commit."""
    db.delete(blend)
    db.flush()


def _escribir_composicion(db: Session, blend: Blend, items: list[BlendComposicionItem]) -> None:
    """Agrega un ``BlendHasTipoDeCafe`` por item, vía la relación del blend.

    Se agrega por la colección y no con la columna suelta, para que el estado en
    memoria del blend quede consistente sin tener que refrescarlo.
    """
    for item in items:
        blend.tipos_de_cafe.append(
            BlendHasTipoDeCafe(
                tipo_de_cafe_id=item.tipo_de_cafe_id,
                porcentaje=item.porcentaje,
            )
        )
    db.flush()


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------
def obtener_lote(db: Session, lote_id: int) -> Lote | None:
    """Devuelve el lote con ese ``id``, o ``None`` si no existe."""
    return db.get(Lote, lote_id)


def existe_registro(db: Session, entidad: type, entidad_id: int) -> bool:
    """Consulta si existe una fila con esa clave primaria en la tabla dada.

    Genérico a propósito: sirve para el origen del lote hoy y para la tabla de
    `orden_tueste` el día que exista.
    """
    return db.get(entidad, entidad_id) is not None


def crear_lote(db: Session, datos: LoteCreate, kg_disponibles: Decimal) -> Lote:
    """Da de alta un lote.

    ``kg_disponibles`` llega calculado por quien llama: este módulo no decide
    de dónde sale ese número, solo lo persiste.
    """
    lote = Lote(
        tipo=datos.tipo,
        estado=datos.estado,
        fecha_vencimiento=datos.fecha_vencimiento,
        humedad=datos.humedad,
        kg_reales=datos.kg_reales,
        kg_disponibles=kg_disponibles,
        ubicacion_fisica=datos.ubicacion_fisica,
        observaciones=datos.observaciones,
        tipo_de_cafe_id=datos.tipo_de_cafe_id,
        blend_id=datos.blend_id,
        orden_tueste_id=datos.orden_tueste_id,
    )
    db.add(lote)
    db.flush()
    return lote


def actualizar_lote(db: Session, lote: Lote, cambios: dict[str, Any]) -> Lote:
    """Aplica solo las claves recibidas, sin commit.

    No puede incluir ``tipo`` ni las tres claves foráneas: `LoteUpdate` no las
    declara, así que `extra="forbid"` ya las rechaza antes de llegar acá.
    """
    for atributo, valor in cambios.items():
        setattr(lote, atributo, valor)
    db.flush()
    return lote


def eliminar_lote(db: Session, lote: Lote) -> None:
    """Marca el lote para borrado. No hace commit.

    No toca `tipo_de_cafe`, `blend` ni `orden_tueste`: son tablas padre, no hijos.
    """
    db.delete(lote)
    db.flush()
