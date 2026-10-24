import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.core.database import Base
from app.main import app
from app.core.database import get_db


# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Crear una nueva sesión de base de datos para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de prueba con override de get_db."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Crear usuario y obtener headers de autenticación."""
    # Registrar usuario admin
    client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "123456",
        "role": "Administrador"
    })
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "123456"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_cliente(db_session):
    """Crear un cliente de prueba."""
    from app.modules.auth.models import Cuenta
    from app.modules.pedidos.models import Persona, Cliente, TipoCliente
    
    # Crear cuenta
    cuenta = Cuenta(correo="cliente@test.com", clave="hashed", rol="Cliente")
    db_session.add(cuenta)
    db_session.flush()
    
    # Crear persona
    persona = Persona(
        nombre="Juan",
        apellido="Perez",
        telefono="1122334455",
        CUIT="20-12345678-9",
        cuenta_id=cuenta.id
    )
    db_session.add(persona)
    db_session.flush()
    
    # Crear cliente
    cliente = Cliente(
        persona_id=persona.id,
        tipo=TipoCliente.MAYORISTA,
        direccion_de_entrega="Calle 123"
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    
    return cliente


@pytest.fixture(scope="function")
def sample_cliente_b2b(db_session):
    """Crear un cliente B2B (Mayorista) de prueba."""
    from app.modules.auth.models import Cuenta
    from app.modules.pedidos.models import Persona, Cliente, TipoCliente
    
    cuenta = Cuenta(correo="b2b@test.com", clave="hashed", rol="Cliente")
    db_session.add(cuenta)
    db_session.flush()
    
    persona = Persona(
        nombre="B2B",
        apellido="Test",
        telefono="5555555555",
        CUIT="20-99999999-9",
        cuenta_id=cuenta.id
    )
    db_session.add(persona)
    db_session.flush()
    
    cliente = Cliente(
        persona_id=persona.id,
        tipo=TipoCliente.MAYORISTA,
        direccion_de_entrega="Calle B2B"
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    
    return cliente


@pytest.fixture(scope="function")
def sample_cliente_consumidor_final(db_session):
    """Crear un cliente Consumidor Final de prueba."""
    from app.modules.auth.models import Cuenta
    from app.modules.pedidos.models import Persona, Cliente, TipoCliente
    
    cuenta = Cuenta(correo="consumidor@test.com", clave="hashed", rol="Cliente")
    db_session.add(cuenta)
    db_session.flush()
    
    persona = Persona(
        nombre="Consumidor",
        apellido="Final",
        telefono="7777777777",
        CUIT="20-88888888-8",
        cuenta_id=cuenta.id
    )
    db_session.add(persona)
    db_session.flush()
    
    cliente = Cliente(
        persona_id=persona.id,
        tipo=TipoCliente.CONSUMIDOR_FINAL,
        direccion_de_entrega="Calle Consumidor"
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    
    return cliente


@pytest.fixture(scope="function")
def sample_empleado(db_session):
    """Crear un empleado de prueba."""
    from app.modules.auth.models import Cuenta
    from app.modules.pedidos.models import Persona, Empleado
    from datetime import date
    
    cuenta = Cuenta(correo="empleado@test.com", clave="hashed", rol="Cajero")
    db_session.add(cuenta)
    db_session.flush()
    
    persona = Persona(
        nombre="Carlos",
        apellido="Gomez",
        telefono="1133445566",
        cuenta_id=cuenta.id
    )
    db_session.add(persona)
    db_session.flush()
    
    empleado = Empleado(
        persona_id=persona.id,
        fecha_de_contratacion=date(2020, 1, 1),
        fecha_de_nacimiento=date(1990, 1, 1),
        salario=500000
    )
    db_session.add(empleado)
    db_session.commit()
    db_session.refresh(empleado)
    
    return empleado


@pytest.fixture(scope="function")
def sample_tipo_cafe(db_session):
    """Crear tipo de café de prueba."""
    from app.modules.pedidos.models import Pais, Region, Variedad, TipoDeCafe
    
    pais = Pais(nombre="Colombia")
    db_session.add(pais)
    db_session.flush()
    
    region = Region(nombre="Huila", pais_id=pais.id)
    db_session.add(region)
    db_session.flush()
    
    variedad = Variedad(nombre="Caturra")
    db_session.add(variedad)
    db_session.flush()
    
    tipo_cafe = TipoDeCafe(
        organico=1,
        precio_por_kg_verde=50000,
        region_id=region.id,
        variedad_id=variedad.id
    )
    db_session.add(tipo_cafe)
    db_session.commit()
    db_session.refresh(tipo_cafe)
    
    return tipo_cafe


@pytest.fixture(scope="function")
def sample_molienda(db_session):
    """Crear molienda de prueba."""
    from app.modules.pedidos.models import Molienda
    
    molienda = Molienda(tipo="Granel", valor_agregado_por_kg=0)
    db_session.add(molienda)
    db_session.commit()
    db_session.refresh(molienda)
    return molienda


@pytest.fixture(scope="function")
def sample_perfil_tostado(db_session):
    """Crear perfil de tostado de prueba."""
    from app.modules.pedidos.models import PerfilDeTostado
    
    perfil = PerfilDeTostado(variante="Medio", valor_agregado_por_kg=5000)
    db_session.add(perfil)
    db_session.commit()
    db_session.refresh(perfil)
    return perfil


@pytest.fixture(scope="function")
def sample_lote(db_session, sample_tipo_cafe):
    """Crear lote de prueba con stock."""
    from app.modules.pedidos.models import Lote, TipoLote, EstadoLote, OrdenTueste, PerfilDeTostado
    from datetime import datetime, timedelta
    
    # Crear orden de tueste si no existe
    perfil = PerfilDeTostado(variante="Medio", valor_agregado_por_kg=5000)
    db_session.add(perfil)
    db_session.flush()
    
    orden = OrdenTueste(
        fecha_tueste=datetime.now(),
        kg_gastados=100,
        kg_obtenidos=85,
        perfil_de_tostado_id=perfil.id
    )
    db_session.add(orden)
    db_session.flush()
    
    lote = Lote(
        tipo="TOSTADO",
        estado="ABIERTO",
        fecha_vencimiento=datetime.now() + timedelta(days=365),
        humedad=12.5,
        kg_disponibles=100,
        kg_reales=100,
        ubicacion_fisica="Bodega A",
        tipo_de_cafe_id=sample_tipo_cafe.id,
        orden_tueste_id=orden.id
    )
    db_session.add(lote)
    db_session.commit()
    db_session.refresh(lote)
    return lote


@pytest.fixture(scope="function")
def sample_lote_detallado(db_session, sample_tipo_cafe):
    """Crear múltiples lotes con diferentes fechas para test FIFO."""
    from app.modules.pedidos.models import Lote, TipoLote, EstadoLote, OrdenTueste, PerfilDeTostado
    from datetime import datetime, timedelta
    
    perfil = PerfilDeTostado(variante="Medio", valor_agregado_por_kg=5000)
    db_session.add(perfil)
    db_session.flush()
    
    orden = OrdenTueste(
        fecha_tueste=datetime.now(),
        kg_gastados=100,
        kg_obtenidos=85,
        perfil_de_tostado_id=perfil.id
    )
    db_session.add(orden)
    db_session.flush()
    
    # Lote 1: vence primero (50kg)
    lote1 = Lote(
        tipo="TOSTADO",
        estado="ABIERTO",
        fecha_vencimiento=datetime.now() + timedelta(days=30),
        humedad=12.5,
        kg_disponibles=50,
        kg_reales=50,
        ubicacion_fisica="Bodega A",
        tipo_de_cafe_id=sample_tipo_cafe.id,
        orden_tueste_id=1
    )
    db_session.add(lote1)
    
    # Lote 2: vence después (50kg)
    lote2 = Lote(
        tipo="TOSTADO",
        estado="ABIERTO",
        fecha_vencimiento=datetime.now() + timedelta(days=60),
        humedad=12.5,
        kg_disponibles=50,
        kg_reales=50,
        ubicacion_fisica="Bodega B",
        tipo_de_cafe_id=sample_tipo_cafe.id,
        orden_tueste_id=1
    )
    db_session.add(lote2)
    db_session.commit()
    db_session.refresh(lote1)
    db_session.refresh(lote2)
    return [lote1, lote2]


@pytest.fixture(scope="function")
def sample_pedido(db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
    """Crear un pedido de prueba básico con un item."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("5"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            cliente_persona_id=sample_cliente.persona_id,
            empleado_persona_id=sample_empleado.persona_id,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("5"),
                    tipo_de_cafe_id=sample_tipo_cafe.id,
                    molienda_id=sample_molienda.id,
                    perfil_de_tostado_id=sample_perfil_tostado.id
                )
            ]
        ), sample_empleado.persona_id)
    return pedido


@pytest.fixture(scope="function")
def sample_pedido_con_stock(db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
    """Crear un pedido con stock reservado."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("10"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        pedido_data, sample_empleado.persona_id)
    return pedido


@pytest.fixture(scope="function")
def sample_pedido_con_stock_detallado(db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote_detallado):
    """Crear un pedido que consuma de múltiples lotes para test FIFO."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("60"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        pedido_data, sample_empleado.persona_id)
    return pedido


@pytest.fixture(scope="function")
def sample_pedido_b2b(db_session, sample_cliente_b2b, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
    """Crear un pedido B2B."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente_b2b.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("10"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        pedido_data, sample_empleado.persona_id)
    return pedido


@pytest.fixture(scope="function")
def sample_pedido_b2b_entregado(db_session, sample_pedido_b2b):
    """Pedido B2B en estado ENTREGADO."""
    from app.modules.pedidos import services
    service = services.PedidoService(db_session)
    service.cambiar_estado_pedido(sample_pedido_b2b.id, "LISTO")
    service.cambiar_estado_pedido(sample_pedido_b2b.id, "ENTREGADO")
    db_session.refresh(sample_pedido_b2b)
    return sample_pedido_b2b


@pytest.fixture(scope="function")
def sample_pedido_b2b_entregado_revierte(db_session, sample_cliente_b2b, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
    """Pedido B2B entregado para test de reversión."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente_b2b.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("10"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        pedido_data, sample_empleado.persona_id)
    
    # Avanzar a ENTREGADO
    service = services.PedidoService(db_session)
    service.cambiar_estado_pedido(pedido.id, "LISTO")
    service.cambiar_estado_pedido(pedido.id, "ENTREGADO")
    db_session.refresh(pedido)
    return pedido


@pytest.fixture(scope="function")
def sample_pedido_consumidor_final(db_session, sample_cliente_consumidor_final, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
    """Crear un pedido para Consumidor Final."""
    from app.modules.pedidos import schemas, services
    
    service = services.PedidoService(db_session)
    
    pedido_data = schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=sample_cliente_consumidor_final.persona_id,
        empleado_persona_id=sample_empleado.persona_id,
        detalles=[
            schemas.DetallePedidoCreate(
                cantidad_kg=Decimal("5"),
                tipo_de_cafe_id=sample_tipo_cafe.id,
                molienda_id=sample_molienda.id,
                perfil_de_tostado_id=sample_perfil_tostado.id
            )
        ]
    )
    
    pedido = services.PedidoService(db_session).crear_pedido_completo(
        pedido_data, sample_empleado.persona_id)
    return pedido