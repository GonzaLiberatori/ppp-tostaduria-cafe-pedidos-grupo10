"""Tests del registro público y del alta interna de cuentas.

El registro público nunca debe otorgar roles internos; para eso existe
``POST /auth/usuarios``, reservado al Administrador.
"""

PREFIJO = "/api/v1/auth"


def _headers(client, correo: str, password: str = "123456") -> dict[str, str]:
    respuesta = client.post(
        PREFIJO + "/login",
        json={"email": correo, "password": password},
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _crear_admin(db_session, correo: str = "admin@test.com"):
    from app.core.security import get_password_hash
    from app.modules.auth.models import Cuenta, UserRole

    cuenta = Cuenta(
        correo=correo,
        clave=get_password_hash("123456"),
        rol=UserRole.ADMINISTRADOR,
    )
    db_session.add(cuenta)
    db_session.commit()
    return cuenta


def test_registro_publico_ignora_el_rol_solicitado(client, db_session):
    """Aunque pidan Administrador, el alta pública crea un Cliente."""
    respuesta = client.post(
        PREFIJO + "/register",
        json={
            "email": "intruso@test.com",
            "password": "123456",
            "role": "Administrador",
        },
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["rol"] == "Cliente"

    perfil = client.get(
        PREFIJO + "/me", headers=_headers(client, "intruso@test.com")
    ).json()
    assert perfil["role"] == "cliente"
    assert perfil["clienteId"] is not None


def test_registro_publico_crea_persona_y_cliente(client, db_session):
    from app.modules.clientes.models import Cliente, Persona

    respuesta = client.post(
        PREFIJO + "/register",
        json={
            "email": "nuevo@test.com",
            "password": "123456",
            "nombre": "Ana Nueva",
            "telefono": "1100001111",
        },
    )

    assert respuesta.status_code == 201
    persona = (
        db_session.query(Persona)
        .filter(Persona.email == "nuevo@test.com")
        .first()
    )
    assert persona is not None
    assert persona.nombre == "Ana"
    assert persona.apellido == "Nueva"
    cliente = (
        db_session.query(Cliente)
        .filter(Cliente.persona_id == persona.id)
        .first()
    )
    assert cliente is not None


def test_registro_vincula_persona_existente(client, db_session):
    """Si el cliente ya fue cargado por el panel, el registro se vincula."""
    from app.modules.clientes.models import Cliente, Persona, TipoCliente

    persona = Persona(
        nombre="Cliente",
        apellido="Previo",
        email="previo@test.com",
        telefono="1122223333",
    )
    db_session.add(persona)
    db_session.flush()
    db_session.add(
        Cliente(persona_id=persona.id, tipo=TipoCliente.CONSUMIDOR_FINAL)
    )
    db_session.commit()

    respuesta = client.post(
        PREFIJO + "/register",
        json={"email": "previo@test.com", "password": "123456"},
    )

    assert respuesta.status_code == 201
    db_session.refresh(persona)
    assert persona.cuenta_id is not None
    assert (
        db_session.query(Cliente)
        .filter(Cliente.persona_id == persona.id)
        .count()
        == 1
    )


def test_registro_duplicado_da_conflicto(client):
    client.post(
        PREFIJO + "/register",
        json={"email": "repetido@test.com", "password": "123456"},
    )

    respuesta = client.post(
        PREFIJO + "/register",
        json={"email": "repetido@test.com", "password": "123456"},
    )

    assert respuesta.status_code == 400


def test_administrador_crea_cuenta_interna(client, db_session):
    _crear_admin(db_session)

    respuesta = client.post(
        PREFIJO + "/usuarios",
        json={
            "email": "cajero@test.com",
            "password": "123456",
            "role": "Cajero",
            "nombre": "Carla Cajera",
        },
        headers=_headers(client, "admin@test.com"),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["rol"] == "Cajero"
    assert (
        client.post(
            PREFIJO + "/login",
            json={"email": "cajero@test.com", "password": "123456"},
        ).status_code
        == 200
    )


def test_no_administrador_no_crea_cuentas_internas(client, db_session):
    from app.core.security import get_password_hash
    from app.modules.auth.models import Cuenta, UserRole

    db_session.add(
        Cuenta(
            correo="operario@test.com",
            clave=get_password_hash("123456"),
            rol=UserRole.OPERARIO,
        )
    )
    db_session.commit()

    respuesta = client.post(
        PREFIJO + "/usuarios",
        json={
            "email": "nuevo-admin@test.com",
            "password": "123456",
            "role": "Administrador",
        },
        headers=_headers(client, "operario@test.com"),
    )

    assert respuesta.status_code == 403
