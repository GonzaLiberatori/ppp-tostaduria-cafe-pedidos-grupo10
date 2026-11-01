"""Reglas de negocio y frontera transaccional de ``TipoDeCafe``.

Es la única capa que otros módulos pueden importar. No conoce HTTP: lanza
excepciones de dominio y el router las traduce a códigos de estado.

Las validaciones de forma (rango de precio, longitud de los nombres, atributos
desconocidos) las hace Pydantic antes de llegar acá, así que este módulo no las
repite.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.inventario import crud
from app.modules.inventario.models import (
    Blend,
    Lote,
    LoteEstado,
    LoteTipo,
    TipoDeCafe,
)
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


class KgDisponiblesExcedeKgReales(Exception):
    """Los kg disponibles no pueden superar los kg reales del lote."""

    def __init__(self, kg_disponibles: Decimal, kg_reales: Decimal) -> None:
        self.kg_disponibles = kg_disponibles
        self.kg_reales = kg_reales
        super().__init__(
            f"Los kg disponibles ({kg_disponibles}) no pueden superar los kg reales ({kg_reales})."
        )


class StockVerdeInsuficiente(Exception):
    """No hay suficiente café verde abierto para cubrir el consumo solicitado."""

    def __init__(
        self, tipo_de_cafe_id: int, solicitado: Decimal, disponible: Decimal
    ) -> None:
        self.tipo_de_cafe_id = tipo_de_cafe_id
        self.solicitado = solicitado
        self.disponible = disponible
        super().__init__(
            f"Stock verde insuficiente para el tipo de café {tipo_de_cafe_id}: "
            f"se solicitan {solicitado} kg y hay {disponible} kg disponibles."
        )


@dataclass(frozen=True)
class ConsumoDeLoteVerde:
    """Consumo aplicado a un lote verde concreto durante una operación."""

    lote_id: int
    kg_consumidos: Decimal


@dataclass(frozen=True)
class LoteTostadoCreado:
    """Datos mínimos del lote tostado creado por una orden de tueste."""

    id: int
    tipo_de_cafe_id: int
    kg_reales: Decimal


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
def _crear_lote_sin_commit(db: Session, datos: LoteCreate) -> Lote:
    """Crea un lote y lo deja en la transacción abierta, sin confirmarla.

    El schema ya garantizó que viene exactamente un origen; acá solo falta
    comprobar que ese registro exista. La derivación de ``kg_disponibles``
    también vive acá para que no haya dos fuentes de verdad del mismo número.
    """
    if datos.tipo_de_cafe_id is not None:
        entidad_origen, origen_id = TipoDeCafe, datos.tipo_de_cafe_id
    else:
        entidad_origen, origen_id = Blend, datos.blend_id

    if not crud.existe_registro(db, entidad_origen, origen_id):
        raise OrigenDeLoteNoEncontrado(entidad_origen.__name__, origen_id)

    return crud.crear_lote(db, datos, kg_disponibles=datos.kg_reales)


def crear_lote(db: Session, datos: LoteCreate) -> LoteRead:
    """Da de alta un lote en una sola transacción."""
    try:
        lote = _crear_lote_sin_commit(db, datos)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


def consumir_stock_verde_fifo(
    db: Session, tipo_de_cafe_id: int, kg: Decimal
) -> list[ConsumoDeLoteVerde]:
    """Descuenta café verde de los lotes abiertos en orden FIFO.

    No hace commit: la transacción completa pertenece a quien orquesta la
    operación. Si el stock no alcanza, lanza ``StockVerdeInsuficiente`` antes
    de modificar cualquier lote.
    """
    if kg <= 0:
        raise ValueError("La cantidad de café verde a consumir debe ser mayor que cero.")

    if not crud.existe_registro(db, TipoDeCafe, tipo_de_cafe_id):
        raise TipoDeCafeNoEncontrado(tipo_de_cafe_id)

    lotes = crud.listar_lotes_verdes_fifo(db, tipo_de_cafe_id)
    disponible = sum(
        (Decimal(lote.kg_disponibles) for lote in lotes), Decimal("0")
    )

    if disponible < kg:
        raise StockVerdeInsuficiente(tipo_de_cafe_id, kg, disponible)

    consumo: list[ConsumoDeLoteVerde] = []
    restante = kg

    for lote in lotes:
        if restante <= 0:
            break

        consumido = min(Decimal(lote.kg_disponibles), restante)
        nuevo_disponible = Decimal(lote.kg_disponibles) - consumido
        crud.actualizar_kg_disponibles(db, lote, nuevo_disponible)

        if nuevo_disponible == 0:
            crud.actualizar_estado(db, lote, LoteEstado.CERRADO)

        consumo.append(
            ConsumoDeLoteVerde(lote_id=lote.id, kg_consumidos=consumido)
        )
        restante -= consumido

    return consumo


def crear_lote_tostado_de_tueste(
    db: Session,
    *,
    tipo_de_cafe_id: int,
    kg_reales: Decimal,
    orden_tueste_id: int,
    fecha_vencimiento: datetime,
    humedad: Decimal,
    ubicacion_fisica: str,
    observaciones: str | None = None,
) -> LoteTostadoCreado:
    """Crea el lote TOSTADO que sale de una orden de tueste, sin commit.

    La orden ya debe existir y estar flusheada para que su ``id`` esté
    disponible. El lote nace abierto y con todos sus kilos disponibles.
    """
    datos = LoteCreate(
        tipo=LoteTipo.TOSTADO,
        estado=LoteEstado.ABIERTO,
        fecha_vencimiento=fecha_vencimiento,
        humedad=humedad,
        kg_reales=kg_reales,
        ubicacion_fisica=ubicacion_fisica,
        observaciones=observaciones,
        tipo_de_cafe_id=tipo_de_cafe_id,
        orden_tueste_id=orden_tueste_id,
    )
    lote = _crear_lote_sin_commit(db, datos)

    return LoteTostadoCreado(
        id=lote.id,
        tipo_de_cafe_id=tipo_de_cafe_id,
        kg_reales=kg_reales,
    )


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


# ---------------------------------------------------------------------------
# Actualizaciones puntuales de Lote
# ---------------------------------------------------------------------------
def actualizar_kg_reales(db: Session, lote_id: int, datos: LoteKgRealesUpdate) -> LoteRead:
    """Actualiza los kilos reales de un lote.

    Si el nuevo valor es mayor al actual, propaga la diferencia a `kg_disponibles`.
    Si es menor o igual, no toca `kg_disponibles`.
    """
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    try:
        diferencia = datos.kg_reales - lote.kg_reales

        if diferencia > 0:
            crud.actualizar_kg_disponibles(db, lote, lote.kg_disponibles + diferencia)

        crud.actualizar_kg_reales(db, lote, datos.kg_reales)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


def actualizar_kg_disponibles(
    db: Session, lote_id: int, datos: LoteKgDisponiblesUpdate
) -> LoteRead:
    """Actualiza los kilos disponibles de un lote.

    Valida que `kg_disponibles` no exceda `kg_reales` del lote.
    """
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    if datos.kg_disponibles > lote.kg_reales:
        raise KgDisponiblesExcedeKgReales(datos.kg_disponibles, lote.kg_reales)

    try:
        crud.actualizar_kg_disponibles(db, lote, datos.kg_disponibles)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


def actualizar_estado(db: Session, lote_id: int, datos: LoteEstadoUpdate) -> LoteRead:
    """Actualiza el estado de un lote."""
    lote = crud.obtener_lote(db, lote_id)

    if lote is None:
        raise LoteNoEncontrado(lote_id)

    try:
        crud.actualizar_estado(db, lote, datos.estado)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LoteRead.model_validate(lote)


# ---------------------------------------------------------------------------
# Listados
# ---------------------------------------------------------------------------
def listar_tipos_de_cafe(db: Session) -> list[TipoDeCafeRead]:
    """Lista todos los tipos de café registrados."""
    tipos = crud.listar_tipos_de_cafe(db)
    return [TipoDeCafeRead.model_validate(tipo) for tipo in tipos]


def listar_blends(db: Session) -> list[BlendRead]:
    """Lista todos los blends registrados con sus composiciones."""
    blends = crud.listar_blends(db)
    return [BlendRead.desde_orm(blend) for blend in blends]


class FiltroLotesInvalido(Exception):
    """El filtrado de lotes requiere exactamente uno de los dos parámetros."""

    def __init__(self) -> None:
        super().__init__(
            "Debe proporcionar exactamente uno de tipo_de_cafe_id o blend_id, no ambos ni ninguno."
        )


def listar_lotes(
    db: Session,
    tipo_de_cafe_id: int | None = None,
    blend_id: int | None = None,
) -> list[LoteRead]:
    """Lista los lotes filtrados por tipo_de_cafe_id o blend_id (XOR)."""
    # Validación XOR: exactamente uno debe tener valor
    if (tipo_de_cafe_id is None) == (blend_id is None):
        raise FiltroLotesInvalido()

    lotes = crud.listar_lotes(db, tipo_de_cafe_id=tipo_de_cafe_id, blend_id=blend_id)
    return [LoteRead.model_validate(lote) for lote in lotes]
