"""Reglas de negocio del tueste.

El caso de uso convierte gramos verdes en gramos tostados en una única
transacción: descuenta los lotes verdes en FIFO, registra la orden, deja la
trazabilidad de los lotes consumidos y crea el lote tostado resultante. Si
cualquier paso falla, no queda ni stock descontado ni orden a medias.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.inventario import services as inventario_services
from app.modules.produccion import crud
from app.modules.produccion.schemas import TuesteCreate, TuesteRead


class TuesteNoEncontrado(Exception):
    """El ``id`` recibido no corresponde a ninguna orden de tueste."""

    def __init__(self, orden_id: int) -> None:
        self.orden_id = orden_id
        super().__init__(f"No existe una orden de tueste con id {orden_id}.")


class TipoDeCafeNoEncontradoParaTueste(Exception):
    """El tipo de café indicado no existe en el inventario."""

    def __init__(self, tipo_de_cafe_id: int) -> None:
        self.tipo_de_cafe_id = tipo_de_cafe_id
        super().__init__(
            f"No existe un tipo de café con id {tipo_de_cafe_id}."
        )


class StockVerdeInsuficienteParaTueste(Exception):
    """No hay café verde suficiente para cubrir los gramos solicitados."""

    def __init__(
        self, tipo_de_cafe_id: int, solicitado: Decimal, disponible: Decimal
    ) -> None:
        self.tipo_de_cafe_id = tipo_de_cafe_id
        self.solicitado = solicitado
        self.disponible = disponible
        super().__init__(
            f"Stock verde insuficiente para el tipo de café {tipo_de_cafe_id}: "
            f"se solicitan {solicitado} kg y hay {disponible} kg disponibles."
        )


def _gramos_a_kg(gramos: int) -> Decimal:
    """Convierte gramos enteros a kilos con la precisión de la columna."""
    return (Decimal(gramos) / Decimal("1000")).quantize(Decimal("0.001"))


def registrar_tueste(db: Session, datos: TuesteCreate) -> TuesteRead:
    """Registra un tueste completo en una sola transacción.

    Orden de las operaciones:

    1. Consumir café verde en FIFO (falla antes de tocar nada si no alcanza).
    2. Crear la orden de tueste y su detalle de lotes consumidos.
    3. Crear el lote tostado, abierto y con todos sus kilos disponibles.
    4. Confirmar la transacción y devolver la orden con su trazabilidad.
    """
    kg_verde = _gramos_a_kg(datos.gramos_verde)
    kg_tostado = _gramos_a_kg(datos.gramos_tostado)

    try:
        consumos = inventario_services.consumir_stock_verde_fifo(
            db, datos.tipo_de_cafe_id, kg_verde
        )

        orden = crud.crear_orden_tueste(
            db,
            fecha_tueste=datetime.now(),
            kg_gastados=kg_verde,
            kg_obtenidos=kg_tostado,
            tipo_de_cafe_id=datos.tipo_de_cafe_id,
        )

        for consumo in consumos:
            crud.registrar_consumo(
                db,
                orden=orden,
                lote_id=consumo.lote_id,
                kg_consumidos=consumo.kg_consumidos,
            )

        inventario_services.crear_lote_tostado_de_tueste(
            db,
            tipo_de_cafe_id=datos.tipo_de_cafe_id,
            kg_reales=kg_tostado,
            orden_tueste_id=orden.id,
            fecha_vencimiento=datos.fecha_vencimiento
            or datetime.now() + timedelta(days=365),
            humedad=datos.humedad if datos.humedad is not None else Decimal("0"),
            ubicacion_fisica=datos.ubicacion_fisica or "Producción",
            observaciones=datos.observaciones
            or f"Lote generado por la orden de tueste #{orden.id}",
        )

        # Se valida el contrato antes del commit para no confirmar una orden
        # que luego no se pueda serializar.
        resultado = TuesteRead.model_validate(orden)
        db.commit()
    except inventario_services.TipoDeCafeNoEncontrado as exc:
        db.rollback()
        raise TipoDeCafeNoEncontradoParaTueste(exc.tipo_id) from exc
    except inventario_services.OrigenDeLoteNoEncontrado as exc:
        db.rollback()
        raise TipoDeCafeNoEncontradoParaTueste(datos.tipo_de_cafe_id) from exc
    except inventario_services.StockVerdeInsuficiente as exc:
        db.rollback()
        raise StockVerdeInsuficienteParaTueste(
            exc.tipo_de_cafe_id, exc.solicitado, exc.disponible
        ) from exc
    except Exception:
        db.rollback()
        raise

    return resultado


def obtener_tueste(db: Session, orden_id: int) -> TuesteRead:
    """Lee una orden de tueste por su ``id`` con sus consumos y lote."""
    orden = crud.obtener_orden(db, orden_id)

    if orden is None:
        raise TuesteNoEncontrado(orden_id)

    return TuesteRead.model_validate(orden)


def listar_tuestes(db: Session) -> list[TuesteRead]:
    """Lista las órdenes de tueste, de la más reciente a la más antigua."""
    return [
        TuesteRead.model_validate(orden)
        for orden in crud.listar_ordenes(db)
    ]
