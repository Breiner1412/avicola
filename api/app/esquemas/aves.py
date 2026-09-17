"""Lotes, movimientos de aves, produccion, pesajes, alimentacion y sanidad."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Proposito = Literal["postura", "engorde", "levante"]
TipoMovimientoAves = Literal["ingreso", "muerte", "descarte", "fuga", "robo", "venta", "traslado", "consumo", "regalo"]
TipoSanidad = Literal["vacuna", "medicamento", "vitamina", "desinfeccion", "otro"]
Via = Literal["agua", "ocular", "aspersion", "inyectado", "alimento", "otro"]


# --- Razas ---
class RazaCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    proposito: Proposito = "postura"


class RazaSalida(BaseModel):
    id: int
    cuenta_id: int | None
    nombre: str
    proposito: str

    model_config = {"from_attributes": True}


# --- Lotes ---
class LoteCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    galpon_id: int
    raza_id: int | None = None
    proposito: Proposito = "postura"
    fecha_ingreso: date
    edad_dias_ingreso: int = Field(default=1, ge=0, le=2000)
    aves_iniciales: int = Field(gt=0, le=1_000_000)
    costo_ave: float = Field(default=0, ge=0)
    observaciones: str | None = Field(default=None, max_length=255)


class LoteActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    raza_id: int | None = None
    costo_ave: float | None = Field(default=None, ge=0)
    observaciones: str | None = Field(default=None, max_length=255)


class LoteSalida(BaseModel):
    id: int
    cuenta_id: int
    finca_id: int
    galpon_id: int
    galpon_nombre: str
    raza_id: int | None
    raza_nombre: str | None
    codigo: str
    proposito: str
    fecha_ingreso: date
    edad_dias: int
    edad_semanas: int
    aves_iniciales: int
    aves_actuales: int
    aves_descarte: int
    mortalidad: int
    mortalidad_porcentaje: float
    costo_ave: float
    estado: str
    fecha_cierre: date | None
    observaciones: str | None


class CerrarLote(BaseModel):
    fecha: date
    observaciones: str | None = Field(default=None, max_length=255)


# --- Movimientos de aves ---
class MovimientoAvesCrear(BaseModel):
    lote_id: int
    fecha: date
    tipo: TipoMovimientoAves
    cantidad: int = Field(gt=0, le=1_000_000)
    galpon_destino_id: int | None = None
    peso_kg: float | None = Field(default=None, ge=0)
    motivo: str | None = Field(default=None, max_length=80)
    observaciones: str | None = Field(default=None, max_length=255)


class MovimientoAvesSalida(BaseModel):
    id: int
    lote_id: int
    lote_codigo: str
    fecha: date
    tipo: str
    cantidad: int
    galpon_destino_id: int | None
    peso_kg: float | None
    motivo: str | None
    observaciones: str | None
    usuario_nombre: str | None
    anulado: bool
    anulado_por: str | None
    motivo_anulacion: str | None
    creado_en: datetime


class AnularMovimientoAves(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


# --- Produccion de huevos ---
class TipoHuevoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=40)
    orden: int = Field(default=50, ge=0, le=999)
    comercial: bool = True


class TipoHuevoSalida(BaseModel):
    id: int
    cuenta_id: int | None
    nombre: str
    orden: int
    comercial: bool

    model_config = {"from_attributes": True}


class DetalleProduccion(BaseModel):
    tipo_huevo_id: int
    cantidad: int = Field(ge=0, le=1_000_000)


class ProduccionCrear(BaseModel):
    lote_id: int
    fecha: date
    detalles: list[DetalleProduccion] = Field(min_length=1)


class ProduccionDia(BaseModel):
    fecha: date
    lote_id: int
    lote_codigo: str
    aves: int
    total: int
    comercial: int
    porcentaje_postura: float
    detalles: dict[str, int]


class StockHuevosSalida(BaseModel):
    tipo_huevo_id: int
    tipo: str
    comercial: bool
    cantidad: int
    panales: float


# --- Pesajes ---
class PesajeCrear(BaseModel):
    lote_id: int
    fecha: date
    aves_muestra: int = Field(gt=0, le=10000)
    peso_total_kg: float = Field(gt=0, le=100000)
    observaciones: str | None = Field(default=None, max_length=255)


class PesajeSalida(BaseModel):
    id: int
    lote_id: int
    fecha: date
    aves_muestra: int
    peso_total_kg: float
    peso_promedio_kg: float
    edad_dias: int | None
    observaciones: str | None
    usuario_nombre: str | None


# --- Consumo de alimento ---
class ConsumoCrear(BaseModel):
    lote_id: int
    fecha: date
    articulo_id: int
    bodega_id: int
    cantidad: float = Field(gt=0, le=1_000_000)
    observaciones: str | None = Field(default=None, max_length=255)


class ConsumoSalida(BaseModel):
    id: int
    lote_id: int
    fecha: date
    articulo_id: int
    articulo_nombre: str
    unidad: str
    bodega_id: int
    cantidad: float
    costo: float
    observaciones: str | None
    usuario_nombre: str | None


# --- Sanidad ---
class SanidadCrear(BaseModel):
    fecha: date
    tipo: TipoSanidad = "vacuna"
    producto: str = Field(min_length=2, max_length=150)
    lote_id: int | None = None
    galpon_id: int | None = None
    articulo_id: int | None = None
    bodega_id: int | None = None
    cantidad_usada: float | None = Field(default=None, ge=0)
    lote_producto: str | None = Field(default=None, max_length=60)
    dosis: str | None = Field(default=None, max_length=60)
    via: Via = "agua"
    aves_tratadas: int | None = Field(default=None, ge=0)
    responsable: str | None = Field(default=None, max_length=120)
    proximo_refuerzo: date | None = None
    observaciones: str | None = Field(default=None, max_length=255)


class SanidadSalida(BaseModel):
    id: int
    fecha: date
    tipo: str
    producto: str
    lote_id: int | None
    lote_codigo: str | None
    galpon_id: int | None
    galpon_nombre: str | None
    articulo_id: int | None
    cantidad_usada: float | None
    lote_producto: str | None
    dosis: str | None
    via: str
    aves_tratadas: int | None
    responsable: str | None
    proximo_refuerzo: date | None
    observaciones: str | None
    usuario_nombre: str | None
    creado_en: datetime


# --- Balance del lote ---
class BalanceLote(BaseModel):
    lote: LoteSalida
    dias_en_granja: int
    alimento_kg: float
    alimento_costo: float
    alimento_por_ave_kg: float
    huevos_total: int
    huevos_comerciales: int
    huevos_por_dia: float
    porcentaje_postura: float
    peso_promedio_kg: float | None
    peso_fecha: date | None
    costo_aves: float
    costo_sanidad: float
    costo_total: float
    costo_por_ave: float
    conversion_alimenticia: float | None
