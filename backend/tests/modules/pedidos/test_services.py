import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, MagicMock

from app.modules.pedidos import services, models, schemas, crud
from app.modules.auth.models import Cuenta
from app.modules.pedidos.models import Persona, Cliente, Empleado, TipoCliente, Lote, TipoLote, EstadoLote, TipoDeCafe, Molienda, PerfilDeTostado, OrdenTueste
from app.modules.ventas.schemas import VentaAnulacionCreate


def _anulacion(motivo: str = "Anulación de prueba") -> VentaAnulacionCreate:
    """Motivo de anulación reutilizado por los tests de reversión."""
    return VentaAnulacionCreate(motivo=motivo)


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
        from app.modules.pedidos.models import MetodoPago
        from app.modules.ventas.schemas import CondicionPago
        from app.modules.ventas import crud as ventas_crud, services as ventas_services
        
        service = services.PedidoService(db_session)
        
        # Pendiente -> Listo
        pedido = service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        assert pedido.estado == "LISTO"
        
        # Listo -> Entregado (al contado: la venta nace en la entrega)
        pedido = service.cambiar_estado_pedido(
            pedido.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.CONTADO,
            metodo_de_pago=MetodoPago.EFECTIVO,
        )
        assert pedido.estado == "ENTREGADO"
        venta = ventas_crud.obtener_vigente_por_pedido(db_session, pedido.id)
        assert venta is not None

        # Entregado -> Listo exige anular la venta vigente primero
        ventas_services.VentaService(db_session).anular_venta(
            venta.id, _anulacion()
        )
        pedido = service.cambiar_estado_pedido(pedido.id, "LISTO")
        assert pedido.estado == "LISTO"
        
        # Listo -> Pendiente
        pedido = service.cambiar_estado_pedido(pedido.id, "PENDIENTE")
        assert pedido.estado == "PENDIENTE"

    def test_entrega_sin_condicion_de_pago_falla(self, db_session, sample_pedido):
        """Sin condición de pago no se puede entregar: la venta no puede nacer."""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        
        with pytest.raises(ValueError, match="condición de pago"):
            service.cambiar_estado_pedido(sample_pedido.id, "ENTREGADO")
        
        db_session.refresh(sample_pedido)
        assert sample_pedido.estado == "LISTO"

    def test_entrega_al_contado_crea_venta_sin_deuda(
        self, db_session, sample_cliente_b2b, sample_pedido_b2b
    ):
        """Entregar al contado confirma la venta y no toca la cuenta corriente."""
        from app.modules.pedidos import services
        from app.modules.pedidos.models import MetodoPago
        from app.modules.ventas import crud as ventas_crud
        from app.modules.ventas.models import VentaEstado
        from app.modules.ventas.schemas import CondicionPago
        
        service = services.PedidoService(db_session)
        db_session.refresh(sample_cliente_b2b)
        saldo_inicial = sample_cliente_b2b.saldo_cuenta_corriente
        
        service.cambiar_estado_pedido(sample_pedido_b2b.id, "LISTO")
        service.cambiar_estado_pedido(
            sample_pedido_b2b.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.CONTADO,
            metodo_de_pago=MetodoPago.TRANSFERENCIA,
            cuenta_id=42,
        )
        
        venta = ventas_crud.obtener_vigente_por_pedido(db_session, sample_pedido_b2b.id)
        assert venta is not None
        assert venta.estado == VentaEstado.CONFIRMADA
        assert venta.cobrada_en is not None
        assert venta.cuenta_id == 42
        assert venta.pagos[0].metodo_de_pago == MetodoPago.TRANSFERENCIA
        
        db_session.refresh(sample_cliente_b2b)
        assert sample_cliente_b2b.saldo_cuenta_corriente == saldo_inicial

    def test_entrega_a_pagare_b2b_genera_deuda(
        self, db_session, sample_cliente_b2b, sample_pedido_b2b
    ):
        """Entregar a pagaré deja la venta pendiente y suma la deuda al cliente."""
        from app.modules.pedidos import services
        from app.modules.ventas import crud as ventas_crud
        from app.modules.ventas.models import VentaEstado
        from app.modules.ventas.schemas import CondicionPago
        
        service = services.PedidoService(db_session)
        db_session.refresh(sample_cliente_b2b)
        saldo_inicial = sample_cliente_b2b.saldo_cuenta_corriente
        
        service.cambiar_estado_pedido(sample_pedido_b2b.id, "LISTO")
        service.cambiar_estado_pedido(
            sample_pedido_b2b.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.PAGARE,
            plazo_dias=60,
        )
        
        venta = ventas_crud.obtener_vigente_por_pedido(db_session, sample_pedido_b2b.id)
        assert venta.estado == VentaEstado.PENDIENTE_COBRO
        assert venta.fecha_vencimiento is not None
        
        db_session.refresh(sample_cliente_b2b)
        assert (
            sample_cliente_b2b.saldo_cuenta_corriente
            == saldo_inicial + sample_pedido_b2b.total
        )

    def test_entrega_a_pagare_de_consumidor_final_falla_sin_deuda(
        self, db_session, sample_pedido_consumidor_final
    ):
        """Un cliente sin cuenta corriente no puede comprar a pagaré."""
        from app.modules.pedidos import services
        from app.modules.ventas import crud as ventas_crud
        from app.modules.ventas import services as ventas_services
        from app.modules.ventas.schemas import CondicionPago
        
        service = services.PedidoService(db_session)
        cliente = sample_pedido_consumidor_final.cliente
        db_session.refresh(cliente)
        saldo_inicial = cliente.saldo_cuenta_corriente
        
        service.cambiar_estado_pedido(sample_pedido_consumidor_final.id, "LISTO")
        with pytest.raises(ventas_services.PagareNoPermitido):
            service.cambiar_estado_pedido(
                sample_pedido_consumidor_final.id,
                "ENTREGADO",
                condicion_pago=CondicionPago.PAGARE,
                plazo_dias=30,
            )
        
        db_session.refresh(sample_pedido_consumidor_final)
        db_session.refresh(cliente)
        assert sample_pedido_consumidor_final.estado == "LISTO"
        assert cliente.saldo_cuenta_corriente == saldo_inicial
        assert (
            ventas_crud.obtener_vigente_por_pedido(
                db_session, sample_pedido_consumidor_final.id
            )
            is None
        )

    def test_fallo_de_la_venta_deja_el_pedido_en_listo(
        self, db_session, sample_cliente_b2b, sample_pedido_b2b, monkeypatch
    ):
        """Si la venta falla, la entrega se revierte completa: estado y deuda."""
        from app.modules.pedidos import services
        from app.modules.ventas import services as ventas_services
        from app.modules.ventas.schemas import CondicionPago
        
        service = services.PedidoService(db_session)
        db_session.refresh(sample_cliente_b2b)
        saldo_inicial = sample_cliente_b2b.saldo_cuenta_corriente
        service.cambiar_estado_pedido(sample_pedido_b2b.id, "LISTO")
        
        def _falla(*_args, **_kwargs):
            raise RuntimeError("fallo simulado al persistir la venta")
        
        monkeypatch.setattr(
            ventas_services, "registrar_venta_de_entrega", _falla
        )
        
        with pytest.raises(RuntimeError, match="fallo simulado"):
            service.cambiar_estado_pedido(
                sample_pedido_b2b.id,
                "ENTREGADO",
                condicion_pago=CondicionPago.PAGARE,
                plazo_dias=30,
            )
        
        db_session.refresh(sample_pedido_b2b)
        db_session.refresh(sample_cliente_b2b)
        assert sample_pedido_b2b.estado == "LISTO"
        assert sample_cliente_b2b.saldo_cuenta_corriente == saldo_inicial

    def test_reversion_entregado_a_listo_bloqueada_por_venta_vigente(
        self, db_session, sample_pedido_b2b_entregado_revierte
    ):
        """Revertir una entrega ya vendida se rechaza con el error de dominio."""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        cliente = sample_pedido_b2b_entregado_revierte.cliente
        db_session.refresh(cliente)
        saldo_entregado = cliente.saldo_cuenta_corriente
        
        with pytest.raises(services.PedidoConVentaVigente):
            service.cambiar_estado_pedido(
                sample_pedido_b2b_entregado_revierte.id, "LISTO"
            )
        
        db_session.refresh(sample_pedido_b2b_entregado_revierte)
        db_session.refresh(cliente)
        assert sample_pedido_b2b_entregado_revierte.estado == "ENTREGADO"
        assert cliente.saldo_cuenta_corriente == saldo_entregado

    def test_reversion_entregado_a_listo_permitida_tras_anular(
        self, db_session, sample_pedido_b2b_entregado_revierte
    ):
        """Anulada la venta, la reversión se permite y no toca el saldo."""
        from app.modules.pedidos import services
        from app.modules.ventas import crud as ventas_crud
        from app.modules.ventas import services as ventas_services
        from app.modules.ventas.models import VentaEstado
        
        venta = ventas_crud.obtener_vigente_por_pedido(
            db_session, sample_pedido_b2b_entregado_revierte.id
        )
        ventas_services.VentaService(db_session).anular_venta(
            venta.id, _anulacion()
        )
        
        cliente = sample_pedido_b2b_entregado_revierte.cliente
        db_session.refresh(cliente)
        saldo_tras_anular = cliente.saldo_cuenta_corriente
        
        pedido = services.PedidoService(db_session).cambiar_estado_pedido(
            sample_pedido_b2b_entregado_revierte.id, "LISTO"
        )
        
        assert pedido.estado == "LISTO"
        db_session.refresh(cliente)
        assert cliente.saldo_cuenta_corriente == saldo_tras_anular
        assert venta.estado == VentaEstado.ANULADA
    
    def test_cambiar_estado_transicion_invalida(self, db_session, sample_pedido):
        """Test que transiciones inválidas lanzan error"""
        from app.modules.pedidos import services
        
        service = services.PedidoService(db_session)
        
        # Pendiente -> Entregado (inválido, debe pasar por Listo)
        with pytest.raises(ValueError, match="Transición inválida"):
            service.cambiar_estado_pedido(sample_pedido.id, "ENTREGADO")
        
        # Entregado -> Pendiente (inválido, debe pasar por Listo)
        # Primero ponemos en Entregado
        from app.modules.pedidos.models import MetodoPago
        from app.modules.ventas.schemas import CondicionPago
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        service.cambiar_estado_pedido(
            sample_pedido.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.CONTADO,
            metodo_de_pago=MetodoPago.EFECTIVO,
        )
        
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
    
    def test_historial_estados_se_registra(self, db_session, sample_pedido):
        """Test que cada cambio de estado se registra en historial"""
        from app.modules.pedidos import services, crud
        from app.modules.pedidos.models import MetodoPago
        from app.modules.ventas import crud as ventas_crud, services as ventas_services
        from app.modules.ventas.schemas import CondicionPago
        
        service = services.PedidoService(db_session)
        
        # Cambiar estado varias veces
        service.cambiar_estado_pedido(sample_pedido.id, "LISTO")
        service.cambiar_estado_pedido(
            sample_pedido.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.CONTADO,
            metodo_de_pago=MetodoPago.EFECTIVO,
        )
        venta = ventas_crud.obtener_vigente_por_pedido(db_session, sample_pedido.id)
        ventas_services.VentaService(db_session).anular_venta(venta.id, _anulacion())
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
        
        # Avanzar a ENTREGADO vendiendo a pagaré: la deuda vive en la venta
        from app.modules.pedidos.models import MetodoPago
        from app.modules.ventas import crud as ventas_crud, services as ventas_services
        from app.modules.ventas.schemas import CondicionPago
        
        service.cambiar_estado_pedido(pedido.id, "LISTO")
        service.cambiar_estado_pedido(
            pedido.id,
            "ENTREGADO",
            condicion_pago=CondicionPago.PAGARE,
            plazo_dias=30,
        )
        
        # Verificar cuenta corriente incrementada
        db_session.refresh(cliente)
        saldo_entregado = cliente.saldo_cuenta_corriente
        assert saldo_entregado == pedido.total
        
        # Revertir sin anular la venta se rechaza
        with pytest.raises(services.PedidoConVentaVigente):
            service.cambiar_estado_pedido(pedido.id, "LISTO")
        
        # Anular la venta revierte la deuda y habilita la reversión
        venta = ventas_crud.obtener_vigente_por_pedido(db_session, pedido.id)
        ventas_services.VentaService(db_session).anular_venta(venta.id, _anulacion())
        service.cambiar_estado_pedido(pedido.id, "LISTO")
        
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


