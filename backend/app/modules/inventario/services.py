"""Stub service for testing - to be replaced by actual implementation from inventario module."""
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from decimal import Decimal


class StockService:
    """Servicio de stock - stub para testing.
    
    La implementación real estará en app/modules/inventario/services.py
    """

    def get_stock_disponible(self, stock_id: int, session: Session) -> Decimal:
        """Retorna stock disponible para un stock_id."""
        # Stub: retorna stock suficiente para testing
        return Decimal("1000")

    def consumir_fifo(
        self, 
        stock_id: int, 
        kilos: float, 
        session: Session
    ) -> Tuple[List[dict], float]:
        """Consume kilos usando FIFO - stub.
        
        Returns:
            Tuple[List[consumo_detalle], faltante]
        """
        # Stub: simula consumo exitoso sin faltante
        consumo = [{
            "stock_id": stock_id,
            "bolsa_id": "stub-bolsa-1",
            "kilos_consumidos": kilos,
        }]
        return consumo, 0.0

    def restaurar_fifo(self, consumo_detalle: List[dict], session: Session) -> None:
        """Restaura stock consumido - stub."""
        pass