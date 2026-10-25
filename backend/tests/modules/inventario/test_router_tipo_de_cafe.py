"""Tests de las rutas HTTP de TipoDeCafe.

La app se arma local en el test y `get_db` se reemplaza con
`dependency_overrides`, de modo que el `get_db` real (que todavía no tiene
engine) nunca se ejecuta.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.deps import get_db
from app.modules.inventario.models import Blend, BlendHasTipoDeCafe, Lote, LoteEstado, LoteTipo, TipoDeCafe
from app.modules.inventario.router import router

PAYLOAD: dict[str, object] = {
    "organico": True,
    "precio_por_kg_verde": "1250.50",
    "variedad": "Caturra",
    "region": "Huila",
    "pais": "Colombia",
}


@pytest.fixture
def db():
    # StaticPool: TestClient atiende las peticiones en otro hilo, y con el pool
    # por defecto ese hilo recibiría una base en memoria distinta y vacía.
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


def _crear(client) -> int:
    respuesta = client.post("/tipos-de-cafe", json=PAYLOAD)
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


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
# 4.1 POST
# ---------------------------------------------------------------------------
def test_crear_devuelve_201_con_el_id(client):
    respuesta = client.post("/tipos-de-cafe", json=PAYLOAD)
    cuerpo = respuesta.json()

    assert respuesta.status_code == 201
    assert cuerpo["id"] > 0
    assert cuerpo["variedad"] == "Caturra"
    assert cuerpo["pais"] == "Colombia"


def test_crear_rechaza_precio_no_positivo_con_422(client):
    respuesta = client.post("/tipos-de-cafe", json={**PAYLOAD, "precio_por_kg_verde": "0"})

    assert respuesta.status_code == 422


def test_crear_rechaza_nombre_de_origen_vacio_con_422(client):
    respuesta = client.post("/tipos-de-cafe", json={**PAYLOAD, "region": ""})

    assert respuesta.status_code == 422


def test_crear_rechaza_atributo_no_declarado_con_422(client):
    respuesta = client.post("/tipos-de-cafe", json={**PAYLOAD, "region_id": 3})

    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 4.2 GET
# ---------------------------------------------------------------------------
def test_leer_devuelve_200_con_el_registro(client):
    tipo_id = _crear(client)

    respuesta = client.get(f"/tipos-de-cafe/{tipo_id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == tipo_id


def test_leer_con_id_inexistente_devuelve_404(client):
    respuesta = client.get("/tipos-de-cafe/999")

    assert respuesta.status_code == 404
    assert "999" in respuesta.json()["detail"]


# ---------------------------------------------------------------------------
# 4.3 PATCH
# ---------------------------------------------------------------------------
def test_editar_devuelve_200_y_cambia_solo_lo_enviado(client):
    tipo_id = _crear(client)

    respuesta = client.patch(f"/tipos-de-cafe/{tipo_id}", json={"organico": False})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["organico"] is False
    assert cuerpo["variedad"] == "Caturra"
    assert cuerpo["pais"] == "Colombia"


def test_editar_con_atributo_en_null_no_lo_modifica(client):
    tipo_id = _crear(client)

    respuesta = client.patch(f"/tipos-de-cafe/{tipo_id}", json={"variedad": None, "region": "Cauca"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["variedad"] == "Caturra"
    assert cuerpo["region"] == "Cauca"


def test_editar_con_id_inexistente_devuelve_404(client):
    respuesta = client.patch("/tipos-de-cafe/999", json={"organico": False})

    assert respuesta.status_code == 404


def test_editar_con_precio_no_positivo_devuelve_422(client):
    tipo_id = _crear(client)

    respuesta = client.patch(f"/tipos-de-cafe/{tipo_id}", json={"precio_por_kg_verde": "-1"})

    assert respuesta.status_code == 422

    # El precio sigue intacto. FastAPI serializa Decimal como string en JSON.
    vigente = client.get(f"/tipos-de-cafe/{tipo_id}")
    assert vigente.json()["precio_por_kg_verde"] == "1250.50"


# ---------------------------------------------------------------------------
# 4.4 DELETE
# ---------------------------------------------------------------------------
def test_eliminar_devuelve_204_y_el_registro_desaparece(client):
    tipo_id = _crear(client)

    respuesta = client.delete(f"/tipos-de-cafe/{tipo_id}")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert client.get(f"/tipos-de-cafe/{tipo_id}").status_code == 404


def test_eliminar_con_id_inexistente_devuelve_404(client):
    respuesta = client.delete("/tipos-de-cafe/999")

    assert respuesta.status_code == 404


def test_eliminar_referenciado_por_un_blend_devuelve_409(client, db):
    tipo_id = _crear(client)
    _referenciar_con_blend(db, tipo_id)

    respuesta = client.delete(f"/tipos-de-cafe/{tipo_id}")

    assert respuesta.status_code == 409
    assert "BlendHasTipoDeCafe" in respuesta.json()["detail"]
    assert client.get(f"/tipos-de-cafe/{tipo_id}").status_code == 200


def test_eliminar_referenciado_por_un_lote_devuelve_409(client, db):
    tipo_id = _crear(client)
    _referenciar_con_lote(db, tipo_id)

    respuesta = client.delete(f"/tipos-de-cafe/{tipo_id}")

    assert respuesta.status_code == 409
    assert "Lote" in respuesta.json()["detail"]
    assert client.get(f"/tipos-de-cafe/{tipo_id}").status_code == 200


def test_eliminar_referenciado_por_varias_entidades_nombrada_a_todas(client, db):
    tipo_id = _crear(client)
    _referenciar_con_blend(db, tipo_id)
    _referenciar_con_lote(db, tipo_id)

    detalle = client.delete(f"/tipos-de-cafe/{tipo_id}").json()["detail"]

    assert "BlendHasTipoDeCafe" in detalle
    assert "Lote" in detalle
