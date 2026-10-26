"""Tests de los schemas de Lote, incluidas sus ediciones puntuales."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.inventario.models import Lote, LoteEstado, LoteTipo
from app.modules.inventario.schemas import (
    LoteCreate,
    LoteEstadoUpdate,
    LoteKgDisponiblesUpdate,
    LoteKgRealesUpdate,
    LoteRead,
    LoteUpdate,
)

PAYLOAD_BASE: dict[str, Any] = {
    "tipo": "VERDE",
    "estado": "ABIERTO",
    "fecha_vencimiento": "2026-12-31T08:00:00",
    "humedad": "11.50",
    "kg_reales": "59.80",
    "ubicacion_fisica": "PASILLO-01",
    "tipo_de_cafe_id": 1,
}

# Nullable que puede venir en null sin romper la regla de origen único:
# `tipo_de_cafe_id` es nullable en el modelo pero acá es el origen, así que no
# puede ser null si `blend_id` tampoco viene.
OPCIONALES: tuple[str, ...] = ("observaciones", "blend_id", "orden_tueste_id")

PROHIBIDAS_EN_UPDATE: tuple[str, ...] = ("tipo", "tipo_de_cafe_id", "blend_id", "orden_tueste_id")

# `LoteRead` sí expone `kg_disponibles`, que el alta ya no pide.
PAYLOAD_LECTURA: dict[str, Any] = {**PAYLOAD_BASE, "kg_disponibles": "59.80"}


# ---------------------------------------------------------------------------
# Creación (4.1 y 4.2)
# ---------------------------------------------------------------------------
def test_create_acepta_payload_minimo():
    creado = LoteCreate(**PAYLOAD_BASE)
    assert creado.tipo == LoteTipo.VERDE
    assert creado.estado == LoteEstado.ABIERTO
    assert creado.fecha_vencimiento == datetime(2026, 12, 31, 8, 0)
    assert creado.kg_reales == Decimal("59.80")


def test_create_no_solicita_kg_disponibles():
    """Se deriva en el servicio: el contrato no lo pide."""
    assert "kg_disponibles" not in LoteCreate.model_fields


def test_create_rechaza_si_se_envia_kg_disponibles():
    with pytest.raises(ValidationError):
        LoteCreate(**PAYLOAD_BASE, kg_disponibles="60.00")


def test_create_con_los_atributos_nullable_es_valido():
    creado = LoteCreate(**PAYLOAD_BASE)
    for campo in OPCIONALES:
        assert getattr(creado, campo) is None


def test_create_con_los_atributos_nullable_en_none_es_valido():
    creado = LoteCreate(**PAYLOAD_BASE, **{campo: None for campo in OPCIONALES})
    assert creado.observaciones is None
    assert creado.blend_id is None
    assert creado.orden_tueste_id is None
    assert creado.tipo_de_cafe_id == 1


def test_create_acepta_los_cuatro_atributos_nullable_informados():
    creado = LoteCreate(
        **{
            **PAYLOAD_BASE,
            "observaciones": "Ingresó con humedad alta.",
            "tipo_de_cafe_id": 4,
            "blend_id": None,
            "orden_tueste_id": None,
        }
    )
    assert creado.observaciones == "Ingresó con humedad alta."
    assert creado.tipo_de_cafe_id == 4


@pytest.mark.parametrize("campo", list(PAYLOAD_BASE))
def test_create_rechaza_campo_obligatorio_faltante(campo: str):
    with pytest.raises(ValidationError):
        LoteCreate(**{k: v for k, v in PAYLOAD_BASE.items() if k != campo})


def test_create_rechaza_estado_fuera_del_enum():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "estado": "PENDIENTE"})


def test_create_rechaza_tipo_fuera_del_enum():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "tipo": "MOLIDO"})


# ---------------------------------------------------------------------------
# Reglas del alta: humedad, kilos, origen y orden de tueste (1.1, 1.2, 1.4, 1.5)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("humedad", ["100.00", "0"])
def test_create_acepta_humedad_en_los_limites(humedad: str):
    assert LoteCreate(**{**PAYLOAD_BASE, "humedad": humedad}).humedad == Decimal(humedad)


@pytest.mark.parametrize("humedad", ["100.01", "-0.01", "101"])
def test_create_rechaza_humedad_fuera_de_rango(humedad: str):
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "humedad": humedad})


def test_create_acepta_kg_reales_en_cero():
    """Cota `>= 0`: un lote puede nacer sin kilos."""
    assert LoteCreate(**{**PAYLOAD_BASE, "kg_reales": "0"}).kg_reales == Decimal("0")


def test_create_rechaza_kg_reales_negativo():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "kg_reales": "-1"})


def test_update_acepta_kg_reales_en_cero():
    assert LoteUpdate(kg_reales="0").kg_reales == Decimal("0")


def test_update_rechaza_kg_reales_negativo():
    with pytest.raises(ValidationError):
        LoteUpdate(kg_reales="-1")


def test_kg_reales_puntual_acepta_cero_y_rechaza_negativo():
    assert LoteKgRealesUpdate(kg_reales="0").kg_reales == Decimal("0")
    with pytest.raises(ValidationError):
        LoteKgRealesUpdate(kg_reales="-1")


def test_create_rechaza_sin_origen():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "tipo_de_cafe_id": None})


def test_create_rechaza_con_ambos_origenes():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "blend_id": 2})


def test_create_acepta_origen_de_blend():
    creado = LoteCreate(**{**PAYLOAD_BASE, "tipo_de_cafe_id": None, "blend_id": 2})
    assert creado.blend_id == 2
    assert creado.tipo_de_cafe_id is None


def test_create_verde_rechaza_orden_de_tueste():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "orden_tueste_id": 5})


def test_create_verde_sin_orden_de_tueste_es_valido():
    assert LoteCreate(**PAYLOAD_BASE).orden_tueste_id is None


def test_create_tostado_exige_orden_de_tueste():
    with pytest.raises(ValidationError):
        LoteCreate(**{**PAYLOAD_BASE, "tipo": "TOSTADO"})


def test_create_tostado_con_orden_de_tueste_es_valido():
    creado = LoteCreate(**{**PAYLOAD_BASE, "tipo": "TOSTADO", "orden_tueste_id": 5})
    assert creado.orden_tueste_id == 5


# ---------------------------------------------------------------------------
# Actualización (4.3)
# ---------------------------------------------------------------------------
def test_update_acepta_cualquier_atributo_permitido():
    for campo in ("estado", "fecha_vencimiento", "humedad", "kg_disponibles", "kg_reales", "ubicacion_fisica", "observaciones"):
        valor = "CERRADO" if campo == "estado" else "2026-12-31T08:00:00" if campo == "fecha_vencimiento" else "1"
        actualizado = LoteUpdate(**{campo: valor})
        assert actualizado.model_fields_set == {campo}


def test_update_parcial_es_valido():
    actualizado = LoteUpdate(kg_disponibles="55.00")
    assert actualizado.kg_disponibles == Decimal("55.00")
    assert actualizado.kg_reales is None
    assert actualizado.estado is None


def test_update_vacio_es_valido():
    assert LoteUpdate().model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize("campo", PROHIBIDAS_EN_UPDATE)
def test_update_rechaza_atributos_no_editables(campo: str):
    """tipo, tipo_de_cafe_id, blend_id y orden_tueste_id no se pueden modificar por aquí."""
    valor = "VERDE" if campo == "tipo" else 1
    with pytest.raises(ValidationError):
        LoteUpdate(**{campo: valor})


def test_update_rechaza_estados_fuera_del_enum():
    with pytest.raises(ValidationError):
        LoteUpdate(estado="PENDIENTE")


# ---------------------------------------------------------------------------
# Lectura (4.4 y 4.5)
# ---------------------------------------------------------------------------
def test_read_serializa_con_los_cuatro_nullable_en_none():
    leido = LoteRead(id=3, **PAYLOAD_LECTURA)
    dump = leido.model_dump()
    assert dump["id"] == 3
    assert dump["tipo"] == LoteTipo.VERDE
    for campo in OPCIONALES:
        assert dump[campo] is None


def test_read_con_atributos_nullable_informados():
    leido = LoteRead(
        id=3,
        **{
            **PAYLOAD_LECTURA,
            "observaciones": "Revisado.",
            "tipo_de_cafe_id": 4,
            "blend_id": 5,
            "orden_tueste_id": 8,
        },
    )
    assert leido.orden_tueste_id == 8
    assert leido.kg_disponibles == Decimal("59.80")


def test_read_incluye_orden_tueste_id_pese_a_que_la_tabla_no_existe():
    """La deuda está registrada en design.md; el contrato expone el campo igual."""
    assert "orden_tueste_id" in LoteRead.model_fields


def test_read_se_construye_desde_el_orm_sin_adaptador():
    """LoteRead coincide campo por campo con Lote: se valida el ORM directamente."""
    lote = Lote(
        id=3,
        tipo=LoteTipo.VERDE,
        estado=LoteEstado.ABIERTO,
        fecha_vencimiento=datetime(2026, 12, 31, 8, 0),
        humedad=Decimal("11.50"),
        kg_disponibles=Decimal("60.00"),
        kg_reales=Decimal("59.80"),
        ubicacion_fisica="PASILLO-01",
    )
    leido = LoteRead.model_validate(lote)
    assert leido.id == 3
    assert leido.tipo == LoteTipo.VERDE
    assert leido.observaciones is None
    assert leido.orden_tueste_id is None


def test_read_no_tiene_adaptador_propio():
    """Regla de la capa de schemas: sin transformación, sin método desde_orm."""
    assert not hasattr(LoteRead, "desde_orm")


# ---------------------------------------------------------------------------
# Ediciones puntuales (5.1, 5.2 y 5.3)
# ---------------------------------------------------------------------------
def test_kg_disponibles_acepta_su_campo():
    assert LoteKgDisponiblesUpdate(kg_disponibles="40.00").kg_disponibles == Decimal("40.00")


def test_kg_disponibles_rechaza_otro_campo():
    with pytest.raises(ValidationError):
        LoteKgDisponiblesUpdate(kg_disponibles="40.00", kg_reales="40.00")


def test_kg_reales_acepta_su_campo():
    assert LoteKgRealesUpdate(kg_reales="40.00").kg_reales == Decimal("40.00")


def test_kg_reales_rechaza_otro_campo():
    with pytest.raises(ValidationError):
        LoteKgRealesUpdate(kg_reales="40.00", kg_disponibles="40.00")


def test_estado_acepta_un_valor_del_enum():
    assert LoteEstadoUpdate(estado="CERRADO").estado == LoteEstado.CERRADO


def test_estado_rechaza_un_valor_fuera_del_enum():
    with pytest.raises(ValidationError):
        LoteEstadoUpdate(estado="PENDIENTE")


def test_estado_rechaza_campos_adicionales():
    with pytest.raises(ValidationError):
        LoteEstadoUpdate(estado="CERRADO", kg_reales="1")


# ---------------------------------------------------------------------------
# Documentación Swagger (4.7)
# ---------------------------------------------------------------------------
def test_json_schema_expone_los_valores_de_los_enums():
    definiciones = LoteCreate.model_json_schema()["$defs"]
    assert definiciones["LoteTipo"]["enum"] == ["VERDE", "TOSTADO"]
    assert definiciones["LoteEstado"]["enum"] == ["CERRADO", "ABIERTO"]


def test_create_describla_todos_los_campos():
    propiedades = LoteCreate.model_json_schema()["properties"]
    assert [n for n, d in propiedades.items() if "description" not in d] == []


def test_update_describla_todos_los_campos():
    propiedades = LoteUpdate.model_json_schema()["properties"]
    assert [n for n, d in propiedades.items() if "description" not in d] == []


def test_puntuales_describen_su_campo():
    for schema in (LoteKgDisponiblesUpdate, LoteKgRealesUpdate, LoteEstadoUpdate):
        propiedades = schema.model_json_schema()["properties"]
        assert len(propiedades) == 1
        assert "description" in next(iter(propiedades.values()))


# ---------------------------------------------------------------------------
# Precisión decimal (1.3)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("columna", ["humedad", "kg_disponibles", "kg_reales"])
def test_precision_coincide_con_la_columna_del_modelo(columna: str):
    tipo_columna = Lote.__table__.c[columna].type
    # Se lee de LoteRead porque `kg_disponibles` ya no forma parte de LoteCreate.
    campo = LoteRead.model_fields[columna]
    precision_schema = next(meta for meta in campo.metadata if hasattr(meta, "max_digits"))
    assert (precision_schema.max_digits, precision_schema.decimal_places) == (
        tipo_columna.precision,
        tipo_columna.scale,
    )
