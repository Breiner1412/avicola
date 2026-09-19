"""Avisos de la campana."""

from datetime import datetime

from pydantic import BaseModel


class AlertaSalida(BaseModel):
    id: int
    tipo: str
    nivel: str
    titulo: str
    detalle: str | None
    ruta: str | None
    entidad_id: int | None
    leida: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class ResumenAlertas(BaseModel):
    total: int
    sin_leer: int
    criticas: int
    alertas: list[AlertaSalida] = []
