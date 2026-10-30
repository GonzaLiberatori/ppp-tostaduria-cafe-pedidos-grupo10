"""Configuración de la aplicación.

Carga variables de entorno desde ``.env`` y define la configuración centralizada
para base de datos, seguridad y otros parámetros del sistema.

La base de datos soportada es SQLite. Las rutas relativas de ``DATABASE_URL``
se resuelven contra el directorio ``backend/`` para que el proyecto funcione
sin importar desde qué directorio se lance el proceso.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta del backend (backend/app/core/config.py -> backend/)
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "db.sqlite"

PREFIJO_SQLITE = "sqlite:///"


def normalizar_url_sqlite(url: str) -> str:
    """Valida que la URL sea SQLite y resuelve rutas relativas contra ``BASE_DIR``."""
    if not url.startswith("sqlite"):
        raise ValueError(
            "Solo se admite SQLite como base de datos: DATABASE_URL debe "
            "comenzar con 'sqlite:///' (o 'sqlite:///:memory:' en tests)."
        )

    if not url.startswith(PREFIJO_SQLITE):
        # sqlite:// (base temporal) u otra variante sin ruta de archivo.
        return url

    ruta = url[len(PREFIJO_SQLITE) :]
    if ruta in ("", ":memory:") or Path(ruta).is_absolute():
        return url

    return f"{PREFIJO_SQLITE}{(BASE_DIR / ruta).resolve().as_posix()}"


class Settings(BaseSettings):
    """Configuración global de la aplicación.

    Todos los valores se pueden sobrescribir desde variables de entorno o desde
    ``.env``. Los defaults permiten levantar el proyecto sin configuración
    adicional en desarrollo.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Base de datos (SQLite)
    # -----------------------------------------------------------------------
    DATABASE_URL: str = f"{PREFIJO_SQLITE}{DEFAULT_DB_PATH.as_posix()}"

    @field_validator("DATABASE_URL")
    @classmethod
    def validar_database_url(cls, url: str) -> str:
        """Rechaza motores distintos de SQLite y normaliza la ruta del archivo."""
        return normalizar_url_sqlite(url)

    # -----------------------------------------------------------------------
    # Seguridad y JWT
    # -----------------------------------------------------------------------
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # -----------------------------------------------------------------------
    # Aplicación
    # -----------------------------------------------------------------------
    APP_NAME: str = "Café de Finca"
    PROJECT_NAME: str = "Café de Finca"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


# Instancia singleton para usar en toda la aplicación
settings = Settings()
