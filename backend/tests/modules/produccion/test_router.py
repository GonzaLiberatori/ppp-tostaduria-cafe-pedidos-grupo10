"""Tests de las rutas HTTP del módulo de producción."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.deps import get_db
from app.modules.inventario.models import Lote, LoteEstado, LoteTipo, TipoDeCafe
from app.modules.produccion.router import router


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


def _crear_tipo_y_lote(db, kg: str = "10.000") -> tuple[TipoDeCafe, Lote]:
    tipo = TipoDeCafe(
        organico=True,
        precio_por_kg_verde=Decimal("1250.50"),
        variedad="Caturra",
        region="Huila",
        pais="Colombia",
    )
    db.add(tipo)
    db.flush()

    lote = Lote(
        tipo=LoteTipo.VERDE,
        estado=LoteEstado.ABIERTO,
        fecha_vencimiento=datetime.now() + timedelta(days=30),
        humedad=Decimal("11.50"),
        kg_disponibles=Decimal(kg),
        kg_reales=Decimal(kg),
        ubicacion_fisica="Bodega verde",
        tipo_de_cafe_id=tipo.id,
    )
    db.add(lote)
    db.commit()
    db.refresh(tipo)
    db.refresh(lote)
    return tipo, lote


def test_post_tueste_devuelve_201_con_trazabilidad(client, db):
    tipo, lote = _crear_tipo_y_lote(db)

    respuesta = client.post(
        "/tuestes",
        json={
            "gramos_verde": 5000,
            "gramos_tostado": 4000,
            "tipo_de_cafe_id": tipo.id,
        },
    )
    cuerpo = respuesta.json()

    assert respuesta.status_code == 201
    assert cuerpo["gramos_gastados"] == 5000
    assert cuerpo["gramos_obtenidos"] == 4000
    assert cuerpo["merma_gramos"] == 1000
    assert cuerpo["merma_porcentaje"] == "20.00"
    assert cuerpo["lote_tostado_id"] is not None
    assert cuerpo["consumos"] == [
        {
            "lote_id": lote.id,
            "kg_consumidos": "5.000",
            "gramos_consumidos": 5000,
        }
    ]


def test_post_tueste_sin_stock_devuelve_409(client, db):
    tipo, _ = _crear_tipo_y_lote(db, kg="1.000")

    respuesta = client.post(
        "/tuestes",
        json={
            "gramos_verde": 2000,
            "gramos_tostado": 1600,
            "tipo_de_cafe_id": tipo.id,
        },
    )

    assert respuesta.status_code == 409
    assert "insuficiente" in respuesta.json()["detail"].lower()


def test_post_tueste_con_tipo_inexistente_devuelve_404(client):
    respuesta = client.post(
        "/tuestes",
        json={
            "gramos_verde": 1000,
            "gramos_tostado": 800,
            "tipo_de_cafe_id": 999,
        },
    )

    assert respuesta.status_code == 404


def test_post_tueste_con_mas_tostado_que_verde_devuelve_422(client):
    respuesta = client.post(
        "/tuestes",
        json={
            "gramos_verde": 1000,
            "gramos_tostado": 1001,
            "tipo_de_cafe_id": 1,
        },
    )

    assert respuesta.status_code == 422
