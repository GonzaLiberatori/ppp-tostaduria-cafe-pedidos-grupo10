"""Tests de las reglas de negocio de Blend en la capa `services`."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.inventario import crud, services
from app.modules.inventario.models import (
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    LoteEstado,
    LoteTipo,
    TipoDeCafe,
)
from app.modules.inventario.schemas import BlendCreate, BlendRead, BlendUpdate

PAYLOAD: dict[str, object] = {
    "nombre": "Mezcla Huila",
    "precio_por_kg_verde": "980.00",
    "descripcion": "Mezcla equilibrada para filtro.",
    "tipos_de_cafe": [
        {"tipo_de_cafe_id": 1, "porcentaje": "50.00"},
        {"tipo_de_cafe_id": 2, "porcentaje": "50.00"},
    ],
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


def _crear(db, **extra) -> BlendRead:
    return services.crear_blend(db, BlendCreate(**{**PAYLOAD, **extra}))


def _hay_blends(db) -> int:
    return int(db.scalar(select(func.count()).select_from(Blend)) or 0)


def _filas_de_composicion(db, blend_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(BlendHasTipoDeCafe)
            .where(BlendHasTipoDeCafe.blend_id == blend_id)
        )
        or 0
    )


def _referenciar_con_lote(db, blend_id: int) -> None:
    db.add(
        Lote(
            tipo=LoteTipo.VERDE,
            estado=LoteEstado.ABIERTO,
            fecha_vencimiento=datetime(2026, 12, 31, 8, 0),
            humedad=Decimal("11.50"),
            kg_disponibles=Decimal("60.00"),
            kg_reales=Decimal("59.00"),
            ubicacion_fisica="PASILLO-01",
            blend_id=blend_id,
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# 3.1 Excepciones de dominio
# ---------------------------------------------------------------------------
def test_excepcion_no_encontrado_carga_el_identificador():
    exc = services.BlendNoEncontrado(7)
    assert exc.blend_id == 7
    assert "7" in str(exc)


def test_excepcion_referenciado_lista_las_entidades():
    exc = services.BlendReferenciado(["Lote"])
    assert exc.entidades == ["Lote"]
    assert "Lote" in str(exc)


def test_excepcion_de_nombre_carga_el_nombre():
    exc = services.NombreDeBlendEnUso("Clásico")
    assert exc.nombre == "Clásico"
    assert "Clásico" in str(exc)


# ---------------------------------------------------------------------------
# 3.2 Crear
# ---------------------------------------------------------------------------
def test_crear_persiste_el_blend_y_su_composicion(db):
    leido = _crear(db)

    assert leido.id is not None
    assert leido.nombre == "Mezcla Huila"
    assert [i.tipo_de_cafe_id for i in leido.tipos_de_cafe] == [1, 2]
    assert _hay_blends(db) == 1
    assert _filas_de_composicion(db, leido.id) == 2


def test_crear_con_nombre_ya_usado_lanza_excepcion_y_no_deja_nada(db):
    _crear(db)

    with pytest.raises(services.NombreDeBlendEnUso) as exc:
        _crear(db)

    assert exc.value.nombre == "Mezcla Huila"
    assert _hay_blends(db) == 1


def test_crear_con_fallo_no_deja_registros_huerfanos(db, monkeypatch):
    """Si falla después de agregar el blend, el rollback no deja nada atrás."""

    def _falla_despues_de_agregar(sesion, datos):
        sesion.add(
            Blend(nombre="A", precio_por_kg_verde=Decimal("10.00"), descripcion="d")
        )
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(crud, "crear_blend", _falla_despues_de_agregar)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        services.crear_blend(db, BlendCreate(**PAYLOAD))

    assert _hay_blends(db) == 0


# ---------------------------------------------------------------------------
# 3.3 Leer
# ---------------------------------------------------------------------------
def test_leer_devuelve_el_blend_con_su_composicion(db):
    creado = _crear(db)

    leido = services.obtener_blend(db, creado.id)

    assert isinstance(leido, BlendRead)
    assert leido.id == creado.id
    assert len(leido.tipos_de_cafe) == 2


def test_leer_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.BlendNoEncontrado) as exc:
        services.obtener_blend(db, 999)

    assert exc.value.blend_id == 999


# ---------------------------------------------------------------------------
# 3.4 Actualizar
# ---------------------------------------------------------------------------
def test_actualizar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.BlendNoEncontrado):
        services.actualizar_blend(db, 999, BlendUpdate(nombre="Otro"))


def test_actualizar_un_solo_atributo_deja_el_resto_igual(db):
    creado = _crear(db)

    leido = services.actualizar_blend(db, creado.id, BlendUpdate(nombre="Otra mezcla"))

    assert leido.nombre == "Otra mezcla"
    assert leido.descripcion == PAYLOAD["descripcion"]
    assert len(leido.tipos_de_cafe) == 2


def test_actualizar_atributo_en_null_no_lo_modifica(db):
    creado = _crear(db)

    leido = services.actualizar_blend(
        db, creado.id, BlendUpdate(nombre=None, descripcion="Nueva descripción")
    )

    assert leido.nombre == "Mezcla Huila"
    assert leido.descripcion == "Nueva descripción"


def test_actualizar_cuerpo_vacio_no_cambia_nada(db):
    creado = _crear(db)

    leido = services.actualizar_blend(db, creado.id, BlendUpdate())

    assert leido.nombre == "Mezcla Huila"
    assert _hay_blends(db) == 1


def test_actualizar_sin_existencia_no_devuelve_un_registro_fantasma(db):
    """El orden importa: existencia primero, cambios después."""
    creado = _crear(db)
    assert services.obtener_blend(db, creado.id).id == creado.id

    with pytest.raises(services.BlendNoEncontrado):
        services.actualizar_blend(db, 4242, BlendUpdate())


def test_actualizar_con_el_nombre_de_otro_blend_lanza_conflicto(db):
    _crear(db, nombre="Primero")
    segundo = _crear(db, nombre="Segundo")

    with pytest.raises(services.NombreDeBlendEnUso) as exc:
        services.actualizar_blend(db, segundo.id, BlendUpdate(nombre="Primero"))

    assert exc.value.nombre == "Primero"
    assert services.obtener_blend(db, segundo.id).nombre == "Segundo"


def test_actualizar_con_el_propio_nombre_no_es_conflicto(db):
    creado = _crear(db)

    leido = services.actualizar_blend(db, creado.id, BlendUpdate(nombre=creado.nombre))

    assert leido.nombre == "Mezcla Huila"


def test_actualizar_reemplaza_la_composicion_completa(db):
    creado = _crear(db)

    leido = services.actualizar_blend(
        db,
        creado.id,
        BlendUpdate(tipos_de_cafe=[
            {"tipo_de_cafe_id": 7, "porcentaje": "60.00"},
            {"tipo_de_cafe_id": 8, "porcentaje": "40.00"},
        ]),
    )

    assert [i.tipo_de_cafe_id for i in leido.tipos_de_cafe] == [7, 8]
    assert _filas_de_composicion(db, creado.id) == 2


def test_actualizar_reemplazando_deja_una_sola_fila_por_item(db):
    """No deben convivir la composición vieja y la nueva."""
    creado = _crear(db)

    services.actualizar_blend(
        db,
        creado.id,
        BlendUpdate(tipos_de_cafe=[
            {"tipo_de_cafe_id": 3, "porcentaje": "40.00"},
            {"tipo_de_cafe_id": 4, "porcentaje": "30.00"},
            {"tipo_de_cafe_id": 5, "porcentaje": "30.00"},
        ]),
    )

    assert _filas_de_composicion(db, creado.id) == 3


# ---------------------------------------------------------------------------
# 3.5 Eliminar
# ---------------------------------------------------------------------------
def test_eliminar_sin_referencias_borra_blend_y_composicion(db):
    creado = _crear(db)

    services.eliminar_blend(db, creado.id)

    assert _hay_blends(db) == 0
    assert _filas_de_composicion(db, creado.id) == 0


def test_eliminar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.BlendNoEncontrado):
        services.eliminar_blend(db, 999)


def test_eliminar_bloqueado_por_un_lote(db):
    creado = _crear(db)
    _referenciar_con_lote(db, creado.id)

    with pytest.raises(services.BlendReferenciado) as exc:
        services.eliminar_blend(db, creado.id)

    assert exc.value.entidades == ["Lote"]
    assert _hay_blends(db) == 1
    assert _filas_de_composicion(db, creado.id) == 2


def test_eliminar_con_composicion_pero_sin_referencias_externas_procede(db):
    """La composición propia no bloquea: son los hijos del blend."""
    creado = _crear(db)

    cuentas = crud.cuentas_de_referencias(db, Blend, creado.id)
    assert cuentas == {"Lote": 0}

    services.eliminar_blend(db, creado.id)
    assert _hay_blends(db) == 0


# ---------------------------------------------------------------------------
# 2.x Cobertura de la capa de datos
# ---------------------------------------------------------------------------
def test_crud_obtiene_blend_por_id_y_devuelve_none(db):
    creado = _crear(db)

    assert crud.obtener_blend(db, creado.id).id == creado.id
    assert crud.obtener_blend(db, 999) is None


def test_crud_detecta_nombre_en_usado(db):
    creado = _crear(db)

    assert crud.nombre_de_blend_ya_en_usado(db, "Mezcla Huila") is True
    assert crud.nombre_de_blend_ya_en_usado(db, "Nombre libre") is False


def test_crud_detecta_nombre_en_usado_excluyendo_al_propio(db):
    creado = _crear(db)

    assert (
        crud.nombre_de_blend_ya_en_usado(db, "Mezcla Huila", excluir_id=creado.id) is False
    )
    assert crud.nombre_de_blend_ya_en_usado(db, "Mezcla Huila", excluir_id=creado.id + 1) is True


def test_crud_actualiza_solo_las_claves_recibidas(db):
    creado = _crear(db)
    blend = crud.obtener_blend(db, creado.id)

    crud.actualizar_blend(db, blend, {"precio_por_kg_verde": Decimal("1100.00")})
    db.commit()

    assert blend.precio_por_kg_verde == Decimal("1100.00")
    assert blend.nombre == "Mezcla Huila"


def test_crud_elimina_composicion_y_blend_sin_commit(db):
    import inspect

    assert ".commit()" not in inspect.getsource(crud)


def test_crud_usa_la_columna_de_lote_correcta_para_blend(db):
    """`Lote` se cuenta por `blend_id`, no por `tipo_de_cafe_id`."""
    creado = _crear(db)
    assert crud.cuentas_de_referencias(db, Blend, creado.id) == {"Lote": 0}

    _referenciar_con_lote(db, creado.id)
    assert crud.cuentas_de_referencias(db, Blend, creado.id) == {"Lote": 1}
    assert crud.cuentas_de_referencias(db, TipoDeCafe, creado.id)["Lote"] == 0