class TestVentaDeCafeVerde:
    """El pedido puede combinar café tostado con materia prima (verde)."""

    def _crear_lote(
        self,
        db_session,
        tipo_cafe_id: int,
        tipo: str,
        kg: Decimal,
        dias_vencimiento: int,
    ) -> Lote:
        from datetime import timedelta

        lote = Lote(
            tipo=tipo,
            estado="ABIERTO",
            fecha_vencimiento=datetime.now() + timedelta(days=dias_vencimiento),
            humedad=12.5,
            kg_disponibles=kg,
            kg_reales=kg,
            ubicacion_fisica=f"Bodega {tipo}",
            tipo_de_cafe_id=tipo_cafe_id,
        )
        db_session.add(lote)
        db_session.commit()
        db_session.refresh(lote)
        return lote

    def test_pedido_verde_consume_solo_lotes_verdes(
        self,
        db_session,
        sample_cliente,
        sample_empleado,
        sample_tipo_cafe,
        sample_lote,
    ) -> None:
        """Comprar verde descuenta los lotes VERDE y deja intacto el tostado."""
        lote_verde = self._crear_lote(
            db_session, sample_tipo_cafe.id, "VERDE", Decimal("30"), 90
        )

        pedido = services.PedidoService(db_session).crear_pedido_completo(
            schemas.PedidoCreate(
                fecha=datetime.now(),
                metodo_de_despacho="Retiro en local",
                estado="PENDIENTE",
                cliente_persona_id=sample_cliente.persona_id,
                empleado_persona_id=sample_empleado.persona_id,
                detalles=[
                    schemas.DetallePedidoCreate(
                        cantidad_kg=Decimal("10"),
                        tipo_de_cafe_id=sample_tipo_cafe.id,
                        tipo_lote=TipoLote.VERDE,
                    )
                ],
            ),
            sample_empleado.persona_id,
        )

        db_session.refresh(lote_verde)
        db_session.refresh(sample_lote)

        assert pedido.detalles[0].tipo_lote == TipoLote.VERDE
        assert lote_verde.kg_disponibles == Decimal("20")
        # El lote tostado no participa de la venta de materia prima.
        assert sample_lote.kg_disponibles == Decimal("100")

    def test_pedido_tostado_no_consume_verde(
        self,
        db_session,
        sample_cliente,
        sample_empleado,
        sample_tipo_cafe,
        sample_lote,
    ) -> None:
        """Un ítem tostado sigue descontando únicamente lotes TOSTADO."""
        lote_verde = self._crear_lote(
            db_session, sample_tipo_cafe.id, "VERDE", Decimal("30"), 90
        )

        services.PedidoService(db_session).crear_pedido_completo(
            schemas.PedidoCreate(
                fecha=datetime.now(),
                metodo_de_despacho="Retiro en local",
                estado="PENDIENTE",
                cliente_persona_id=sample_cliente.persona_id,
                empleado_persona_id=sample_empleado.persona_id,
                detalles=[
                    schemas.DetallePedidoCreate(
                        cantidad_kg=Decimal("10"),
                        tipo_de_cafe_id=sample_tipo_cafe.id,
                    )
                ],
            ),
            sample_empleado.persona_id,
        )

        db_session.refresh(lote_verde)
        db_session.refresh(sample_lote)

        assert lote_verde.kg_disponibles == Decimal("30")
        assert sample_lote.kg_disponibles == Decimal("90")

    def test_verde_sin_stock_no_toma_el_tostado(
        self,
        db_session,
        sample_cliente,
        sample_empleado,
        sample_tipo_cafe,
        sample_lote,
    ) -> None:
        """Sin stock verde el pedido falla aunque haya tostado disponible."""
        with pytest.raises(ValueError, match="VERDE"):
            services.PedidoService(db_session).crear_pedido_completo(
                schemas.PedidoCreate(
                    fecha=datetime.now(),
                    metodo_de_despacho="Retiro en local",
                    estado="PENDIENTE",
                    cliente_persona_id=sample_cliente.persona_id,
                    empleado_persona_id=sample_empleado.persona_id,
                    detalles=[
                        schemas.DetallePedidoCreate(
                            cantidad_kg=Decimal("10"),
                            tipo_de_cafe_id=sample_tipo_cafe.id,
                            tipo_lote=TipoLote.VERDE,
                        )
                    ],
                ),
                sample_empleado.persona_id,
            )

        db_session.refresh(sample_lote)
        assert sample_lote.kg_disponibles == Decimal("100")
