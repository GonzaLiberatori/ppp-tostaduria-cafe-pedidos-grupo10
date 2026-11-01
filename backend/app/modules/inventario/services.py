"""Reglas de negocio y frontera transaccional de ``TipoDeCafe``.

Es la única capa que otros módulos pueden importar. No conoce HTTP: lanza
excepciones de dominio y el router las traduce a códigos de estado.

Las validaciones de forma (rango de precio, longitud de los nombres, atributos
desconocidos) las hace Pydantic antes de llegar acá, así que este módulo no las
repite.
"""

from decimal import Decimal
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.inventario import crud
from app.modules.inventario.models import Blend, Lote, LoteEstado, LoteTipo, TipoDeCafe
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
from app.modules.inventario.schemas_panel import (
    BolsaPanelCreate,
    BolsaPanelRead,
    BolsaPanelUpdate,
    StockPanelCreate,
    StockPanelRead,
    StockPanelUpdate,
)
from app.modules.produccion.models import OrdenTueste, PerfilDeTostado


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


# ---------------------------------------------------------------------------
# Panel de stock: cafés con bolsas
#
# El identificador plano tiene la forma ``tc-<id>-<TIPO>`` para un TipoDeCafe y
# ``bl-<id>-<TIPO>`` para un Blend. Así una misma variedad puede mostrarse como
# café verde y como café tostado sin mezclar sus bolsas.
# ---------------------------------------------------------------------------
class StockItemNoEncontrado(Exception):
    """El identificador plano no corresponde a ningún café del stock."""

    def __init__(self, stock_id: str) -> None:
        self.stock_id = stock_id
        super().__init__(f"No existe stock con identificador '{stock_id}'.")


class StockItemInvalido(Exception):
    """El identificador plano no tiene el formato esperado."""

    def __init__(self, stock_id: str) -> None:
        self.stock_id = stock_id
        super().__init__(
            f"Identificador de stock inválido: '{stock_id}'. "
            "Se esperaba 'tc-<id>-<TIPO>' o 'bl-<id>-<TIPO>'."
        )


class TipoDeStockInmutable(Exception):
    """El tipo (verde/tostado) de un café no se puede cambiar."""

    def __init__(self) -> None:
        super().__init__(
            "El tipo de un café no se puede modificar: eliminá el café y creá uno nuevo."
        )


class BolsaNoEncontrada(Exception):
    """El id recibido no corresponde a ninguna bolsa."""

    def __init__(self, bolsa_id: int) -> None:
        self.bolsa_id = bolsa_id
        super().__init__(f"No existe una bolsa con id {bolsa_id}.")


class BolsaNoPerteneceAlStock(Exception):
    """La bolsa existe pero pertenece a otro café."""

    def __init__(self, bolsa_id: int, stock_id: str) -> None:
        self.bolsa_id = bolsa_id
        self.stock_id = stock_id
        super().__init__(f"La bolsa {bolsa_id} no pertenece al stock '{stock_id}'.")


_TIPOS_STOCK = {
    "verde": LoteTipo.VERDE,
    "tostado": LoteTipo.TOSTADO,
    "VERDE": LoteTipo.VERDE,
    "TOSTADO": LoteTipo.TOSTADO,
}

_ESTADOS_BOLSA = {
    "cerrada": LoteEstado.CERRADO,
    "abierta": LoteEstado.ABIERTO,
    "CERRADO": LoteEstado.CERRADO,
    "ABIERTO": LoteEstado.ABIERTO,
}


def _normalizar_tipo_stock(valor: str) -> LoteTipo:
    """Convierte 'verde'/'tostado' o los valores canónicos a LoteTipo."""
    tipo = _TIPOS_STOCK.get((valor or "").strip())
    if tipo is None:
        raise ValueError("Tipo de stock inválido. Debe ser verde o tostado.")
    return tipo


def _normalizar_estado_bolsa(valor: str) -> LoteEstado:
    """Convierte 'cerrada'/'abierta' o los valores canónicos a LoteEstado."""
    estado = _ESTADOS_BOLSA.get((valor or "").strip())
    if estado is None:
        raise ValueError("Estado de bolsa inválido. Debe ser cerrada o abierta.")
    return estado


def _nombre_tipo(tipo: LoteTipo) -> str:
    return "VERDE" if tipo == LoteTipo.VERDE else "TOSTADO"


