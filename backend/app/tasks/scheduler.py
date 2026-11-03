"""Planificador de tareas de la aplicación.

Solo programa y dispara: el caso de uso de negocio vive en el módulo
``envios``. Se activa explícitamente con ``SCHEDULER_ENABLED=true`` para no
arrancar hilos durante los tests ni en scripts de mantenimiento.
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.tasks.jobs import generar_entregas_del_dia

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None

JOB_GENERAR_ENVIOS = "generar_envios_del_dia"


def iniciar_scheduler() -> Optional[BackgroundScheduler]:
    """Arranca el planificador si está habilitado por configuración."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Planificador deshabilitado (SCHEDULER_ENABLED=false).")
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
    _scheduler.add_job(
        generar_entregas_del_dia,
        CronTrigger(
            hour=settings.SCHEDULER_HOUR,
            minute=settings.SCHEDULER_MINUTE,
            timezone=settings.SCHEDULER_TIMEZONE,
        ),
        id=JOB_GENERAR_ENVIOS,
        replace_existing=True,
        name="Generar envíos programados del día",
    )
    _scheduler.start()
    logger.info(
        "Planificador iniciado: envíos diarios a las %02d:%02d (%s).",
        settings.SCHEDULER_HOUR,
        settings.SCHEDULER_MINUTE,
        settings.SCHEDULER_TIMEZONE,
    )
    return _scheduler


def detener_scheduler() -> None:
    """Detiene el planificador si está corriendo."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Planificador detenido.")
    _scheduler = None


__all__ = ["iniciar_scheduler", "detener_scheduler", "JOB_GENERAR_ENVIOS"]
