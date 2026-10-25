"""Tests de los schemas de Blend y su composición."""

from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.inventario.models import Blend, BlendHasTipoDeCafe
from app.modules.inventario.schemas import (
    BlendComposicionItem,
    BlendCreate,
    BlendRead,
    BlendUpdate,
)

COMPOSICION_BASE: list[dict[str, Any]] = [
    {"tipo_de_cafe_id": 1, "porcentaje": "50.00"},
    {"tipo_de_cafe_id": 2, "porcentaje": "50.00"},
]

PAYLOAD_BASE: dict[str, Any] = {
    "nombre": "Mezcla Huila",
    "precio_por_kg_verde": "980.00",
    "descripcion": "Mezcla equilibrada para filtro.",
    "tipos_de_cafe": COMPOSICION_BASE,
}


def _payload_sin_composicion(**extra: Any) -> dict[str, Any]:
    return {k: v for k, v in PAYLOAD_BASE.items() if k != "tipos_de_cafe"} | extra


# ---------------------------------------------------------------------------
# Ítem de composición (3.1)
# ---------------------------------------------------------------------------
def test_item_acepta_porcentaje_positivo():
    item = BlendComposicionItem(tipo_de_cafe_id=1, porcentaje="25.50")
    assert item.porcentaje == Decimal("25.50")


def test_item_rechaza_porcentaje_cero():
    with pytest.raises(ValidationError):
        BlendComposicionItem(tipo_de_cafe_id=1, porcentaje="0")


def test_item_rechaza_porcentaje_negativo():
    with pytest.raises(ValidationError):
        BlendComposicionItem(tipo_de_cafe_id=1, porcentaje="-10")


def test_item_rechaza_campos_no_declarados():
    with pytest.raises(ValidationError):
        BlendComposicionItem(tipo_de_cafe_id=1, porcentaje="10", id=5)


# ---------------------------------------------------------------------------
# Creación (3.2 y 3.3)
# ---------------------------------------------------------------------------
def test_create_acepta_composicion_de_tres_proporciones():
    creado = BlendCreate(**_payload_sin_composicion(tipos_de_cafe=[
        {"tipo_de_cafe_id": 1, "porcentaje": "33.33"},
        {"tipo_de_cafe_id": 2, "porcentaje": "33.33"},
        {"tipo_de_cafe_id": 3, "porcentaje": "33.34"},
    ]))
    assert len(creado.tipos_de_cafe) == 3


def test_create_acepta_payload_con_dos_proporciones():
    creado = BlendCreate(**PAYLOAD_BASE)
    assert creado.nombre == "Mezcla Huila"


def test_create_rechaza_composicion_vacia():
    with pytest.raises(ValidationError):
        BlendCreate(**_payload_sin_composicion(tipos_de_cafe=[]))


def test_create_rechaza_tipo_de_cafe_repetido():
    with pytest.raises(ValidationError):
        BlendCreate(**_payload_sin_composicion(tipos_de_cafe=[
            {"tipo_de_cafe_id": 1, "porcentaje": "50.00"},
            {"tipo_de_cafe_id": 1, "porcentaje": "50.00"},
        ]))


def test_create_rechaza_porcentajes_que_no_suman_cien():
    with pytest.raises(ValidationError):
        BlendCreate(**_payload_sin_composicion(tipos_de_cafe=[
            {"tipo_de_cafe_id": 1, "porcentaje": "60.00"},
            {"tipo_de_cafe_id": 2, "porcentaje": "39.99"},
        ]))


def test_create_acepta_suma_exacta_de_cien_con_tercios():
    """33.33 + 33.33 + 33.34 debe sumar 100 sin errar por representación."""
    creado = BlendCreate(**_payload_sin_composicion(tipos_de_cafe=[
        {"tipo_de_cafe_id": 1, "porcentaje": "33.33"},
        {"tipo_de_cafe_id": 2, "porcentaje": "33.33"},
        {"tipo_de_cafe_id": 3, "porcentaje": "33.34"},
    ]))
    assert sum((i.porcentaje for i in creado.tipos_de_cafe), Decimal("0")) == Decimal("100.00")


def test_create_rechaza_campo_obligatorio_faltante():
    for campo in ("nombre", "precio_por_kg_verde", "descripcion", "tipos_de_cafe"):
        with pytest.raises(ValidationError):
            BlendCreate(**{k: v for k, v in PAYLOAD_BASE.items() if k != campo})


def test_create_rechaza_campos_no_declarados():
    with pytest.raises(ValidationError):
        BlendCreate(**PAYLOAD_BASE, id=4)


