"""Stub service for testing - to be replaced by actual implementation from clientes module."""
from typing import Optional
from sqlalchemy.orm import Session
from decimal import Decimal


class Cliente:
    """Stub model for testing."""
    def __init__(self, id: int, tipo: str = "B2B"):
        self.id = id
        self.tipo = tipo
        self.monto_deuda = Decimal("0")


class ClienteService:
    """Servicio de clientes - stub para testing.
    
    La implementación real estará en app/modules/clientes/services.py
    """

    def __init__(self):
        self._clientes = {}  # id -> Cliente

    def get_by_id(self, cliente_id: int, session: Session) -> Optional[Cliente]:
        """Obtiene cliente por ID."""
        if cliente_id not in self._clientes:
            # Default: B2B para testing de cuenta corriente
            self._clientes[cliente_id] = Cliente(id=cliente_id, tipo="B2B")
        return self._clientes[cliente_id]

    def get_by_id_con_tipo(self, cliente_id: int, session: Session) -> Optional[Cliente]:
        """Obtiene cliente con su tipo."""
        return self.get_by_id(cliente_id, session)

    def ajustar_cuenta_corriente(
        self, 
        cliente_id: int, 
        delta: Decimal, 
        session: Session
    ) -> None:
        """Ajusta cuenta corriente del cliente."""
        cliente = self.get_by_id(cliente_id, session)
        if cliente and cliente.tipo == "B2B":
            cliente.monto_deuda += delta
            # En implementación real: UPDATE clientes SET monto_deuda = monto_deuda + delta WHERE id = cliente_id