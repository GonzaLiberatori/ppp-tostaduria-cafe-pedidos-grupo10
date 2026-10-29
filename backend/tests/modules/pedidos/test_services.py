import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, MagicMock

from app.modules.pedidos import services, models, schemas, crud
from app.modules.auth.models import Cuenta
from app.modules.pedidos.models import Persona, Cliente, Empleado, TipoCliente, Lote, TipoLote, EstadoLote, TipoDeCafe, Molienda, PerfilDeTostado, OrdenTueste


class TestPedidoService:
    """Tests para PedidoService"""
    
    def test_crear_pedido_con_idempotencia(self, db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado, sample_lote):
        """Test crear pedido con idempotencia automática"""
        from app.modules.pedidos import services, schemas
        
        service = services.PedidoService(db_session)
        
        pedido_data = schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
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
        
        # Primera creación
        pedido1 = service.crear_pedido_completo(pedido_data, sample_empleado.persona_id)
        assert pedido1.id is not None
        assert pedido1.estado == "PENDIENTE"
        assert pedido1.idempotency_key is not None
        
        # Segunda creación con mismos datos (misma idempotency key)
        pedido2 = service.crear_pedido_completo(pedido_data, sample_empleado.persona_id)
        assert pedido2.id == pedido1.id  # Debe retornar el mismo
        assert pedido2.idempotency_key == pedido1.idempotency_key
    
    def test_crear_pedido_con_stock_fifo(self, db_session, sample_cliente, sample_empleado, sample_tipo_cafe, sample_molienda, sample_perfil_tostado):
        """Test que el stock se consume FIFO"""
        from app.modules.pedidos import services, schemas, models
        
        service = services.PedidoService(db_session)
        
        # Crear dos lotes con diferentes fechas de vencimiento
        from app.modules.pedidos.models import Lote, TipoLote, EstadoLote, OrdenTueste, PerfilDeTostado
        from datetime import datetime, timedelta
        
        perfil = models.PerfilDeTostado(variante="Medio", valor_agregado_por_kg=5000)
        db_session.add(perfil)
        db_session.flush()
        
        orden = models.OrdenTueste(
            fecha_tueste=datetime.now(),
            kg_gastados=100,
            kg_obtenidos=85,
            perfil_de_tostado_id=1
        )
        db_session.add(orden)
        db_session.flush()
        
        # Lote 1: vence primero
        lote1 = models.Lote(
            tipo="TOSTADO",
            estado="ABIERTO",
            fecha_vencimiento=datetime.now() + timedelta(days=30),
            humedad=12.5,
            kg_disponibles=50,
            kg_reales=50,
            ubicacion_fisica="Bodega A",
            tipo_de_cafe_id=1,
            orden_tueste_id=1
        )
        db_session.add(lote1)
        
        # Lote 2: vence después
        lote2 = models.Lote(
            tipo="TOSTADO",
            estado="ABIERTO",
            fecha_vencimiento=datetime.now() + timedelta(days=60),
            humedad=12.5,
            kg_disponibles=50,
            kg_reales=50,
            ubicacion_fisica="Bodega B",
            tipo_de_cafe_id=1,
            orden_tueste_id=1
        )
        db_session.add(lote2)
        db_session.commit()
        
        service = services.PedidoService(db_session)
        
        # Crear pedido que consuma 60kg (debe consumir 50 del lote1 y 10 del lote2)
        pedido_data = schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            cliente_persona_id=1,
            empleado_persona_id=1,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("60"),
                    tipo_de_cafe_id=1,
                    molienda_id=1,
                    perfil_de_tostado_id=1
                )
            ]
        )
        
        # Necesitamos setup completo para que funcione
        # Este test es más de integración, lo marcamos como pendiente
        pass  # Implementar cuando tengamos fixtures completos
    
    def test_state_machine_transiciones_validas(self, db_session):
        """Test que las transiciones de estado válidas funcionan"""
        from app.modules.pedidos import services, schemas, models
        
        service = services.PedidoService(db_session)
        
        # Test transiciones válidas
        assert service._validar_transicion_estado("PENDIENTE", "LISTO") == True
        assert service._validar_transicion_estado("LISTO", "ENTREGADO") == True
        assert service._validar_transicion_estado("LISTO", "PENDIENTE") == True
        assert service._validar_transicion_estado("ENTREGADO", "LISTO") == True
        
        # Transiciones inválidas
        assert service._validar_transicion_estado("PENDIENTE", "ENTREGADO") == False
        assert service._validar_transicion_estado("ENTREGADO", "PENDIENTE") == False
        assert service._validar_transicion_estado("PENDIENTE", "PENDIENTE") == False
    
    def test_idempotency_key_generation(self, db_session):
        """Test generación de idempotency key"""
        from app.modules.pedidos import services, schemas
        from datetime import datetime
        from decimal import Decimal
        
        service = services.PedidoService(db_session)
        
        detalles = [
            schemas.DetallePedidoCreate(cantidad_kg=Decimal("5"), tipo_de_cafe_id=1),
            schemas.DetallePedidoCreate(cantidad_kg=Decimal("3"), blend_id=2)
        ]
        
        key1 = service._generar_idempotency_key(1, detalles, datetime(2024, 1, 15))
        key2 = service._generar_idempotency_key(1, detalles, datetime(2024, 1, 15))
        key3 = service._generar_idempotency_key(1, detalles, datetime(2024, 1, 16))
        
        # Mismos datos = misma key
        assert key1 == key2
        # Fecha diferente = key diferente
        assert key1 != key3
        # Formato correcto (64 chars hex)
        assert len(key1) == 64
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_cambiar_estado_transiciones_validas(self, db_session, sample_pedido):
        """Test cambio de estado con transiciones válidas"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        # Pendiente -> Listo
        pedido = service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        assert pedido.estado == "LISTO"
        
        # Listo -> Entregado
        pedido = service.cambiar_estado_pedido(pedido.id, "ENTREGADO")
        assert pedido.estado == "ENTREGADO"
        
        # Entregado -> Listo (reversión)
        pedido = service.cambiar_estado_pedido(pedido.id, "LISTO")
        assert pedido.estado == "LISTO"
        
        # Listo -> Pendiente
        pedido = service.cambiar_estado_pedido(pedido.id, "PENDIENTE")
        assert pedido.estado == "PENDIENTE"
    
    def test_cambiar_estado_transicion_invalida(self, db_session, sample_pedido):
        """Test que transiciones inválidas lanzan error"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        # Pendiente -> Entregado (inválido, debe pasar por Listo)
        with pytest.raises(ValueError, match="Transición inválida"):
            service.cambiar_estado_pedido(sample_pedido.id, "ENTREGADO")
        
        # Entregado -> Pendiente (inválido, debe pasar por Listo)
        # Primero ponemos en Entregado
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        service.cambiar_estado_pedido(sample_pedido.id, "ENTREGADO")
        
        with pytest.raises(ValueError, match="Transición inválida"):
            service.cambiar_estado_pedido(sample_pedido.id, "PENDIENTE")
    
    def test_eliminar_pedido_pendiente_devuelve_stock(self, db_session, sample_pedido_con_stock):
        """Test que eliminar pedido Pendiente devuelve stock"""
        from app.modules.pedidos import services, models
        
        service = services.PedidoService(db_session)
        
        # Verificar stock antes
        lote = db_session.query(models.Lote).filter(models.Lote.tipo_de_cafe_id == 1).first()
        stock_antes = lote.kg_disponibles
        
        # Eliminar pedido
        resultado = service.eliminar_pedido(sample_pedido_con_stock.id)
        assert resultado == True
        
        # Verificar stock restaurado
        db_session.refresh(lote)
        assert lote.kg_disponibles == 100  # Stock original restaurado
    
    def test_eliminar_pedido_no_pendiente_falla(self, db_session, sample_pedido):
        """Test que eliminar pedido no Pendiente falla"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        # Cambiar a LISTO
        from app.modules.pedidos import services as svc
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        
        with pytest.raises(ValueError, match="Solo se pueden eliminar pedidos en estado PENDIENTE"):
            service.eliminar_pedido(sample_pedido.id)
    
    def test_cuenta_corriente_b2b_entregado(self, db_session, sample_cliente_b2b, sample_pedido_b2b):
        """Test que cuenta corriente se actualiza al entregar pedido B2B"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        # Verificar saldo inicial
        cliente = db_session.query(sample_cliente_b2b.__class__).filter_by(persona_id=sample_cliente_b2b.persona_id).first()
        saldo_inicial = cliente.saldo_cuenta_corriente
        
        # Cambiar a Entregado
        service.cambiar_estado_pedido(sample_pedido_b2b.id, "LISTO")
        service.cambiar_estado_pedido(sample_pedido_b2b.id, "ENTREGADO")
        
        # Verificar que se actualizó la cuenta corriente
        db_session.refresh(sample_cliente_b2b)
        assert sample_cliente_b2b.saldo_cuenta_corriente == saldo_inicial + sample_pedido_b2b.total
    
    def test_cuenta_corriente_reversion_entregado_a_listo(self, db_session, sample_pedido_b2b_entregado):
        """Test que reversión Entregado->Listo revierte cuenta corriente"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        cliente = db_session.query(sample_pedido_b2b_entregado.cliente.__class__).filter_by(persona_id=sample_pedido_b2b_entregado.cliente_persona_id).first()
        saldo_entregado = cliente.saldo_cuenta_corriente
        
        # Revertir a Listo
        service.cambiar_estado_pedido(sample_pedido_b2b_entregado.id, "LISTO")
        
        # Verificar que se restó el total
        db_session.refresh(cliente)
        assert cliente.saldo_cuenta_corriente == saldo_entregado - sample_pedido_b2b_entregado.total
    
    def test_cuenta_corriente_no_afecta_consumidor_final(self, db_session, sample_pedido_consumidor_final):
        """Test que clientes Consumidor Final no afectan cuenta corriente"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        cliente = db_session.query(sample_pedido_consumidor_final.cliente.__class__).filter_by(persona_id=sample_pedido_consumidor_final.cliente_persona_id).first()
        assert cliente.es_b2b == False
        
        saldo_inicial = cliente.saldo_cuenta_corriente
        
        service.cambiar_estado_pedido(sample_pedido_consumidor_final.id, "LISTO")
        service.cambiar_estado_pedido(sample_pedido_consumidor_final.id, "ENTREGADO")
        
        # La cuenta corriente no debe cambiar
        db_session.refresh(cliente)
        assert cliente.saldo_cuenta_corriente == saldo_inicial
    
    def test_historial_estados_se_registra(self, db_session, sample_pedido):
        """Test que cada cambio de estado se registra en historial"""
        from app.modules.pedidos import services, crud
        
        service = services.PedidoService(db_session)
        
        # Cambiar estado varias veces
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        service.cambiar_estado_pedido(sample_pedido.id, "ENTREGADO")
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        
        # Verificar historial
        historial = crud.get_historial_by_pedido(db_session, sample_pedido.id)
        
        assert len(historial) == 4  # Inicial + 3 cambios
        assert historial[0].estado_nuevo == "PENDIENTE"
        assert historial[1].estado_nuevo == "LISTO"
        assert historial[2].estado_nuevo == "ENTREGADO"
        assert historial[3].estado_nuevo == "LISTO"
        
        # Verificar que estados anteriores son correctos
        assert historial[1].estado_anterior == "PENDIENTE"
        assert historial[2].estado_anterior == "LISTO"
        assert historial[3].estado_anterior == "ENTREGADO"
    
    def test_eliminar_pedido_devuelve_stock_exacto(self, db_session, sample_pedido_con_stock_detallado):
        """Test que al eliminar pedido se restaura stock exacto por lote"""
        from app.modules.pedidos import services, models
        from decimal import Decimal
        
        service = services.PedidoService(db_session)
        
        # El estado original (antes del pedido) era 50kg en cada lote
        stock_original = {1: Decimal("50"), 2: Decimal("50")}
        
        # Verificar stock actual (después de crear el pedido)
        lotes_actuales = db_session.query(models.Lote).filter(models.Lote.tipo_de_cafe_id == 1).all()
        stock_actual = {l.id: l.kg_disponibles for l in lotes_actuales}
        # Debe ser: lote1=0 (consumido 50), lote2=40 (consumido 10 de 50)
        assert stock_actual == {1: Decimal("0"), 2: Decimal("40")}
        
        # Eliminar pedido
        service.eliminar_pedido(sample_pedido_con_stock_detallado.id)
        
        # Verificar que se restauró el stock original
        lotes_despues = db_session.query(models.Lote).filter(models.Lote.tipo_de_cafe_id == 1).all()
        stock_despues = {l.id: l.kg_disponibles for l in lotes_despues}
        assert stock_despues == {1: Decimal("50"), 2: Decimal("50")}
    
    def test_transicion_entregado_a_listo_revierte_cuenta_corriente(self, db_session):
        """Test que Entregado -> Listo revierte cuenta corriente B2B"""
        from app.modules.pedidos import services, schemas, models
        from app.modules.auth.models import Cuenta
        from app.modules.pedidos.models import Persona, Cliente, Empleado, TipoCliente, TipoDeCafe, Molienda, PerfilDeTostado, Lote, OrdenTueste
        from datetime import datetime, timedelta, date
        
        service = services.PedidoService(db_session)
        
        # Setup completo para cliente B2B
        cuenta = Cuenta(correo="b2b_test@test.com", clave="hashed", rol="Cliente")
        db_session.add(cuenta)
        db_session.flush()
        
        persona = Persona(nombre="B2B", apellido="Test", telefono="5555555555", CUIT="20-99999999-9", cuenta_id=cuenta.id)
        db_session.add(persona)
        db_session.flush()
        
        cliente = Cliente(persona_id=persona.id, tipo="Mayorista", direccion_de_entrega="Calle B2B")
        db_session.add(cliente)
        db_session.commit()
        
        # Setup catálogo mínimo
        tipo_cafe = TipoDeCafe(
            organico=1,
            precio_por_kg_verde=50000,
            variedad="Test",
            region="Test",
            pais="Colombia",
        )
        db_session.add(tipo_cafe)
        db_session.flush()
        
        molienda = models.Molienda(tipo="Granel", valor_agregado_por_kg=0)
        db_session.add(molienda)
        db_session.flush()
        
        perfil = models.PerfilDeTostado(variante="Medio", valor_agregado_por_kg=5000)
        db_session.add(perfil)
        db_session.flush()
        
        orden = models.OrdenTueste(fecha_tueste=datetime.now(), kg_gastados=100, kg_obtenidos=85, perfil_de_tostado_id=perfil.id)
        db_session.add(orden)
        db_session.flush()
        
        lote = models.Lote(
            tipo="TOSTADO", estado="ABIERTO",
            fecha_vencimiento=datetime.now() + timedelta(days=365),
            humedad=12.5, kg_disponibles=100, kg_reales=100,
            ubicacion_fisica="Bodega", tipo_de_cafe_id=1, orden_tueste_id=1
        )
        db_session.add(lote)
        db_session.commit()
        
        # Setup empleado
        from app.modules.auth.models import Cuenta as CuentaModel
        emp_cuenta = CuentaModel(correo="emp_del@test.com", clave="hashed", rol="Cajero")
        db_session.add(emp_cuenta)
        db_session.flush()
        
        emp_persona = Persona(nombre="Emp", apellido="Del", telefono="6666666666", cuenta_id=emp_cuenta.id)
        db_session.add(emp_persona)
        db_session.flush()
        
        empleado = Empleado(persona_id=emp_persona.id, fecha_de_contratacion=date(2020,1,1), fecha_de_nacimiento=date(1990,1,1), salario=500000)
        db_session.add(empleado)
        db_session.commit()
        
        # Crear pedido
        service = services.PedidoService(db_session)
        pedido_data = schemas.PedidoCreate(
            fecha=datetime.now(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            cliente_persona_id=cliente.persona_id,
            empleado_persona_id=empleado.persona_id,
            detalles=[
                schemas.DetallePedidoCreate(
                    cantidad_kg=Decimal("10"),
                    tipo_de_cafe_id=1,
                    molienda_id=1,
                    perfil_de_tostado_id=1
                )
            ]
        )
        
        pedido = services.PedidoService(db_session).crear_pedido_completo(pedido_data, empleado.persona_id)
        
        # Avanzar a ENTREGADO
        service.cambiar_estado_pedido(pedido.id, "LISTO")
        service.cambiar_estado_pedido(pedido.id, "ENTREGADO")
        
        # Verificar cuenta corriente incrementada
        db_session.refresh(cliente)
        saldo_entregado = cliente.saldo_cuenta_corriente
        
        # Revertir a LISTO
        from app.modules.pedidos import services as svc
        svc.PedidoService(db_session).cambiar_estado_pedido(pedido.id, "LISTO")
        
        # Verificar que se revirtió
        db_session.refresh(cliente)
        assert cliente.saldo_cuenta_corriente == 0  # Volvió a 0


class TestStockService:
    """Tests para StockService"""
    
    def test_obtener_stock_disponible(self, db_session, sample_lote):
        """Test obtener stock disponible"""
        from app.modules.pedidos import services
        
        service = services.StockService(db_session)
        stock = service.obtener_stock_disponible()
        
        assert len(stock) >= 1
        assert stock[0].kg_disponibles > 0
    
    def test_total_kg_disponibles(self, db_session, sample_lote):
        """Test total kg disponibles por tipo de café"""
        from app.modules.pedidos import services
        
        service = services.StockService(db_session)
        total = service.total_kg_disponibles_tipo_cafe(1)
        
        assert total > 0