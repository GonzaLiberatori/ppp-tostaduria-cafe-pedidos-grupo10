"""Tests de las reglas de negocio de Lote en la capa `services`."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.inventario import crud, services
from app.modules.inventario.models import Blend, Lote, LoteEstado, LoteTipo, TipoDeCafe
from app.modules.inventario.schemas import LoteCreate, LoteRead, LoteUpdate

PAYLOAD: dict[str, object] = {
    "tipo": "VERDE",
    "estado": "ABIERTO",
    "fecha_vencimiento": "2026-12-31T08:00:00",
    "humedad": "11.50",
    "kg_reales": "59.80",
    "ubicacion_fisica": "PASILLO-01",
    "tipo_de_cafe_id": 1,
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


def _crear_tipo_de_cafe(db) -> int:
    tipo = TipoDeCafe(
        organico=True,
        precio_por_kg_verde=Decimal("1250.50"),
        variedad="Caturra",
        region="Huila",
        pais="Colombia",
    )
    db.add(tipo)
    db.commit()
    return tipo.id


def _crear_blend(db) -> int:
    blend = Blend(
        nombre="Blend de prueba",
        precio_por_kg_verde=Decimal("900.00"),
        descripcion="Mezcla para el test.",
    )
    db.add(blend)
    db.commit()
    return blend.id


def _dar_de_alta(db, **extra) -> LoteRead:
    return services.crear_lote(db, LoteCreate(**{**PAYLOAD, **extra}))


def _hay_lotes(db) -> int:
    return int(db.scalar(select(func.count()).select_from(Lote)) or 0)


@pytest.fixture
def origen(db) -> int:
    """Crea el tipo de café que el payload referencia."""
    return _crear_tipo_de_cafe(db)


# ---------------------------------------------------------------------------
# 3.1 Excepciones de dominio
# ---------------------------------------------------------------------------
def test_excepcion_lote_no_encontrado_carga_el_identificador():
    exc = services.LoteNoEncontrado(42)
    assert exc.lote_id == 42
    assert "42" in str(exc)


def test_excepcion_de_origen_carga_entidad_e_id():
    exc = services.OrigenDeLoteNoEncontrado("TipoDeCafe", 9)
    assert exc.entidad == "TipoDeCafe"
    assert exc.entidad_id == 9
    assert "TipoDeCafe" in str(exc)


# ---------------------------------------------------------------------------
# 3.2 Crear
# ---------------------------------------------------------------------------
def test_crear_deriva_kg_disponibles_de_los_reales(db, origen):
    leido = _dar_de_alta(db)

    assert leido.id is not None
    assert leido.kg_reales == Decimal("59.80")
    assert leido.kg_disponibles == Decimal("59.80")
    assert _hay_lotes(db) == 1


def test_crear_con_kg_reales_en_cero_da_disponibles_en_cero(db, origen):
    leido = _dar_de_alta(db, kg_reales="0")

    assert leido.kg_reales == Decimal("0")
    assert leido.kg_disponibles == Decimal("0")


def test_crear_con_origen_inexistente_lanza_excepcion(db):
    _crear_tipo_de_cafe(db)

    with pytest.raises(services.OrigenDeLoteNoEncontrado) as exc:
        _dar_de_alta(db, tipo_de_cafe_id=999)

    assert exc.value.entidad == "TipoDeCafe"
    assert exc.value.entidad_id == 999
    assert _hay_lotes(db) == 0


def test_crear_con_origen_de_blend(db):
    _crear_blend(db)

    leido = _dar_de_alta(db, tipo_de_cafe_id=None, blend_id=1)

    assert leido.blend_id == 1
    assert leido.tipo_de_cafe_id is None


def test_crear_con_fallo_no_deja_registros_huerfanos(db, origen, monkeypatch):
    """Si falla después de agregar el lote, el rollback no deja nada atrás."""

    def _falla_despues_de_agregar(sesion, datos, kg_disponibles):
        sesion.add(
            Lote(
                tipo=LoteTipo.VERDE,
                estado=LoteEstado.ABIERTO,
                fecha_vencimiento=datetime(2026, 12, 31, 8, 0),
                humedad=Decimal("11.50"),
                kg_disponibles=kg_disponibles,
                kg_reales=datos.kg_reales,
                ubicacion_fisica="X",
                tipo_de_cafe_id=datos.tipo_de_cafe_id,
            )
        )
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(crud, "crear_lote", _falla_despues_de_agregar)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        services.crear_lote(db, LoteCreate(**PAYLOAD))

    assert _hay_lotes(db) == 0


# ---------------------------------------------------------------------------
# 3.3 Leer
# ---------------------------------------------------------------------------
def test_leer_devuelve_el_lote_con_sus_claves(db, origen):
    creado = _dar_de_alta(db)

    leido = services.obtener_lote(db, creado.id)

    assert isinstance(leido, LoteRead)
    assert leido.id == creado.id
    assert leido.tipo_de_cafe_id == origen
    assert leido.blend_id is None
    assert leido.orden_tueste_id is None


def test_leer_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.LoteNoEncontrado) as exc:
        services.obtener_lote(db, 999)

    assert exc.value.lote_id == 999


# ---------------------------------------------------------------------------
# 3.4 Actualizar
# ---------------------------------------------------------------------------
def test_actualizar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.LoteNoEncontrado):
        services.actualizar_lote(db, 999, LoteUpdate(estado="CERRADO"))


def test_actualizar_un_solo_atributo_deja_el_resto_igual(db, origen):
    creado = _dar_de_alta(db)

    leido = services.actualizar_lote(db, creado.id, LoteUpdate(estado="CERRADO"))

    assert leido.estado == LoteEstado.CERRADO
    assert leido.humedad == Decimal("11.50")
    assert leido.kg_reales == Decimal("59.80")
    assert leido.tipo_de_cafe_id == origen


def test_actualizar_atributo_en_null_no_lo_modifica(db, origen):
    creado = _dar_de_alta(db)

    leido = services.actualizar_lote(
        db, creado.id, LoteUpdate(observaciones=None, ubicacion_fisica="PASILLO-09")
    )

    assert leido.observaciones is None
    assert leido.ubicacion_fisica == "PASILLO-09"


def test_actualizar_cuerpo_vacio_no_cambia_nada(db, origen):
    creado = _dar_de_alta(db)

    leido = services.actualizar_lote(db, creado.id, LoteUpdate())

    assert leido.ubicacion_fisica == "PASILLO-01"
    assert _hay_lotes(db) == 1


def test_actualizar_sin_existencia_no_devuelve_un_registro_fantasma(db, origen):
    creado = _dar_de_alta(db)
    assert services.obtener_lote(db, creado.id).id == creado.id

    with pytest.raises(services.LoteNoEncontrado):
        services.actualizar_lote(db, 4242, LoteUpdate())


def test_actualizar_con_humedad_fuera_de_rango_falla_en_el_borde(db, origen):
    creado = _dar_de_alta(db)

    with pytest.raises(Exception):
        services.actualizar_lote(db, creado.id, LoteUpdate(humedad="101"))

    assert services.obtener_lote(db, creado.id).humedad == Decimal("11.50")


def test_actualizar_con_kg_reales_negativos_falla_en_el_borde(db, origen):
    creado = _dar_de_alta(db)

    with pytest.raises(Exception):
        services.actualizar_lote(db, creado.id, LoteUpdate(kg_reales="-1"))

    assert services.obtener_lote(db, creado.id).kg_reales == Decimal("59.80")


# ---------------------------------------------------------------------------
# 3.5 Eliminar
# ---------------------------------------------------------------------------
def test_eliminar_sin_referencias_borra_el_lote(db, origen):
    creado = _dar_de_alta(db)

    services.eliminar_lote(db, creado.id)

    assert _hay_lotes(db) == 0
    assert crud.obtener_lote(db, creado.id) is None


def test_eliminar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.LoteNoEncontrado):
        services.eliminar_lote(db, 999)


def test_eliminar_no_arrasta_al_tipo_de_cafe_referenciado(db):
    """El lote es hoja: borrarlo no toca a sus tablas padre."""
    tipo_id = _crear_tipo_de_cafe(db)
    creado = _dar_de_alta(db)

    services.eliminar_lote(db, creado.id)

    assert _hay_lotes(db) == 0
    assert crud.obtener_tipo_de_cafe(db, tipo_id) is not None


def test_eliminar_no_arrasta_al_blend_referenciado(db):
    blend_id = _crear_blend(db)
    creado = _dar_de_alta(db, tipo_de_cafe_id=None, blend_id=blend_id)

    services.eliminar_lote(db, creado.id)

    assert _hay_lotes(db) == 0
    assert crud.obtener_blend(db, blend_id) is not None


# ---------------------------------------------------------------------------
# 2.x Cobertura de la capa de datos
# ---------------------------------------------------------------------------
def test_crud_obtiene_lote_por_id_y_devuelve_none(db, origen):
    creado = _dar_de_alta(db)

    assert crud.obtener_lote(db, creado.id).id == creado.id
    assert crud.obtener_lote(db, 999) is None


def test_crud_crea_lote_con_el_kg_disponibles_que_le_pasan(db, origen):
    datos = LoteCreate(**PAYLOAD)

    lote = crud.crear_lote(db, datos, kg_disponibles=Decimal("12.00"))
    db.commit()

    assert lote.kg_disponibles == Decimal("12.00")
    assert lote.kg_reales == Decimal("59.80")


def test_crud_actualiza_solo_las_claves_recibidas(db, origen):
    creado = _dar_de_alta(db)
    lote = crud.obtener_lote(db, creado.id)

    crud.actualizar_lote(db, lote, {"estado": LoteEstado.CERRADO})
    db.commit()

    assert lote.estado == LoteEstado.CERRADO
    assert lote.ubicacion_fisica == "PASILLO-01"


def test_crud_existe_registro_para_cualquier_entidad(db):
    tipo_id = _crear_tipo_de_cafe(db)
    blend_id = _crear_blend(db)

    assert crud.existe_registro(db, TipoDeCafe, tipo_id) is True
    assert crud.existe_registro(db, Blend, blend_id) is True
    assert crud.existe_registro(db, TipoDeCafe, 999) is False
    assert crud.existe_registro(db, Blend, 999) is False


def test_crud_no_hace_commit(db):
    import inspect

    assert ".commit()" not in inspect.getsource(crud)
