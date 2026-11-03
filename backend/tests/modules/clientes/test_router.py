"""Tests del contrato HTTP de clientes: RBAC, portal y auto-scoping.

El portal del cliente ya consume ``/clientes/me`` y ``/clientes/{id}``, así que
se valida que un rol ``Cliente`` solo pueda ver y editar su propio perfil y que
el personal interno conserve sus permisos.
"""

import pytest

PREFIJO = "/api/v1/clientes"


def _crear_cuenta(db_session, correo: str, rol: str):
    """Inserta una cuenta con contraseña conocida para probar el login."""
    from app.core.security import get_password_hash
    from app.modules.auth.models import Cuenta, UserRole

    cuenta = Cuenta(
        correo=correo,
        clave=get_password_hash("123456"),
        rol=UserRole(rol),
    )
    db_session.add(cuenta)
    db_session.commit()
    return cuenta


def _headers(client, correo: str) -> dict[str, str]:
    """Inicia sesión y devuelve el header Authorization."""
    respuesta = client.post(
        "/api/v1/auth/login",
        json={"email": correo, "password": "123456"},
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _registrar_cliente(client, correo: str) -> dict[str, str]:
    """Registra un cliente público y devuelve sus headers."""
    respuesta = client.post(
        "/api/v1/auth/register",
        json={"email": correo, "password": "123456", "nombre": "Cliente Portal"},
    )
    assert respuesta.status_code == 201
    return _headers(client, correo)


def _crear_cliente_panel(client, headers: dict[str, str], **extra) -> dict:
    """Crea un cliente desde el panel y devuelve el contrato plano."""
    cuerpo = {
        "nombre": "Cliente Panel",
        "tipo": "B2C",
        "telefono": "1144440000",
        "email": "panel@test.com",
        "direccion": "Calle Panel 123",
    }
    cuerpo.update(extra)
    respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


class TestRBACPanel:
    """Permisos del personal interno sobre el padrón de clientes."""

    @pytest.mark.parametrize(
        "rol",
        ["Administrador", "Cajero", "Operario"],
    )
    def test_personal_interno_puede_listar(self, client, db_session, rol):
        correo = f"{rol.lower()}@test.com"
        _crear_cuenta(db_session, correo, rol)

        respuesta = client.get(PREFIJO + "/", headers=_headers(client, correo))

        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_operario_no_puede_crear(self, client, db_session):
        _crear_cuenta(db_session, "operario@test.com", "Operario")

        respuesta = client.post(
            PREFIJO + "/",
            json={"nombre": "No Permitido", "tipo": "B2C"},
            headers=_headers(client, "operario@test.com"),
        )

        assert respuesta.status_code == 403

    def test_cajero_puede_crear(self, client, db_session):
        _crear_cuenta(db_session, "cajero@test.com", "Cajero")

        cuerpo = _crear_cliente_panel(
            client, _headers(client, "cajero@test.com")
        )

        assert cuerpo["nombre"] == "Cliente Panel"
        assert cuerpo["tipo"] == "B2C"

    def test_cliente_no_puede_listar_el_padron(self, client):
        headers = _registrar_cliente(client, "portal@test.com")

        respuesta = client.get(PREFIJO + "/", headers=headers)

        assert respuesta.status_code == 403

    def test_solo_administrador_puede_eliminar(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        _crear_cuenta(db_session, "cajero@test.com", "Cajero")
        cuerpo = _crear_cliente_panel(
            client, _headers(client, "admin@test.com")
        )

        respuesta = client.delete(
            f"{PREFIJO}/{cuerpo['id']}",
            headers=_headers(client, "cajero@test.com"),
        )

        assert respuesta.status_code == 403

        respuesta = client.delete(
            f"{PREFIJO}/{cuerpo['id']}",
            headers=_headers(client, "admin@test.com"),
        )

        assert respuesta.status_code == 204


class TestPortalCliente:
    """Perfil propio y auto-scoping del rol Cliente."""

    def test_el_registro_publico_expone_cliente_id(self, client):
        headers = _registrar_cliente(client, "portal@test.com")

        respuesta = client.get("/api/v1/auth/me", headers=headers)

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["role"] == "cliente"
        assert cuerpo["clienteId"] is not None

    def test_cliente_ve_su_propio_perfil(self, client, db_session):
        headers = _registrar_cliente(client, "portal@test.com")

        respuesta = client.get(PREFIJO + "/me", headers=headers)

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["nombre"] == "Cliente Portal"
        assert cuerpo["email"] == "portal@test.com"

    def test_cliente_edita_su_propio_perfil(self, client):
        headers = _registrar_cliente(client, "portal@test.com")

        respuesta = client.patch(
            PREFIJO + "/me",
            json={
                "nombre": "Nombre Actualizado",
                "telefono": "1155550000",
                "direccion": "Nueva Direccion 456",
            },
            headers=headers,
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["nombre"] == "Nombre Actualizado"
        assert cuerpo["telefono"] == "1155550000"
        assert cuerpo["direccion"] == "Nueva Direccion 456"

    def test_cliente_no_puede_ver_otro_cliente(self, client, db_session):
        headers = _registrar_cliente(client, "portal@test.com")
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        otro = _crear_cliente_panel(
            client, _headers(client, "admin@test.com")
        )

        respuesta = client.get(f"{PREFIJO}/{otro['id']}", headers=headers)

        assert respuesta.status_code == 403

    def test_cliente_puede_ver_su_propio_id(self, client):
        headers = _registrar_cliente(client, "portal@test.com")
        perfil = client.get("/api/v1/auth/me", headers=headers).json()

        respuesta = client.get(f"{PREFIJO}/{perfil['clienteId']}", headers=headers)

        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == perfil["clienteId"]

    def test_cliente_no_puede_cambiarse_el_tipo_comercial(self, client):
        headers = _registrar_cliente(client, "portal@test.com")

        respuesta = client.patch(
            PREFIJO + "/me",
            json={"tipo": "B2B", "limiteCredito": 999999},
            headers=headers,
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["tipo"] == "B2C"
        assert cuerpo["limiteCredito"] is None


class TestAccesoPortal:
    """Alta de clientes con acceso de portal y limpieza al eliminarlos."""

    def test_crear_cliente_con_password_permite_login(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        cuerpo = _crear_cliente_panel(
            client,
            _headers(client, "admin@test.com"),
            email="nuevo@test.com",
            telefono="1166660000",
            password="secreto123",
        )

        respuesta = client.post(
            "/api/v1/auth/login",
            json={"email": "nuevo@test.com", "password": "secreto123"},
        )

        assert respuesta.status_code == 200
        headers = {
            "Authorization": f"Bearer {respuesta.json()['access_token']}"
        }
        perfil = client.get("/api/v1/auth/me", headers=headers).json()
        assert perfil["role"] == "cliente"
        assert perfil["clienteId"] == cuerpo["id"]

    def test_password_sin_email_es_invalido(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")

        respuesta = client.post(
            PREFIJO + "/",
            json={
                "nombre": "Sin Correo",
                "tipo": "B2C",
                "password": "secreto123",
            },
            headers=_headers(client, "admin@test.com"),
        )

        assert respuesta.status_code == 400

    def test_eliminar_cliente_borra_su_acceso(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        headers = _headers(client, "admin@test.com")
        cuerpo = _crear_cliente_panel(
            client,
            headers,
            email="borrar@test.com",
            telefono="1177770000",
            password="secreto123",
        )

        assert (
            client.delete(f"{PREFIJO}/{cuerpo['id']}", headers=headers).status_code
            == 204
        )

        respuesta = client.post(
            "/api/v1/auth/login",
            json={"email": "borrar@test.com", "password": "secreto123"},
        )

        assert respuesta.status_code == 401

    def test_actualizar_email_sincroniza_el_login(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        headers = _headers(client, "admin@test.com")
        cuerpo = _crear_cliente_panel(
            client,
            headers,
            email="viejo@test.com",
            telefono="1188880000",
            password="secreto123",
        )

        respuesta = client.patch(
            f"{PREFIJO}/{cuerpo['id']}",
            json={"email": "nuevo-correo@test.com"},
            headers=headers,
        )

        assert respuesta.status_code == 200

        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "viejo@test.com", "password": "secreto123"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "nuevo-correo@test.com", "password": "secreto123"},
            ).status_code
            == 200
        )

    def test_no_se_puede_vaciar_el_email_de_un_acceso(self, client, db_session):
        _crear_cuenta(db_session, "admin@test.com", "Administrador")
        headers = _headers(client, "admin@test.com")
        cuerpo = _crear_cliente_panel(
            client,
            headers,
            email="con-acceso@test.com",
            telefono="1199990000",
            password="secreto123",
        )

        respuesta = client.patch(
            f"{PREFIJO}/{cuerpo['id']}",
            json={"email": ""},
            headers=headers,
        )

        assert respuesta.status_code == 400
