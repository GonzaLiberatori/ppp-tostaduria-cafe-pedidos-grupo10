"""Tests de los endpoints del módulo de ventas: contratos y RBAC."""

from decimal import Decimal

import pytest

from app.modules.pedidos import services as pedidos_services
from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas import schemas as ventas_schemas
from app.modules.ventas import services as ventas_services

PREFIJO = "/api/v1/ventas"


def _headers(client, db_session, correo: str, rol: str) -> dict[str, str]:
    """Crea la cuenta en la base e inicia sesión con el rol pedido.

    El registro público solo permite el rol ``Cliente``; los roles internos se
    insertan directamente para poder probar el RBAC.
    """
    from app.core.security import get_password_hash
    from app.modules.auth.models import Cuenta, UserRole

    cuenta = Cuenta(
        correo=correo,
        clave=get_password_hash("123456"),
        rol=UserRole(rol),
    )
    db_session.add(cuenta)
    db_session.commit()

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


def _cuerpo_pagare(pedido, plazo: int = 30) -> dict:
    """Alta de venta a pagaré con el pago a crédito que representa la deuda."""
    return {
        "pedido_id": pedido.id,
        "facturacion": Facturacion.FACTURA_A.value,
        "condicion_pago": ventas_schemas.CondicionPago.PAGARE.value,
        "plazo_dias": plazo,
        "pagos": [
            {
                "metodo_de_pago": MetodoPago.CREDITO.value,
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

    def test_resumen_mensual_sin_token(self, client) -> None:
        assert client.get(f"{PREFIJO}/resumen-mensual").status_code == 401

    def test_cobranza_mensual_sin_token(self, client) -> None:
        assert client.get(f"{PREFIJO}/cobranza-mensual").status_code == 401

    def test_por_cobrar_sin_token(self, client) -> None:
        assert client.get(f"{PREFIJO}/por-cobrar").status_code == 401


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
        self, client, db_session, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, db_session, "cajero@test.com", "Cajero")

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b), headers=headers
        )

        assert respuesta.status_code == 201

    def test_operario_no_puede_registrar(
        self, client, db_session, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, db_session, "operario@test.com", "Operario")

        respuesta = client.post(
            PREFIJO + "/", json=_cuerpo(pedido_entregado_b2b), headers=headers
        )

        assert respuesta.status_code == 403

    def test_cliente_no_puede_registrar(
        self, client, db_session, pedido_entregado_b2b
    ) -> None:
        headers = _headers(client, db_session, "portal@test.com", "Cliente")

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

    def test_operario_puede_listar(self, client, db_session, venta_confirmada) -> None:
        headers = _headers(client, db_session, "operario@test.com", "Operario")

        respuesta = client.get(f"{PREFIJO}/", headers=headers)

        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1

    def test_cliente_no_puede_listar(self, client, db_session, venta_confirmada) -> None:
        headers = _headers(client, db_session, "portal@test.com", "Cliente")

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

    def test_resumen_mensual(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.get(
            f"{PREFIJO}/resumen-mensual", headers=auth_headers
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert len(cuerpo) == 1
        assert cuerpo[0]["mes"] == f"{venta_confirmada.fecha:%Y-%m}"
        assert cuerpo[0]["cantidad_ventas"] == 1
        assert Decimal(cuerpo[0]["total_facturado"]) == Decimal(
            str(venta_confirmada.total)
        )
        assert cuerpo[0]["totales_por_metodo"][0]["metodo_de_pago"] == "CREDITO"

    def test_cajero_consulta_resumen_mensual(
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "cajero@test.com", "Cajero")

        respuesta = client.get(
            f"{PREFIJO}/resumen-mensual", headers=headers
        )

        assert respuesta.status_code == 200

    def test_operario_consulta_resumen_mensual(
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "operario@test.com", "Operario")

        respuesta = client.get(
            f"{PREFIJO}/resumen-mensual", headers=headers
        )

        assert respuesta.status_code == 200

    def test_cliente_no_puede_consultar_resumen_mensual(
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "portal@test.com", "Cliente")

        respuesta = client.get(
            f"{PREFIJO}/resumen-mensual", headers=headers
        )

        assert respuesta.status_code == 403

    def test_resumen_mensual_publicado_en_openapi(self, client) -> None:
        respuesta = client.get("/openapi.json")

        assert respuesta.status_code == 200
        assert f"{PREFIJO}/resumen-mensual" in respuesta.json()["paths"]

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
# Cobranza
# ---------------------------------------------------------------------------


class TestCobranza:
    """GET /api/v1/ventas/cobranza-mensual y /por-cobrar."""

    def test_por_cobrar_lista_la_venta_pendiente(
        self, client, auth_headers, db_session, pedido_entregado_b2b
    ) -> None:
        venta = _venta_pendiente(db_session, pedido_entregado_b2b)

        respuesta = client.get(f"{PREFIJO}/por-cobrar", headers=auth_headers)

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert len(cuerpo["items"]) == 1
        assert cuerpo["items"][0]["venta_id"] == venta.id
        assert Decimal(cuerpo["total_por_cobrar"]) == Decimal(str(venta.total))
        assert cuerpo["cantidad_vencidas"] == 0

    def test_cobranza_mensual_lista_el_cobro(
        self, client, auth_headers, db_session, pedido_entregado_b2b
    ) -> None:
        venta = _venta_pendiente(db_session, pedido_entregado_b2b)
        assert (
            client.post(
                f"{PREFIJO}/{venta.id}/cobrar",
                json={"metodo_de_pago": MetodoPago.TRANSFERENCIA.value},
                headers=auth_headers,
            ).status_code
            == 200
        )

        respuesta = client.get(f"{PREFIJO}/cobranza-mensual", headers=auth_headers)

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert len(cuerpo) == 1
        assert cuerpo[0]["mes"] == f"{venta.fecha:%Y-%m}"
        assert cuerpo[0]["cantidad_cobros"] == 1
        assert Decimal(cuerpo[0]["total_cobrado"]) == Decimal(str(venta.total))
        assert (
            cuerpo[0]["totales_por_metodo"][0]["metodo_de_pago"]
            == MetodoPago.TRANSFERENCIA.value
        )

    def test_operario_puede_consultar_cobranza_y_por_cobrar(
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "operario@test.com", "Operario")

        assert (
            client.get(f"{PREFIJO}/cobranza-mensual", headers=headers).status_code
            == 200
        )
        assert (
            client.get(f"{PREFIJO}/por-cobrar", headers=headers).status_code
            == 200
        )

    def test_cliente_no_puede_consultar_cobranza_ni_por_cobrar(
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "portal@test.com", "Cliente")

        assert (
            client.get(f"{PREFIJO}/cobranza-mensual", headers=headers).status_code
            == 403
        )
        assert (
            client.get(f"{PREFIJO}/por-cobrar", headers=headers).status_code
            == 403
        )

    def test_endpoints_publicados_en_openapi(self, client) -> None:
        rutas = client.get("/openapi.json").json()["paths"]

        assert f"{PREFIJO}/cobranza-mensual" in rutas
        assert f"{PREFIJO}/por-cobrar" in rutas


# ---------------------------------------------------------------------------
# Cobro
# ---------------------------------------------------------------------------


def _venta_pendiente(db_session, pedido):
    """Crea una venta a pagaré a 30 días y confirma la transacción."""
    venta = ventas_services.registrar_venta_de_entrega(
        db_session,
        pedido,
        ventas_schemas.CondicionPago.PAGARE,
        plazo_dias=30,
    )
    db_session.commit()
    return venta


class TestCobro:
    """POST /api/v1/ventas/{id}/cobrar."""

    def test_administrador_cobra_una_venta_pendiente(
        self, client, auth_headers, db_session, pedido_entregado_b2b
    ) -> None:
        venta = _venta_pendiente(db_session, pedido_entregado_b2b)

        respuesta = client.post(
            f"{PREFIJO}/{venta.id}/cobrar",
            json={"metodo_de_pago": MetodoPago.TRANSFERENCIA.value},
            headers=auth_headers,
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["estado"] == "CONFIRMADA"
        assert cuerpo["cobrada_en"] is not None
        assert cuerpo["pagos"][0]["metodo_de_pago"] == MetodoPago.TRANSFERENCIA.value

    def test_cobrar_una_venta_ya_cobrada_da_conflicto(
        self, client, auth_headers, venta_confirmada
    ) -> None:
        respuesta = client.post(
            f"{PREFIJO}/{venta_confirmada.id}/cobrar",
            json={"metodo_de_pago": MetodoPago.EFECTIVO.value},
            headers=auth_headers,
        )

        assert respuesta.status_code == 409
        assert "PENDIENTE_COBRO" in respuesta.json()["detail"]

    def test_cobrar_una_venta_inexistente(
        self, client, auth_headers
    ) -> None:
        respuesta = client.post(
            f"{PREFIJO}/999999/cobrar",
            json={"metodo_de_pago": MetodoPago.EFECTIVO.value},
            headers=auth_headers,
        )

        assert respuesta.status_code == 404

    def test_cobro_sin_metodo_da_validacion(
        self, client, auth_headers, db_session, pedido_entregado_b2b
    ) -> None:
        venta = _venta_pendiente(db_session, pedido_entregado_b2b)

        respuesta = client.post(
            f"{PREFIJO}/{venta.id}/cobrar", json={}, headers=auth_headers
        )

        assert respuesta.status_code == 422

    def test_pagare_a_cliente_no_mayorista_da_conflicto(
        self, client, auth_headers, pedido_entregado_consumidor
    ) -> None:
        cuerpo = _cuerpo(pedido_entregado_consumidor)
        cuerpo["condicion_pago"] = ventas_schemas.CondicionPago.PAGARE.value
        cuerpo["plazo_dias"] = 30

        respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=auth_headers)

        assert respuesta.status_code == 409
        assert "cuenta corriente" in respuesta.json()["detail"]

    def test_plazo_fuera_de_los_admitidos_da_validacion(
        self, client, auth_headers, pedido_entregado_b2b
    ) -> None:
        cuerpo = _cuerpo(pedido_entregado_b2b)
        cuerpo["condicion_pago"] = ventas_schemas.CondicionPago.PAGARE.value
        cuerpo["plazo_dias"] = 45

        respuesta = client.post(PREFIJO + "/", json=cuerpo, headers=auth_headers)

        assert respuesta.status_code == 422
        assert "30, 60 o 90" in str(respuesta.json()["detail"])

    def test_plazo_invalido_del_servicio_da_validacion(
        self, client, auth_headers, pedido_entregado_b2b, monkeypatch
    ) -> None:
        """El plazo que valida el servicio (entrega desde pedidos) también es 422."""

        def _falla(*_args, **_kwargs):
            raise ventas_services.PlazoInvalido(45)

        monkeypatch.setattr(
            ventas_services.VentaService, "registrar_venta", _falla
        )

        respuesta = client.post(
            PREFIJO + "/",
            json=_cuerpo(pedido_entregado_b2b),
            headers=auth_headers,
        )

        assert respuesta.status_code == 422
        assert "30, 60, 90" in respuesta.json()["detail"]


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
        self, client, db_session, venta_confirmada
    ) -> None:
        headers = _headers(client, db_session, "cajero@test.com", "Cajero")

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