def parsear_stock_id(stock_id: str) -> tuple[str, int, LoteTipo]:
    """Parte un identificador plano en ``(origen, id, tipo)``.

    Es pública porque el módulo de pedidos la usa para traducir el ``stockId``
    que envía el panel a las claves canónicas del detalle.
    """
    partes = (stock_id or "").split("-")
    if len(partes) != 3:
        raise StockItemInvalido(stock_id)

    origen, id_texto, tipo_texto = partes
    if origen not in {"tc", "bl"}:
        raise StockItemInvalido(stock_id)

    try:
        entidad_id = int(id_texto)
    except ValueError:
        raise StockItemInvalido(stock_id) from None

    tipo = _TIPOS_STOCK.get(tipo_texto)
    if tipo is None:
        raise StockItemInvalido(stock_id)

    return origen, entidad_id, tipo


def _obtener_origen(db: Session, origen: str, entidad_id: int):
    """Devuelve el TipoDeCafe o Blend del identificador plano."""
    entidad = (
        crud.obtener_tipo_de_cafe(db, entidad_id)
        if origen == "tc"
        else crud.obtener_blend(db, entidad_id)
    )
    if entidad is None:
        raise StockItemNoEncontrado(f"{origen}-{entidad_id}")
    return entidad


def _resolver_stock_id(db: Session, stock_id: str):
    """Devuelve ``(origen, entidad, tipo)`` a partir del identificador plano."""
    origen, entidad_id, tipo = parsear_stock_id(stock_id)
    entidad = _obtener_origen(db, origen, entidad_id)
    return origen, entidad, tipo


def _filtro_origen(origen: str, entidad_id: int):
    """Condición SQLAlchemy que selecciona los lotes de un origen."""
    if origen == "tc":
        return Lote.tipo_de_cafe_id == entidad_id
    return Lote.blend_id == entidad_id


def _lotes_de(db: Session, origen: str, entidad_id: int, tipo: LoteTipo) -> list[Lote]:
    """Lotes de un origen y tipo, ordenados por ingreso (FIFO)."""
    return (
        db.query(Lote)
        .filter(
            _filtro_origen(origen, entidad_id),
            Lote.tipo == tipo,
        )
        .order_by(Lote.fecha_ingreso, Lote.id)
        .all()
    )


def _a_bolsa(lote: Lote) -> BolsaPanelRead:
    return BolsaPanelRead(
        id=str(lote.id),
        estado="abierta" if lote.estado == LoteEstado.ABIERTO else "cerrada",
        kilos=float(lote.kg_disponibles or 0),
        fechaCreacion=lote.fecha_ingreso or datetime.utcnow(),
        loteRef=lote.codigo_lote or f"LOTE-{lote.id}",
    )


def _a_stock(
    origen: str,
    entidad: TipoDeCafe | Blend,
    tipo: LoteTipo,
    lotes: list[Lote],
) -> StockPanelRead:
    es_tipo_de_cafe = origen == "tc"
    variedad = entidad.variedad if es_tipo_de_cafe else entidad.nombre
    origen_texto = (
        f"{entidad.pais} - {entidad.region}"
        if es_tipo_de_cafe
        else entidad.descripcion
    )
    fecha_ingreso = min(
        (lote.fecha_ingreso for lote in lotes if lote.fecha_ingreso),
        default=datetime.utcnow(),
    )
    lote_principal = next(
        (lote.codigo_lote for lote in lotes if lote.codigo_lote),
        f"LOTE-{entidad.id}",
    )

    return StockPanelRead(
        id=f"{origen}-{entidad.id}-{_nombre_tipo(tipo)}",
        tipo="verde" if tipo == LoteTipo.VERDE else "tostado",
        variedad=variedad,
        origen=origen_texto,
        precioKg=float(entidad.precio_por_kg_verde),
        lotePrincipal=lote_principal,
        fechaIngreso=fecha_ingreso,
        bolsas=[_a_bolsa(lote) for lote in lotes],
    )


def _perfil_de_tostado_por_defecto(db: Session) -> PerfilDeTostado:
    """Devuelve el perfil de tueste por defecto, creándolo si no existe."""
    perfil = (
        db.query(PerfilDeTostado)
        .filter(PerfilDeTostado.variante == "Medio")
        .first()
    )
    if perfil is None:
        perfil = PerfilDeTostado(variante="Medio", valor_agregado_por_kg=Decimal("0"))
        db.add(perfil)
        db.flush()
    return perfil


