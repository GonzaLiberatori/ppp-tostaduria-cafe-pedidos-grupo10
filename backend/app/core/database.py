from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import settings


def get_connect_args(database_url: str) -> dict:
    """Get database-specific connection arguments."""
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {"charset": "utf8mb4"}


def get_pool_class(database_url: str):
    """Get appropriate pool class for database."""
    if database_url.startswith("sqlite"):
        return StaticPool
    return QueuePool


def get_engine_kwargs(database_url: str) -> dict:
    """Get engine kwargs based on database type."""
    kwargs = {
        "pool_pre_ping": True,
        "poolclass": get_pool_class(database_url),
        "connect_args": get_connect_args(database_url),
    }
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return kwargs


engine = create_engine(
    settings.DATABASE_URL,
    **get_engine_kwargs(settings.DATABASE_URL),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()