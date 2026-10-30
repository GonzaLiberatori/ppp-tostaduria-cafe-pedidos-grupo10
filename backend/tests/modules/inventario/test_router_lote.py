"""Tests de las rutas HTTP de Lote.

Mismo patrón que los routers de TipoDeCafe y Blend: app local, `get_db`
reemplazado con `dependency_overrides` y SQLite en memoria con `StaticPool`,
porque `TestClient` atiende las peticiones en otro hilo.
"""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.deps import get_db
from app.modules.inventario.models import Lote, TipoDeCafe
from app.modules.inventario.router import router

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


@pytest.fixture
def origen(db) -> int:
    return _crear_tipo_de_cafe(db)


def _crear(client, **extra) -> int:
    respuesta = client.post("/lotes", json={**PAYLOAD, **extra})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


# ---------------------------------------------------------------------------
# 4.1 POST
# ---------------------------------------------------------------------------
def test_crear_devuelve_201_y_deriva_kg_disponibles(client, db, origen):
    respuesta = client.post("/lotes", json=PAYLOAD)
    cuerpo = respuesta.json()

    assert respuesta.status_code == 201
    assert cuerpo["id"] > 0
    assert cuerpo["kg_reales"] == "59.80"
    assert cuerpo["kg_disponibles"] == "59.80"


def test_crear_con_kg_reales_en_cero(client, db, origen):
    cuerpo = client.post("/lotes", json={**PAYLOAD, "kg_reales": "0"}).json()

    assert cuerpo["kg_reales"] == "0.00"
    assert cuerpo["kg_disponibles"] == "0.00"


def test_crear_con_origen_inexistente_devuelve_404(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "tipo_de_cafe_id": 999})

    assert respuesta.status_code == 404
    assert "TipoDeCafe" in respuesta.json()["detail"]


def test_crear_sin_origen_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "tipo_de_cafe_id": None})

    assert respuesta.status_code == 422


def test_crear_con_ambos_origenes_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "blend_id": 7})

    assert respuesta.status_code == 422


def test_crear_tostado_sin_orden_de_tueste_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "tipo": "TOSTADO"})

    assert respuesta.status_code == 422


def test_crear_verde_con_orden_de_tueste_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "orden_tueste_id": 5})

    assert respuesta.status_code == 422


def test_crear_enviando_kg_disponibles_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "kg_disponibles": "10.00"})

    assert respuesta.status_code == 422


def test_crear_con_humedad_fuera_de_rango_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "humedad": "101"})

    assert respuesta.status_code == 422


def test_crear_con_kg_reales_negativos_devuelve_422(client, db, origen):
    respuesta = client.post("/lotes", json={**PAYLOAD, "kg_reales": "-1"})

    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 4.2 GET
# ---------------------------------------------------------------------------
def test_leer_devuelve_200_con_las_claves_foraneas(client, db, origen):
    lote_id = _crear(client)

    cuerpo = client.get(f"/lotes/{lote_id}").json()

    assert cuerpo["tipo_de_cafe_id"] == origen
    assert cuerpo["blend_id"] is None
    assert cuerpo["orden_tueste_id"] is None
    assert cuerpo["kg_disponibles"] == "59.80"


def test_leer_con_id_inexistente_devuelve_404(client, db, origen):
    assert client.get("/lotes/999").status_code == 404


# ---------------------------------------------------------------------------
# 4.3 PATCH
# ---------------------------------------------------------------------------
def test_editar_devuelve_200_y_cambia_solo_lo_enviado(client, db, origen):
    lote_id = _crear(client)

    cuerpo = client.patch(f"/lotes/{lote_id}", json={"estado": "CERRADO"}).json()

    assert cuerpo["estado"] == "CERRADO"
    assert cuerpo["ubicacion_fisica"] == "PASILLO-01"
    assert cuerpo["kg_reales"] == "59.80"


def test_editar_con_id_inexistente_devuelve_404(client, db, origen):
    assert client.patch("/lotes/999", json={"estado": "CERRADO"}).status_code == 404


def test_editar_con_humedad_fuera_de_rango_devuelve_422(client, db, origen):
    lote_id = _crear(client)

    assert client.patch(f"/lotes/{lote_id}", json={"humedad": "101"}).status_code == 422

    vigente = client.get(f"/lotes/{lote_id}")
    assert vigente.json()["humedad"] == "11.50"


def test_editar_rechaza_el_tipo_o_una_clave_foranea(client, db, origen):
    lote_id = _crear(client)

    for prohibido in ("tipo", "tipo_de_cafe_id", "blend_id", "orden_tueste_id"):
        respuesta = client.patch(f"/lotes/{lote_id}", json={prohibido: 1})
        assert respuesta.status_code == 422, prohibido


# ---------------------------------------------------------------------------
# 4.4 DELETE
# ---------------------------------------------------------------------------
def test_eliminar_devuelve_204_y_no_arrasta_al_origen(client, db, origen):
    lote_id = _crear(client)

    respuesta = client.delete(f"/lotes/{lote_id}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert client.get(f"/lotes/{lote_id}").status_code == 404
    assert db.get(TipoDeCafe, origen) is not None
    assert db.get(Lote, lote_id) is None


def test_eliminar_con_id_inexistente_devuelve_404(client, db, origen):
    assert client.delete("/lotes/999").status_code == 404
