"""Tests de validación de los schemas del módulo de ventas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas.schemas import (
    CondicionPago,
    PagoCreate,
    ResumenPorMetodo,
    VentaAnulacionCreate,
    VentaCobroCreate,
    VentaCreate,
    VentaPorCobrarRead,
    VentaResumenMensualRead,
)


class TestPagoCreate:
    """Validaciones de entrada de un pago."""

    def test_pago_valido(self) -> None:
        pago = PagoCreate(
            metodo_de_pago=MetodoPago.EFECTIVO,
            monto=Decimal("1500.50"),
            moneda=Moneda.ARS,
        )
        assert pago.monto == Decimal("1500.50")
        assert pago.aclaracion is None

    def test_moneda_por_defecto_es_ars(self) -> None:
        pago = PagoCreate(
            metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("10")
        )
        assert pago.moneda == Moneda.ARS

    def test_monto_cero_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            PagoCreate(
                metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("0")
            )

    def test_monto_negativo_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            PagoCreate(
                metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("-5")
            )

    def test_metodo_inexistente_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            PagoCreate(metodo_de_pago="BITCOIN", monto=Decimal("10"))

    def test_metodo_valido_se_convierte_al_enum(self) -> None:
        pago = PagoCreate(
            metodo_de_pago="MERCADO_PAGO", monto=Decimal("10")
        )
        assert pago.metodo_de_pago == MetodoPago.MERCADO_PAGO

    def test_aclaracion_demasiado_larga_es_invalida(self) -> None:
        with pytest.raises(ValidationError):
            PagoCreate(
                metodo_de_pago=MetodoPago.EFECTIVO,
                monto=Decimal("10"),
                aclaracion="x" * 256,
            )


class TestVentaCreate:
    """Validaciones de entrada de una venta."""

    def test_venta_valida(self) -> None:
        venta = VentaCreate(
            pedido_id=1,
            facturacion=Facturacion.TICKET,
            pagos=[
                PagoCreate(
                    metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("100")
                )
            ],
        )
        assert venta.pedido_id == 1
        assert len(venta.pagos) == 1

    def test_sin_pagos_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaCreate(
                pedido_id=1, facturacion=Facturacion.TICKET, pagos=[]
            )

    def test_pedido_id_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaCreate(
                pedido_id=0,
                facturacion=Facturacion.TICKET,
                pagos=[
                    PagoCreate(
                        metodo_de_pago=MetodoPago.EFECTIVO,
                        monto=Decimal("10"),
                    )
                ],
            )

    def test_facturacion_inexistente_es_invalida(self) -> None:
        with pytest.raises(ValidationError):
            VentaCreate(
                pedido_id=1,
                facturacion="Factura Z",
                pagos=[
                    PagoCreate(
                        metodo_de_pago=MetodoPago.EFECTIVO,
                        monto=Decimal("10"),
                    )
                ],
            )


class TestVentaAnulacionCreate:
    """Validaciones del motivo de anulación."""

    def test_motivo_valido(self) -> None:
        datos = VentaAnulacionCreate(motivo="  Cobro cargado dos veces  ")
        assert datos.motivo == "Cobro cargado dos veces"

    def test_motivo_vacio_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaAnulacionCreate(motivo="")

    def test_motivo_solo_espacios_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaAnulacionCreate(motivo="   ")

    def test_motivo_demasiado_largo_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaAnulacionCreate(motivo="x" * 256)


class TestVentaResumenMensualRead:
    """Contrato de la fila mensual del resumen de ventas."""

    def test_fila_valida(self) -> None:
        fila = VentaResumenMensualRead(
            mes="2026-10",
            cantidad_ventas=2,
            total_facturado=Decimal("1500.00"),
            totales_por_metodo=[
                ResumenPorMetodo(
                    metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("1500.00")
                )
            ],
        )
        assert fila.mes == "2026-10"
        assert fila.cantidad_ventas == 2
        assert fila.total_facturado == Decimal("1500.00")
        assert fila.totales_por_metodo[0].metodo_de_pago == MetodoPago.EFECTIVO

    def test_totales_por_metodo_por_defecto_vacio(self) -> None:
        fila = VentaResumenMensualRead(
            mes="2026-10",
            cantidad_ventas=0,
            total_facturado=Decimal("0"),
        )
        assert fila.totales_por_metodo == []

    def test_mes_es_obligatorio(self) -> None:
        with pytest.raises(ValidationError):
            VentaResumenMensualRead(
                cantidad_ventas=1, total_facturado=Decimal("10")
            )


class TestVentaCreateCondicionDePago:
    """Validaciones de la condición de pago y su plazo."""

    def _pago(self) -> PagoCreate:
        return PagoCreate(
            metodo_de_pago=MetodoPago.EFECTIVO, monto=Decimal("100")
        )

    def test_condicion_por_defecto_es_contado(self) -> None:
        venta = VentaCreate(
            pedido_id=1,
            facturacion=Facturacion.TICKET,
            pagos=[self._pago()],
        )
        assert venta.condicion_pago is CondicionPago.CONTADO
        assert venta.plazo_dias is None

    def test_pagare_con_plazo_valido(self) -> None:
        venta = VentaCreate(
            pedido_id=1,
            facturacion=Facturacion.FACTURA_A,
            pagos=[self._pago()],
            condicion_pago=CondicionPago.PAGARE,
            plazo_dias=60,
        )
        assert venta.condicion_pago is CondicionPago.PAGARE
        assert venta.plazo_dias == 60

    def test_pagare_sin_plazo_es_invalido(self) -> None:
        with pytest.raises(ValidationError, match="necesita plazo_dias"):
            VentaCreate(
                pedido_id=1,
                facturacion=Facturacion.FACTURA_A,
                pagos=[self._pago()],
                condicion_pago=CondicionPago.PAGARE,
            )

    @pytest.mark.parametrize("plazo", [0, 15, 45, 120])
    def test_pagare_con_plazo_fuera_de_los_admitidos(self, plazo: int) -> None:
        with pytest.raises(ValidationError, match="30, 60 o 90"):
            VentaCreate(
                pedido_id=1,
                facturacion=Facturacion.FACTURA_A,
                pagos=[self._pago()],
                condicion_pago=CondicionPago.PAGARE,
                plazo_dias=plazo,
            )

    def test_contado_con_plazo_es_invalido(self) -> None:
        with pytest.raises(ValidationError, match="solo aplica"):
            VentaCreate(
                pedido_id=1,
                facturacion=Facturacion.TICKET,
                pagos=[self._pago()],
                condicion_pago=CondicionPago.CONTADO,
                plazo_dias=30,
            )


class TestVentaCobroCreate:
    """Contrato del cobro de una venta pendiente."""

    def test_cobro_valido(self) -> None:
        datos = VentaCobroCreate(
            metodo_de_pago=MetodoPago.TRANSFERENCIA,
            aclaracion="  Transferencia Banco Nación  ",
        )
        assert datos.metodo_de_pago is MetodoPago.TRANSFERENCIA
        assert datos.aclaracion == "Transferencia Banco Nación"

    def test_sin_metodo_es_invalido(self) -> None:
        with pytest.raises(ValidationError):
            VentaCobroCreate()

    def test_aclaracion_demasiado_larga_es_invalida(self) -> None:
        with pytest.raises(ValidationError):
            VentaCobroCreate(
                metodo_de_pago=MetodoPago.EFECTIVO, aclaracion="x" * 256
            )


class TestVentaPorCobrarRead:
    """Contrato del saldo por cobrar."""

    def test_sin_pendientes_es_una_lista_vacia(self) -> None:
        saldo = VentaPorCobrarRead(total_por_cobrar=Decimal("0"))
        assert saldo.items == []
        assert saldo.cantidad_vencidas == 0

