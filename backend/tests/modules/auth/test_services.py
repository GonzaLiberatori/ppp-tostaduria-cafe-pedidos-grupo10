"""Tests de autenticación: login, refresh rotado y revocación."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth import services
from app.modules.auth.models import RefreshToken, Rol, Usuario
from tests.conftest import API, PASSWORD_PRUEBA


def _login(
    api: TestClient,
    username: str = "admin",
    password: str = PASSWORD_PRUEBA,
) -> dict[str, str]:
    respuesta = api.post(
        f"{API}/auth/login",
        json={"username": username, "password": password},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_login_devuelve_access_token_y_cookie_httponly(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    respuesta = api.post(
        f"{API}/auth/login",
        json={"username": "admin", "password": PASSWORD_PRUEBA},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["accessToken"]
    assert cuerpo["tokenType"] == "bearer"
    assert cuerpo["expiresIn"] == 15 * 60

    cookie = respuesta.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/auth" in cookie
    assert "SameSite=lax" in cookie


def test_login_con_password_incorrecta_devuelve_401(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    respuesta = api.post(
        f"{API}/auth/login",
        json={"username": "admin", "password": "incorrecta"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos"


def test_login_de_usuario_inexistente_devuelve_401(api: TestClient) -> None:
    respuesta = api.post(
        f"{API}/auth/login",
        json={"username": "fantasma", "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 401


def test_login_de_usuario_inactivo_devuelve_401(
    api: TestClient,
    crear_usuario: Callable[..., Usuario],
) -> None:
    crear_usuario(username="inactivo", rol=Rol.ADMIN, activo=False)

    respuesta = api.post(
        f"{API}/auth/login",
        json={"username": "inactivo", "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 401


def test_me_requiere_token(api: TestClient) -> None:
    assert api.get(f"{API}/auth/me").status_code == 401
    respuesta = api.get(
        f"{API}/auth/me",
        headers={"Authorization": "Bearer token-invalido"},
    )
    assert respuesta.status_code == 401


def test_me_devuelve_usuario_autenticado(
    api: TestClient,
    usuario_admin: Usuario,
    auth_headers: Callable[..., dict[str, str]],
) -> None:
    respuesta = api.get(
        f"{API}/auth/me",
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "admin"
    assert cuerpo["rol"] == "ADMIN"
    assert "password_hash" not in cuerpo


def test_refresh_token_no_sirve_como_access_token(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    _login(api, usuario_admin.username)
    refresh = api.cookies.get("refresh_token")
    assert refresh

    respuesta = api.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert respuesta.status_code == 401


def test_refresh_sin_cookie_devuelve_401(api: TestClient) -> None:
    assert api.post(f"{API}/auth/refresh").status_code == 401


def test_refresh_rota_el_token(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    login = _login(api, usuario_admin.username)
    refresh_original = api.cookies.get("refresh_token")
    assert refresh_original

    respuesta = api.post(f"{API}/auth/refresh")

    assert respuesta.status_code == 200
    nuevo_access = respuesta.json()["accessToken"]
    refresh_nuevo = api.cookies.get("refresh_token")
    assert refresh_nuevo
    assert refresh_nuevo != refresh_original

    me = api.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {nuevo_access}"},
    )
    assert me.status_code == 200
    assert login["accessToken"]


def test_reutilizar_refresh_rotado_revoca_la_familia(
    api: TestClient,
    usuario_admin: Usuario,
    db: Session,
) -> None:
    _login(api, usuario_admin.username)
    refresh_original = api.cookies.get("refresh_token")
    assert refresh_original

    assert api.post(f"{API}/auth/refresh").status_code == 200
    refresh_nuevo = api.cookies.get("refresh_token")
    assert refresh_nuevo and refresh_nuevo != refresh_original

    # Se reutiliza el token viejo: debe fallar y revocar el token vigente.
    api.cookies.clear()
    reutilizado = api.post(
        f"{API}/auth/refresh",
        cookies={"refresh_token": refresh_original},
    )
    assert reutilizado.status_code == 401

    api.cookies.clear()
    vigente = api.post(
        f"{API}/auth/refresh",
        cookies={"refresh_token": refresh_nuevo},
    )
    assert vigente.status_code == 401

    activos = (
        db.query(RefreshToken)
        .filter(RefreshToken.revocado_en.is_(None))
        .count()
    )
    assert activos == 0


def test_refresh_firmado_con_otra_clave_devuelve_401(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    _login(api, usuario_admin.username)
    refresh = api.cookies.get("refresh_token")
    assert refresh

    api.cookies.clear()
    respuesta = api.post(
        f"{API}/auth/refresh",
        cookies={"refresh_token": refresh[:-3] + "abc"},
    )
    assert respuesta.status_code == 401


def test_crear_usuario_inicial_es_idempotente(db: Session) -> None:
    primero = services.crear_usuario_inicial(db)
    segundo = services.crear_usuario_inicial(db)

    assert primero.id == segundo.id
    assert primero.username == settings.ADMIN_USERNAME
    assert primero.rol == Rol.ADMIN
    assert db.query(Usuario).count() == 1


def test_logout_revoca_el_refresh_y_borra_la_cookie(
    api: TestClient,
    usuario_admin: Usuario,
) -> None:
    _login(api, usuario_admin.username)
    refresh = api.cookies.get("refresh_token")
    assert refresh

    respuesta = api.post(f"{API}/auth/logout")

    assert respuesta.status_code == 204
    assert api.cookies.get("refresh_token") is None

    api.cookies.clear()
    reutilizado = api.post(
        f"{API}/auth/refresh",
        cookies={"refresh_token": refresh},
    )
    assert reutilizado.status_code == 401

    # El logout es idempotente y no revela si el token era válido.
    assert api.post(f"{API}/auth/logout").status_code == 204
