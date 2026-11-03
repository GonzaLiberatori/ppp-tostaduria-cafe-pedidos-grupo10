"""Jobs programados del sistema.

El job solo abre una sesión, invoca el caso de uso del módulo dueño y registra
el resultado. La regla de negocio vive en ``modules/envios/services.py``.
"""

import logging
from datetime import date
from typing import Optional

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def generar_entregas_del_dia(fecha: Optional[date] = None) -> dict:
    """Genera los despachos programados para una fecha (por defecto, hoy).

    Es idempotente por ``(cliente, fecha)``: si el job se ejecuta dos veces,
    las entregas ya generadas se omiten y el stock no se descuenta de nuevo.
    """
    from app.modules.envios.services import EnvioService

    db = SessionLocal()
    try:
        resultado = EnvioService(db).generar_del_dia(fecha)
        datos = resultado.model_dump(mode="json")
        logger.info(
            "Envíos programados %s: %s generadas, %s omitidas, %s errores",
            datos.get("fecha"),
            datos.get("generadas"),
            datos.get("omitidas"),
            datos.get("errores"),
        )
        return datos
    finally:
        db.close()


__all__ = ["generar_entregas_del_dia"]
