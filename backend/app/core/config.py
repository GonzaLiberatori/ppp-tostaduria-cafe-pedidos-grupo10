"""Configuración de la aplicación.

Carga variables de entorno desde .env y define la configuración centralizada
para base de datos, seguridad y otros parámetros del sistema.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación.

    Todos los valores se leen desde variables de entorno. Si no existen,
    se usan los defaults definidos acá.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Base de datos (requerido en .env)
    # -----------------------------------------------------------------------
    DATABASE_URL: str

    # -----------------------------------------------------------------------
    # Seguridad y JWT
    # -----------------------------------------------------------------------
    SECRET_KEY: str  # Requerido en .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # -----------------------------------------------------------------------
    # Aplicación
    # -----------------------------------------------------------------------
    APP_NAME: str = "Café de Finca"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"


# Instancia singleton para usar en toda la aplicación
settings = Settings()
