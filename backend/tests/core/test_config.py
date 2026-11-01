"""Tests de la configuración central del backend."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BASE_DIR, Settings


def test_url_relativa_se_resuelve_contra_backend() -> None:
    """Una ruta SQLite relativa no debe depender del directorio de ejecución."""
    config = Settings(DATABASE_URL="sqlite:///./db.sqlite", _env_file=None)

    esperada = f"sqlite:///{(BASE_DIR / 'db.sqlite').as_posix()}"
    assert config.DATABASE_URL == esperada
    assert Path(config.DATABASE_URL.removeprefix("sqlite:///")).is_absolute()


def test_url_en_memoria_no_se_modifica() -> None:
    """La base en memoria de los tests se conserva tal cual."""
    config = Settings(DATABASE_URL="sqlite:///:memory:", _env_file=None)

    assert config.DATABASE_URL == "sqlite:///:memory:"


def test_rechaza_motores_distintos_de_sqlite() -> None:
    """El proyecto solo admite SQLite como base de datos."""
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/cafe_finca",
            _env_file=None,
        )
