"""Tests de las reglas de negocio de envíos programados.

Los casos críticos se prueban contra ``EnvioService``: generación diaria,
idempotencia, deuda en cuenta corriente, descuento de stock y aislamiento de
errores entre clientes.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.clientes.models import Cliente
from app.modules.envios import models, schemas, services
from app.modules.pedidos.models import EstadoPedido, Pedido
from app.modules.ventas.models import VentaComercial, VentaEstado

# Lunes: ``date.weekday() == 0``.
FECHA_LUNES = date(2026, 11, 2)


def crear_suscripcion(
    servicio: services.EnvioService,
    cliente_id: int,
    tipo_de_cafe_id: int,
    cantidad_kg: str = "5",
    dia_semana: int = FECHA_LUNES.weekday(),
    plazo_dias: int = 30,
    fecha_inicio: date = FECHA_LUNES,
) -> schemas.SuscripcionRead:
    """Alta de suscripción reutilizable en los tests."""
    return servicio.crear_suscripcion(
        schemas.SuscripcionCreate(
            clienteId=str(cliente_id),
            tipoDeCafeId=tipo_de_cafe_id,
            cantidadKg=Decimal(cantidad_kg),
            diaSemana=dia_semana,
            plazoDias=plazo_dias,
            fechaInicio=fecha_inicio,
        )
    )


class TestSuscripciones:
    def test_alta_b2b_devuelve_contrato_del_panel(
        self, suscripcion_lunes, sample_cliente_b2b, sample_tipo_cafe
    ):
        assert suscripcion_lunes.clienteId == str(sample_cliente_b2b.persona_id)
        assert suscripcion_lunes.clienteNombre == "B2B Test"
        assert suscripcion_lunes.producto == "tipo"
        assert suscripcion_lunes.productoId == sample_tipo_cafe.id
        assert suscripcion_lunes.variedad == sample_tipo_cafe.variedad
        assert suscripcion_lunes.diaNombre == "Lunes"
        assert suscripcion_lunes.activa is True

    def test_rechaza_cliente_consumidor_final(
        self, servicio_envios, sample_cliente_consumidor_final, sample_tipo_cafe
    ):
        with pytest.raises(services.ClienteNoHabilitado):
            crear_suscripcion(
                servicio_envios,
                sample_cliente_consumidor_final.persona_id,
                sample_tipo_cafe.id,
            )

    def test_rechaza_producto_inexistente(
        self, servicio_envios, sample_cliente_b2b
    ):
        with pytest.raises(services.ProductoInvalido):
            crear_suscripcion(
                servicio_envios, sample_cliente_b2b.persona_id, tipo_de_cafe_id=9999
            )

    def test_schema_exige_exactamente_un_producto(self):
        base = dict(
            clienteId="1",
            cantidadKg=Decimal("5"),
            diaSemana=0,
        )
        with pytest.raises(ValidationError):
            schemas.SuscripcionCreate(**base)
        with pytest.raises(ValidationError):
            schemas.SuscripcionCreate(**base, tipoDeCafeId=1, blendId=2)

    def test_desactivar_no_borra_la_suscripcion(
        self, servicio_envios, suscripcion_lunes
    ):
        servicio_envios.desactivar_suscripcion(suscripcion_lunes.id)

        listadas = servicio_envios.listar_suscripciones()
        assert len(listadas) == 1
        assert listadas[0].id == suscripcion_lunes.id
        assert listadas[0].activa is False

    def test_actualizar_cantidad_y_plazo(
        self, servicio_envios, suscripcion_lunes
    ):
        actualizada = servicio_envios.actualizar_suscripcion(
            suscripcion_lunes.id,
            schemas.SuscripcionUpdate(
                cantidadKg=Decimal("8"), plazoDias=60
            ),
        )

        assert actualizada.cantidadKg == 8.0
        assert actualizada.plazoDias == 60


class TestGeneracionDiaria:
    def test_genera_pedido_venta_y_deuda(
        self,
        servicio_envios,
        db_session,
        suscripcion_lunes,
        sample_cliente_b2b,
        sample_tipo_cafe,
        sample_lote,
    ):
        resultado = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert resultado.generadas == 1
        assert resultado.errores == 0

        clave = (
            f"envio-{sample_cliente_b2b.persona_id}-"
            f"{FECHA_LUNES.isoformat()}"
        )
        pedido = (
            db_session.query(Pedido)
            .filter(Pedido.idempotency_key == clave)
            .one()
        )
        assert pedido.estado == EstadoPedido.ENTREGADO
        assert pedido.total == Decimal("250000.00")

        venta = (
            db_session.query(VentaComercial)
            .filter(VentaComercial.pedido_id == pedido.id)
            .one()
        )
        assert venta.estado == VentaEstado.PENDIENTE_COBRO
        assert venta.fecha_vencimiento is not None
        assert venta.cobrada_en is None

        cliente = db_session.get(Cliente, sample_cliente_b2b.persona_id)
        assert cliente.saldo_cuenta_corriente == pedido.total

        db_session.refresh(sample_lote)
        assert sample_lote.kg_disponibles == Decimal("95.00")

        entrega = db_session.query(models.EntregaProgramada).one()
        assert entrega.estado == models.EstadoEntrega.GENERADA
        assert entrega.pedido_id == pedido.id
        assert entrega.error is None
        assert entrega.generada_en is not None

    def test_es_idempotente_si_corre_dos_veces(
        self,
        servicio_envios,
        db_session,
        suscripcion_lunes,
        sample_cliente_b2b,
        sample_lote,
    ):
        primera = servicio_envios.generar_del_dia(FECHA_LUNES)
        segunda = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert primera.generadas == 1
        assert segunda.generadas == 0
        assert segunda.omitidas == 1

        assert db_session.query(Pedido).count() == 1
        assert db_session.query(VentaComercial).count() == 1
        assert db_session.query(models.EntregaProgramada).count() == 1

        pedido = db_session.query(Pedido).one()
        cliente = db_session.get(Cliente, sample_cliente_b2b.persona_id)
        assert cliente.saldo_cuenta_corriente == pedido.total

        db_session.refresh(sample_lote)
        assert sample_lote.kg_disponibles == Decimal("95.00")

    def test_dia_sin_suscripciones_no_genera_nada(
        self, servicio_envios, db_session, suscripcion_lunes
    ):
        martes = FECHA_LUNES + timedelta(days=1)

        resultado = servicio_envios.generar_del_dia(martes)

        assert resultado.procesadas == 0
        assert resultado.generadas == 0
        assert db_session.query(Pedido).count() == 0

    def test_suscripcion_inactiva_no_genera(
        self, servicio_envios, db_session, suscripcion_lunes
    ):
        servicio_envios.desactivar_suscripcion(suscripcion_lunes.id)

        resultado = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert resultado.procesadas == 0
        assert db_session.query(Pedido).count() == 0

    def test_stock_insuficiente_marca_error_sin_generar_venta(
        self,
        servicio_envios,
        db_session,
        sample_cliente_b2b,
        sample_tipo_cafe,
        sample_lote,
    ):
        crear_suscripcion(
            servicio_envios,
            sample_cliente_b2b.persona_id,
            sample_tipo_cafe.id,
            cantidad_kg="200",
        )

        resultado = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert resultado.generadas == 0
        assert resultado.errores == 1
        assert resultado.detalle[0].estado == "ERROR"
        assert "Stock insuficiente" in resultado.detalle[0].mensaje

        assert db_session.query(Pedido).count() == 0
        assert db_session.query(VentaComercial).count() == 0

        entrega = db_session.query(models.EntregaProgramada).one()
        assert entrega.estado == models.EstadoEntrega.ERROR
        assert entrega.error is not None
        assert entrega.pedido_id is None

        cliente = db_session.get(Cliente, sample_cliente_b2b.persona_id)
        assert cliente.saldo_cuenta_corriente == Decimal("0.00")

        db_session.refresh(sample_lote)
        assert sample_lote.kg_disponibles == Decimal("100.00")

    def test_varias_suscripciones_del_mismo_cliente_generan_un_pedido(
        self,
        servicio_envios,
        db_session,
        sample_cliente_b2b,
        sample_tipo_cafe,
        sample_lote,
    ):
        crear_suscripcion(
            servicio_envios,
            sample_cliente_b2b.persona_id,
            sample_tipo_cafe.id,
            cantidad_kg="5",
        )
        crear_suscripcion(
            servicio_envios,
            sample_cliente_b2b.persona_id,
            sample_tipo_cafe.id,
            cantidad_kg="7",
        )

        resultado = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert resultado.generadas == 1
        pedido = db_session.query(Pedido).one()
        assert len(pedido.detalles) == 2
        assert pedido.total == Decimal("600000.00")
        assert db_session.query(VentaComercial).count() == 1

        cliente = db_session.get(Cliente, sample_cliente_b2b.persona_id)
        assert cliente.saldo_cuenta_corriente == pedido.total

        db_session.refresh(sample_lote)
        assert sample_lote.kg_disponibles == Decimal("88.00")

    def test_error_de_un_cliente_no_frena_a_los_demas(
        self,
        servicio_envios,
        db_session,
        sample_cliente_b2b,
        otro_cliente_b2b,
        sample_tipo_cafe,
        sample_lote,
    ):
        crear_suscripcion(
            servicio_envios,
            sample_cliente_b2b.persona_id,
            sample_tipo_cafe.id,
            cantidad_kg="200",
        )
        crear_suscripcion(
            servicio_envios,
            otro_cliente_b2b.persona_id,
            sample_tipo_cafe.id,
            cantidad_kg="5",
        )

        resultado = servicio_envios.generar_del_dia(FECHA_LUNES)

        assert resultado.procesadas == 2
        assert resultado.generadas == 1
        assert resultado.errores == 1
        assert db_session.query(Pedido).count() == 1

        estados = {
            entrega.cliente_id: entrega.estado
            for entrega in db_session.query(models.EntregaProgramada).all()
        }
        assert estados[sample_cliente_b2b.persona_id] == models.EstadoEntrega.ERROR
        assert estados[otro_cliente_b2b.persona_id] == models.EstadoEntrega.GENERADA

    def test_hoja_de_ruta_incluye_producto_y_condicion(
        self,
        servicio_envios,
        suscripcion_lunes,
        sample_tipo_cafe,
        sample_lote,
    ):
        servicio_envios.generar_del_dia(FECHA_LUNES)

        hoja = servicio_envios.hoja_de_ruta(FECHA_LUNES)

        assert len(hoja) == 1
        parada = hoja[0]
        assert parada.clienteNombre == "B2B Test"
        assert parada.direccion == "Calle B2B"
        assert parada.telefono == "5555555555"
        assert parada.condicionPago == "PAGARE"
        assert parada.estado == "ENTREGADO"
        assert len(parada.items) == 1
        assert parada.items[0].stockId == f"tc-{sample_tipo_cafe.id}-TOSTADO"
        assert parada.items[0].kilos == 5.0
        assert parada.items[0].precioKg == 50000.0
