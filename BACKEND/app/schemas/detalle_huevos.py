from pydantic import BaseModel, Field
from typing import Optional

from decimal import Decimal

class DetalleHuevosBase(BaseModel):
    id_producto: int = Field(gt = 0)
    cantidad: int = Field(ge = 0)
    id_venta: int = Field(gt = 0)
    valor_descuento: Decimal = Field(ge = 0)
    precio_venta: Decimal = Field(ge = 0)

class DetalleHuevosCreate(DetalleHuevosBase):
    cantidad: int = Field(gt=0)
    
class DetalleHuevosUpdate(BaseModel):
    id_producto: Optional[int] = Field(default=None, gt=0)
    cantidad: Optional[int] = Field(default=None, gt=0)
    id_venta: Optional[int] = Field(default=None, gt=0)
    valor_descuento: Optional[Decimal] = Field(default=None, ge=0)
    precio_venta: Optional[Decimal] = Field(default=None, ge=0)

class DetalleHuevosOut(DetalleHuevosBase):
    id_detalle: int

class StockProductosOut(BaseModel):
    id_producto: int
    unidad_medida: str
    color: str
    tamanio: str