def _crear_orden_tueste(db: Session, kilos_obtenidos: Decimal) -> OrdenTueste:
    """Crea una orden de tueste con una merma estimada del 15 %."""
    perfil = _perfil_de_tostado_por_defecto(db)
    kg_gastados = (kilos_obtenidos / Decimal("0.85")).quantize(Decimal("0.01"))
    orden = OrdenTueste(
        fecha_tueste=datetime.utcnow(),
        kg_gastados=kg_gastados,
        kg_obtenidos=kilos_obtenidos,
        perfil_de_tostado_id=perfil.id,
    )
    db.add(orden)
    db.flush()
    return orden


def _nuevo_lote(
    db: Session,
    origen: str,
    entidad_id: int,
    tipo: LoteTipo,
    datos: BolsaPanelCreate,
    codigo_lote: str,
    orden_tueste_id: int | None = None,
) -> Lote:
    """Crea el lote (bolsa) con los valores por defecto del panel."""
    ahora = datetime.utcnow()
    lote = Lote(
        codigo_lote=codigo_lote,
        fecha_ingreso=ahora,
        tipo=tipo,
        estado=_normalizar_estado_bolsa(datos.estado),
        fecha_vencimiento=ahora + timedelta(days=365),
        humedad=Decimal("12.00"),
        kg_disponibles=datos.kilos,
        kg_reales=datos.kilos,
        ubicacion_fisica="Depósito principal",
        observaciones=None,
        tipo_de_cafe_id=entidad_id if origen == "tc" else None,
        blend_id=entidad_id if origen == "bl" else None,
        orden_tueste_id=orden_tueste_id,
    )
    db.add(lote)
    db.flush()
    return lote


def _partir_origen(origen: str) -> tuple[str, str]:
    """Parte 'País - Región' en (país, región)."""
    partes = [parte.strip() for parte in re.split(r"\s*[-–,]\s*", origen, maxsplit=1)]
    pais = partes[0] or "Sin especificar"
    region = partes[1] if len(partes) > 1 and partes[1] else pais
    return pais, region


def listar_stock(db: Session) -> list[StockPanelRead]:
    """Lista todos los cafés con bolsas agrupados por origen y tipo."""
    grupos: dict[tuple[str, int, LoteTipo], list[Lote]] = {}

    for lote in db.query(Lote).order_by(Lote.fecha_ingreso, Lote.id).all():
        if lote.tipo_de_cafe_id is not None:
            clave = ("tc", lote.tipo_de_cafe_id, lote.tipo)
        elif lote.blend_id is not None:
            clave = ("bl", lote.blend_id, lote.tipo)
        else:
            continue
        grupos.setdefault(clave, []).append(lote)

    items: list[StockPanelRead] = []
    for (origen, entidad_id, tipo), lotes in grupos.items():
        entidad = _obtener_origen(db, origen, entidad_id)
        items.append(_a_stock(origen, entidad, tipo, lotes))

    items.sort(key=lambda item: (item.tipo, item.variedad.lower()))
    return items


