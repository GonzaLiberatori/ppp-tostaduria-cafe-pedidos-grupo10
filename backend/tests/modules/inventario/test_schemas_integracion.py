"""Verificación de integración de la capa de schemas de inventario."""

import pytest
from pydantic import BaseModel

from app.modules.inventario import schemas as schemas_inventario

ESQUEMAS_ESPERADOS = {
    "BlendComposicionItem",
    "BlendCreate",
    "BlendRead",
    "BlendUpdate",
    "LoteCreate",
    "LoteEstadoUpdate",
    "LoteKgDisponiblesUpdate",
    "LoteKgRealesUpdate",
    "LoteRead",
    "LoteUpdate",
    "TipoDeCafeCreate",
    "TipoDeCafeRead",
    "TipoDeCafeUpdate",
}


def _todos_los_schemas() -> dict[str, type[BaseModel]]:
    return {
        nombre: objeto
        for nombre, objeto in vars(schemas_inventario).items()
        if isinstance(objeto, type) and issubclass(objeto, BaseModel) and objeto is not BaseModel
    }


def test_el_modulo_expone_los_trece_schemas():
    assert set(_todos_los_schemas()) == ESQUEMAS_ESPERADOS


def test_no_existen_schemas_de_borrado():
    """El `id` del DELETE viaja por parámetro de ruta; un cuerpo con solo `id` sería redundante."""
    assert not any(nombre.endswith("Delete") for nombre in _todos_los_schemas())


@pytest.mark.parametrize("nombre", sorted(ESQUEMAS_ESPERADOS))
def test_todos_los_schemas_generan_json_schema(nombre: str):
    esquema = _todos_los_schemas()[nombre].model_json_schema()
    assert esquema.get("title")


@pytest.mark.parametrize("nombre", sorted(ESQUEMAS_ESPERADOS))
def test_ningun_schema_admite_campos_no_declarados(nombre: str):
    assert _todos_los_schemas()[nombre].model_config.get("extra") == "forbid"


@pytest.mark.parametrize("nombre", sorted(ESQUEMAS_ESPERADOS))
def test_todos_los_campos_tienen_descripcion_para_swagger(nombre: str):
    esquema = _todos_los_schemas()[nombre].model_json_schema()
    propiedades = esquema.get("properties", {})
    sin_descripcion = [campo for campo, datos in propiedades.items() if "description" not in datos]
    assert sin_descripcion == [], f"{nombre} sin descripción en: {sin_descripcion}"
