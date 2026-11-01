"""Tests de la capa de acceso a datos del módulo de ventas."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas import crud, schemas, services
from app.modules.ventas.models import VentaComercial, VentaEstado


def _registrar(db, pedido, metodo: MetodoPago, facturacion=Facturacion.TICKET):
    """Registra una venta del pedido con un único pago por su total."""
    service = services.VentaService(db)
    return service.registrar_venta(
        schemas.VentaCreate(
            pedido_id=pedido.id,
            facturacion=facturacion,
            pagos=[
                schemas.PagoCreate(
                    metodo_de_pago=metodo,
                    monto=Decimal(str(pedido.total)),
                    moneda=Moneda.ARS,
                )
            ],
        )
    )


def _registrar_pagare(db, pedido, plazo: int = 30):
    """Registra la venta a pagaré del pedido, pendiente de cobro."""
    service = services.VentaService(db)
    return service.registrar_venta(
        schemas.VentaCreate(
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
    )


def _mover_vencimiento(db, venta, fecha: datetime) -> None:
    """Fija el vencimiento para poder verificar el orden de la cobranza."""
    modelo = crud.obtener_por_id(db, venta.id)
    modelo.fecha_vencimiento = fecha
    db.commit()
    db.refresh(modelo)


def _nuevo_pedido_entregado(
    db, cliente, empleado, tipo_cafe, molienda, perfil, cantidad: str = "7"
):
    """Crea un pedido B2B nuevo y lo deja ENTREGADO sin venta.

    Se usa una cantidad distinta de la de las fixtures compartidas para que la
    clave de idempotencia no devuelva un pedido ya existente.
    """
    from app.modules.pedidos import schemas as pedidos_schemas
    from app.modules.pedidos import services as pedidos_services

    datos = pedidos_schemas.PedidoCreate(
        fecha=datetime.now(),
        metodo_de_despacho="Retiro en local",
        estado="PENDIENTE",
        cliente_persona_id=cliente.persona_id,
        empleado_persona_id=empleado.persona_id,
        detalles=[
            pedidos_schemas.DetallePedidoCreate(
                cantidad_kg=Decimal(cantidad),
                tipo_de_cafe_id=tipo_cafe.id,
                molienda_id=molienda.id,
                perfil_de_tostado_id=perfil.id,
            )
        ],
    )
    pedido = pedidos_services.PedidoService(db).crear_pedido_completo(
        datos, empleado.persona_id
    )
    pedido.estado = "ENTREGADO"
    db.commit()
    db.refresh(pedido)
    return pedido


@pytest.fixture
def dos_ventas(db_session, pedido_entregado_b2b, pedido_entregado_consumidor):
    """Una venta a crédito y otra en efectivo, de clientes distintos."""
    primera = _registrar(db_session, pedido_entregado_b2b, MetodoPago.CREDITO)
    segunda = _registrar(db_session, pedido_entregado_consumidor, MetodoPago.EFECTIVO)
    return primera, segunda


def _mover_fecha(db, venta, fecha: datetime) -> None:
    """Reubica la venta en un mes calendario distinto al actual."""
    modelo = crud.obtener_por_id(db, venta.id)
    modelo.fecha = fecha
    db.commit()
    db.refresh(modelo)


class TestLecturaBasica:
    """Búsquedas puntuales."""

    def test_obtener_por_id(self, db_session, venta_confirmada) -> None:
        venta = crud.obtener_por_id(db_session, venta_confirmada.id)
        assert venta is not None
        assert venta.id == venta_confirmada.id
        assert venta.estado == VentaEstado.CONFIRMADA

    def test_obtener_por_id_inexistente(self, db_session) -> None:
        assert crud.obtener_por_id(db_session, 999999) is None

    def test_obtener_por_comprobante(self, db_session, venta_confirmada) -> None:
        venta = crud.obtener_por_comprobante(
            db_session, venta_confirmada.numero_comprobante
        )
        assert venta is not None
        assert venta.id == venta_confirmada.id

    def test_obtener_vigente_por_pedido(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        venta = crud.obtener_vigente_por_pedido(db_session, pedido_entregado_b2b.id)
        assert venta is not None
        assert venta.id == venta_confirmada.id

    def test_obtener_vigente_ignora_anuladas(
        self, db_session, venta_confirmada, pedido_entregado_b2b
    ) -> None:
        services.VentaService(db_session).anular_venta(
            venta_confirmada.id, schemas.VentaAnulacionCreate(motivo="Error de cobro")
        )
        assert (
            crud.obtener_vigente_por_pedido(db_session, pedido_entregado_b2b.id)
            is None
        )


class TestListado:
    """Filtros y paginación del listado."""

    def test_listado_sin_filtros(self, db_session, dos_ventas) -> None:
        filas = crud.listar(db_session)
        assert len(filas) == 2

    def test_venta_de_pedido_inexistente_sigue_en_el_listado(
        self, db_session, venta_confirmada
    ) -> None:
        """Un join interno haría desaparecer la venta sin aviso."""
        huerfana = VentaComercial(
            pedido_id=999999,
            fecha=datetime.now(),
            facturacion=Facturacion.TICKET,
            estado=VentaEstado.CONFIRMADA,
            total=Decimal("100.00"),
            numero_comprobante="V-999999-999999",
            creada_en=datetime.now(),
        )
        db_session.add(huerfana)
        db_session.commit()

        filas = {fila[0].id: fila for fila in crud.listar(db_session)}

        assert set(filas) == {venta_confirmada.id, huerfana.id}
        _, persona_id, nombre, apellido = filas[huerfana.id]
        assert persona_id is None
        assert nombre is None
        assert apellido is None

    def test_orden_descendente_por_fecha(self, db_session, dos_ventas) -> None:
        filas = crud.listar(db_session)
        ids = [fila[0].id for fila in filas]
        assert ids == sorted(ids, reverse=True)

    def test_incluye_nombre_del_cliente(self, db_session, dos_ventas) -> None:
        for _, _, nombre, apellido in crud.listar(db_session):
            assert nombre
            assert apellido

    def test_filtro_por_estado(self, db_session, dos_ventas) -> None:
        services.VentaService(db_session).anular_venta(
            dos_ventas[0].id, schemas.VentaAnulacionCreate(motivo="Duplicada")
        )

        anuladas = crud.listar(db_session, estado=VentaEstado.ANULADA)
        confirmadas = crud.listar(db_session, estado=VentaEstado.CONFIRMADA)

        assert len(anuladas) == 1
        assert anuladas[0][0].id == dos_ventas[0].id
        assert len(confirmadas) == 1
        assert confirmadas[0][0].id == dos_ventas[1].id

    def test_filtro_por_cliente(
        self, db_session, dos_ventas, pedido_entregado_consumidor
    ) -> None:
        filas = crud.listar(
            db_session, cliente_persona_id=pedido_entregado_consumidor.cliente_persona_id
        )
        assert len(filas) == 1
        assert filas[0][0].id == dos_ventas[1].id

    def test_filtro_por_metodo_de_pago(self, db_session, dos_ventas) -> None:
        filas = crud.listar(db_session, metodo_de_pago=MetodoPago.EFECTIVO)
        assert len(filas) == 1
        assert filas[0][0].id == dos_ventas[1].id

    def test_filtro_por_texto_del_comprobante(self, db_session, venta_confirmada) -> None:
        filas = crud.listar(db_session, q=venta_confirmada.numero_comprobante[-6:])
        assert len(filas) == 1
        assert filas[0][0].id == venta_confirmada.id

    def test_filtro_por_texto_del_cliente(self, db_session, dos_ventas) -> None:
        filas = crud.listar(db_session, q="Consumidor")
        assert len(filas) == 1
        assert filas[0][0].id == dos_ventas[1].id

    def test_filtro_por_rango_de_fechas(self, db_session, dos_ventas) -> None:
        ayer = datetime.now() - timedelta(days=1)
        manana = datetime.now() + timedelta(days=1)

        incluidas = crud.listar(db_session, fecha_desde=ayer, fecha_hasta=manana)
        futuras = crud.listar(db_session, fecha_desde=manana)

        assert len(incluidas) == 2
        assert futuras == []

    def test_paginacion(self, db_session, dos_ventas) -> None:
        primera_pagina = crud.listar(db_session, skip=0, limit=1)
        segunda_pagina = crud.listar(db_session, skip=1, limit=1)

        assert len(primera_pagina) == 1
        assert len(segunda_pagina) == 1
        assert primera_pagina[0][0].id != segunda_pagina[0][0].id

    def test_metodos_por_venta(self, db_session, dos_ventas) -> None:
        metodos = crud.metodos_por_venta(
            db_session, [dos_ventas[0].id, dos_ventas[1].id]
        )
        assert metodos[dos_ventas[0].id] == [MetodoPago.CREDITO]
        assert metodos[dos_ventas[1].id] == [MetodoPago.EFECTIVO]

    def test_metodos_por_venta_sin_ids(self, db_session) -> None:
        assert crud.metodos_por_venta(db_session, []) == {}


class TestTotales:
    """Agregados del arqueo."""

    def test_totales_generales(self, db_session, dos_ventas) -> None:
        cantidad, total = crud.totales_generales(db_session)
        esperado = Decimal(str(dos_ventas[0].total)) + Decimal(
            str(dos_ventas[1].total)
        )
        assert cantidad == 2
        assert total == esperado

    def test_totales_generales_sin_ventas(self, db_session) -> None:
        cantidad, total = crud.totales_generales(db_session)
        assert cantidad == 0
        assert total == Decimal("0")

    def test_totales_por_metodo(self, db_session, dos_ventas) -> None:
        totales = dict(crud.totales_por_metodo(db_session))
        assert totales[MetodoPago.CREDITO] == Decimal(str(dos_ventas[0].total))
        assert totales[MetodoPago.EFECTIVO] == Decimal(str(dos_ventas[1].total))

    def test_totales_excluyen_anuladas(self, db_session, dos_ventas) -> None:
        services.VentaService(db_session).anular_venta(
            dos_ventas[0].id, schemas.VentaAnulacionCreate(motivo="Error de cobro")
        )

        cantidad, total = crud.totales_generales(db_session)
        totales = dict(crud.totales_por_metodo(db_session))

        assert cantidad == 1
        assert total == Decimal(str(dos_ventas[1].total))
        assert MetodoPago.CREDITO not in totales
        assert totales[MetodoPago.EFECTIVO] == Decimal(str(dos_ventas[1].total))

    def test_totales_por_rango_vacio(self, db_session, dos_ventas) -> None:
        manana = datetime.now() + timedelta(days=1)
        cantidad, total = crud.totales_generales(db_session, fecha_desde=manana)
        assert cantidad == 0
        assert total == Decimal("0")
        assert crud.totales_por_metodo(db_session, fecha_desde=manana) == []


class TestResumenMensual:
    """Agregado por mes calendario que alimenta la contabilidad."""

    def test_agrupa_por_mes(self, db_session, dos_ventas) -> None:
        _mover_fecha(db_session, dos_ventas[0], datetime(2026, 9, 15, 10, 30))
        _mover_fecha(db_session, dos_ventas[1], datetime(2026, 10, 20, 12, 0))

        filas = crud.resumen_por_mes(db_session)

        assert [clave for clave, _, _ in filas] == ["2026-10", "2026-09"]
        assert filas[0][1] == 1
        assert filas[0][2] == Decimal(str(dos_ventas[1].total))
        assert filas[1][1] == 1
        assert filas[1][2] == Decimal(str(dos_ventas[0].total))

    def test_suma_ventas_del_mismo_mes(self, db_session, dos_ventas) -> None:
        _mover_fecha(db_session, dos_ventas[0], datetime(2026, 10, 5, 9, 0))
        _mover_fecha(db_session, dos_ventas[1], datetime(2026, 10, 25, 18, 0))

        filas = crud.resumen_por_mes(db_session)

        assert len(filas) == 1
        clave, cantidad, total = filas[0]
        assert clave == "2026-10"
        assert cantidad == 2
        assert total == Decimal(str(dos_ventas[0].total)) + Decimal(
            str(dos_ventas[1].total)
        )

    def test_excluye_anuladas(self, db_session, dos_ventas) -> None:
        _mover_fecha(db_session, dos_ventas[0], datetime(2026, 9, 15, 10, 30))
        _mover_fecha(db_session, dos_ventas[1], datetime(2026, 10, 20, 12, 0))
        services.VentaService(db_session).anular_venta(
            dos_ventas[0].id, schemas.VentaAnulacionCreate(motivo="Error de cobro")
        )

        filas = crud.resumen_por_mes(db_session)
        totales = crud.totales_por_mes_y_metodo(db_session)

        assert [clave for clave, _, _ in filas] == ["2026-10"]
        assert {clave for clave, _, _ in totales} == {"2026-10"}
        assert all(metodo != MetodoPago.CREDITO for _, metodo, _ in totales)

    def test_rango_vacio(self, db_session, dos_ventas) -> None:
        manana = datetime.now() + timedelta(days=1)

        assert crud.resumen_por_mes(db_session, fecha_desde=manana) == []
        assert crud.totales_por_mes_y_metodo(db_session, fecha_desde=manana) == []

    def test_totales_por_mes_y_metodo(self, db_session, dos_ventas) -> None:
        _mover_fecha(db_session, dos_ventas[0], datetime(2026, 9, 15, 10, 30))
        _mover_fecha(db_session, dos_ventas[1], datetime(2026, 10, 20, 12, 0))

        totales = {
            (clave, metodo): total
            for clave, metodo, total in crud.totales_por_mes_y_metodo(db_session)
        }

        assert totales[("2026-09", MetodoPago.CREDITO)] == Decimal(
            str(dos_ventas[0].total)
        )
        assert totales[("2026-10", MetodoPago.EFECTIVO)] == Decimal(
            str(dos_ventas[1].total)
        )

    def test_pendiente_cuenta_en_facturado_y_no_en_cobrado(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        """Un pagaré está facturado pero todavía no cobrado."""
        venta = _registrar_pagare(db_session, pedido_entregado_b2b)
        _mover_fecha(db_session, venta, datetime(2026, 9, 10, 9, 0))

        filas = crud.resumen_por_mes(db_session)
        totales = crud.totales_por_mes_y_metodo(db_session)

        assert [(clave, cantidad) for clave, cantidad, _ in filas] == [
            ("2026-09", 1)
        ]
        assert filas[0][2] == Decimal(str(venta.total))
        # El pago CREDITO del pagaré no es dinero cobrado.
        assert totales == []


class TestCobranza:
    """Agregados de cobranza, medidos por el mes en que entró el dinero."""

    def test_cobro_de_mes_anterior_aparece_en_el_mes_del_cobro(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        venta = _registrar_pagare(db_session, pedido_entregado_b2b)
        _mover_fecha(db_session, venta, datetime(2026, 8, 20, 10, 0))
        services.VentaService(db_session).cobrar_venta(
            venta.id,
            schemas.VentaCobroCreate(metodo_de_pago=MetodoPago.TRANSFERENCIA),
        )

        filas = crud.cobranza_por_mes(db_session)
        mes_actual = datetime.now().strftime("%Y-%m")

        assert [clave for clave, _, _ in filas] == [mes_actual]
        assert filas[0][1] == 1
        assert filas[0][2] == Decimal(str(venta.total))

    def test_pendientes_no_entran_en_la_cobranza(
        self, db_session, pedido_entregado_b2b
    ) -> None:
        _registrar_pagare(db_session, pedido_entregado_b2b)

        assert crud.cobranza_por_mes(db_session) == []
        assert crud.totales_de_cobranza_por_metodo(db_session) == []

    def test_anuladas_quedan_afuera_de_la_cobranza(
        self, db_session, dos_ventas
    ) -> None:
        services.VentaService(db_session).anular_venta(
            dos_ventas[0].id, schemas.VentaAnulacionCreate(motivo="Error de cobro")
        )

        filas = crud.cobranza_por_mes(db_session)
        totales = {
            (clave, metodo)
            for clave, metodo, _ in crud.totales_de_cobranza_por_metodo(
                db_session
            )
        }

        assert sum(cantidad for _, cantidad, _ in filas) == 1
        assert all(metodo != MetodoPago.CREDITO for _, metodo in totales)
        assert any(metodo == MetodoPago.EFECTIVO for _, metodo in totales)

    def test_rango_sin_cobros(self, db_session, dos_ventas) -> None:
        manana = datetime.now() + timedelta(days=1)

        assert crud.cobranza_por_mes(db_session, fecha_desde=manana) == []
        assert (
            crud.totales_de_cobranza_por_metodo(db_session, fecha_desde=manana)
            == []
        )

    def test_totales_de_cobranza_por_metodo(
        self, db_session, dos_ventas
    ) -> None:
        totales = {
            (clave, metodo): total
            for clave, metodo, total in crud.totales_de_cobranza_por_metodo(
                db_session
            )
        }
        mes_actual = datetime.now().strftime("%Y-%m")

        assert totales[(mes_actual, MetodoPago.CREDITO)] == Decimal(
            str(dos_ventas[0].total)
        )
        assert totales[(mes_actual, MetodoPago.EFECTIVO)] == Decimal(
            str(dos_ventas[1].total)
        )


class TestPendientesDeCobro:
    """Consulta del saldo por cobrar."""

    def test_solo_pendientes_ordenadas_por_vencimiento(
        self,
        db_session,
        sample_pedido_b2b_entregado_revierte,
        sample_cliente_b2b,
        sample_empleado,
        sample_tipo_cafe,
        sample_molienda,
        sample_perfil_tostado,
    ) -> None:
        # El pedido ya entregado a pagaré tiene su venta pendiente; se registra
        # otra sobre un pedido nuevo para poder comparar el orden.
        nuevo = _nuevo_pedido_entregado(
            db_session,
            sample_cliente_b2b,
            sample_empleado,
            sample_tipo_cafe,
            sample_molienda,
            sample_perfil_tostado,
        )
        otra = _registrar_pagare(db_session, nuevo, plazo=90)
        pendiente_previa = crud.obtener_vigente_por_pedido(
            db_session, sample_pedido_b2b_entregado_revierte.id
        )
        _mover_vencimiento(db_session, otra, datetime(2027, 1, 15, 10, 0))
        _mover_vencimiento(
            db_session, pendiente_previa, datetime(2026, 12, 1, 10, 0)
        )

        filas = crud.pendientes_de_cobro(db_session)

        assert [venta.id for venta, *_ in filas] == [
            pendiente_previa.id,
            otra.id,
        ]
        assert all(
            venta.estado == VentaEstado.PENDIENTE_COBRO for venta, *_ in filas
        )

    def test_sin_pendientes(self, db_session, dos_ventas) -> None:
        assert crud.pendientes_de_cobro(db_session) == []

