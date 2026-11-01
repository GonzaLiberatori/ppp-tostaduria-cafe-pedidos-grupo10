"""Tests de las reglas de negocio del módulo de clientes.

El caso crítico es el ajuste de la cuenta corriente que usa ``ventas`` para
administrar la deuda de las ventas a pagaré: tiene que sumar, restar y no
confirmar la transacción por su cuenta.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.modules.clientes import services


def test_ajustar_saldo_suma_y_devuelve_el_nuevo_saldo(
    db_session, sample_cliente_b2b
):
    """Un ajuste positivo aumenta el saldo y lo devuelve actualizado."""
    nuevo_saldo = services.ajustar_saldo_cuenta_corriente(
        db_session, sample_cliente_b2b.persona_id, Decimal("1500.50")
    )

    assert nuevo_saldo == Decimal("1500.50")
    db_session.refresh(sample_cliente_b2b)
    assert sample_cliente_b2b.saldo_cuenta_corriente == Decimal("1500.50")


def test_ajustar_saldo_resta_sobre_el_saldo_existente(
    db_session, sample_cliente_b2b
):
    """Un ajuste negativo descuenta deuda sin bajar de cero por error de signo."""
    services.ajustar_saldo_cuenta_corriente(
        db_session, sample_cliente_b2b.persona_id, Decimal("2000")
    )

    nuevo_saldo = services.ajustar_saldo_cuenta_corriente(
        db_session, sample_cliente_b2b.persona_id, Decimal("-750.25")
    )

    assert nuevo_saldo == Decimal("1249.75")
    db_session.refresh(sample_cliente_b2b)
    assert sample_cliente_b2b.saldo_cuenta_corriente == Decimal("1249.75")


def test_ajustar_saldo_no_commitea(db_session, sample_cliente_b2b):
    """El ajuste participa de la transacción del llamador, no la cierra."""
    with patch.object(
        db_session,
        "commit",
        side_effect=AssertionError("ajustar_saldo_cuenta_corriente no debe commitear"),
    ):
        services.ajustar_saldo_cuenta_corriente(
            db_session, sample_cliente_b2b.persona_id, Decimal("100")
        )


def test_ajustar_saldo_de_cliente_inexistente(db_session):
    """Un id que no existe se informa como cliente no encontrado."""
    with pytest.raises(services.ClienteNoEncontrado):
        services.ajustar_saldo_cuenta_corriente(db_session, 999999, Decimal("100"))
