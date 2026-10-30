"""Tests de las reglas de negocio del módulo de ventas.

Los casos críticos de idempotencia y transacción se prueban contra
``services.py``, no contra el router.
"""

from datetime import datetime, timedelta
from decimal import Decimal

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

    def test_no_modifica_stock_ni_saldo(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        stock_previo = _kilos_por_lote(db_session)
        saldo_previo = _saldo_cliente(db_session, pedido_entregado_b2b)

        services.VentaService(db_session).anular_venta(
            venta_confirmada.id,
            schemas.VentaAnulacionCreate(motivo="Error"),
        )

        assert _kilos_por_lote(db_session) == stock_previo
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

        nueva = service.registrar_venta(_datos_venta(pedido_entregado_b2b))

        assert nueva.id != venta_confirmada.id
        assert nueva.estado == VentaEstado.CONFIRMADA
        assert nueva.numero_comprobante != venta_confirmada.numero_comprobante


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
