from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class VentaBase(BaseModel):
    # id_usuario = id de quien registra la venta
    id_usuario: int
    fecha_hora: datetime

class VentaCreate(BaseModel):
    # El id_usuario ya NO se recibe del cliente: se toma del token en el router.
    # Se acepta (y se ignora) por compatibilidad con el frontend.
    id_usuario: Optional[int] = None
    fecha_hora: datetime

class VentaUpdate(BaseModel):
    tipo_pago: Optional [int] = Field(default=None, gt=0)


class VentaEstado(BaseModel):
    estado: Optional[bool] = None
    
    
class VentaOut(VentaBase):
    id_venta: int
    nombre_usuario: str
    tipo_pago: int
    metodo_pago: str
    # este campo es calculado
    total: Decimal
    estado: bool
    
class ventaPag(BaseModel):
    page: int
    page_size: int
    total_ventas: int
    total_pages: int
    ventas: List[VentaOut]
    

class DatosVentaCreate(BaseModel):
    id_usuario: int
    nombre_usuario: str
    tipo_pago: int
    metodo_pago: str
    id_venta: int
    fecha_hora: datetime
    estado: bool

    
class VentaCreateResponse(BaseModel):
    message: str
    data_venta: DatosVentaCreate
    
    
class DetalleVenta(BaseModel):
    tipo: str
    id_detalle: int
    id_producto: int
    descripcion: str
    cantidad: int
    id_venta: int
    valor_descuento: Decimal
    precio_venta: Decimal
    
