"""Fixtures propias del módulo de envíos programados.

Se apoyan en las fixtures compartidas de ``backend/tests/conftest.py``. La
sesión se redefine con ``StaticPool`` para que el ``TestClient`` (que atiende
en otro hilo) vea las mismas tablas que el test.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import create_access_token
from app.modules.auth.models import Cuenta
from app.modules.clientes.models import Cliente, Persona, TipoCliente
from app.modules.envios import schemas as envios_schemas
from app.modules.envios import services as envios_services

# Lunes: ``date.weekday() == 0``, que es el día que usan las suscripciones.
FECHA_LUNES = date(2026, 11, 2)


@pytest.fixture
def db_session():
    """Sesión sobre una SQLite en memoria compartida entre hilos."""
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
def servicio_envios(db_session):
    """Instancia del servicio de envíos sobre la sesión de prueba."""
    return envios_services.EnvioService(db_session)


@pytest.fixture
def suscripcion_lunes(db_session, sample_cliente_b2b, sample_tipo_cafe):
    """Suscripción activa del cliente B2B para el lunes de prueba."""
    return envios_services.EnvioService(db_session).crear_suscripcion(
        envios_schemas.SuscripcionCreate(
            clienteId=str(sample_cliente_b2b.persona_id),
            tipoDeCafeId=sample_tipo_cafe.id,
            cantidadKg=Decimal("5"),
            diaSemana=FECHA_LUNES.weekday(),
            plazoDias=30,
            fechaInicio=FECHA_LUNES,
        )
    )


@pytest.fixture
def otro_cliente_b2b(db_session):
    """Segundo cliente mayorista, con datos únicos para no chocar con el otro."""
    cuenta = Cuenta(correo="otro-b2b@test.com", clave="hashed", rol="Cliente")
    db_session.add(cuenta)
    db_session.flush()

    persona = Persona(
        nombre="Otro",
        apellido="Mayorista",
        telefono="5550001111",
        CUIT="20-11111111-1",
        cuenta_id=cuenta.id,
    )
    db_session.add(persona)
    db_session.flush()

    cliente = Cliente(
        persona_id=persona.id,
        tipo=TipoCliente.MAYORISTA,
        direccion_de_entrega="Avenida 456",
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


@pytest.fixture
def headers_admin(auth_headers):
    """Headers del usuario administrador creado por la fixture compartida."""
    return auth_headers


@pytest.fixture
def headers_cliente_b2b(db_session, sample_cliente_b2b):
    """Token de un usuario Cliente vinculado al cliente B2B de prueba."""
    persona = db_session.get(Persona, sample_cliente_b2b.persona_id)
    token = create_access_token({"sub": persona.cuenta.correo})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_cliente_consumidor(db_session, sample_cliente_consumidor_final):
    """Token de un usuario Cliente Consumidor Final."""
    persona = db_session.get(Persona, sample_cliente_consumidor_final.persona_id)
    token = create_access_token({"sub": persona.cuenta.correo})
    return {"Authorization": f"Bearer {token}"}
