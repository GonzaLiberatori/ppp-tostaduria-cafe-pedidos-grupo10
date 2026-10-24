"""Tests de los schemas de TipoDeCafe."""

from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.inventario.models import Pais, Region, TipoDeCafe, Variedad
from app.modules.inventario.schemas import (
    TipoDeCafeCreate,
    TipoDeCafeRead,
    TipoDeCafeUpdate,
)

PAYLOAD_BASE: dict[str, Any] = {
    "organico": True,
    "precio_por_kg_verde": "1250.50",
    "variedad": "Caturra",
    "region": "Huila",
    "pais": "Colombia",
}


# ---------------------------------------------------------------------------
# Creación
# ---------------------------------------------------------------------------
def test_crea_con_payload_minimo():
    creado = TipoDeCafeCreate(**PAYLOAD_BASE)
    assert creado.variedad == "Caturra"
    assert creado.pais == "Colombia"
    assert creado.precio_por_kg_verde == Decimal("1250.50")


@pytest.mark.parametrize("campo", list(PAYLOAD_BASE))
def test_create_rechaza_campo_obligatorio_faltante(campo: str):
    payload = {k: v for k, v in PAYLOAD_BASE.items() if k != campo}
    with pytest.raises(ValidationError):
        TipoDeCafeCreate(**payload)


@pytest.mark.parametrize("campo", ["variedad", "region", "pais"])
def test_create_rechaza_nombres_de_origen_vacios(campo: str):
    payload = {**PAYLOAD_BASE, campo: ""}
    with pytest.raises(ValidationError):
        TipoDeCafeCreate(**payload)


def test_create_rechaza_campos_no_declarados():
    with pytest.raises(ValidationError):
        TipoDeCafeCreate(**PAYLOAD_BASE, region_id=3)


def test_create_rechaza_id_porque_no_es_un_campo_de_este_contrato():
    """El id lo asigna la base; la creación no lo recibe."""
    with pytest.raises(ValidationError):
        TipoDeCafeCreate(**PAYLOAD_BASE, id=1)


# ---------------------------------------------------------------------------
# Actualización
# ---------------------------------------------------------------------------
def test_update_de_un_solo_campo_es_valido():
    actualizado = TipoDeCafeUpdate(organico=False)
    assert actualizado.organico is False
    assert actualizado.precio_por_kg_verde is None
    assert actualizado.pais is None


def test_update_vacio_es_valido():
    actualizado = TipoDeCafeUpdate()
    assert actualizado.model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize("campo", ["variedad", "region", "pais"])
def test_update_rechaza_nombre_de_origen_vacio(campo: str):
    with pytest.raises(ValidationError):
        TipoDeCafeUpdate(**{campo: ""})


def test_update_rechaza_id_de_origen():
    """La actualización no admite variedad_id ni region_id."""
    with pytest.raises(ValidationError):
        TipoDeCafeUpdate(variedad_id=2)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
def test_read_expone_id_como_clave_y_no_los_ids_de_origen():
    propiedades = TipoDeCafeRead.model_json_schema()["properties"]
    assert "id" in propiedades
    assert "variedad_id" not in propiedades
    assert "region_id" not in propiedades


def test_read_tiene_descripcion_en_todos_los_campos():
    propiedades = TipoDeCafeRead.model_json_schema()["properties"]
    sin_descripcion = [nombre for nombre, datos in propiedades.items() if "description" not in datos]
    assert sin_descripcion == []


def _tipo_de_cafe_de_ejemplo() -> TipoDeCafe:
    pais = Pais(id=1, nombre="Colombia")
    region = Region(id=2, nombre="Huila", pais=pais)
    variedad = Variedad(id=3, nombre="Caturra")
    return TipoDeCafe(
        id=7,
        organico=True,
        precio_por_kg_verde=Decimal("1250.50"),
        region=region,
        variedad=variedad,
    )


def test_read_desde_orm_aplama_los_tres_nombres():
    leido = TipoDeCafeRead.desde_orm(_tipo_de_cafe_de_ejemplo())
    assert leido.id == 7
    assert leido.variedad == "Caturra"
    assert leido.region == "Huila"
    assert leido.pais == "Colombia"


# ---------------------------------------------------------------------------
# Precisión decimal, espejo de models.py
# ---------------------------------------------------------------------------
def test_precio_por_kg_verde_coincide_con_la_columna_del_modelo():
    columna = TipoDeCafe.__table__.c["precio_por_kg_verde"].type
    campo = TipoDeCafeCreate.model_fields["precio_por_kg_verde"]
    precision_schema = next(meta for meta in campo.metadata if hasattr(meta, "max_digits"))
    assert (precision_schema.max_digits, precision_schema.decimal_places) == (
        columna.precision,
        columna.scale,
    )
