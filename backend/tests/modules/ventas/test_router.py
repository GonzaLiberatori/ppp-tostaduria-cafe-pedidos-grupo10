"""Tests de los endpoints del módulo de ventas: contratos y RBAC."""

from decimal import Decimal

import pytest

from app.modules.pedidos import services as pedidos_services
from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas import services as ventas_services

PREFIJO = "/api/v1/ventas"


def _headers(client, correo: str, rol: str) -> dict[str, str]:
    """Registra (si hace falta) e inicia sesión con el rol pedido."""
    client.post(
        "/api/v1/auth/register",
        json={"email": correo, "password": "123456", "role": rol},
    )
    respuesta = client.post(
        "/api/v1/auth/login",
        json={"email": correo, "password": "123456"},
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _cuerpo(pedido, metodo: MetodoPago = MetodoPago.EFECTIVO) -> dict:
    """Alta de venta con un único pago por el total del pedido."""
    return {
        "pedido_id": pedido.id,
        "facturacion": Facturacion.TICKET.value,
        "pagos": [
            {
                "metodo_de_pago": metodo.value,
                "monto": str(pedido.total),
                "moneda": Moneda.ARS.value,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------


class TestAutenticacion:
    """Sin token no se accede a ningún endpoint."""

    def test_listado_sin_token(self, client) -> None:
        assert client.get(f"{PREFIJO}/").status_code == 401

    def test_registro_sin_token(self, client, pedido_entregado_b2b) -> None:
        respuesta = client.post(PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b))
        assert respuesta.status_code == 401

    def test_anulacion_sin_token(self, client, venta_confirmada) -> None:
        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular", json={"motivo": "Error"}
        )
        assert respuesta.status_code == 401


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


class TestRegistro:
    """POST /api/v1/ventas."""

    def test_administrador_registra_venta(
        self, client, auth_headers, pedido_entregado_b2b
    ) -> None:
        respuesta = client.post(
            PREFIJO + "/",
            json=_cuerpo(pedido_entregado_b2b),
            headers=auth_headers,
        )

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["estado"] == "CONFIRMADA"
        assert cuerpo["pedido_id"] == pedido_entregado_b2b.id
        assert cuerpo["numero_comprobante"].startswith("V-")
        assert cuerpo["pedido_estado"] == "ENTREGADO"
        assert len(cuerpo["pagos"]) == 1

    def test_cajero_registra_venta(
        self, client, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, "cajero@test.com", "Cajero")

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b), headers=headers
        )

        assert respuesta.status_code == 201

    def test_operario_no_puede_registrar(
        self, client, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, "operario@test.com", "Operario")

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b), headers=headers
        )

        assert respuesta.status_code == 403

    def test_cliente_no_puede_registrar(
        self, client, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, "portal@test.com", "Cliente")

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b), headers=headers
        )

        assert respuesta.status_code == 403

    def test_pedido_inexistente(
        self, client, auth_headers
    ) -> None:
        respuesta = client.post(
            PREFIJO + "/",
            json={
                "pedido_id": 999999,
                "facturacion": Facturacion.TICKET.value,
                "pagos": [
                    {
                        "metodo_de_pago": MetodoPago.EFECTIVO.value,
                        "monto": "10.00",
                    }
                ],
            },
            headers=auth_headers,
        )

        assert respuesta.status_code == 404

    def test_pedido_en_listo_da_conflicto(
        self, client, auth_headers, db_session, sample_pedido_b2b
    ) -> None:
        pedidos_services.PedidoService(db_session).cambiar_estado_pedido(
            sample_pedido_b2b.id, "LISTO"
        )

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(sample_pedido_b2b), headers=auth_headers
        )

        assert respuesta.status_code == 409

    def test_venta_duplicada_da_conflicto(
        self, client, auth_headers, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        respuesta = client.post(
            PREFIJO + "/",
            json=_cuerpo(pedido_entregado_b2b),
            headers=auth_headers,
        )

        assert respuesta.status_code == 409

    def test_comprobante_duplicado_da_conflicto(
        self, client, auth_headers, pedido_entregado_b2b, monkeypatch
    ) -> None:
        def _falla(*_args, **_kwargs):
            raise ventas_services.ComprobanteDuplicado("V-202610-000001")

        monkeypatch.setattr(
            ventas_services.VentaService, "registrar_venta", _falla
        )

        respuesta = client.post(
            PREFIJO + "/",
            json=_cuerpo(pedido_entregado_b2b),
            headers=auth_headers,
        )

        assert respuesta.status_code == 409
        assert "comprobante" in respuesta.json()["detail"]

    def test_suma_incorrecta_da_conflicto(
        self, client, auth_headers, pedido_entregado_b2b
    ) -> None:
        cuerpo = _cuerpo(pedido_entregado_b2b)
        cuerpo["pagos"][0]["monto"] = "1.00"

        respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=auth_headers)

        assert respuesta.status_code == 409
        assert "diferencia" in respuesta.json()["detail"]

    def test_sin_pagos_da_validacion(
        self, client, auth_headers, pedido_entregado_b2b
    ) -> None:
        cuerpo = _cuerpo(pedido_entregado_b2b)
        cuerpo["pagos"] = []

        respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=auth_headers)

        assert respuesta.status_code == 422

    def test_monto_invalido_da_validacion(
        self, client, auth_headers, pedido_entregado_b2b
    ) -> None:
        cuerpo = _cuerpo(pedido_entregado_b2b)
        cuerpo["pagos"][0]["monto"] = "0"

        respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=auth_headers)

        assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


