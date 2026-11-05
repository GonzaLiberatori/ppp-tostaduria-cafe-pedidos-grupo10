"""Tests de las reglas de negocio del módulo de ventas.

Los casos críticos de idempotencia y transacción se prueban contra
``services.py``, no contra el router.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from sqlalchemy.exc import IntegrityError

from app.modules.clientes.models import Cliente
from app.modules.inventario.models import Lote
from app.modules.pedidos import services as pedidos_services
from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas import crud, schemas, services
from app.modules.ventas.models import PagoVenta, VentaComercial, VentaEstado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _datos_venta(pedido, pagos=None, facturacion=Facturacion.TICKET):
    """Arma el alta de venta con un pago por el total si no se especifica."""
    if pagos is None:
        pagos = [
            schemas.PagoCreate(
                metodo_de_pago=MetodoPago.EFECTIVO,
                monto=Decimal(str(pedido.total)),
                moneda=Moneda.ARS,
            )
        ]
    return schemas.VentaCreate(
        pedido_id=pedido.id, facturacion=facturacion, pagos=pagos
    )


def _saldo_cliente(db, pedido) -> Decimal:
    """Saldo de cuenta corriente del cliente del pedido."""
    cliente = db.get(Cliente, pedido.cliente_persona_id)
    db.refresh(cliente)
    return Decimal(str(cliente.saldo_cuenta_corriente))


def _kilos_por_lote(db) -> dict[int, Decimal]:
    """Kilos disponibles de cada lote de café tostado."""
    return {
        lote.id: Decimal(str(lote.kg_disponibles))
        for lote in db.query(Lote).order_by(Lote.id).all()
    }


def _fijar_fecha(db, venta, fecha: datetime) -> None:
    """Reubica la venta en el mes calendario indicado."""
    modelo = crud.obtener_por_id(db, venta.id)
    modelo.fecha = fecha
    db.commit()
    db.refresh(modelo)


def _fijar_vencimiento(db, venta, fecha: datetime) -> None:
    """Fija el vencimiento del pagaré para probar la marca de vencida."""
    modelo = crud.obtener_por_id(db, venta.id)
    modelo.fecha_vencimiento = fecha
    db.commit()
    db.refresh(modelo)


def _datos_pagare(pedido, plazo: int = 30) -> schemas.VentaCreate:
    """Alta de venta a pagaré con el pago a crédito que representa la deuda."""
    return schemas.VentaCreate(
        pedido_id=pedido.id,
        facturacion=Facturacion.FACTURA_A,
        condicion_pago=schemas.CondicionPago.PAGARE,
        plazo_dias=plazo,
        pagos=[
            schemas.PagoCreate(
                metodo_de_pago=MetodoPago.CREDITO,
                monto=Decimal(str(pedido.total)),
                moneda=Moneda.ARS,
            )
        ],
    )


@pytest.fixture
def dos_ventas(db_session, pedido_entregado_b2b, pedido_entregado_consumidor):
    """Una venta de septiembre a crédito y otra de octubre en efectivo."""
    service = services.VentaService(db_session)
    primera = service.registrar_venta(
        _datos_venta(
            pedido_entregado_b2b,
            pagos=[
                schemas.PagoCreate(
                    metodo_de_pago=MetodoPago.CREDITO,
                    monto=Decimal(str(pedido_entregado_b2b.total)),
                    moneda=Moneda.ARS,
                )
            ],
        )
    )
    segunda = service.registrar_venta(_datos_venta(pedido_entregado_consumidor))
    _fijar_fecha(db_session, primera, datetime(2026, 9, 15, 10, 30))
    _fijar_fecha(db_session, segunda, datetime(2026, 10, 20, 12, 0))
    return primera, segunda


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


class TestRegistrarVenta:
    """Alta del cobro de un pedido entregado."""

    def test_registro_exitoso(self, db_session, pedido_entregado_b2b) -> None:
        venta = services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b, facturacion=Facturacion.FACTURA_A)
        )

        assert venta.id is not None
        assert venta.estado == VentaEstado.CONFIRMADA
        assert venta.total == Decimal(str(pedido_entregado_b2b.total))
        assert venta.pedido_estado == "ENTREGADO"
        assert venta.cliente_nombre
        assert len(venta.pagos) == 1
        assert venta.pagos[0].metodo_de_pago == MetodoPago.EFECTIVO
        assert len(venta.historial) == 1
        assert venta.historial[0].estado_nuevo == VentaEstado.CONFIRMADA

    def test_comprobante_con_formato_esperado(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        venta = services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b)
        )

        prefijo = f"V-{venta.fecha:%Y%m}-"
        assert venta.numero_comprobante.startswith(prefijo)
        assert venta.numero_comprobante == f"{prefijo}{venta.id:06d}"

    def test_pago_mixto(self, db_session, pedido_entregado_b2b) -> None:
        total = Decimal(str(pedido_entregado_b2b.total))
        mitad = (total / 2).quantize(Decimal("0.01"))

        venta = services.VentaService(db_session).registrar_venta(
            _datos_venta(
                pedido_entregado_b2b,
                pagos=[
                    schemas.PagoCreate(
                        metodo_de_pago=MetodoPago.EFECTIVO,
                        monto=mitad,
                        moneda=Moneda.ARS,
                    ),
                    schemas.PagoCreate(
                        metodo_de_pago=MetodoPago.TRANSFERENCIA,
                        monto=total - mitad,
                        moneda=Moneda.ARS,
                    ),
                ],
            )
        )

        assert len(venta.pagos) == 2
        assert sum(pago.monto for pago in venta.pagos) == total

    def test_pedido_inexistente(self, db_session) -> None:
        datos = schemas.VentaCreate(
            pedido_id=999999,
            facturacion=Facturacion.TICKET,
            pagos=[
                schemas.PagoCreate(
                    metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("10")
                )
            ],
        )

        with pytest.raises(services.PedidoNoEncontrado):
            services.VentaService(db_session).registrar_venta(datos)

    def test_pedido_en_estado_listo_no_es_vendible(
        self, db_session, sample_pedido_b2b
    ) -> None:
        pedidos_services.PedidoService(db_session).cambiar_estado_pedido(
            sample_pedido_b2b.id, "LISTO"
        )
        db_session.refresh(sample_pedido_b2b)

        with pytest.raises(services.PedidoNoVendible) as error:
            services.VentaService(db_session).registrar_venta(
                _datos_venta(sample_pedido_b2b)
            )

        assert error.value.estado == "LISTO"

    def test_pedido_pendiente_no_es_vendible(
        self, db_session, sample_pedido_b2b
    ) -> None:
        with pytest.raises(services.PedidoNoVendible):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(sample_pedido_b2b)
            )

    def test_segundo_registro_es_rechazado(
        self, db_session, pedido_entregado_b2b, venta_confirmada
    ) -> None:
        with pytest.raises(services.VentaDuplicada):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        assert db_session.query(VentaComercial).count() == 1

    def test_suma_de_pagos_incorrecta(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        total = Decimal(str(pedido_entregado_b2b.total))

        with pytest.raises(services.PagosNoCuadran) as error:
            services.VentaService(db_session).registrar_venta(
                _datos_venta(
                    pedido_entregado_b2b,
                    pagos=[
                        schemas.PagoCreate(
                            metodo_de_pago=MetodoPago.EFECTIVO,
                            monto=total - Decimal("1"),
                        )
                    ],
                )
            )

        assert error.value.diferencia == Decimal("1")
        assert db_session.query(VentaComercial).count() == 0
        assert db_session.query(PagoVenta).count() == 0

    def test_no_modifica_el_stock(self, db_session, pedido_entregado_b2b) -> None:
        stock_previo = _kilos_por_lote(db_session)

        services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b)
        )

        assert _kilos_por_lote(db_session) == stock_previo

    def test_no_modifica_la_cuenta_corriente(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        saldo_previo = _saldo_cliente(db_session, pedido_entregado_b2b)

        services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b)
        )

        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_previo

    def test_el_pedido_sigue_entregado(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b)
        )

        db_session.refresh(pedido_entregado_b2b)
        assert getattr(pedido_entregado_b2b.estado, "value", pedido_entregado_b2b.estado) == (
            "ENTREGADO"
        )


# ---------------------------------------------------------------------------
# Alta por entrega (participa de la transacción de pedidos)
# ---------------------------------------------------------------------------


class TestRegistrarVentaDeEntrega:
    """Venta que nace al confirmar la entrega de un pedido."""

    def test_contado_crea_venta_confirmada_sin_deuda(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_b2b)

        venta = services.registrar_venta_de_entrega(
            db_session,
            pedido_entregado_b2b,
            schemas.CondicionPago.CONTADO,
            metodo_de_pago=MetodoPago.EFECTIVO,
            cuenta_id=7,
        )

        assert venta.estado == VentaEstado.CONFIRMADA
        assert venta.cobrada_en is not None
        assert venta.fecha_vencimiento is None
        assert venta.cuenta_id == 7
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial
        assert len(venta.pagos) == 1
        assert venta.pagos[0].metodo_de_pago == MetodoPago.EFECTIVO
        assert venta.pagos[0].monto == Decimal(str(pedido_entregado_b2b.total))

    def test_pagare_suma_deuda_y_calcula_vencimiento(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_b2b)
        total = Decimal(str(pedido_entregado_b2b.total))

        venta = services.registrar_venta_de_entrega(
            db_session,
            pedido_entregado_b2b,
            schemas.CondicionPago.PAGARE,
            plazo_dias=30,
        )

        assert venta.estado == VentaEstado.PENDIENTE_COBRO
        assert venta.cobrada_en is None
        assert venta.fecha_vencimiento is not None
        assert venta.fecha_vencimiento - venta.fecha == timedelta(days=30)
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial + total
        assert venta.pagos[0].metodo_de_pago == MetodoPago.CREDITO
        assert venta.pagos[0].monto == total
        assert venta.historial[0].estado_nuevo == VentaEstado.PENDIENTE_COBRO

    def test_pagare_a_cliente_no_mayorista_es_rechazado(
        self, db_session, pedido_entregado_consumidor
    ) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_consumidor)

        with pytest.raises(services.PagareNoPermitido):
            services.registrar_venta_de_entrega(
                db_session,
                pedido_entregado_consumidor,
                schemas.CondicionPago.PAGARE,
                plazo_dias=30,
            )

        assert crud.obtener_vigente_por_pedido(
            db_session, pedido_entregado_consumidor.id
        ) is None
        assert (
            _saldo_cliente(db_session, pedido_entregado_consumidor)
            == saldo_inicial
        )

    @pytest.mark.parametrize("plazo", [None, 0, 15, 45, 120])
    def test_plazo_invalido_es_rechazado(
        self, db_session, pedido_entregado_b2b, plazo
    ) -> None:
        with pytest.raises(services.PlazoInvalido):
            services.registrar_venta_de_entrega(
                db_session,
                pedido_entregado_b2b,
                schemas.CondicionPago.PAGARE,
                plazo_dias=plazo,
            )

        assert crud.obtener_vigente_por_pedido(
            db_session, pedido_entregado_b2b.id
        ) is None

    def test_no_commitea(self, db_session, pedido_entregado_b2b) -> None:
        with patch.object(
            db_session,
            "commit",
            side_effect=AssertionError(
                "registrar_venta_de_entrega no debe commitear"
            ),
        ):
            services.registrar_venta_de_entrega(
                db_session,
                pedido_entregado_b2b,
                schemas.CondicionPago.CONTADO,
                metodo_de_pago=MetodoPago.EFECTIVO,
            )

    def test_venta_vigente_bloquea_una_segunda_entrega(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        services.registrar_venta_de_entrega(
            db_session,
            pedido_entregado_b2b,
            schemas.CondicionPago.PAGARE,
            plazo_dias=30,
        )

        with pytest.raises(services.VentaDuplicada):
            services.registrar_venta_de_entrega(
                db_session,
                pedido_entregado_b2b,
                schemas.CondicionPago.CONTADO,
                metodo_de_pago=MetodoPago.EFECTIVO,
            )


# ---------------------------------------------------------------------------
# Cobro
# ---------------------------------------------------------------------------


class TestCobrarVenta:
    """Cobro de una venta pendiente."""

    def _venta_pendiente(self, db_session, pedido):
        """Crea una venta a pagaré a 30 días y confirma la deuda."""
        venta = services.registrar_venta_de_entrega(
            db_session,
            pedido,
            schemas.CondicionPago.PAGARE,
            plazo_dias=30,
        )
        db_session.commit()
        return venta

    def test_cobro_exitoso(self, db_session, pedido_entregado_b2b) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_b2b)
        total = Decimal(str(pedido_entregado_b2b.total))
        venta = self._venta_pendiente(db_session, pedido_entregado_b2b)

        cobrada = services.VentaService(db_session).cobrar_venta(
            venta.id,
            schemas.VentaCobroCreate(
                metodo_de_pago=MetodoPago.TRANSFERENCIA,
                aclaracion="Transferencia Banco Nación",
            ),
            cuenta_id=3,
        )

        assert cobrada.estado == VentaEstado.CONFIRMADA
        assert cobrada.cobrada_en is not None
        assert cobrada.numero_comprobante == venta.numero_comprobante
        assert cobrada.pagos[0].metodo_de_pago == MetodoPago.TRANSFERENCIA
        assert cobrada.pagos[0].aclaracion == "Transferencia Banco Nación"
        assert sum(pago.monto for pago in cobrada.pagos) == total
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial
        assert len(cobrada.historial) == 2
        assert cobrada.historial[-1].estado_anterior == VentaEstado.PENDIENTE_COBRO
        assert cobrada.historial[-1].estado_nuevo == VentaEstado.CONFIRMADA
        assert cobrada.historial[-1].cuenta_id == 3

    def test_cobro_de_una_venta_ya_confirmada(
        self, db_session, venta_confirmada
    ) -> None:
        with pytest.raises(services.VentaNoPendienteDeCobro):
            services.VentaService(db_session).cobrar_venta(
                venta_confirmada.id,
                schemas.VentaCobroCreate(metodo_de_pago=MetodoPago.EFECTIVO),
            )

    def test_cobro_de_una_venta_anulada(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        venta = self._venta_pendiente(db_session, pedido_entregado_b2b)
        services.VentaService(db_session).anular_venta(
            venta.id, schemas.VentaAnulacionCreate(motivo="Error de carga")
        )

        with pytest.raises(services.VentaNoPendienteDeCobro):
            services.VentaService(db_session).cobrar_venta(
                venta.id,
                schemas.VentaCobroCreate(metodo_de_pago=MetodoPago.EFECTIVO),
            )

    def test_cobro_de_una_venta_inexistente(self, db_session) -> None:
        with pytest.raises(services.VentaNoEncontrada):
            services.VentaService(db_session).cobrar_venta(
                999999,
                schemas.VentaCobroCreate(metodo_de_pago=MetodoPago.EFECTIVO),
            )


# ---------------------------------------------------------------------------
# Anulación
# ---------------------------------------------------------------------------


class TestAnularVenta:
    """Anulación lógica."""

    def test_anulacion_exitosa(self, db_session, venta_confirmada) -> None:
        anulada = services.VentaService(db_session).anular_venta(
            venta_confirmada.id,
            schemas.VentaAnulacionCreate(motivo="Cobro cargado dos veces"),
        )

        assert anulada.estado == VentaEstado.ANULADA
        assert anulada.anulada_en is not None
        assert anulada.pedido_id == venta_confirmada.pedido_id
        assert [entrada.estado_nuevo for entrada in anulada.historial] == [
            VentaEstado.CONFIRMADA,
            VentaEstado.ANULADA,
        ]
        assert anulada.historial[-1].motivo == "Cobro cargado dos veces"

    def test_conserva_pagos_y_comprobante(
        self, db_session, venta_confirmada
    ) -> None:
        anulada = services.VentaService(db_session).anular_venta(
            venta_confirmada.id,
            schemas.VentaAnulacionCreate(motivo="Error"),
        )

        assert anulada.numero_comprobante == venta_confirmada.numero_comprobante
        assert len(anulada.pagos) == 1

    def test_anulacion_devuelve_el_stock_y_no_toca_el_saldo(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        stock_previo = _kilos_por_lote(db_session)
        saldo_previo = _saldo_cliente(db_session, pedido_entregado_b2b)

        services.VentaService(db_session).anular_venta(
            venta_confirmada.id,
            schemas.VentaAnulacionCreate(motivo="Error"),
        )

        assert _kilos_por_lote(db_session) == {
            lote_id: kilos + Decimal("10")
            for lote_id, kilos in stock_previo.items()
        }
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_previo

    def test_doble_anulacion_es_rechazada(
        self, db_session, venta_confirmada
    ) -> None:
        service = services.VentaService(db_session)
        service.anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )

        with pytest.raises(services.VentaYaAnulada):
            service.anular_venta(
                venta_confirmada.id,
                schemas.VentaAnulacionCreate(motivo="Otra vez"),
            )

    def test_venta_inexistente(self, db_session) -> None:
        with pytest.raises(services.VentaNoEncontrada):
            services.VentaService(db_session).anular_venta(
                999999, schemas.VentaAnulacionCreate(motivo="Error")
            )

    def test_se_puede_revender_tras_anular(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        service.anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )
        stock_tras_anular = _kilos_por_lote(db_session)

        nueva = service.registrar_venta(_datos_venta(pedido_entregado_b2b))

        assert nueva.id != venta_confirmada.id
        assert nueva.estado == VentaEstado.CONFIRMADA
        assert nueva.numero_comprobante != venta_confirmada.numero_comprobante
        assert _kilos_por_lote(db_session) == {
            lote_id: kilos - Decimal("10")
            for lote_id, kilos in stock_tras_anular.items()
        }

    def test_segunda_anulacion_vuelve_a_devolver_el_stock(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        service.anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )
        stock_original = _kilos_por_lote(db_session)

        nueva = service.registrar_venta(_datos_venta(pedido_entregado_b2b))
        service.anular_venta(
            nueva.id, schemas.VentaAnulacionCreate(motivo="Error de nuevo")
        )

        assert _kilos_por_lote(db_session) == stock_original

    def test_anular_pagare_revierte_la_deuda(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_b2b)
        total = Decimal(str(pedido_entregado_b2b.total))
        venta = services.registrar_venta_de_entrega(
            db_session,
            pedido_entregado_b2b,
            schemas.CondicionPago.PAGARE,
            plazo_dias=60,
        )
        db_session.commit()
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial + total

        anulada = services.VentaService(db_session).anular_venta(
            venta.id, schemas.VentaAnulacionCreate(motivo="Cliente desistió")
        )

        assert anulada.estado == VentaEstado.ANULADA
        assert len(anulada.pagos) == 1
        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial

    def test_anular_venta_al_contado_no_toca_el_saldo(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        saldo_inicial = _saldo_cliente(db_session, pedido_entregado_b2b)

        services.VentaService(db_session).anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )

        assert _saldo_cliente(db_session, pedido_entregado_b2b) == saldo_inicial


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


class TestConsultas:
    """Detalle, listado y arqueo."""

    def test_obtener_venta(self, db_session, venta_confirmada) -> None:
        venta = services.VentaService(db_session).obtener_venta(
            venta_confirmada.id
        )
        assert venta.id == venta_confirmada.id
        assert venta.numero_comprobante == venta_confirmada.numero_comprobante

    def test_listado_tolera_venta_sin_pedido(self, db_session, venta_confirmada) -> None:
        """El listado no debe romperse ni mostrar ``None None`` como cliente."""
        db_session.add(
            VentaComercial(
                pedido_id=999999,
                fecha=datetime.now(),
                facturacion=Facturacion.TICKET,
                estado=VentaEstado.CONFIRMADA,
                total=Decimal("100.00"),
                numero_comprobante="V-999999-999999",
                creada_en=datetime.now(),
            )
        )
        db_session.commit()

        ventas = services.VentaService(db_session).listar_ventas()
        huerfana = next(venta for venta in ventas if venta.pedido_id == 999999)

        assert len(ventas) == 2
        assert huerfana.cliente_persona_id is None
        assert huerfana.cliente_nombre is None
        assert huerfana.metodos_de_pago == []

    def test_obtener_venta_inexistente(self, db_session) -> None:
        with pytest.raises(services.VentaNoEncontrada):
            services.VentaService(db_session).obtener_venta(999999)

    def test_obtener_por_comprobante(self, db_session, venta_confirmada) -> None:
        venta = services.VentaService(db_session).obtener_por_comprobante(
            venta_confirmada.numero_comprobante
        )
        assert venta.id == venta_confirmada.id

    def test_obtener_por_comprobante_inexistente(self, db_session) -> None:
        with pytest.raises(services.VentaNoEncontrada):
            services.VentaService(db_session).obtener_por_comprobante("V-000000-000000")

    def test_listar_ventas(self, db_session, venta_confirmada) -> None:
        ventas = services.VentaService(db_session).listar_ventas()
        assert len(ventas) == 1
        assert ventas[0].id == venta_confirmada.id
        assert ventas[0].metodos_de_pago == [MetodoPago.CREDITO]
        assert ventas[0].cliente_nombre

    def test_listar_por_estado(self, db_session, venta_confirmada) -> None:
        services.VentaService(db_session).anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )

        anuladas = services.VentaService(db_session).listar_ventas(
            estado=VentaEstado.ANULADA
        )
        confirmadas = services.VentaService(db_session).listar_ventas(
            estado=VentaEstado.CONFIRMADA
        )

        assert len(anuladas) == 1
        assert confirmadas == []

    def test_resumen_arqueo(self, db_session, venta_confirmada) -> None:
        resumen = services.VentaService(db_session).resumen_arqueo()

        assert resumen.cantidad_ventas == 1
        assert resumen.total_facturado == Decimal(str(venta_confirmada.total))
        assert len(resumen.totales_por_metodo) == 1
        assert resumen.totales_por_metodo[0].metodo_de_pago == MetodoPago.CREDITO
        assert resumen.totales_por_metodo[0].monto == Decimal(
            str(venta_confirmada.total)
        )

    def test_resumen_excluye_anuladas(self, db_session, venta_confirmada) -> None:
        services.VentaService(db_session).anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )

        resumen = services.VentaService(db_session).resumen_arqueo()

        assert resumen.cantidad_ventas == 0
        assert resumen.total_facturado == Decimal("0")
        assert resumen.totales_por_metodo == []

    def test_resumen_de_rango_sin_ventas(self, db_session, venta_confirmada) -> None:
        manana = datetime.now() + timedelta(days=1)

        resumen = services.VentaService(db_session).resumen_arqueo(
            fecha_desde=manana
        )

        assert resumen.cantidad_ventas == 0
        assert resumen.total_facturado == Decimal("0")
        assert resumen.totales_por_metodo == []

    def test_resumen_mensual(self, db_session, dos_ventas) -> None:
        serie = services.VentaService(db_session).resumen_mensual()

        assert [fila.mes for fila in serie] == ["2026-10", "2026-09"]
        assert serie[0].cantidad_ventas == 1
        assert serie[0].total_facturado == Decimal(str(dos_ventas[1].total))
        assert serie[1].cantidad_ventas == 1
        assert serie[1].total_facturado == Decimal(str(dos_ventas[0].total))

    def test_resumen_mensual_incluye_metodos_del_mes(
        self, db_session, dos_ventas
    ) -> None:
        serie = services.VentaService(db_session).resumen_mensual()
        por_mes = {fila.mes: fila for fila in serie}

        assert [pago.metodo_de_pago for pago in por_mes["2026-09"].totales_por_metodo] == [
            MetodoPago.CREDITO
        ]
        assert [pago.metodo_de_pago for pago in por_mes["2026-10"].totales_por_metodo] == [
            MetodoPago.EFECTIVO
        ]

    def test_resumen_mensual_excluye_anuladas(self, db_session, dos_ventas) -> None:
        services.VentaService(db_session).anular_venta(
            dos_ventas[0].id, schemas.VentaAnulacionCreate(motivo="Error de cobro")
        )

        serie = services.VentaService(db_session).resumen_mensual()

        assert [fila.mes for fila in serie] == ["2026-10"]
        assert serie[0].total_facturado == Decimal(str(dos_ventas[1].total))

    def test_resumen_mensual_filtra_por_rango(self, db_session, dos_ventas) -> None:
        serie = services.VentaService(db_session).resumen_mensual(
            fecha_desde=datetime(2026, 10, 1)
        )

        assert [fila.mes for fila in serie] == ["2026-10"]

    def test_resumen_mensual_sin_ventas(self, db_session) -> None:
        serie = services.VentaService(db_session).resumen_mensual()

        assert serie == []


class TestCobranzaYPorCobrar:
    """Serie de cobranza y saldo por cobrar."""

    def test_cobranza_mensual_usa_el_mes_del_cobro(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        venta = service.registrar_venta(_datos_pagare(pedido_entregado_b2b))
        _fijar_fecha(db_session, venta, datetime(2026, 8, 20, 10, 0))

        service.cobrar_venta(
            venta.id,
            schemas.VentaCobroCreate(metodo_de_pago=MetodoPago.TRANSFERENCIA),
        )

        serie = service.cobranza_mensual()
        mes_actual = datetime.now().strftime("%Y-%m")

        assert [fila.mes for fila in serie] == [mes_actual]
        assert serie[0].cantidad_cobros == 1
        assert serie[0].total_cobrado == Decimal(str(venta.total))
        assert serie[0].totales_por_metodo[0].metodo_de_pago == (
            MetodoPago.TRANSFERENCIA
        )

    def test_cobranza_mensual_sin_cobros(self, db_session) -> None:
        assert services.VentaService(db_session).cobranza_mensual() == []

    def test_por_cobrar_marca_vencidas_y_suma_el_total(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        venta = service.registrar_venta(_datos_pagare(pedido_entregado_b2b))
        _fijar_vencimiento(
            db_session, venta, datetime.now() - timedelta(days=5)
        )

        por_cobrar = service.por_cobrar()

        assert len(por_cobrar.items) == 1
        item = por_cobrar.items[0]
        assert item.venta_id == venta.id
        assert item.vencida is True
        assert item.fecha_vencimiento is not None
        assert por_cobrar.total_por_cobrar == item.total
        assert por_cobrar.cantidad_vencidas == 1

    def test_por_cobrar_no_marca_vencida_una_pendiente_futura(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        venta = service.registrar_venta(
            _datos_pagare(pedido_entregado_b2b, plazo=90)
        )
        _fijar_vencimiento(
            db_session, venta, datetime.now() + timedelta(days=10)
        )

        por_cobrar = service.por_cobrar()

        assert por_cobrar.items[0].vencida is False
        assert por_cobrar.cantidad_vencidas == 0

    def test_por_cobrar_excluye_cobradas(
        self, db_session, venta_confirmada
    ) -> None:
        por_cobrar = services.VentaService(db_session).por_cobrar()

        assert por_cobrar.items == []
        assert por_cobrar.total_por_cobrar == Decimal("0")

    def test_por_cobrar_excluye_anuladas(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        service = services.VentaService(db_session)
        anulada = service.registrar_venta(_datos_pagare(pedido_entregado_b2b))
        service.anular_venta(
            anulada.id, schemas.VentaAnulacionCreate(motivo="Error")
        )

        por_cobrar = service.por_cobrar()

        assert por_cobrar.items == []
        assert por_cobrar.total_por_cobrar == Decimal("0")
        assert por_cobrar.cantidad_vencidas == 0


# ---------------------------------------------------------------------------
# Clasificación de errores de integridad
# ---------------------------------------------------------------------------


class TestErroresDeIntegridad:
    """Una violación de integridad no se rotula siempre como venta duplicada."""

    def test_carrera_de_dos_altas_se_informa_como_venta_duplicada(
        self, db_session, pedido_entregado_b2b, venta_confirmada, monkeypatch
    ) -> None:
        """Si el chequeo previo no ve la venta, el índice parcial la frena."""
        monkeypatch.setattr(
            crud, "obtener_vigente_por_pedido", lambda *_args, **_kwargs: None
        )

        with pytest.raises(services.VentaDuplicada):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        monkeypatch.undo()
        assert db_session.query(VentaComercial).count() == 1
        assert db_session.query(PagoVenta).count() == 1

    def test_comprobante_duplicado_se_informa_como_tal(
        self, db_session, pedido_entregado_b2b, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise IntegrityError(
                "UPDATE venta_comercial",
                {},
                Exception(
                    "UNIQUE constraint failed: venta_comercial.numero_comprobante"
                ),
            )

        monkeypatch.setattr(crud, "actualizar_venta", _falla)

        with pytest.raises(services.ComprobanteDuplicado):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        monkeypatch.undo()
        assert db_session.query(VentaComercial).count() == 0
        assert db_session.query(PagoVenta).count() == 0

    def test_otra_violacion_de_integridad_no_se_disfraza(
        self, db_session, pedido_entregado_b2b, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise IntegrityError(
                "INSERT INTO pago_venta",
                {},
                Exception("FOREIGN KEY constraint failed"),
            )

        monkeypatch.setattr(crud, "crear_pago", _falla)

        with pytest.raises(IntegrityError):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        monkeypatch.undo()
        assert db_session.query(VentaComercial).count() == 0


class TestAtomicidad:
    """Si falla un paso, no queda ningún registro parcial."""

    def test_fallo_al_guardar_un_pago(
        self, db_session, pedido_entregado_b2b, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise RuntimeError("falla simulada al guardar el pago")

        monkeypatch.setattr(crud, "crear_pago", _falla)

        with pytest.raises(RuntimeError):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        monkeypatch.undo()
        assert db_session.query(VentaComercial).count() == 0
        assert db_session.query(PagoVenta).count() == 0
        assert (
            crud.obtener_vigente_por_pedido(db_session, pedido_entregado_b2b.id)
            is None
        )

    def test_fallo_al_guardar_el_historial(
        self, db_session, pedido_entregado_b2b, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise RuntimeError("falla simulada al guardar el historial")

        monkeypatch.setattr(crud, "crear_historial", _falla)

        with pytest.raises(RuntimeError):
            services.VentaService(db_session).registrar_venta(
                _datos_venta(pedido_entregado_b2b)
            )

        monkeypatch.undo()
        assert db_session.query(VentaComercial).count() == 0

        # El comprobante no quedó consumido: se puede volver a registrar.
        nueva = services.VentaService(db_session).registrar_venta(
            _datos_venta(pedido_entregado_b2b)
        )
        assert nueva.numero_comprobante.endswith(f"{nueva.id:06d}")

    def test_fallo_al_anular_deja_la_venta_confirmada(
        self, db_session, venta_confirmada, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise RuntimeError("falla simulada al guardar el historial")

        monkeypatch.setattr(crud, "crear_historial", _falla)

        with pytest.raises(RuntimeError):
            services.VentaService(db_session).anular_venta(
                venta_confirmada.id,
                schemas.VentaAnulacionCreate(motivo="Error"),
            )

        monkeypatch.undo()
        venta = crud.obtener_por_id(db_session, venta_confirmada.id)
        assert venta is not None
        assert venta.estado == VentaEstado.CONFIRMADA
        assert venta.anulada_en is None
        assert len(venta.pagos) == 1
