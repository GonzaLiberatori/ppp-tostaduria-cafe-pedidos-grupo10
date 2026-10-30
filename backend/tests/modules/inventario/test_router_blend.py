"""Tests de las rutas HTTP de Blend.

Mismo patrón que el router de TipoDeCafe: app local, `get_db` reemplazado con
`dependency_overrides` y SQLite en memoria con `StaticPool`, porque `TestClient`
atiende las peticiones en otro hilo.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.deps import get_db
from app.modules.inventario.models import Blend, BlendHasTipoDeCafe, Lote, LoteEstado, LoteTipo
from app.modules.inventario.router import router

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
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as cliente:
        yield cliente

    app.dependency_overrides.clear()


def _crear(client, **extra) -> int:
    respuesta = client.post("/blends", json={**PAYLOAD, **extra})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


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
# 4.1 POST
# ---------------------------------------------------------------------------
def test_crear_devuelve_201_con_composicion(client):
    respuesta = client.post("/blends", json=PAYLOAD)
    cuerpo = respuesta.json()

    assert respuesta.status_code == 201
    assert cuerpo["id"] > 0
    assert cuerpo["nombre"] == "Mezcla Huila"
    assert [i["tipo_de_cafe_id"] for i in cuerpo["tipos_de_cafe"]] == [1, 2]


def test_crear_con_nombre_duplicado_devuelve_409(client):
    _crear(client)

    respuesta = client.post("/blends", json=PAYLOAD)

    assert respuesta.status_code == 409
    assert "Mezcla Huila" in respuesta.json()["detail"]


def test_crear_con_un_solo_tipo_devuelve_422(client):
    respuesta = client.post(
        "/blends", json={**PAYLOAD, "tipos_de_cafe": [{"tipo_de_cafe_id": 1, "porcentaje": "100.00"}]}
    )

    assert respuesta.status_code == 422


def test_crear_con_suma_de_99_99_devuelve_201(client):
    """Tolerancia de redondeo: 99.99 se acepta."""
    respuesta = client.post(
        "/blends",
        json={
            **PAYLOAD,
            "tipos_de_cafe": [
                {"tipo_de_cafe_id": 1, "porcentaje": "60.00"},
                {"tipo_de_cafe_id": 2, "porcentaje": "39.99"},
            ],
        },
    )

    assert respuesta.status_code == 201


def test_crear_con_suma_de_99_98_devuelve_422(client):
    respuesta = client.post(
        "/blends",
        json={
            **PAYLOAD,
            "tipos_de_cafe": [
                {"tipo_de_cafe_id": 1, "porcentaje": "60.00"},
                {"tipo_de_cafe_id": 2, "porcentaje": "39.98"},
            ],
        },
    )

    assert respuesta.status_code == 422


def test_crear_con_precio_no_positivo_devuelve_422(client):
    respuesta = client.post("/blends", json={**PAYLOAD, "precio_por_kg_verde": "0"})

    assert respuesta.status_code == 422


def test_crear_con_atributo_no_declarado_devuelve_422(client):
    respuesta = client.post("/blends", json={**PAYLOAD, "id": 9})

    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 4.2 GET
# ---------------------------------------------------------------------------
def test_leer_devuelve_200_con_la_composicion(client):
    blend_id = _crear(client)

    respuesta = client.get(f"/blends/{blend_id}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == blend_id
    assert len(cuerpo["tipos_de_cafe"]) == 2


def test_leer_con_id_inexistente_devuelve_404(client):
    respuesta = client.get("/blends/999")

    assert respuesta.status_code == 404


# ---------------------------------------------------------------------------
# 4.3 PATCH
# ---------------------------------------------------------------------------
def test_editar_devuelve_200_y_cambia_solo_lo_enviado(client):
    blend_id = _crear(client)

    respuesta = client.patch(f"/blends/{blend_id}", json={"precio_por_kg_verde": "1100.00"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["precio_por_kg_verde"] == "1100.00"
    assert cuerpo["nombre"] == "Mezcla Huila"
    assert len(cuerpo["tipos_de_cafe"]) == 2


def test_editar_reemplaza_la_composicion(client):
    blend_id = _crear(client)

    respuesta = client.patch(
        f"/blends/{blend_id}",
        json={
            "tipos_de_cafe": [
                {"tipo_de_cafe_id": 7, "porcentaje": "40.00"},
                {"tipo_de_cafe_id": 8, "porcentaje": "30.00"},
                {"tipo_de_cafe_id": 9, "porcentaje": "30.00"},
            ]
        },
    )

    assert respuesta.status_code == 200
    assert [i["tipo_de_cafe_id"] for i in respuesta.json()["tipos_de_cafe"]] == [7, 8, 9]


def test_editar_con_id_inexistente_devuelve_404(client):
    respuesta = client.patch("/blends/999", json={"nombre": "Otro"})

    assert respuesta.status_code == 404


def test_editar_con_precio_no_positivo_devuelve_422(client):
    blend_id = _crear(client)

    respuesta = client.patch(f"/blends/{blend_id}", json={"precio_por_kg_verde": "-1"})

    assert respuesta.status_code == 422

    vigente = client.get(f"/blends/{blend_id}")
    assert vigente.json()["precio_por_kg_verde"] == "980.00"


def test_editar_con_el_nombre_de_otro_blend_devuelve_409(client):
    _crear(client, nombre="Primero")
    segundo = _crear(client, nombre="Segundo")

    respuesta = client.patch(f"/blends/{segundo}", json={"nombre": "Primero"})

    assert respuesta.status_code == 409
    assert client.get(f"/blends/{segundo}").json()["nombre"] == "Segundo"


def test_editar_con_el_propio_nombre_no_es_conflicto(client):
    blend_id = _crear(client)

    respuesta = client.patch(f"/blends/{blend_id}", json={"nombre": "Mezcla Huila"})

    assert respuesta.status_code == 200


# ---------------------------------------------------------------------------
# 4.4 DELETE
# ---------------------------------------------------------------------------
def test_eliminar_devuelve_204_y_se_lleva_la_composicion(client, db):
    blend_id = _crear(client)

    respuesta = client.delete(f"/blends/{blend_id}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert client.get(f"/blends/{blend_id}").status_code == 404
    assert (
        db.query(BlendHasTipoDeCafe).filter_by(blend_id=blend_id).count() == 0
    )


def test_eliminar_con_id_inexistente_devuelve_404(client):
    respuesta = client.delete("/blends/999")

    assert respuesta.status_code == 404


def test_eliminar_referenciado_por_un_lote_devuelve_409(client, db):
    blend_id = _crear(client)
    _referenciar_con_lote(db, blend_id)

    respuesta = client.delete(f"/blends/{blend_id}")

    assert respuesta.status_code == 409
    assert "Lote" in respuesta.json()["detail"]
    assert client.get(f"/blends/{blend_id}").status_code == 200


def test_eliminar_con_composicion_sin_referencias_externas_devuelve_204(client):
    """La composición propia no bloquea: si lo hiciera, ningún blend se borra."""
    blend_id = _crear(client)

    assert client.delete(f"/blends/{blend_id}").status_code == 204
