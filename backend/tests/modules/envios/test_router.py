"""Tests del router HTTP de envíos programados con autenticación y RBAC."""

from datetime import date
from decimal import Decimal

from app.modules.envios import models

FECHA_LUNES = date(2026, 11, 2)


class TestSuscripcionesRouter:
    def test_admin_crea_suscripcion_b2b(
        self, client, headers_admin, sample_cliente_b2b, sample_tipo_cafe
    ):
        resp = client.post(
            "/api/v1/envios/suscripciones",
            headers=headers_admin,
            json={
                "clienteId": str(sample_cliente_b2b.persona_id),
                "tipoDeCafeId": sample_tipo_cafe.id,
                "cantidadKg": "3",
                "diaSemana": FECHA_LUNES.weekday(),
                "plazoDias": 30,
                "fechaInicio": FECHA_LUNES.isoformat(),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["clienteId"] == str(sample_cliente_b2b.persona_id)
        assert data["activa"] is True

    def test_cliente_crea_su_propia_suscripcion(
        self, client, headers_cliente_b2b, sample_tipo_cafe
    ):
        resp = client.post(
            "/api/v1/envios/suscripciones",
            headers=headers_cliente_b2b,
            json={
                "clienteId": "999",
                "tipoDeCafeId": sample_tipo_cafe.id,
                "cantidadKg": "4",
                "diaSemana": 1,
                "plazoDias": 60,
                "fechaInicio": FECHA_LUNES.isoformat(),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["clienteId"] != "999"

    def test_cliente_no_puede_crear_para_otro_cliente(
        self,
        client,
        headers_cliente_b2b,
        sample_cliente_b2b,
        otro_cliente_b2b,
        sample_tipo_cafe,
        db_session,
    ):
        # El router reemplaza el ``clienteId`` recibido por el del token: la
        # suscripción queda a nombre del autenticado y nunca del cliente ajeno.
        resp = client.post(
            "/api/v1/envios/suscripciones",
            headers=headers_cliente_b2b,
            json={
                "clienteId": str(otro_cliente_b2b.persona_id),
                "tipoDeCafeId": sample_tipo_cafe.id,
                "cantidadKg": "4",
                "diaSemana": 1,
                "plazoDias": 60,
                "fechaInicio": FECHA_LUNES.isoformat(),
            },
        )
        assert resp.status_code == 201

        from app.modules.envios.models import SuscripcionEnvio

        suscripcion = db_session.query(SuscripcionEnvio).one()
        assert suscripcion.cliente_id == sample_cliente_b2b.persona_id
        assert suscripcion.cliente_id != otro_cliente_b2b.persona_id

    def test_cliente_solo_ve_sus_propias_suscripciones(
        self,
        client,
        headers_cliente_b2b,
        suscripcion_lunes,
        otro_cliente_b2b,
        sample_tipo_cafe,
        db_session,
    ):
        from app.modules.envios import services as envios_services
        from app.modules.envios import schemas as envios_schemas

        envios_services.EnvioService(db_session).crear_suscripcion(
            envios_schemas.SuscripcionCreate(
                clienteId=str(otro_cliente_b2b.persona_id),
                tipoDeCafeId=sample_tipo_cafe.id,
                cantidadKg=Decimal("10"),
                diaSemana=2,
                plazoDias=30,
                fechaInicio=FECHA_LUNES,
            )
        )

        resp = client.get("/api/v1/envios/suscripciones", headers=headers_cliente_b2b)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == suscripcion_lunes.id

    def test_consumidor_final_no_puede_crear_suscripcion(
        self, client, headers_cliente_consumidor, sample_tipo_cafe
    ):
        resp = client.post(
            "/api/v1/envios/suscripciones",
            headers=headers_cliente_consumidor,
            json={
                "clienteId": "1",
                "tipoDeCafeId": sample_tipo_cafe.id,
                "cantidadKg": "3",
                "diaSemana": FECHA_LUNES.weekday(),
                "plazoDias": 30,
                "fechaInicio": FECHA_LUNES.isoformat(),
            },
        )
        assert resp.status_code == 400


class TestGeneracionRouter:
    def test_generar_requiere_permisos_de_gestion(
        self, client, headers_cliente_b2b, suscripcion_lunes
    ):
        resp = client.post(
            "/api/v1/envios/generar", headers=headers_cliente_b2b
        )
        assert resp.status_code == 403

    def test_generar_crea_pedido_y_venta_a_pagare(
        self, client, headers_admin, suscripcion_lunes, sample_lote
    ):
        resp = client.post(
            f"/api/v1/envios/generar?fecha={FECHA_LUNES.isoformat()}",
            headers=headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generadas"] == 1
        assert data["detalle"][0]["estado"] == "GENERADA"
        assert data["detalle"][0]["pedidoId"] is not None


class TestHojaDeRutaRouter:
    def test_hoja_de_ruta_requiere_logistica(
        self, client, headers_cliente_b2b, suscripcion_lunes
    ):
        resp = client.get("/api/v1/envios/hoja-de-ruta", headers=headers_cliente_b2b)
        assert resp.status_code == 403

    def test_hoja_de_ruta_para_admin(
        self, client, headers_admin, suscripcion_lunes, sample_lote
    ):
        client.post(
            f"/api/v1/envios/generar?fecha={FECHA_LUNES.isoformat()}",
            headers=headers_admin,
        )
        resp = client.get(
            f"/api/v1/envios/hoja-de-ruta?fecha={FECHA_LUNES.isoformat()}",
            headers=headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["condicionPago"] == "PAGARE"
        assert len(data[0]["items"]) == 1


class TestEntregasRouter:
    def test_listado_de_entregas_filtrado_por_cliente(
        self,
        client,
        headers_admin,
        suscripcion_lunes,
        sample_cliente_b2b,
        sample_lote,
    ):
        client.post(
            f"/api/v1/envios/generar?fecha={FECHA_LUNES.isoformat()}",
            headers=headers_admin,
        )
        resp = client.get(
            f"/api/v1/envios/entregas?clienteId={sample_cliente_b2b.persona_id}",
            headers=headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["estado"] == models.EstadoEntrega.GENERADA.value
        assert data[0]["pedidoId"] is not None
