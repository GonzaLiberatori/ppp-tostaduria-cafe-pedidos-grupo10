from decimal import Decimal
from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.modules.pedidos.models import Pedido, PedidoItem, PedidoEstadoHistorial, EstadoPedidoEnum
from app.modules.pedidos.schemas import PedidoCreate, PedidoItemCreate, EstadoPedidoEnum as SchemaEstadoPedidoEnum
from app.modules.pedidos.crud import (
    create_pedido as crud_create_pedido,
    get_pedido as crud_get_pedido,
    get_pedido_by_idempotency_key,
    get_pedidos_con_filtros as crud_get_pedidos_con_filtros,
    update_pedido as crud_update_pedido,
    delete_pedido as crud_delete_pedido,
    create_estado_historial,
    generate_idempotency_key,
)

# Type hints for external services (implemented by other modules)
# These will be imported at runtime to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.inventario.services import StockService
    from app.modules.clientes.services import ClienteService


class PedidoService:
    """Servicio de lógica de negocio para pedidos.
    
    Orquesta transacciones ACID que involucran:
    - Validación y consumo de stock (via StockService)
    - Gestión de cuenta corriente (via ClienteService)
    - Persistencia de pedidos e historial
    """

    # Transiciones de estado válidas: estado_actual -> [estados_destino_permitidos]
    TRANSICIONES_VALIDAS = {
        EstadoPedidoEnum.PENDIENTE: [EstadoPedidoEnum.LISTO],
        EstadoPedidoEnum.LISTO: [EstadoPedidoEnum.ENTREGADO, EstadoPedidoEnum.PENDIENTE],
        EstadoPedidoEnum.ENTREGADO: [EstadoPedidoEnum.LISTO],
    }

    # Transiciones que afectan cuenta corriente B2B
    TRANSICIONES_CUENTA_CORRIENTE = {
        (EstadoPedidoEnum.LISTO, EstadoPedidoEnum.ENTREGADO): "sumar",
        (EstadoPedidoEnum.ENTREGADO, EstadoPedidoEnum.LISTO): "restar",
    }

    def __init__(self):
        # Lazy imports to avoid circular dependencies
        self._stock_service = None
        self._cliente_service = None

    def _get_stock_service(self):
        if self._stock_service is None:
            from app.modules.inventario.services import StockService
            self._stock_service = StockService()
        return self._stock_service

    def _get_cliente_service(self):
        if self._cliente_service is None:
            from app.modules.clientes.services import ClienteService
            self._cliente_service = ClienteService()
        return self._cliente_service

    def crear_pedido(
        self,
        dto: PedidoCreate,
        user_id: Optional[int],
        session: Session,
    ) -> Pedido:
        """Crea un pedido con validación de stock, consumo FIFO y cuenta corriente.
        
        Todo en una única transacción:
        1. Verifica idempotencia
        2. Valida stock disponible para cada item
        3. Consume stock FIFO (StockService.consumir_fifo)
        4. Crea pedido + items
        5. Actualiza cuenta corriente si B2B (ClienteService.ajustar_cuenta_corriente)
        6. Registra historial de estado inicial
        """
        # 1. Verificar idempotencia
        idempotency_key = generate_idempotency_key(
            dto.cliente_id, dto.items, dto.fecha if hasattr(dto, 'fecha') else datetime.now()
        )
        existing = get_pedido_by_idempotency_key(session, idempotency_key)
        if existing:
            return existing

        # 2. Validar stock disponible y consumir FIFO
        stock_service = self._get_stock_service()
        consumo_total = []
        
        for item in dto.items:
            # Validar stock disponible
            stock_disponible = stock_service.get_stock_disponible(item.stock_id, session)
            if stock_disponible < item.kilos:
                raise ValueError(
                    f"Stock insuficiente para {item.variedad}: "
                    f"disponible {stock_disponible}, solicitado {item.kilos}"
                )
            
            # Consumir FIFO
            consumo, faltante = stock_service.consumir_fifo(
                item.stock_id, 
                float(item.kilos), 
                session
            )
            if faltante > 0:
                raise ValueError(
                    f"Faltante al consumir FIFO para {item.variedad}: {faltante}"
                )
            consumo_total.append({
                "stock_id": item.stock_id,
                "consumo": consumo,
            })

        # 3. Calcular total
        total = sum(item.kilos * item.precio_kg for item in dto.items)

        # 4. Preparar items para BD
        items_data = []
        for item in dto.items:
            items_data.append({
                "stock_id": item.stock_id,
                "variedad": item.variedad,
                "kilos": item.kilos,
                "precio_kg": item.precio_kg,
            })

        # 5. Crear pedido en BD
        pedido = crud_create_pedido(
            session,
            cliente_id=dto.cliente_id,
            estado=EstadoPedidoEnum.PENDIENTE,
            medio_contacto=dto.medio_contacto,
            observaciones=dto.observaciones,
            items=items_data,
            total=total,
            idempotency_key=idempotency_key,
        )

        # 6. Registrar historial de estado inicial
        create_estado_historial(
            session,
            pedido_id=pedido.id,
            estado_anterior=None,
            estado_nuevo=EstadoPedidoEnum.PENDIENTE,
            usuario_id=user_id,
        )

        # 7. Actualizar cuenta corriente si B2B
        cliente_service = self._get_cliente_service()
        cliente = cliente_service.get_by_id(dto.cliente_id, session)
        if cliente and getattr(cliente, 'tipo', None) == 'B2B':
            cliente_service.ajustar_cuenta_corriente(
                dto.cliente_id, 
                total, 
                session
            )

        return pedido

    def cambiar_estado(
        self,
        pedido_id: int,
        nuevo_estado: EstadoPedidoEnum,
        user_id: Optional[int],
        session: Session,
    ) -> Pedido:
        """Cambia el estado de un pedido validando transiciones y efectos laterales."""
        # Obtener pedido actual
        pedido = crud_get_pedido(session, pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} no encontrado")

        estado_actual = pedido.estado

        # Validar transición
        if nuevo_estado not in self.TRANSICIONES_VALIDAS.get(estado_actual, []):
            raise ValueError(
                f"Transición inválida: {estado_actual} -> {nuevo_estado}. "
                f"Transiciones permitidas: {self.TRANSICIONES_VALIDAS.get(estado_actual, [])}"
            )

        # Actualizar estado
        pedido = crud_update_pedido(session, pedido=pedido, estado=nuevo_estado)

        # Registrar historial
        create_estado_historial(
            session,
            pedido_id=pedido_id,
            estado_anterior=estado_actual,
            estado_nuevo=nuevo_estado,
            usuario_id=user_id,
        )

        # Efectos laterales: cuenta corriente
        transicion_key = (estado_actual, nuevo_estado)
        if transicion_key in self.TRANSICIONES_CUENTA_CORRIENTE:
            accion = self.TRANSICIONES_CUENTA_CORRIENTE[transicion_key]
            cliente_service = self._get_cliente_service()
            cliente = cliente_service.get_by_id(pedido.cliente_id, session)
            
            if cliente and getattr(cliente, 'tipo', None) == 'B2B':
                delta = pedido.total if accion == "sumar" else -pedido.total
                cliente_service.ajustar_cuenta_corriente(
                    pedido.cliente_id,
                    delta,
                    session
                )

        return pedido

    def eliminar_pedido(
        self,
        pedido_id: int,
        session: Session,
    ) -> None:
        """Elimina un pedido solo si está en estado Pendiente.
        
        Revierte:
        - Consumo FIFO de stock (StockService.restaurar_fifo)
        - Cuenta corriente B2B (ClienteService.ajustar_cuenta_corriente con delta negativo)
        - Historial de estados
        """
        pedido = crud_get_pedido(session, pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} no encontrado")

        if pedido.estado != EstadoPedidoEnum.PENDIENTE:
            raise ValueError(
                f"Solo se pueden eliminar pedidos en estado Pendiente. "
                f"Estado actual: {pedido.estado}"
            )

        # Revertir consumo FIFO
        stock_service = self._get_stock_service()
        for item in pedido.items:
            # Reconstruir consumo_detalle para restaurar
            consumo_detalle = [{
                "stock_id": item.stock_id,
                "kilos": float(item.kilos),
            }]
            stock_service.restaurar_fifo(consumo_detalle, session)

        # Revertir cuenta corriente si B2B
        cliente_service = self._get_cliente_service()
        cliente = cliente_service.get_by_id(pedido.cliente_id, session)
        if cliente and getattr(cliente, 'tipo', None) == 'B2B':
            cliente_service.ajustar_cuenta_corriente(
                pedido.cliente_id,
                -pedido.total,
                session
            )

        # Eliminar historial de estados (cascade delete en BD)
        # y luego el pedido (cascade delete items)
        crud_delete_pedido(session, pedido)

    def get_pedidos_con_filtros(
        self,
        estado: Optional[EstadoPedidoEnum] = None,
        cliente_id: Optional[int] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        session: Session = None,
    ) -> Tuple[List[Pedido], int]:
        """Lista pedidos con filtros y paginación."""
        return crud_get_pedidos_con_filtros(
            session,
            estado=estado,
            cliente_id=cliente_id,
            fecha_desde=fecha_desde.date() if fecha_desde else None,
            fecha_hasta=fecha_hasta.date() if fecha_hasta else None,
            search=search,
            page=page,
            page_size=page_size,
        )

    def get_pedido_detalle(self, pedido_id: int, session: Session) -> Optional[Pedido]:
        """Obtiene detalle completo de un pedido."""
        return crud_get_pedido(session, pedido_id)