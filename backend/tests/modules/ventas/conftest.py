"""Fixtures propias del módulo de ventas.

Se apoyan en las fixtures compartidas de ``backend/tests/conftest.py``, que no
se modifica: pytest combina los dos archivos automáticamente.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas import schemas as ventas_schemas
from app.modules.ventas import services as ventas_services


@pytest.fixture
def db_session():
    """Sesión sobre una SQLite en memoria compartida entre hilos.

    Reemplaza la fixture de ``tests/conftest.py`` solo para este módulo: el
    ``client`` de FastAPI atiende los requests en otro hilo y necesita ver las
    mismas tablas, cosa que ``sqlite:///:memory:`` sin ``StaticPool`` no
    garantiza. Es el mismo patrón que usan los tests de router de inventario.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


@pytest.fixture
def pedido_entregado_b2b(sample_pedido_b2b_entregado):
    """Pedido de cliente Mayorista ya ENTREGADO, sin venta registrada.

    Es el dato heredado que sigue entrando por el alta manual ``POST /ventas/``:
    desde 005 la entrega normal ya crea la venta, así que este pedido se fuerza
    a ``ENTREGADO`` sin pasar por el caso de uso de entrega.
    """
    return sample_pedido_b2b_entregado


@pytest.fixture
def pedido_entregado_consumidor(db_session, sample_pedido_consumidor_final):
    """Pedido de Consumidor Final ya ENTREGADO, sin venta registrada."""
    sample_pedido_consumidor_final.estado = "ENTREGADO"
    db_session.commit()
    db_session.refresh(sample_pedido_consumidor_final)
    return sample_pedido_consumidor_final


@pytest.fixture
def venta_confirmada(db_session, pedido_entregado_b2b):
    """Venta confirmada del pedido B2B, con un único pago a crédito."""
    service = ventas_services.VentaService(db_session)
    datos = ventas_schemas.VentaCreate(
        pedido_id=pedido_entregado_b2b.id,
        facturacion=Facturacion.FACTURA_A,
        pagos=[
            ventas_schemas.PagoCreate(
                metodo_de_pago=MetodoPago.CREDITO,
                monto=Decimal(str(pedido_entregado_b2b.total)),
                moneda=Moneda.ARS,
            )
        ],
    )
    return service.registrar_venta(datos)
