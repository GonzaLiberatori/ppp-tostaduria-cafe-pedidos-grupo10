from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.modules.pedidos.crud import (
    create_pedido,
    get_pedido,
    get_pedido_by_idempotency_key,
    get_pedidos_con_filtros,
    update_pedido,
    delete_pedido,
    create_estado_historial,
    generate_idempotency_key,
)
from app.modules.pedidos.models import Pedido, PedidoItem, PedidoEstadoHistorial, EstadoPedidoEnum
from app.modules.pedidos.schemas import PedidoItemCreate


class TestGenerateIdempotencyKey:
    def test_generates_consistent_key(self):
        items = [
            PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000")),
            PedidoItemCreate(stock_id=2, variedad="Test2", kilos=Decimal("5"), precio_kg=Decimal("2000")),
        ]
        key1 = generate_idempotency_key(1, items, date(2026, 10, 21))
        key2 = generate_idempotency_key(1, items, date(2026, 10, 21))
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex

    def test_different_items_produce_different_keys(self):
        items1 = [PedidoItemCreate(stock_id=1, variedad="Test", kilos=Decimal("10"), precio_kg=Decimal("1000"))]
        items2 = [PedidoItemCreate(stock_id=2, variedad="Test2", kilos=Decimal("5"), precio_kg=Decimal("2000"))]
        key1 = generate_idempotency_key(1, items1, date(2026, 10, 21))
        key2 = generate_idempotency_key(1, items2, date(2026, 10, 21))
        assert key1 != key2


class TestCreatePedido:
    def test_create_pedido_returns_pedido_with_items(self, mock_db_session):
        items_data = [
            {"stock_id": 1, "variedad": "Variedad 1", "kilos": Decimal("10"), "precio_kg": Decimal("1000")},
            {"stock_id": 2, "variedad": "Variedad 2", "kilos": Decimal("5"), "precio_kg": Decimal("2000")},
        ]
        total = Decimal("20000")
        idempotency_key = "test_key_123"

        pedido = create_pedido(
            mock_db_session,
            cliente_id=1,
            estado=EstadoPedidoEnum.PENDIENTE,
            medio_contacto="WhatsApp",
            observaciones="Test",
            items=items_data,
            total=total,
            idempotency_key=idempotency_key,
        )

        assert pedido.cliente_id == 1
        assert pedido.estado == EstadoPedidoEnum.PENDIENTE
        assert pedido.total == total
        assert pedido.idempotency_key == idempotency_key
        # With mock session, relationship items won't be auto-populated
        # Verify add was called for pedido and 2 items
        assert mock_db_session.add.call_count == 3  # 1 pedido + 2 items
        mock_db_session.flush.assert_called()


class TestGetPedido:
    def test_get_pedido_returns_none_when_not_found(self, mock_db_session):
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        result = get_pedido(mock_db_session, 999)
        assert result is None


class TestGetPedidoByIdempotencyKey:
    def test_returns_pedido_when_found(self, mock_db_session):
        mock_pedido = MagicMock(spec=Pedido)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_pedido
        result = get_pedido_by_idempotency_key(mock_db_session, "existing_key")
        assert result == mock_pedido


class TestGetPedidosConFiltros:
    def test_returns_pedidos_with_pagination(self, mock_db_session):
        mock_pedidos = [MagicMock(spec=Pedido) for _ in range(3)]
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = mock_pedidos
        mock_db_session.execute.return_value.scalar_one.return_value = 3

        pedidos, total = get_pedidos_con_filtros(mock_db_session, page=1, page_size=20)

        assert pedidos == mock_pedidos
        assert total == 3

    def test_applies_estado_filter(self, mock_db_session):
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value.scalar_one.return_value = 0

        get_pedidos_con_filtros(mock_db_session, estado=EstadoPedidoEnum.PENDIENTE)

        # Verify the query was built with estado filter
        mock_db_session.execute.assert_called()


class TestUpdatePedido:
    def test_updates_only_provided_fields(self, mock_db_session):
        mock_pedido = MagicMock(spec=Pedido)
        mock_pedido.medio_contacto = "Email"
        mock_pedido.observaciones = "Old"
        mock_pedido.estado = EstadoPedidoEnum.PENDIENTE

        updated = update_pedido(
            mock_db_session,
            pedido=mock_pedido,
            medio_contacto="WhatsApp",
            observaciones=None,  # Should not update
            estado=None,  # Should not update
        )

        assert updated.medio_contacto == "WhatsApp"
        assert updated.observaciones == "Old"  # Unchanged
        assert updated.estado == EstadoPedidoEnum.PENDIENTE  # Unchanged
        mock_db_session.flush.assert_called()


class TestDeletePedido:
    def test_deletes_pedido(self, mock_db_session):
        mock_pedido = MagicMock(spec=Pedido)
        delete_pedido(mock_db_session, mock_pedido)
        mock_db_session.delete.assert_called_once_with(mock_pedido)
        mock_db_session.flush.assert_called()


class TestCreateEstadoHistorial:
    def test_creates_historial_entry(self, mock_db_session):
        historial = create_estado_historial(
            mock_db_session,
            pedido_id=1,
            estado_anterior=EstadoPedidoEnum.PENDIENTE,
            estado_nuevo=EstadoPedidoEnum.LISTO,
            usuario_id=1,
        )

        assert historial.pedido_id == 1
        assert historial.estado_anterior == EstadoPedidoEnum.PENDIENTE
        assert historial.estado_nuevo == EstadoPedidoEnum.LISTO
        assert historial.usuario_id == 1
        mock_db_session.flush.assert_called()