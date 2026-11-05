"""Tests de las reglas de negocio del tueste.

Los casos críticos se prueban contra ``services.registrar_tueste``: conversión
correcta, FIFO entre lotes, rollback por stock insuficiente y tipo inexistente.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.inventario.models import Lote, LoteEstado, LoteTipo
from app.modules.produccion import services
from app.modules.produccion.models import ConsumoTueste, OrdenTueste
from app.modules.produccion.schemas import TuesteCreate


def _crear_lote_verde(
    db,
    tipo_de_cafe_id: int,
    kg: str,
    dias_para_vencer: int,
    *,
    estado: LoteEstado = LoteEstado.ABIERTO,
    ubicacion: str = "Bodega verde",
) -> Lote:
    """Alta un lote verde con stock y vencimiento controlados por el test."""
    lote = Lote(
        tipo=LoteTipo.VERDE,
        estado=estado,
        fecha_vencimiento=datetime.now() + timedelta(days=dias_para_vencer),
        humedad=Decimal("11.50"),
        kg_disponibles=Decimal(kg),
        kg_reales=Decimal(kg),
        ubicacion_fisica=ubicacion,
        tipo_de_cafe_id=tipo_de_cafe_id,
    )
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


def test_registrar_tueste_convierte_gramos_y_crea_lote_tostado(
    db_session, sample_tipo_cafe
):
    lote_verde = _crear_lote_verde(
        db_session, sample_tipo_cafe.id, "10.000", 30
    )

    resultado = services.registrar_tueste(
        db_session,
        TuesteCreate(
            gramos_verde=5000,
            gramos_tostado=4000,
            tipo_de_cafe_id=sample_tipo_cafe.id,
        ),
    )

    assert resultado.id > 0
    assert resultado.tipo_de_cafe_id == sample_tipo_cafe.id
    assert resultado.kg_gastados == Decimal("5.000")
    assert resultado.kg_obtenidos == Decimal("4.000")
    assert resultado.gramos_gastados == 5000
    assert resultado.gramos_obtenidos == 4000
    assert resultado.merma_gramos == 1000
    assert resultado.merma_porcentaje == Decimal("20.00")

    db_session.refresh(lote_verde)
    assert lote_verde.kg_disponibles == Decimal("5.000")
    assert lote_verde.estado == LoteEstado.ABIERTO

    lote_tostado = db_session.get(Lote, resultado.lote_tostado_id)
    assert lote_tostado is not None
    assert lote_tostado.tipo == LoteTipo.TOSTADO
    assert lote_tostado.estado == LoteEstado.ABIERTO
    assert lote_tostado.kg_reales == Decimal("4.000")
    assert lote_tostado.kg_disponibles == Decimal("4.000")
    assert lote_tostado.tipo_de_cafe_id == sample_tipo_cafe.id
    assert lote_tostado.orden_tueste_id == resultado.id

    assert len(resultado.consumos) == 1
    assert resultado.consumos[0].lote_id == lote_verde.id
    assert resultado.consumos[0].kg_consumidos == Decimal("5.000")
    assert resultado.consumos[0].gramos_consumidos == 5000


def test_registrar_tueste_consume_lotes_en_orden_fifo(
    db_session, sample_tipo_cafe
):
    lote_viejo = _crear_lote_verde(
        db_session, sample_tipo_cafe.id, "2.000", 10, ubicacion="Bodega A"
    )
    lote_nuevo = _crear_lote_verde(
        db_session, sample_tipo_cafe.id, "5.000", 60, ubicacion="Bodega B"
    )

    resultado = services.registrar_tueste(
        db_session,
        TuesteCreate(
            gramos_verde=4000,
            gramos_tostado=3200,
            tipo_de_cafe_id=sample_tipo_cafe.id,
        ),
    )

    db_session.refresh(lote_viejo)
    db_session.refresh(lote_nuevo)

    assert lote_viejo.kg_disponibles == Decimal("0.000")
    assert lote_viejo.estado == LoteEstado.CERRADO
    assert lote_nuevo.kg_disponibles == Decimal("3.000")
    assert lote_nuevo.estado == LoteEstado.ABIERTO

    assert [consumo.lote_id for consumo in resultado.consumos] == [
        lote_viejo.id,
        lote_nuevo.id,
    ]
    assert [consumo.kg_consumidos for consumo in resultado.consumos] == [
        Decimal("2.000"),
        Decimal("2.000"),
    ]


def test_registrar_tueste_con_stock_insuficiente_no_deja_cambios(
    db_session, sample_tipo_cafe
):
    lote_verde = _crear_lote_verde(
        db_session, sample_tipo_cafe.id, "1.000", 30
    )

    with pytest.raises(services.StockVerdeInsuficienteParaTueste):
        services.registrar_tueste(
            db_session,
            TuesteCreate(
                gramos_verde=2000,
                gramos_tostado=1600,
                tipo_de_cafe_id=sample_tipo_cafe.id,
            ),
        )

    assert db_session.query(OrdenTueste).count() == 0
    assert db_session.query(ConsumoTueste).count() == 0
    assert db_session.query(Lote).count() == 1

    db_session.refresh(lote_verde)
    assert lote_verde.kg_disponibles == Decimal("1.000")
    assert lote_verde.estado == LoteEstado.ABIERTO


def test_registrar_tueste_con_tipo_inexistente_no_deja_cambios(db_session):
    with pytest.raises(services.TipoDeCafeNoEncontradoParaTueste):
        services.registrar_tueste(
            db_session,
            TuesteCreate(
                gramos_verde=1000,
                gramos_tostado=800,
                tipo_de_cafe_id=999,
            ),
        )

    assert db_session.query(OrdenTueste).count() == 0
    assert db_session.query(ConsumoTueste).count() == 0
    assert db_session.query(Lote).count() == 0


def test_tueste_no_admite_mas_tostado_que_verde():
    with pytest.raises(ValidationError):
        TuesteCreate(
            gramos_verde=1000,
            gramos_tostado=1001,
            tipo_de_cafe_id=1,
        )


def test_listar_y_obtener_tueste_incluyen_trazabilidad(
    db_session, sample_tipo_cafe
):
    _crear_lote_verde(db_session, sample_tipo_cafe.id, "5.000", 30)

    creado = services.registrar_tueste(
        db_session,
        TuesteCreate(
            gramos_verde=2500,
            gramos_tostado=2000,
            tipo_de_cafe_id=sample_tipo_cafe.id,
        ),
    )

    listado = services.listar_tuestes(db_session)
    assert len(listado) == 1
    assert listado[0].id == creado.id
    assert listado[0].lote_tostado_id == creado.lote_tostado_id
    assert len(listado[0].consumos) == 1

    obtenido = services.obtener_tueste(db_session, creado.id)
    assert obtenido.id == creado.id
    assert obtenido.gramos_gastados == 2500
    assert obtenido.gramos_obtenidos == 2000

    with pytest.raises(services.TuesteNoEncontrado):
        services.obtener_tueste(db_session, 999)