def obtener_stock(db: Session, stock_id: str) -> StockPanelRead:
    """Devuelve un café del panel por su identificador plano."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)
    lotes = _lotes_de(db, origen, entidad.id, tipo)
    if not lotes:
        raise StockItemNoEncontrado(stock_id)
    return _a_stock(origen, entidad, tipo, lotes)


def crear_stock(db: Session, datos: StockPanelCreate) -> StockPanelRead:
    """Crea el TipoDeCafe y sus bolsas iniciales en una sola transacción."""
    tipo = _normalizar_tipo_stock(datos.tipo)
    pais, region = _partir_origen(datos.origen)

    try:
        entidad = TipoDeCafe(
            organico=False,
            precio_por_kg_verde=datos.precioKg,
            variedad=datos.variedad,
            region=region,
            pais=pais,
        )
        db.add(entidad)
        db.flush()

        total_kilos = sum((bolsa.kilos for bolsa in datos.bolsas), Decimal("0"))
        orden = (
            _crear_orden_tueste(db, total_kilos)
            if tipo == LoteTipo.TOSTADO
            else None
        )

        for indice, bolsa in enumerate(datos.bolsas, start=1):
            _nuevo_lote(
                db,
                "tc",
                entidad.id,
                tipo,
                bolsa,
                codigo_lote=bolsa.loteRef or f"{datos.lotePrincipal}-{indice:02d}",
                orden_tueste_id=orden.id if orden else None,
            )

        db.commit()
        db.refresh(entidad)
    except Exception:
        db.rollback()
        raise

    return obtener_stock(db, f"tc-{entidad.id}-{_nombre_tipo(tipo)}")


def actualizar_stock(
    db: Session, stock_id: str, datos: StockPanelUpdate
) -> StockPanelRead:
    """Actualiza los datos del café y el código del primer lote."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)

    if datos.tipo is not None and _normalizar_tipo_stock(datos.tipo) != tipo:
        raise TipoDeStockInmutable()

    try:
        if datos.precioKg is not None:
            entidad.precio_por_kg_verde = datos.precioKg

        if origen == "tc":
            if datos.variedad is not None:
                entidad.variedad = datos.variedad
            if datos.origen is not None:
                entidad.pais, entidad.region = _partir_origen(datos.origen)
        else:
            if datos.variedad is not None:
                entidad.nombre = datos.variedad
            if datos.origen is not None:
                entidad.descripcion = datos.origen

        if datos.lotePrincipal is not None:
            lotes = _lotes_de(db, origen, entidad.id, tipo)
            if lotes:
                lotes[0].codigo_lote = datos.lotePrincipal

        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_stock(db, stock_id)


def eliminar_stock(db: Session, stock_id: str) -> None:
    """Borra las bolsas de un café. El catálogo del origen se conserva."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)

    try:
        db.query(Lote).filter(
            _filtro_origen(origen, entidad.id),
            Lote.tipo == tipo,
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise


def agregar_bolsa(
    db: Session, stock_id: str, datos: BolsaPanelCreate
) -> BolsaPanelRead:
    """Agrega una bolsa al café indicado."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)
    cantidad = len(_lotes_de(db, origen, entidad.id, tipo)) + 1

    try:
        orden = _crear_orden_tueste(db, datos.kilos) if tipo == LoteTipo.TOSTADO else None
        lote = _nuevo_lote(
            db,
            origen,
            entidad.id,
            tipo,
            datos,
            codigo_lote=datos.loteRef or f"LOTE-{entidad.id}-{cantidad:02d}",
            orden_tueste_id=orden.id if orden else None,
        )
        db.commit()
        db.refresh(lote)
    except Exception:
        db.rollback()
        raise

    return _a_bolsa(lote)


def _obtener_bolsa_del_stock(
    db: Session, origen: str, entidad_id: int, tipo: LoteTipo, bolsa_id: int
) -> Lote:
    lote = db.get(Lote, bolsa_id)
    if lote is None:
        raise BolsaNoEncontrada(bolsa_id)

    pertenece = (
        lote.tipo_de_cafe_id == entidad_id
        if origen == "tc"
        else lote.blend_id == entidad_id
    )
    if not pertenece or lote.tipo != tipo:
        raise BolsaNoPerteneceAlStock(bolsa_id, f"{origen}-{entidad_id}-{_nombre_tipo(tipo)}")

    return lote


def actualizar_bolsa(
    db: Session, stock_id: str, bolsa_id: int, datos: BolsaPanelUpdate
) -> BolsaPanelRead:
    """Actualiza estado, kilos y código de una bolsa."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)
    lote = _obtener_bolsa_del_stock(db, origen, entidad.id, tipo, bolsa_id)

    try:
        if datos.estado is not None:
            lote.estado = _normalizar_estado_bolsa(datos.estado)
        if datos.kilos is not None:
            lote.kg_reales = datos.kilos
            lote.kg_disponibles = datos.kilos
        if datos.loteRef is not None:
            lote.codigo_lote = datos.loteRef or None

        db.commit()
        db.refresh(lote)
    except Exception:
        db.rollback()
        raise

    return _a_bolsa(lote)


def eliminar_bolsa(db: Session, stock_id: str, bolsa_id: int) -> None:
    """Elimina una bolsa del café indicado."""
    origen, entidad, tipo = _resolver_stock_id(db, stock_id)
    lote = _obtener_bolsa_del_stock(db, origen, entidad.id, tipo, bolsa_id)

    try:
        db.delete(lote)
        db.commit()
    except Exception:
        db.rollback()
        raise
