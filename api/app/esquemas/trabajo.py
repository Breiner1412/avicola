"""Tareas, rutinas y novedades."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Prioridad = Literal["baja", "media", "alta"]
EstadoTarea = Literal["pendiente", "en_proceso", "hecha", "cancelada"]
Frecuencia = Literal["diaria", "semanal", "mensual"]
CategoriaNovedad = Literal["infraestructura", "clima", "animales", "servicios", "seguridad", "salud", "otro"]
Gravedad = Literal["baja", "media", "alta"]
EstadoNovedad = Literal["abierta", "en_proceso", "cerrada"]


# --- Tareas ---
class TareaCrear(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    descripcion: str | None = None
    fecha: date
    hora: str | None = Field(default=None, max_length=5)
    prioridad: Prioridad = "media"
    asignado_a: int | None = None
    galpon_id: int | None = None
    lote_id: int | None = None


class TareaActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=120)
    descripcion: str | None = None
    fecha: date | None = None
    hora: str | None = Field(default=None, max_length=5)
    prioridad: Prioridad | None = None
    estado: EstadoTarea | None = None
    asignado_a: int | None = None
    galpon_id: int | None = None
    lote_id: int | None = None
    notas: str | None = Field(default=None, max_length=255)


class TareaSalida(BaseModel):
    id: int
    finca_id: int
    titulo: str
    descripcion: str | None
    prioridad: str
    estado: str
    fecha: date
    hora: str | None
    asignado_a: int | None
    asignado_nombre: str | None
    galpon_id: int | None
    lote_id: int | None
    rutina_id: int | None
    creado_por: str | None
    terminada_en: datetime | None
    terminada_por: str | None
    notas: str | None
    creado_en: datetime


# --- Rutinas ---
class RutinaCrear(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    descripcion: str | None = None
    frecuencia: Frecuencia = "diaria"
    dias_semana: list[int] = Field(default_factory=list)
    dia_mes: int | None = Field(default=None, ge=1, le=31)
    hora: str | None = Field(default=None, max_length=5)
    prioridad: Prioridad = "media"
    asignado_a: int | None = None
    galpon_id: int | None = None


class RutinaActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=120)
    descripcion: str | None = None
    frecuencia: Frecuencia | None = None
    dias_semana: list[int] | None = None
    dia_mes: int | None = Field(default=None, ge=1, le=31)
    hora: str | None = Field(default=None, max_length=5)
    prioridad: Prioridad | None = None
    asignado_a: int | None = None
    galpon_id: int | None = None
    activo: bool | None = None


class RutinaSalida(BaseModel):
    id: int
    finca_id: int
    titulo: str
    descripcion: str | None
    frecuencia: str
    dias_semana: list[int] | None
    dia_mes: int | None
    hora: str | None
    prioridad: str
    asignado_a: int | None
    galpon_id: int | None
    activo: bool
    ultima_generacion: date | None


class GenerarTareas(BaseModel):
    fecha: date | None = None


# --- Novedades ---
class NovedadCrear(BaseModel):
    fecha: date
    categoria: CategoriaNovedad = "otro"
    subtipo: str | None = Field(default=None, max_length=80)
    titulo: str = Field(min_length=3, max_length=140)
    descripcion: str | None = None
    gravedad: Gravedad = "media"
    galpon_id: int | None = None
    lote_id: int | None = None
    aves_afectadas: int = Field(default=0, ge=0)
    # Si las aves murieron, tambien se descuentan del lote
    descontar_aves: bool = False
    costo_estimado: float = Field(default=0, ge=0)
    acciones: str | None = None


class NovedadActualizar(BaseModel):
    categoria: CategoriaNovedad | None = None
    subtipo: str | None = Field(default=None, max_length=80)
    titulo: str | None = Field(default=None, min_length=3, max_length=140)
    descripcion: str | None = None
    gravedad: Gravedad | None = None
    estado: EstadoNovedad | None = None
    costo_estimado: float | None = Field(default=None, ge=0)
    acciones: str | None = None


class CerrarNovedad(BaseModel):
    acciones: str | None = None


class NovedadSalida(BaseModel):
    id: int
    finca_id: int
    fecha: date
    categoria: str
    subtipo: str | None
    titulo: str
    descripcion: str | None
    gravedad: str
    estado: str
    galpon_id: int | None
    lote_id: int | None
    aves_afectadas: int
    costo_estimado: float
    acciones: str | None
    reportado_por: str | None
    cerrada_en: datetime | None
    cerrada_por: str | None
    creado_en: datetime
