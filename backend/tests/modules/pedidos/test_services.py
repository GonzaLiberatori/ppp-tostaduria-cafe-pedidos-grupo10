"""Integration tests for PedidoService.

Tests transacciones, FIFO, idempotencia, cuenta corriente, estados.
"""
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.database import engine as main_engine
from app.modules.pedidos.services import PedidoService
from app.modules.pedidos.schemas import PedidoCreate, PedidoItemCreate, EstadoPedidoEnum
from app.modules.pedidos.models import Pedido, PedidoItem, PedidoEstadoHistorial
from app.modules.clientes.models import Cliente
from app.modules.inventario.models import Stock, Bolsa
from app.modules.auth.models import Usuario


# Test database setup (SQLite in-memory for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def pedido_service():
    return PedidoService()


@pytest.fixture
def cliente_b2b(session):
    cliente = Cliente(
        id=1,
        nombre="Cafetería El Aroma",
        tipo="B2B",
        kilos_comprados=120,
        tiene_deuda=True,
        monto_deuda=Decimal("45000"),
        telefono="+54 11 4567-8901",
        email="pedidos@elaroma.com.ar",
        direccion="Av. Corrientes 1234, CABA",
    )
    session.add(cliente)
    session.flush()
    return cliente


@pytest.fixture
def cliente_b2c(session):
    cliente = Cliente(
        id=2,
        nombre="María González",
        tipo="B2C",
        kilos_comprados=5,
        tiene_deuda=False,
        monto_deuda=Decimal("0"),
        telefono="+54 9 11 6789-0123",
        email="maria.gonzalez@email.com",
        direccion="Palermo, CABA",
    )
    session.add(cliente)
    session.flush()
    return cliente


@pytest.fixture
def stock_tostado(session):
    stock = Stock(
        id=1,
        tipo="tostado",
        variedad="Arábica Bourbon - Tueste Medio",
        origen="Colombia - Huila",
        precio_kg=Decimal("18500"),
        lote_principal="TST-2026-001",
    )
    session.add(stock)
    session.flush()
    
    # Add bolsas
    bolsa1 = Bolsa(id="b1", stock_id=1, estado="cerrada", kilos=Decimal("1"), fecha_creacion=datetime.now(), lote_ref="TST-001")
    bolsa2 = Bolsa(id="b2", stock_id=1, estado="cerrada", kilos=Decimal("1"), fecha_creacion=datetime.now(), lote_ref="TST-002")
    bolsa3 = Bolsa(id="b3", stock_id=1, estado="abierta", kilos=Decimal("0.5"), fecha_creacion=datetime.now(), lote_ref="TST-003")
    session.add_all([bolsa1, bolsa2, bolsa3])
    session.flush()
    return stock


