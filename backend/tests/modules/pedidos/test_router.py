"""Tests de contrato API para el router de pedidos."""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, func, Enum as SQLEnum, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.deps import get_current_user
from app.modules.pedidos.models import EstadoPedidoEnum


# Test database (SQLite in-memory)
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Stub tables for foreign key references - using extend_existing to avoid conflicts
class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {"extend_existing": True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(10), nullable=False, default="B2B")
    monto_deuda = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = {"extend_existing": True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    variedad = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"extend_existing": True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="operador")
    activo = Column(Boolean, nullable=False, default=True)


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override para usar BD de test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Mock usuario autenticado."""
    user = MagicMock()
    user.id = 1
    return user


# Override dependencies
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Crea tablas frescas para cada test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestPedidosRouter:
    """Tests de endpoints de pedidos."""

    def test_listar_pedidos_sin_autenticacion(self):
        """GET /pedidos/ sin auth debe retornar 401."""
        app.dependency_overrides = {}  # Remove auth override
        response = client.get("/api/v1/pedidos/")
        assert response.status_code == 401
        # Restore
        app.dependency_overrides[get_current_user] = override_get_current_user

    def test_listar_pedidos_con_autenticacion(self):
        """GET /pedidos/ con auth debe retornar 200 (lista vacía)."""
        response = client.get("/api/v1/pedidos/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_listar_pedidos_con_filtros(self):
        """GET /pedidos/ con query params."""
        response = client.get("/api/v1/pedidos/?estado=Pendiente&page=1&page_size=10")
        assert response.status_code == 200

    def test_crear_pedido_datos_invalidos(self):
        """POST /pedidos/ con datos inválidos debe retornar 422."""
        response = client.post("/api/v1/pedidos/", json={
            "cliente_id": "invalid",
            "items": []
        })
        assert response.status_code == 422

    def test_crear_pedido_sin_items(self):
        """POST /pedidos/ sin items debe retornar 422."""
        response = client.post("/api/v1/pedidos/", json={
            "cliente_id": 1,
            "items": []
        })
        assert response.status_code == 422

    def test_obtener_pedido_inexistente(self):
        """GET /pedidos/{id} inexistente debe retornar 404."""
        response = client.get("/api/v1/pedidos/999999")
        assert response.status_code == 404

    def test_actualizar_pedido_inexistente(self):
        """PATCH /pedidos/{id} inexistente debe retornar 404."""
        response = client.patch("/api/v1/pedidos/999999", json={
            "observaciones": "Test"
        })
        assert response.status_code == 404

    def test_cambiar_estado_inexistente(self):
        """PATCH /pedidos/{id}/estado inexistente debe retornar 404."""
        response = client.patch("/api/v1/pedidos/999999/estado", json="Listo")
        assert response.status_code == 404

    def test_eliminar_pedido_inexistente(self):
        """DELETE /pedidos/{id} inexistente debe retornar 404."""
        response = client.delete("/api/v1/pedidos/999999")
        assert response.status_code == 404

    def test_listar_pedidos_por_cliente(self):
        """GET /pedidos/cliente/{cliente_id}."""
        response = client.get("/api/v1/pedidos/cliente/1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_health_check(self):
        """GET /health debe retornar ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"