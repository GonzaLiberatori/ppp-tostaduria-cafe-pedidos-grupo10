from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación."""

    PROJECT_NAME: str = "Café de Finca"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = (
        "mysql+pymysql://cafe_finca:cafe_finca@localhost:3306/cafe_finca"
        "?charset=utf8mb4"
    )

    JWT_SECRET_KEY: str = "cambiar-esta-clave-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "cambiar-en-produccion"
    ADMIN_NOMBRE: str = "Administrador"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def refresh_cookie_path(self) -> str:
        """Ruta mínima donde se envía la cookie de refresco."""
        return f"{self.API_PREFIX}/auth"


settings = Settings()
