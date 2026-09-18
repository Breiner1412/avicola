"""Importacion de archivos de Excel o CSV."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CampoInfo(BaseModel):
    clave: str
    etiqueta: str
    obligatorio: bool


class TipoInfo(BaseModel):
    clave: str
    etiqueta: str
    campos: list[CampoInfo]


class PlantillaCrear(BaseModel):
    tipo: str
    nombre: str = Field(min_length=2, max_length=80)
    mapeo: dict[str, str]


class PlantillaSalida(BaseModel):
    id: int
    tipo: str
    nombre: str
    mapeo: dict[str, str]
    usuario_nombre: str | None
    creado_en: datetime

    model_config = {"from_attributes": True}


class AnalisisSalida(BaseModel):
    id: int
    tipo: str
    etiqueta_tipo: str
    archivo: str
    hoja: str | None
    columnas: list[str]
    filas_totales: int
    vista_previa: list[dict[str, Any]]
    mapeo_sugerido: dict[str, str]
    campos: list[CampoInfo]
    plantillas: list[PlantillaSalida] = []


class MapeoEntrada(BaseModel):
    mapeo: dict[str, str]
    opciones: dict[str, Any] = {}


class ErrorFila(BaseModel):
    numero: int
    error: str


class ValidacionSalida(BaseModel):
    filas_totales: int
    filas_ok: int
    filas_error: int
    errores: list[ErrorFila] = []
    vista_previa: list[dict[str, Any]] = []


class ImportacionSalida(BaseModel):
    id: int
    tipo: str
    etiqueta_tipo: str
    archivo: str
    hoja: str | None
    estado: str
    filas_totales: int
    filas_ok: int
    filas_error: int
    resumen: dict[str, Any] | None
    usuario_nombre: str | None
    creado_en: datetime
    aplicada_en: datetime | None
    revertida_en: datetime | None
    revertida_por: str | None


class DetalleFila(BaseModel):
    numero: int
    estado: str
    error: str | None
    datos: dict[str, Any]


class ImportacionDetalle(ImportacionSalida):
    columnas: list[str] = []
    mapeo: dict[str, str] | None = None
    filas: list[DetalleFila] = []
