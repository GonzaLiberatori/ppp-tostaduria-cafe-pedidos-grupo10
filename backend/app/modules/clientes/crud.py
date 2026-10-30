"""Acceso a datos del módulo de clientes.

Consultas puras sobre ``Persona``, ``Cliente`` y los pedidos asociados. No
deciden reglas de negocio ni abren transacciones.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.modules.clientes.models import Cliente, Persona
from app.modules.pedidos.models import DetallePedido, Pedido


def listar_clientes(db: Session) -> list[Cliente]:
    """Devuelve todos los clientes con su persona cargada, ordenados por id."""
    return (
        db.query(Cliente)
        .options(joinedload(Cliente.persona))
        .join(Persona, Persona.id == Cliente.persona_id)
        .order_by(Persona.id)
        .all()
    )


def obtener_cliente(db: Session, persona_id: int) -> Optional[Cliente]:
    """Devuelve el cliente con su persona cargada, o ``None``."""
    return (
        db.query(Cliente)
        .options(joinedload(Cliente.persona))
        .filter(Cliente.persona_id == persona_id)
        .first()
    )


def obtener_persona_por_email(db: Session, email: str) -> Optional[Persona]:
    """Busca una persona por correo, para validar la unicidad."""
    return db.query(Persona).filter(Persona.email == email).first()


def obtener_persona_por_telefono(db: Session, telefono: str) -> Optional[Persona]:
    """Busca una persona por teléfono, para validar la unicidad."""
    return db.query(Persona).filter(Persona.telefono == telefono).first()


def kilos_comprados_de_clientes(db: Session) -> dict[int, Decimal]:
    """Suma los kilos de todos los pedidos de cada cliente.

    Se agrupa en una sola consulta para no hacer N+1 al listar el panel.
    """
    filas = (
        db.query(
            Pedido.cliente_persona_id,
            func.coalesce(func.sum(DetallePedido.cantidad_kg), 0),
        )
        .join(DetallePedido, DetallePedido.pedido_id == Pedido.id)
        .group_by(Pedido.cliente_persona_id)
        .all()
    )
    return {cliente_id: Decimal(str(total)) for cliente_id, total in filas}


def kilos_comprados_de_cliente(db: Session, persona_id: int) -> Decimal:
    """Suma los kilos de todos los pedidos de un cliente."""
    total = (
        db.query(func.coalesce(func.sum(DetallePedido.cantidad_kg), 0))
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .filter(Pedido.cliente_persona_id == persona_id)
        .scalar()
    )
    return Decimal(str(total or 0))


def contar_pedidos_de_cliente(db: Session, persona_id: int) -> int:
    """Cuenta los pedidos asociados a un cliente."""
    return (
        db.query(Pedido)
        .filter(Pedido.cliente_persona_id == persona_id)
        .count()
    )
