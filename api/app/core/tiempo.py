"""Fechas en la hora de la granja.

Las marcas de tiempo se guardan en UTC (sin zona). Las fechas de negocio (el dia
de una venta, hoy, el rango de un reporte) se toman en la zona de la granja, sin
depender de la zona del servidor o del contenedor.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.core.config import config


def zona() -> ZoneInfo:
    return ZoneInfo(config.zona_horaria)


def hoy() -> date:
    """El dia de hoy en la granja (no el del servidor, que puede estar en UTC)."""
    return datetime.now(zona()).date()


def a_utc(fecha: date, hora: time) -> datetime:
    """Un momento de la hora de la granja, en UTC sin zona (como se guarda)."""
    return datetime.combine(fecha, hora, tzinfo=zona()).astimezone(timezone.utc).replace(tzinfo=None)


def inicio_del_dia(fecha: date) -> datetime:
    return a_utc(fecha, time.min)


def fin_del_dia(fecha: date) -> datetime:
    return a_utc(fecha, time.max)
