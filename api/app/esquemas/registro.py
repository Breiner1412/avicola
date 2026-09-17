"""Registro de cambios."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditoriaSalida(BaseModel):
    id: int
    cuenta_id: int | None
    finca_id: int | None
    usuario_id: int | None
    usuario_nombre: str | None
    accion: str
    entidad: str
    entidad_id: int | None
    descripcion: str | None
    datos: dict[str, Any] | None
    ip: str | None
    creado_en: datetime

    model_config = {"from_attributes": True}
