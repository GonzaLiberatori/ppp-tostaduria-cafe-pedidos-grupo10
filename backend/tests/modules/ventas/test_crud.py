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


@pytest.fixture
def dos_ventas(db_session, pedido_entregado_b2b, pedido_entregado_consumidor):
    """Una venta a crédito y otra en efectivo, de clientes distintos."""
    primera = _registrar(db_session, pedido_entregado_b2b, MetodoPago.CREDITO)
    segunda = _registrar(db_session, pedido_entregado_consumidor, MetodoPago.EFECTIVO)
    return primera, segunda


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
