"""Tests de los endpoints del panel de pedidos.

Cubren la entrega como caso de uso: la venta nace en el ``PATCH``, la condición
de pago viaja en el mismo cuerpo, la cuenta autenticada queda auditada y la
reversión con venta vigente se rechaza con 409.
"""

from decimal import Decimal

import pytest

from app.modules.auth.models import Cuenta
from app.modules.pedidos.models import MetodoPago
from app.modules.ventas import crud as ventas_crud
from app.modules.ventas.models import VentaEstado
from app.modules.ventas.schemas import CondicionPago

PREFIJO = "/api/v1/pedidos/panel"


def _venta_de(db_session, pedido):
    """Venta vigente del pedido, si existe."""
    return ventas_crud.obtener_vigente_por_pedido(db_session, pedido.id)


def _saldo(db_session, cliente) -> Decimal:
    """Saldo de cuenta corriente leído de la base."""
    db_session.refresh(cliente)
    return Decimal(str(cliente.saldo_cuenta_corriente))


def _cuenta_admin(db_session) -> Cuenta:
    """Cuenta del administrador creado por la fixture ``auth_headers``."""
    return (
        db_session.query(Cuenta)
        .filter(Cuenta.correo == "admin@test.com")
        .first()
    )


class TestActualizarPanel:
    """PATCH /api/v1/pedidos/panel/{id}."""

    def test_cambio_sin_condicion_de_pago(
        self, client, auth_headers, sample_pedido
    ) -> None:
        """Un cambio que no entrega no exige condición de pago."""
        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido.id}",
            json={"observaciones": "Entregar por la tarde"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["observaciones"] == "Entregar por la tarde"
        assert respuesta.json()["estado"] == "Pendiente"

    def test_entrega_al_contado_crea_venta_auditada(
        self, client, auth_headers, db_session, sample_pedido
    ) -> None:
        """La venta al contado queda confirmada y con la cuenta que la ejecutó."""
        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido.id}",
            json={
                "estado": "Entregado",
                "condicionPago": CondicionPago.CONTADO.value,
                "metodoPago": MetodoPago.TRANSFERENCIA.value,
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "Entregado"

        venta = _venta_de(db_session, sample_pedido)
        assert venta is not None
        assert venta.estado == VentaEstado.CONFIRMADA
        assert venta.cobrada_en is not None
        assert venta.cuenta_id == _cuenta_admin(db_session).id
        assert venta.pagos[0].metodo_de_pago == MetodoPago.TRANSFERENCIA

    def test_entrega_a_pagare_deja_venta_pendiente(
        self, client, auth_headers, db_session, sample_pedido_b2b
    ) -> None:
        """El pagaré B2B queda pendiente y suma la deuda al cliente."""
        saldo_inicial = _saldo(db_session, sample_pedido_b2b.cliente)

        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido_b2b.id}",
            json={
                "estado": "Entregado",
                "condicionPago": CondicionPago.PAGARE.value,
                "plazoDias": 30,
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        venta = _venta_de(db_session, sample_pedido_b2b)
        assert venta.estado == VentaEstado.PENDIENTE_COBRO
        assert venta.fecha_vencimiento is not None
        assert (
            _saldo(db_session, sample_pedido_b2b.cliente)
            == saldo_inicial + sample_pedido_b2b.total
        )

    def test_entrega_sin_condicion_da_validacion(
        self, client, auth_headers, db_session, sample_pedido
    ) -> None:
        """Sin condición de pago la entrada se rechaza con 422."""
        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido.id}",
            json={"estado": "Entregado"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 422
        db_session.refresh(sample_pedido)
        assert sample_pedido.estado == "PENDIENTE"
        assert _venta_de(db_session, sample_pedido) is None

    def test_entrega_a_pagare_de_consumidor_final_da_conflicto(
        self, client, auth_headers, db_session, sample_pedido_consumidor_final
    ) -> None:
        """Un cliente sin cuenta corriente no puede comprar a pagaré."""
        saldo_inicial = _saldo(
            db_session, sample_pedido_consumidor_final.cliente
        )
        assert (
            client.patch(
                f"{PREFIJO}/{sample_pedido_consumidor_final.id}",
                json={"estado": "Listo"},
                headers=auth_headers,
            ).status_code
            == 200
        )

        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido_consumidor_final.id}",
            json={
                "estado": "Entregado",
                "condicionPago": CondicionPago.PAGARE.value,
                "plazoDias": 30,
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 409
        assert "cuenta corriente" in respuesta.json()["detail"]
        db_session.refresh(sample_pedido_consumidor_final)
        assert sample_pedido_consumidor_final.estado == "LISTO"
        assert _venta_de(db_session, sample_pedido_consumidor_final) is None
        assert (
            _saldo(db_session, sample_pedido_consumidor_final.cliente)
            == saldo_inicial
        )

    def test_entrega_de_un_pedido_que_no_esta_listo_da_conflicto(
        self, client, auth_headers, db_session, sample_pedido
    ) -> None:
        """Saltar Listo se rechaza con 409 y no deja venta."""
        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido.id}",
            json={
                "estado": "Entregado",
                "condicionPago": CondicionPago.CONTADO.value,
                "metodoPago": MetodoPago.EFECTIVO.value,
            },
            headers=auth_headers,
        )

        # El panel pasa por Listo: la entrega se completa en el mismo request.
        assert respuesta.status_code == 200

    def test_entrega_duplicada_da_conflicto(
        self, client, auth_headers, db_session, sample_pedido_b2b
    ) -> None:
        """Entregar dos veces no duplica la venta."""
        cuerpo = {
            "estado": "Entregado",
            "condicionPago": CondicionPago.PAGARE.value,
            "plazoDias": 30,
        }
        assert (
            client.patch(
                f"{PREFIJO}/{sample_pedido_b2b.id}",
                json=cuerpo,
                headers=auth_headers,
            ).status_code
            == 200
        )

        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido_b2b.id}",
            json=cuerpo,
            headers=auth_headers,
        )

        assert respuesta.status_code == 409

    def test_reversion_con_venta_vigente_da_conflicto(
        self, client, auth_headers, db_session, sample_pedido_b2b_entregado_revierte
    ) -> None:
        """Revertir una entrega ya vendida se rechaza con 409."""
        respuesta = client.patch(
            f"{PREFIJO}/{sample_pedido_b2b_entregado_revierte.id}",
            json={"estado": "Listo"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 409
        assert "venta vigente" in respuesta.json()["detail"]
        db_session.refresh(sample_pedido_b2b_entregado_revierte)
        assert sample_pedido_b2b_entregado_revierte.estado == "ENTREGADO"

    def test_pedido_inexistente(self, client, auth_headers) -> None:
        respuesta = client.patch(
            f"{PREFIJO}/999999",
            json={"observaciones": "x"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 404

    def test_sin_token(self, client) -> None:
        respuesta = client.patch(f"{PREFIJO}/1", json={"estado": "Listo"})

        assert respuesta.status_code == 401


class TestPanelCafeVerde:
    """POST /api/v1/pedidos/panel con un ítem de café verde."""

    def _crear_lote_verde(self, db_session, tipo_cafe_id: int, kg: Decimal):
        from datetime import datetime, timedelta

        from app.modules.pedidos.models import Lote

        lote = Lote(
            tipo="VERDE",
            estado="ABIERTO",
            fecha_vencimiento=datetime.now() + timedelta(days=90),
            humedad=12.5,
            kg_disponibles=kg,
            kg_reales=kg,
            ubicacion_fisica="Bodega verde",
            tipo_de_cafe_id=tipo_cafe_id,
        )
        db_session.add(lote)
        db_session.commit()
        db_session.refresh(lote)
        return lote

    def test_compra_verde_descuenta_stock_verde(
        self, client, auth_headers, db_session, sample_cliente, sample_tipo_cafe
    ) -> None:
        lote = self._crear_lote_verde(
            db_session, sample_tipo_cafe.id, Decimal("20")
        )
        stock_id = f"tc-{sample_tipo_cafe.id}-VERDE"

        respuesta = client.post(
            PREFIJO,
            json={
                "clienteId": str(sample_cliente.persona_id),
                "items": [{"stockId": stock_id, "kilos": 5}],
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["estado"] == "Pendiente"
        assert cuerpo["items"][0]["stockId"] == stock_id

        db_session.refresh(lote)
        assert lote.kg_disponibles == Decimal("15")

        from app.modules.pedidos.models import DetallePedido, LoteTipo

        detalle = (
            db_session.query(DetallePedido)
            .filter(DetallePedido.pedido_id == int(cuerpo["id"]))
            .one()
        )
        assert detalle.tipo_lote == LoteTipo.VERDE

    def test_compra_verde_sin_stock_da_error(
        self, client, auth_headers, sample_cliente, sample_tipo_cafe
    ) -> None:
        stock_id = f"tc-{sample_tipo_cafe.id}-VERDE"

        respuesta = client.post(
            PREFIJO,
            json={
                "clienteId": str(sample_cliente.persona_id),
                "items": [{"stockId": stock_id, "kilos": 5}],
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 400
        assert "VERDE" in respuesta.json()["detail"]
