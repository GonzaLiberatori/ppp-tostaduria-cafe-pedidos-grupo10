import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, MagicMock

from app.modules.pedidos import crud, models, schemas


class TestPedidoCRUD:
    """Tests para la capa CRUD de pedidos"""
    
    def test_create_pedido(self, db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado):
        """Test crear pedido básico"""
        pedido_data = schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            total=Decimal("1000"),
            cliente_persona_id=sample_cliente.persona_id,
            empleado_persona_id=sample_empleado.persona_id,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("5"),
                    tipo_de_cafe_id=sample_tipo_cafe.id,
                    molienda_id=sample_molienda.id,
                    perfil_de_tostado_id=sample_perfil_tostado.id
                )
            ]
        )
        
        pedido = crud.create_pedido(db_session, pedido_data)
        
        assert pedido.id is not None
        assert pedido.total == Decimal("1000")
        assert pedido.estado == "PENDIENTE"
    
    def test_get_pedido_by_idempotency_key(self, db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado):
        """Test búsqueda por idempotency_key"""
        from app.modules.pedidos import crud, schemas
        
        pedido_data = schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            total=Decimal("1000"),
            idempotency_key="test-key-123",
            cliente_persona_id=sample_cliente.persona_id,
            empleado_persona_id=sample_empleado.persona_id,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("5"),
                    tipo_de_cafe_id=sample_tipo_cafe.id,
                    molienda_id=sample_molienda.id,
                    perfil_de_tostado_id=sample_perfil_tostado.id
                )
            ]
        )
        
        pedido = crud.create_pedido(db_session, pedido_data)
        
        # Buscar por idempotency_key
        found = crud.get_pedido_by_idempotency_key(db_session, "test-key-123")
        assert found is not None
        assert found.id == pedido.id
        assert found.idempotency_key == "test-key-123"
        
        # Clave inexistente
        not_found = crud.get_pedido_by_idempotency_key(db_session, "non-existent")
        assert not_found is None


class TestPedidoEstadoHistorialCRUD:
    """Tests para CRUD de historial de estados"""
    
    def test_create_estado_historial(self, db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado):
        """Test crear registro en historial"""
        from app.modules.pedidos import crud, schemas
        
        pedido = crud.create_pedido(db_session, schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            total=Decimal("1000"),
            cliente_persona_id=sample_cliente.persona_id,
            empleado_persona_id=sample_empleado.persona_id,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("5"),
                    tipo_de_cafe_id=sample_tipo_cafe.id,
                    molienda_id=sample_molienda.id,
                    perfil_de_tostado_id=sample_perfil_tostado.id
                )
            ]
        ))
        
        # Crear historial
        historial = crud.create_estado_historial(db_session, pedido.id, None, "PENDIENTE", 1)
        
        assert historial.id is not None
        assert historial.pedido_id == pedido.id
        assert historial.estado_anterior is None
        assert historial.estado_nuevo == "PENDIENTE"
        
        # Verificar que se puede recuperar
        historial_db = crud.get_historial_by_pedido(db_session, pedido.id)
        assert len(historial_db) == 1
        assert historial_db[0].estado_nuevo == "PENDIENTE"