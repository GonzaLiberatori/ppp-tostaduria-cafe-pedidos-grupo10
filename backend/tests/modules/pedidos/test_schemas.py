"""Tests de validación de los schemas del panel de pedidos.

El contrato de la entrega vive en ``PedidoPanelUpdate``: los tres campos de pago
son opcionales para que un ``PATCH`` que no entrega siga siendo válido, pero al
pasar a ``Entregado`` tienen que venir completos.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.modules.pedidos.models import MetodoPago
from app.modules.pedidos.schemas import PedidoPanelUpdate
from app.modules.ventas.schemas import CondicionPago


class TestPedidoPanelUpdateSinEntrega:
    """Un PATCH que no entrega no necesita condición de pago."""

    def test_solo_observaciones_es_valido(self) -> None:
        datos = PedidoPanelUpdate(observaciones="Entregar por la tarde")

        assert datos.observaciones == "Entregar por la tarde"
        assert datos.condicionPago is None
        assert datos.metodoPago is None
        assert datos.plazoDias is None

    def test_cambio_a_listo_sin_condicion_es_valido(self) -> None:
        datos = PedidoPanelUpdate(estado="Listo")

        assert datos.estado == "Listo"
        assert datos.condicionPago is None

    def test_campos_desconocidos_se_ignoran(self) -> None:
        datos = PedidoPanelUpdate(estado="Listo", total=Decimal("10"))

        assert not hasattr(datos, "total")


class TestPedidoPanelUpdateEntrega:
    """La entrega exige la condición completa."""

    def test_entrega_al_contado_con_metodo(self) -> None:
        datos = PedidoPanelUpdate(
            estado="Entregado",
            condicionPago=CondicionPago.CONTADO,
            metodoPago=MetodoPago.TRANSFERENCIA,
        )

        assert datos.condicionPago is CondicionPago.CONTADO
        assert datos.metodoPago is MetodoPago.TRANSFERENCIA

    def test_entrega_a_pagare_con_plazo(self) -> None:
        datos = PedidoPanelUpdate(
            estado="Entregado",
            condicionPago=CondicionPago.PAGARE,
            plazoDias=60,
        )

        assert datos.condicionPago is CondicionPago.PAGARE
        assert datos.plazoDias == 60

    def test_entrega_sin_condicion_es_invalida(self) -> None:
        with pytest.raises(ValidationError, match="condicionPago"):
            PedidoPanelUpdate(estado="Entregado")

    def test_entrega_al_contado_sin_metodo_es_invalida(self) -> None:
        with pytest.raises(ValidationError, match="metodoPago"):
            PedidoPanelUpdate(
                estado="Entregado", condicionPago=CondicionPago.CONTADO
            )

    def test_entrega_a_pagare_sin_plazo_es_invalida(self) -> None:
        with pytest.raises(ValidationError, match="plazoDias"):
            PedidoPanelUpdate(
                estado="Entregado", condicionPago=CondicionPago.PAGARE
            )

    @pytest.mark.parametrize("plazo", [0, 15, 45, 120])
    def test_entrega_a_pagare_con_plazo_invalido(self, plazo: int) -> None:
        with pytest.raises(ValidationError, match="30, 60 o 90"):
            PedidoPanelUpdate(
                estado="Entregado",
                condicionPago=CondicionPago.PAGARE,
                plazoDias=plazo,
            )

    def test_condicion_desconocida_es_invalida(self) -> None:
        with pytest.raises(ValidationError):
            PedidoPanelUpdate(estado="Entregado", condicionPago="FIADO")
