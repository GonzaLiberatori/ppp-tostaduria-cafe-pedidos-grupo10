"""Configuración de la aplicación.

Carga variables de entorno desde ``.env`` y define la configuración centralizada
para base de datos, seguridad y otros parámetros del sistema.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta del backend, para que la base SQLite por defecto no dependa del
# directorio desde el que se lance el proceso.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "demo.db")


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
    # Base de datos
    # -----------------------------------------------------------------------
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"

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