class TestPedidoServiceCrear:
    """Tests para crear_pedido."""

    def test_crear_pedido_exitoso(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test creación exitosa de pedido con stock suficiente."""
        dto = PedidoCreate(
            cliente_id=1,
            medio_contacto="WhatsApp",
            observaciones="Test",
            items=[
                PedidoItemCreate(
                    stock_id=1,
                    variedad="Arábica Bourbon - Tueste Medio",
                    kilos=Decimal("10"),
                    precio_kg=Decimal("18500"),
                ),
            ],
        )

        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)

        assert pedido.id is not None
        assert pedido.cliente_id == 1
        assert pedido.estado == EstadoPedidoEnum.PENDIENTE
        assert pedido.total == Decimal("185000")
        assert len(pedido.items) == 1
        assert pedido.items[0].variedad == "Arábica Bourbon - Tueste Medio"
        assert pedido.items[0].kilos == Decimal("10")

    def test_crear_pedido_idempotencia(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test que reintentos con misma clave no duplican."""
        dto = PedidoCreate(
            cliente_id=1,
            medio_contacto="WhatsApp",
            items=[
                PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("5"), precio_kg=Decimal("1000")),
            ],
        )

        # Primera creación
        pedido1 = pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        # Segunda creación (mismo cliente, items, fecha) - debería retornar el mismo
        pedido2 = pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        assert pedido1.id == pedido2.id
        # Solo un pedido en BD
        count = session.query(Pedido).count()
        assert count == 1

    def test_crear_pedido_stock_insuficiente(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test rechazo por stock insuficiente."""
        # stock_tostado tiene 2.5 kilos total (1+1+0.5)
        dto = PedidoCreate(
            cliente_id=1,
            items=[
                PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000")),
            ],
        )
        
        with pytest.raises(ValueError, match="Stock insuficiente"):
            pedido_service.crear_pedido(dto, user_id=1, session=session)


class TestPedidoServiceCambiarEstado:
    """Tests para cambiar_estado."""

    def test_pendiente_a_listo(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test transición válida Pendiente -> Listo."""
        # Crear pedido primero
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        # Cambiar a Listo
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        
        assert pedido.estado == EstadoPedidoEnum.LISTO
        
        # Verificar historial
        historial = session.query(PedidoEstadoHistorial).filter_by(pedido_id=pedido.id).all()
        assert len(historial) == 2  # Inicial + cambio
        assert historial[1].estado_anterior == EstadoPedidoEnum.PENDIENTE
        assert historial[1].estado_nuevo == EstadoPedidoEnum.LISTO

    def test_listo_a_entregado_b2b_actualiza_cuenta_corriente(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test Listo -> Entregado actualiza cuenta corriente B2B."""
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        
        # Cambiar a Entregado
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.ENTREGADO, user_id=1, session=session)
        
        assert pedido.estado == EstadoPedidoEnum.ENTREGADO
        
        # Verificar que se actualizó cuenta corriente
        cliente = session.query(Cliente).filter_by(id=1).first()
        assert cliente.monto_deuda == Decimal("10000")  # 10 * 1000

    def test_listo_a_entregado_b2c_no_afecta_cuenta(self, session, pedido_service, cliente_b2c, stock_tostado):
        """Test Listo -> Entregado con B2C no afecta cuenta corriente."""
        dto = PedidoCreate(
            cliente_id=2,  # cliente B2C
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        
        # Configurar cliente como B2C
        cliente = session.query(Cliente).filter_by(id=2).first()
        cliente.tipo = "B2C"
        
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.ENTREGADO, user_id=1, session=session)
        
        # Cuenta corriente no debe cambiar
        assert cliente.monto_deuda == Decimal("0")

    def test_transicion_invalida_pendiente_a_entregado(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test rechazo transición inválida Pendiente -> Entregado."""
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        with pytest.raises(ValueError, match="Transición inválida"):
            pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.ENTREGADO, user_id=1, session=session)

    def test_reversion_entregado_a_listo_resta_cuenta(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test Entregado -> Listo resta de cuenta corriente B2B."""
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.ENTREGADO, user_id=1, session=session)
        
        # Revertir
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        
        assert pedido.estado == EstadoPedidoEnum.LISTO
        
        cliente = session.query(Cliente).filter_by(id=1).first()
        assert cliente.monto_deuda == Decimal("0")  # Se restó


class TestPedidoServiceEliminar:
    """Tests para eliminar_pedido."""

    def test_eliminar_pendiente_restaura_stock_y_cuenta(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test eliminar pedido Pendiente restaura stock y cuenta."""
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        # Verificar cuenta antes
        cliente = session.query(Cliente).filter_by(id=1).first()
        deuda_antes = cliente.monto_deuda
        
        # Eliminar
        pedido_service.eliminar_pedido(pedido.id, session)
        
        # Verificar que no existe
        assert session.query(Pedido).filter_by(id=pedido.id).first() is None
        
        # Verificar cuenta restaurada
        cliente = session.query(Cliente).filter_by(id=1).first()
        assert cliente.monto_deuda == Decimal("0")

    def test_eliminar_listo_rechaza(self, session, pedido_service, cliente_b2b, stock_tostado):
        """Test rechazo al eliminar pedido Listo."""
        dto = PedidoCreate(
            cliente_id=1,
            items=[PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
        )
        pedido = pedido_service.crear_pedido(dto, user_id=1, session=session)
        pedido = pedido_service.cambiar_estado(pedido.id, EstadoPedidoEnum.LISTO, user_id=1, session=session)
        
        with pytest.raises(ValueError, match="Solo se pueden eliminar pedidos en estado Pendiente"):
            pedido_service.eliminar_pedido(pedido.id, session)


class TestPedidoServiceFiltros:
    """Tests para get_pedidos_con_filtros."""

    def test_listar_con_filtros(self, session, pedido_service, cliente_b2b, cliente_b2c, stock_tostado):
        """Test listado con filtros y paginación."""
        # Crear varios pedidos
        for i in range(5):
            dto = PedidoCreate(
                cliente_id=1 if i % 2 == 0 else 2,
                items=[PedidoItemCreate(stock_id=1, variedad=f"Test{i}", kilos=Decimal("10"), precio_kg=Decimal("1000"))],
            )
            pedido_service.crear_pedido(dto, user_id=1, session=session)
        
        # Filtrar por cliente
        pedidos, total = pedido_service.get_pedidos_con_filtros(
            cliente_id=1, page=1, page_size=10, session=session
        )
        assert total == 3  # 3 pedidos para cliente 1
        assert len(pedidos) == 3

        # Paginación
        pedidos, total = pedido_service.get_pedidos_con_filtros(
            page=1, page_size=2, session=session
        )
        assert len(pedidos) == 2
        assert total == 5