from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.modules.clientes.models import Cliente


def obtener_cliente(db: Session, cliente_id: int) -> Cliente | None:
    return db.get(Cliente, cliente_id)


def listar_clientes(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Cliente]:
    return db.scalars(
        select(Cliente).order_by(Cliente.id).offset(skip).limit(limit)
    ).all()


def crear_cliente(db: Session, cliente: Cliente) -> Cliente:
    db.add(cliente)
    db.flush()
    return cliente


def actualizar_cliente(
    db: Session,
    cliente: Cliente,
    cambios: dict[str, object],
) -> Cliente:
    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)
    db.flush()
    return cliente


def eliminar_cliente(db: Session, cliente: Cliente) -> None:
    db.delete(cliente)
    db.flush()


def tablas_relacionadas(db: Session, cliente_id: int) -> list[str]:
    """Detecta tablas con FK a clientes que tengan filas para este cliente.

    Cuando se agregue el módulo de pedidos, su FK a clientes quedará cubierta
    automáticamente sin modificar este módulo.
    """
    relacionadas: list[str] = []

    for tabla in Base.metadata.sorted_tables:
        if tabla.name == Cliente.__tablename__:
            continue

        for fk in tabla.foreign_keys:
            if (
                fk.column.table.name != Cliente.__tablename__
                or fk.column.name != "id"
            ):
                continue

            total = db.scalar(
                select(func.count())
                .select_from(tabla)
                .where(fk.parent == cliente_id)
            )
            if total:
                relacionadas.append(tabla.name)
                break

    return relacionadas
