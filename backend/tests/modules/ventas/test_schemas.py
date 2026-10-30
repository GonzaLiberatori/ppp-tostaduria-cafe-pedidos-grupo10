"""Tests de validación de los schemas del módulo de ventas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas.schemas import (
    PagoCreate,
    VentaAnulacionCreate,
    VentaCreate,
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
