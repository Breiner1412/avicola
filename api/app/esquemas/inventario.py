"""Bodegas, articulos, proveedores y movimientos de inventario."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Unidad = Literal["unidad", "kg", "litro", "bulto", "dosis", "metro"]
Clase = Literal["alimento", "medicamento", "vacuna", "herramienta", "repuesto", "insumo", "otro"]
TipoMovimiento = Literal["entrada", "salida", "traslado", "ajuste"]


# --- Bodegas ---
class BodegaCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=2, max_length=100)
    ubicacion: str | None = Field(default=None, max_length=150)
    # Vacio = bodega central de la cuenta
    finca_id: int | None = None


class BodegaActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    ubicacion: str | None = Field(default=None, max_length=150)
    finca_id: int | None = None
    activo: bool | None = None


class BodegaSalida(BaseModel):
    id: int
    cuenta_id: int
    finca_id: int | None
    codigo: str
    nombre: str
    ubicacion: str | None
    activo: bool
    es_central: bool = False

    model_config = {"from_attributes": True}


# --- Categorias ---
class CategoriaCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    clase: Clase = "insumo"


class CategoriaSalida(BaseModel):
    id: int
    cuenta_id: int | None
    nombre: str
    clase: str

    model_config = {"from_attributes": True}


# --- Articulos ---
class ArticuloCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=2, max_length=150)
    categoria_id: int
    unidad: Unidad = "unidad"
    kg_por_bulto: float | None = Field(default=None, ge=0, le=100000)
    stock_minimo: float = Field(default=0, ge=0)
    observaciones: str | None = Field(default=None, max_length=255)


class ArticuloActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    categoria_id: int | None = None
    unidad: Unidad | None = None
    kg_por_bulto: float | None = Field(default=None, ge=0, le=100000)
    stock_minimo: float | None = Field(default=None, ge=0)
    observaciones: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class ArticuloSalida(BaseModel):
    id: int
    cuenta_id: int
    categoria_id: int
    categoria_nombre: str
    clase: str
    codigo: str
    nombre: str
    unidad: str
    kg_por_bulto: float | None
    stock_minimo: float
    observaciones: str | None
    activo: bool
    existencia_total: float = 0
    bajo_minimo: bool = False


# --- Proveedores ---
class ProveedorCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=200)


class ProveedorActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=200)
    activo: bool | None = None


class ProveedorSalida(BaseModel):
    id: int
    cuenta_id: int
    nombre: str
    documento: str | None
    telefono: str | None
    email: str | None
    direccion: str | None
    activo: bool

    model_config = {"from_attributes": True}


# --- Existencias ---
class ExistenciaSalida(BaseModel):
    bodega_id: int
    bodega_nombre: str
    articulo_id: int
    articulo_codigo: str
    articulo_nombre: str
    unidad: str
    cantidad: float
    costo_promedio: float
    stock_minimo: float
    bajo_minimo: bool


# --- Movimientos ---
class ItemEntrada(BaseModel):
    articulo_id: int
    # En un ajuste es la cantidad contada; en los demas, lo que entra o sale.
    cantidad: float = Field(ge=0)
    costo_unitario: float = Field(default=0, ge=0)
    lote: str | None = Field(default=None, max_length=40)
    vencimiento: date | None = None


class MovimientoCrear(BaseModel):
    tipo: TipoMovimiento
    fecha: date
    bodega_id: int
    bodega_destino_id: int | None = None
    proveedor_id: int | None = None
    motivo: str | None = Field(default=None, max_length=60)
    documento: str | None = Field(default=None, max_length=60)
    observaciones: str | None = Field(default=None, max_length=255)
    items: list[ItemEntrada] = Field(min_length=1)


class ItemSalida(BaseModel):
    id: int
    articulo_id: int
    articulo_codigo: str
    articulo_nombre: str
    unidad: str
    cantidad: float
    cantidad_aplicada: float
    costo_unitario: float
    lote: str | None
    vencimiento: date | None


class MovimientoSalida(BaseModel):
    id: int
    tipo: str
    fecha: date
    bodega_id: int
    bodega_nombre: str
    bodega_destino_id: int | None
    bodega_destino_nombre: str | None
    proveedor_id: int | None
    proveedor_nombre: str | None
    motivo: str | None
    documento: str | None
    observaciones: str | None
    total: float
    usuario_nombre: str | None
    anulado: bool
    anulado_en: datetime | None
    anulado_por: str | None
    motivo_anulacion: str | None
    creado_en: datetime
    items: list[ItemSalida] = []


class AnularMovimiento(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)
