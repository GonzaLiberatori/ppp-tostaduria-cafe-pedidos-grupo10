"""Tests de las reglas de negocio de TipoDeCafe en la capa `services`."""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.inventario import crud, services
from app.modules.inventario.models import Blend, BlendHasTipoDeCafe, Lote, LoteEstado, LoteTipo, TipoDeCafe
from app.modules.inventario.schemas import TipoDeCafeCreate, TipoDeCafeRead, TipoDeCafeUpdate

PAYLOAD: dict[str, object] = {
    "organico": True,
    "precio_por_kg_verde": "1250.50",
    "variedad": "Caturra",
    "region": "Huila",
    "pais": "Colombia",
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


def _dar_de_alta(db) -> TipoDeCafe:
    """Crea un tipo de café a través del servicio y devuelve el registro."""
    services.crear_tipo_de_cafe(db, TipoDeCafeCreate(**PAYLOAD))
    return db.scalar(select(TipoDeCafe))


def _hay_tipos(db) -> int:
    return int(db.scalar(select(func.count()).select_from(TipoDeCafe)) or 0)


def _referenciar_con_blend(db, tipo_id: int) -> None:
    blend = Blend(
        nombre="Blend de prueba",
        precio_por_kg_verde=Decimal("900.00"),
        descripcion="Mezcla para el test.",
    )
    db.add(blend)
    db.flush()
    db.add(
        BlendHasTipoDeCafe(blend_id=blend.id, tipo_de_cafe_id=tipo_id, porcentaje=Decimal("100.00"))
    )
    db.commit()


def _referenciar_con_lote(db, tipo_id: int) -> None:
    db.add(
        Lote(
            tipo=LoteTipo.VERDE,
            estado=LoteEstado.ABIERTO,
            fecha_vencimiento=datetime(2026, 12, 31, 8, 0),
            humedad=Decimal("11.50"),
            kg_disponibles=Decimal("60.00"),
            kg_reales=Decimal("59.00"),
            ubicacion_fisica="PASILLO-01",
            tipo_de_cafe_id=tipo_id,
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# 3.1 Excepciones de dominio
# ---------------------------------------------------------------------------
def test_excepcion_no_encontrado_carga_el_identificador():
    exc = services.TipoDeCafeNoEncontrado(42)
    assert exc.tipo_id == 42
    assert "42" in str(exc)


def test_excepcion_referenciado_lista_las_entidades():
    exc = services.TipoDeCafeReferenciado(["BlendHasTipoDeCafe", "Lote"])
    assert exc.entidades == ["BlendHasTipoDeCafe", "Lote"]
    assert "BlendHasTipoDeCafe" in str(exc)
    assert "Lote" in str(exc)


# ---------------------------------------------------------------------------
# 3.2 Crear
# ---------------------------------------------------------------------------
def test_crear_persiste_el_registro(db):
    leido = services.crear_tipo_de_cafe(db, TipoDeCafeCreate(**PAYLOAD))

    assert leido.id is not None
    assert leido.variedad == "Caturra"
    assert _hay_tipos(db) == 1


def test_crear_con_fallo_no_deja_registros_huerfanos(db, monkeypatch):
    """Si falla después de agregar la fila, el rollback no deja nada atrás."""

    def _falla_despues_de_agregar(sesion, datos):
        sesion.add(
            TipoDeCafe(
                organico=True,
                precio_por_kg_verde=Decimal("10.00"),
                variedad="X",
                region="Y",
                pais="Z",
            )
        )
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(crud, "crear_tipo_de_cafe", _falla_despues_de_agregar)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        services.crear_tipo_de_cafe(db, TipoDeCafeCreate(**PAYLOAD))

    assert _hay_tipos(db) == 0


def test_crear_rechaza_precio_no_positivo_en_el_borde(db):
    """La validación del precio vive en Pydantic, no en el servicio."""
    payload = {**PAYLOAD, "precio_por_kg_verde": "0"}

    with pytest.raises(ValidationError):
        TipoDeCafeCreate(**payload)

    assert _hay_tipos(db) == 0


def test_servicio_no_duplica_la_validacion_de_precio(db):
    """El servicio no vuelve a comprobar precio > 0."""
    import inspect

    cuerpo = inspect.getsource(services)
    assert "precio_por_kg_verde <=" not in cuerpo
    assert "precio_por_kg_verde >" not in cuerpo


# ---------------------------------------------------------------------------
# 3.3 Leer
# ---------------------------------------------------------------------------
def test_leer_devuelve_el_registro(db):
    tipo = _dar_de_alta(db)

    leido = services.obtener_tipo_de_cafe(db, tipo.id)

    assert isinstance(leido, TipoDeCafeRead)
    assert leido.id == tipo.id
    assert leido.pais == "Colombia"


def test_leer_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.TipoDeCafeNoEncontrado) as exc:
        services.obtener_tipo_de_cafe(db, 999)

    assert exc.value.tipo_id == 999


# ---------------------------------------------------------------------------
# 3.4 Actualizar
# ---------------------------------------------------------------------------
def test_actualizar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.TipoDeCafeNoEncontrado):
        services.actualizar_tipo_de_cafe(db, 999, TipoDeCafeUpdate(organico=False))


def test_actualizar_un_solo_atributo_deja_el_resto_igual(db):
    tipo = _dar_de_alta(db)

    leido = services.actualizar_tipo_de_cafe(db, tipo.id, TipoDeCafeUpdate(organico=False))

    assert leido.organico is False
    assert leido.variedad == "Caturra"
    assert leido.region == "Huila"
    assert leido.pais == "Colombia"
    assert leido.precio_por_kg_verde == Decimal("1250.50")


def test_actualizar_atributo_en_null_no_lo_modifica(db):
    tipo = _dar_de_alta(db)

    leido = services.actualizar_tipo_de_cafe(
        db, tipo.id, TipoDeCafeUpdate(variedad=None, region="Cauca")
    )

    assert leido.variedad == "Caturra"
    assert leido.region == "Cauca"


def test_actualizar_cuerpo_vacio_no_cambia_nada(db):
    tipo = _dar_de_alta(db)

    leido = services.actualizar_tipo_de_cafe(db, tipo.id, TipoDeCafeUpdate())

    assert leido.organico is True
    assert leido.variedad == "Caturra"
    assert _hay_tipos(db) == 1


def test_actualizar_sin_existencia_no_devuelve_un_registro_fantasma(db):
    """El orden importa: existencia primero, cambios después."""
    leido_vacio = services.obtener_tipo_de_cafe(db, _dar_de_alta(db).id)
    assert leido_vacio.id is not None

    with pytest.raises(services.TipoDeCafeNoEncontrado):
        services.actualizar_tipo_de_cafe(db, 4242, TipoDeCafeUpdate())


# ---------------------------------------------------------------------------
# 3.5 Eliminar
# ---------------------------------------------------------------------------
def test_eliminar_sin_referencias_borra_el_registro(db):
    tipo = _dar_de_alta(db)

    services.eliminar_tipo_de_cafe(db, tipo.id)

    assert _hay_tipos(db) == 0
    assert db.get(TipoDeCafe, tipo.id) is None


def test_eliminar_con_id_inexistente_lanza_no_encontrado(db):
    with pytest.raises(services.TipoDeCafeNoEncontrado):
        services.eliminar_tipo_de_cafe(db, 999)


def test_eliminar_bloqueado_por_un_blend(db):
    tipo = _dar_de_alta(db)
    _referenciar_con_blend(db, tipo.id)

    with pytest.raises(services.TipoDeCafeReferenciado) as exc:
        services.eliminar_tipo_de_cafe(db, tipo.id)

    assert "BlendHasTipoDeCafe" in exc.value.entidades
    assert db.get(TipoDeCafe, tipo.id) is not None


def test_eliminar_bloqueado_por_un_lote(db):
    tipo = _dar_de_alta(db)
    _referenciar_con_lote(db, tipo.id)

    with pytest.raises(services.TipoDeCafeReferenciado) as exc:
        services.eliminar_tipo_de_cafe(db, tipo.id)

    assert "Lote" in exc.value.entidades
    assert db.get(TipoDeCafe, tipo.id) is not None


def test_eliminar_bloqueado_por_varias_entidades_a_la_vez(db):
    """Las referencias no son mutuamente excluyentes: el aviso nombra a todas."""
    tipo = _dar_de_alta(db)
    _referenciar_con_blend(db, tipo.id)
    _referenciar_con_lote(db, tipo.id)

    with pytest.raises(services.TipoDeCafeReferenciado) as exc:
        services.eliminar_tipo_de_cafe(db, tipo.id)

    assert set(exc.value.entidades) == {"BlendHasTipoDeCafe", "Lote"}


# ---------------------------------------------------------------------------
# 2.x Cobertura de la capa de datos
# ---------------------------------------------------------------------------
def test_crud_obtiene_por_id_y_devuelve_none(db):
    tipo = _dar_de_alta(db)

    assert crud.obtener_tipo_de_cafe(db, tipo.id).id == tipo.id
    assert crud.obtener_tipo_de_cafe(db, 999) is None


def test_crud_aplica_solo_las_claves_recibidas(db):
    tipo = _dar_de_alta(db)

    crud.actualizar_tipo_de_cafe(db, tipo, {"organico": False})
    db.commit()

    assert tipo.organico is False
    assert tipo.variedad == "Caturra"


def test_crud_cuenta_referencias_con_ceros_incluidos(db):
    tipo = _dar_de_alta(db)
    assert crud.cuentas_de_referencias(db, TipoDeCafe, tipo.id) == {
        "BlendHasTipoDeCafe": 0,
        "Lote": 0,
    }

    _referenciar_con_blend(db, tipo.id)
    assert crud.cuentas_de_referencias(db, TipoDeCafe, tipo.id) == {
        "BlendHasTipoDeCafe": 1,
        "Lote": 0,
    }


def test_crud_usa_la_columna_correcta_por_entidad(db):
    """`Lote` bloquea a TipoDeCafe por `tipo_de_cafe_id` y a Blend por `blend_id`."""
    tipo = _dar_de_alta(db)
    _referenciar_con_lote(db, tipo.id)

    assert crud.cuentas_de_referencias(db, TipoDeCafe, tipo.id)["Lote"] == 1
    assert crud.cuentas_de_referencias(db, Blend, tipo.id)["Lote"] == 0


def test_crud_no_hace_commit(db):
    """`services` es la única frontera transaccional."""
    import inspect

    assert ".commit()" not in inspect.getsource(crud)
