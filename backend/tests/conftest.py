"""Fixtures compartidas de la suite de tests.

La configuración se define antes de importar la aplicación para que
``Settings`` use la base SQLite en memoria y una clave JWT de pruebas.
"""

import os
from collections.abc import Callable, Generator

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "clave-de-pruebas-con-mas-de-32-caracteres"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "ClaveSegura123"
os.environ["ADMIN_NOMBRE"] = "Administrador"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.modules.auth.models import Rol, Usuario

PASSWORD_PRUEBA = "ClaveSegura123"
API = "/api"

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _activar_claves_foraneas(dbapi_connection: object, _: object) -> None:
    """SQLite no valida FKs por defecto; MySQL sí lo hace siempre."""

    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Base limpia por test y sesión única compartida con la API."""

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture()
def api(db: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP con la sesión de prueba inyectada."""

    def _get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def crear_usuario(
    db: Session,
) -> Callable[..., Usuario]:
    """Fábrica de usuarios con contraseña conocida."""

    def _crear(
        *,
        username: str,
        rol: Rol,
        password: str = PASSWORD_PRUEBA,
        activo: bool = True,
    ) -> Usuario:
        usuario = Usuario(
            username=username,
            nombre=username.title(),
            password_hash=hash_password(password),
            rol=rol,
            activo=activo,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    return _crear


@pytest.fixture()
def usuario_admin(crear_usuario: Callable[..., Usuario]) -> Usuario:
    return crear_usuario(username="admin", rol=Rol.ADMIN)


@pytest.fixture()
def usuario_empleado(crear_usuario: Callable[..., Usuario]) -> Usuario:
    return crear_usuario(username="empleado", rol=Rol.EMPLEADO)


@pytest.fixture()
def usuario_vendedor(crear_usuario: Callable[..., Usuario]) -> Usuario:
    return crear_usuario(username="vendedor", rol=Rol.VENDEDOR)


@pytest.fixture()
def auth_headers(
    api: TestClient,
) -> Callable[..., dict[str, str]]:
    """Inicia sesión y devuelve la cabecera Authorization."""

    def _headers(
        usuario: Usuario,
        password: str = PASSWORD_PRUEBA,
    ) -> dict[str, str]:
        respuesta = api.post(
            f"{API}/auth/login",
            json={"username": usuario.username, "password": password},
        )
        assert respuesta.status_code == 200, respuesta.text
        token = respuesta.json()["accessToken"]
        return {"Authorization": f"Bearer {token}"}

    return _headers
