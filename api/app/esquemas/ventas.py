"""Puntos de venta, productos, precios, caja y ventas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Clase = Literal["huevo", "ave_descarte", "ave_engorde", "otro"]
Presentacion = Literal["unidad", "docena", "medio_panal", "panal", "kg"]
CobroPor = Literal["unidad", "kg"]


# --- Puntos de venta ---
class PuntoVentaCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=10)
    nombre: str = Field(min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    prefijo: str | None = Field(default=None, max_length=10)
    finca_id: int | None = None  # vacio = punto central


class PuntoVentaActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=10)
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    prefijo: str | None = Field(default=None, max_length=10)
    finca_id: int | None = None
    activo: bool | None = None


class PuntoVentaSalida(BaseModel):
    id: int
    cuenta_id: int
    finca_id: int | None
    codigo: str
    nombre: str
    direccion: str | None
    prefijo: str
    consecutivo: int
    activo: bool
    es_central: bool = False

    model_config = {"from_attributes": True}


# --- Productos ---
class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    clase: Clase
    presentacion: Presentacion = "unidad"
    tipo_huevo_id: int | None = None
    cobro_por: CobroPor = "unidad"
    precio: float | None = Field(default=None, ge=0)
    orden: int = Field(default=0, ge=0, le=999)


class ProductoActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    tipo_huevo_id: int | None = None
    orden: int | None = Field(default=None, ge=0, le=999)
    activo: bool | None = None


class ProductoSalida(BaseModel):
    id: int
    cuenta_id: int
    nombre: str
    clase: str
    tipo_huevo_id: int | None
    tipo_huevo: str | None
    presentacion: str
    factor: int
    cobro_por: str
    orden: int
    activo: bool
    precio: float | None
    disponible: float | None = None


class PrecioCrear(BaseModel):
    producto_id: int
    precio: float = Field(ge=0)
    punto_venta_id: int | None = None
    desde: date | None = None


class PrecioSalida(BaseModel):
    id: int
    producto_id: int
    punto_venta_id: int | None
    precio: float
    desde: date
    hasta: date | None
    usuario_nombre: str | None


class MetodoPagoSalida(BaseModel):
    id: int
    nombre: str
    es_efectivo: bool

    model_config = {"from_attributes": True}


# --- Caja ---
class AbrirTurno(BaseModel):
    punto_venta_id: int
    base_inicial: float = Field(default=0, ge=0)
    observaciones: str | None = Field(default=None, max_length=255)


class CerrarTurno(BaseModel):
    efectivo_contado: float = Field(ge=0)
    observaciones: str | None = Field(default=None, max_length=255)


class TurnoSalida(BaseModel):
    id: int
    punto_venta_id: int
    punto_venta_nombre: str
    usuario_id: int
    usuario_nombre: str | None
    estado: str
    base_inicial: float
    abierto_en: datetime
    cerrado_en: datetime | None
    ventas: int = 0
    total_vendido: float = 0
    total_efectivo: float = 0
    esperado_en_caja: float = 0
    efectivo_contado: float | None = None
    diferencia: float | None = None
    observaciones: str | None = None


# --- Ventas ---
class ItemVenta(BaseModel):
    producto_id: int
    # Presentaciones (panales, docenas, unidades) o kilos si se cobra por kg
    cantidad: float = Field(gt=0, le=1_000_000)
    precio_unitario: float | None = Field(default=None, ge=0)
    lote_id: int | None = None
    aves: int | None = Field(default=None, ge=0)


class PagoVenta(BaseModel):
    metodo_pago_id: int
    monto: float = Field(gt=0)
    referencia: str | None = Field(default=None, max_length=60)


class VentaCrear(BaseModel):
    items: list[ItemVenta] = Field(min_length=1)
    pagos: list[PagoVenta] = []
    descuento: float = Field(default=0, ge=0)
    # Si se indica, el descuento se calcula como porcentaje del subtotal (y 'descuento' se ignora)
    descuento_porcentaje: float | None = Field(default=None, ge=0, le=100)
    observaciones: str | None = Field(default=None, max_length=255)


class DetalleSalida(BaseModel):
    id: int
    producto_id: int
    descripcion: str
    clase: str
    cantidad: float
    precio_unitario: float
    subtotal: float
    unidades: int
    peso_kg: float | None
    lote_id: int | None


class PagoSalida(BaseModel):
    metodo_pago_id: int
    metodo_nombre: str
    es_efectivo: bool
    monto: float
    referencia: str | None


class VentaSalida(BaseModel):
    id: int
    numero: str
    punto_venta_id: int
    punto_venta_nombre: str
    turno_id: int | None
    fecha: date
    subtotal: float
    descuento: float
    total: float
    estado: str
    observaciones: str | None
    usuario_nombre: str | None
    anulada_en: datetime | None
    anulada_por: str | None
    motivo_anulacion: str | None
    creado_en: datetime
    detalles: list[DetalleSalida] = []
    pagos: list[PagoSalida] = []


class AnularVenta(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class ResumenVentas(BaseModel):
    ventas: int
    total: float
    efectivo: float
    otros_medios: float
    anuladas: int
    huevos_vendidos: int
    aves_vendidas: int


class AjustesVentas(BaseModel):
    descuento_maximo: int
    tengo_tope: bool = False


class AjustesVentasActualizar(BaseModel):
    descuento_maximo: int = Field(ge=0, le=100)