# ---------------------------------------------------------------------------
# Actualización (3.4)
# ---------------------------------------------------------------------------
def test_update_de_solo_nombre_es_valido():
    actualizado = BlendUpdate(nombre="Otra mezcla")
    assert actualizado.nombre == "Otra mezcla"
    assert actualizado.tipos_de_cafe is None
    assert actualizado.precio_por_kg_verde is None


def test_update_de_solo_composicion_es_valido():
    actualizado = BlendUpdate(tipos_de_cafe=COMPOSICION_BASE)
    assert [i.tipo_de_cafe_id for i in actualizado.tipos_de_cafe] == [1, 2]
    assert actualizado.nombre is None


def test_update_vacio_es_valido():
    assert BlendUpdate().model_dump(exclude_unset=True) == {}


def test_update_rechaza_composicion_invalida():
    with pytest.raises(ValidationError):
        BlendUpdate(tipos_de_cafe=[
            {"tipo_de_cafe_id": 1, "porcentaje": "40.00"},
            {"tipo_de_cafe_id": 2, "porcentaje": "40.00"},
        ])


def test_update_rechaza_composicion_vacia():
    with pytest.raises(ValidationError):
        BlendUpdate(tipos_de_cafe=[])


# ---------------------------------------------------------------------------
# Lectura (3.5)
# ---------------------------------------------------------------------------
def test_read_serializa_composicion_completa():
    leido = BlendRead(
        id=9,
        nombre="Mezcla Huila",
        precio_por_kg_verde=Decimal("980.00"),
        descripcion="Mezcla equilibrada para filtro.",
        tipos_de_cafe=COMPOSICION_BASE,
    )
    dump = leido.model_dump()
    assert dump["id"] == 9
    assert dump["tipos_de_cafe"] == [
        {"tipo_de_cafe_id": 1, "porcentaje": Decimal("50.00")},
        {"tipo_de_cafe_id": 2, "porcentaje": Decimal("50.00")},
    ]


def test_read_desde_orm_convierte_la_composicion():
    """Único adaptador de la capa: de filas de BlendHasTipoDeCafe a pares id+porcentaje."""
    blend = Blend(
        id=9,
        nombre="Mezcla Huila",
        precio_por_kg_verde=Decimal("980.00"),
        descripcion="Mezcla equilibrada para filtro.",
    )
    blend.tipos_de_cafe = [
        BlendHasTipoDeCafe(blend_id=9, tipo_de_cafe_id=1, porcentaje=Decimal("50.00")),
        BlendHasTipoDeCafe(blend_id=9, tipo_de_cafe_id=2, porcentaje=Decimal("50.00")),
    ]

    leido = BlendRead.desde_orm(blend)

    # Solo viajan tipo_de_cafe_id y porcentaje: se descartan blend_id y las relaciones.
    assert [item.model_dump() for item in leido.tipos_de_cafe] == [
        {"tipo_de_cafe_id": 1, "porcentaje": Decimal("50.00")},
        {"tipo_de_cafe_id": 2, "porcentaje": Decimal("50.00")},
    ]


# ---------------------------------------------------------------------------
# Documentación Swagger (3.7)
# ---------------------------------------------------------------------------
def test_read_describla_todos_los_campos():
    propiedades = BlendRead.model_json_schema()["properties"]
    assert [n for n, d in propiedades.items() if "description" not in d] == []


def test_json_schema_de_read_describe_el_item_de_composicion():
    esquema = BlendRead.model_json_schema()
    definicion = esquema["$defs"]["BlendComposicionItem"]
    item = definicion["properties"]
    assert "description" in item["tipo_de_cafe_id"]
    assert "description" in item["porcentaje"]
    assert definicion.get("description")


# ---------------------------------------------------------------------------
# Precisión decimal (1.2 y 1.3)
# ---------------------------------------------------------------------------
def test_porcentaje_con_tres_decimales_rechaza_validacion():
    """Campo 5,2: `Decimal("1.999")` debe fallar en el borde, no truncar en MySQL."""
    with pytest.raises(ValidationError):
        BlendComposicionItem(tipo_de_cafe_id=1, porcentaje="1.999")


@pytest.mark.parametrize(
    ("columna", "modelo", "schema"),
    [
        ("porcentaje", BlendHasTipoDeCafe, BlendComposicionItem),
        ("precio_por_kg_verde", Blend, BlendCreate),
    ],
)
def test_precision_coincide_con_la_columna_del_modelo(columna: str, modelo: type, schema: type):
    tipo_columna = modelo.__table__.c[columna].type
    campo = schema.model_fields[columna]
    precision_schema = next(meta for meta in campo.metadata if hasattr(meta, "max_digits"))
    assert (precision_schema.max_digits, precision_schema.decimal_places) == (
        tipo_columna.precision,
        tipo_columna.scale,
    )