class TestConsultas:
    """Listado, resumen y detalle."""

    def test_operario_puede_listar(self, client, venta_confirmada) -> None:
        headers = _headers(client, "operario@test.com", "Operario")

        respuesta = client.get(f"{PREFIJO}/", headers=headers)

        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1

    def test_cliente_no_puede_listar(self, client, venta_confirmada) -> None:
        headers = _headers(client, "portal@test.com", "Cliente")

        respuesta = client.get(f"{PREFIJO}/", headers=headers)

        assert respuesta.status_code == 403

    def test_listado_con_filtro_de_metodo(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.get(
            f"{PREFIJO}/?metodo_de_pago=CREDITO", headers=auth_headers
        )
        vacio = client.get(
            f"{PREFIJO}/?metodo_de_pago=EFECTIVO", headers=auth_headers
        )

        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1
        assert vacio.json() == []

    def test_resumen(self, client, auth_headers, venta_confirmada) -> None:
        respuesta = client.get(f"{PREFIJO}/resumen", headers=auth_headers)

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["cantidad_ventas"] == 1
        assert Decimal(cuerpo["total_facturado"]) == Decimal(
            str(venta_confirmada.total)
        )
        assert cuerpo["totales_por_metodo"][0]["metodo_de_pago"] == "CREDITO"

    def test_detalle_por_id(self, client, auth_headers, venta_confirmada) -> None:
        respuesta = client.get(
            f"{PREFIJO}/{venta_confirmada.id}", headers=auth_headers
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == venta_confirmada.id

    def test_detalle_por_id_inexistente(
        self, client, auth_headers
    ) -> None:
        respuesta = client.get(f"{PREFIJO}/999999", headers=auth_headers)
        assert respuesta.status_code == 404

    def test_detalle_por_comprobante(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.get(
            f"{PREFIJO}/comprobante/{venta_confirmada.numero_comprobante}",
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == venta_confirmada.id

    def test_comprobante_inexistente(self, client, auth_headers) -> None:
        respuesta = client.get(
            f"{PREFIJO}/comprobante/V-000000-000000", headers=auth_headers
        )
        assert respuesta.status_code == 404


# ---------------------------------------------------------------------------
# Anulación
# ---------------------------------------------------------------------------


class TestAnulacion:
    """POST /api/v1/ventas/{id}/anular."""

    def test_administrador_anula(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular",
            json={"motivo": "Cobro duplicado"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["estado"] == "ANULADA"
        assert cuerpo["anulada_en"] is not None
        assert cuerpo["pedido_id"] == venta_confirmada.pedido_id
        assert cuerpo["historial"][-1]["motivo"] == "Cobro duplicado"

    def test_cajero_no_puede_anular(
        self, client, venta_confirmada
    ) -> None:
        headers = _headers(client, "cajero@test.com", "Cajero")

        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular",
            json={"motivo": "Error"},
            headers=headers,
        )

        assert respuesta.status_code == 403

    def test_anulacion_sin_motivo_da_validacion(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular",
            json={"motivo": ""},
            headers=auth_headers,
        )

        assert respuesta.status_code == 422

    def test_doble_anulacion_da_conflicto(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular",
            json={"motivo": "Error"},
            headers=auth_headers,
        )

        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/anular",
            json={"motivo": "Otra vez"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 409

    def test_anular_inexistente(self, client, auth_headers) -> None:
        respuesta = client.post(
            f"{PREFIJO}/999999/anular",
            json={"motivo": "Error"},
            headers=auth_headers,
        )

        assert respuesta.status_code == 404
