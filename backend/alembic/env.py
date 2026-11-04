"""Configuración de Alembic para migraciones automáticas.

Lee la URL de base de datos desde la configuración centralizada (.env) y
registra el metadata de SQLAlchemy para que `alembic revision --autogenerate`
pueda detectar cambios en los modelos.
"""

import sys
from logging.config import fileConfig
from os import path

from alembic import context
from sqlalchemy import engine_from_config, pool

# El backend/ debe estar en sys.path para que los imports absolutos funcionen
# cuando Alembic corre desde su propia carpeta.
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "..")))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

# Importar modelos para que SQLAlchemy los registre en Base.metadata
from app.modules.inventario.models import (  # noqa: E402, F401
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    TipoDeCafe,
)

# ---------------------------------------------------------------------------
# Configuración de logging desde alembic.ini
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Metadata para detección automática de cambios
# ---------------------------------------------------------------------------
target_metadata = Base.metadata

# Sobrescribir la URL del .ini con la de configuración (.env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ---------------------------------------------------------------------------
# Modo offline: genera SQL sin conectarse a la base
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'.

    No necesita un engine ni una DBAPI disponible. Genera el SQL y lo escribe
    en el script de migración.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Modo online: se conecta a la base y aplica migraciones
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'.

    Crea un engine y asocia una conexión con el contexto de Alembic.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
