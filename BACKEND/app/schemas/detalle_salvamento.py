from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

# NOTA: 
#     BaseModel: Define la estructura y validación básica de datos
#     Field: Añade validaciones específicas y metadata
#     Juntos: Crean un sistema robusto de validación y documentación
#     Sin ellos tendrías que escribir montones de validaciones manuales y tu código sería más propenso a errores.

class DetalleSalvamentoBase(BaseModel): 
    id_producto: int = Field(gt=0)   # gt=0 para recibir datos estrictamente mayores que 0
    cantidad: int = Field(ge=0)  # ge=0 para recibir datos mayores o iguales que 0 pero no inferiores
    id_venta: int = Field(gt=0)  
    valor_descuento: Decimal = Field(ge=0) 
    precio_venta: Decimal = Field(gt=0) 
    
class CreateDetalleSalvamento(DetalleSalvamentoBase): 
    cantidad: int = Field(gt=0) 

class DetalleSalvamentoUpdate(BaseModel):
    id_producto: Optional[int] = Field(default=None, gt=0)
    cantidad: Optional[int] = Field(default=None, gt=0) # default=None → Puede omitirse || gt=0 → Si se envía, debe ser válido
    valor_descuento: Optional[Decimal] = Field(default=None, ge=0)
    precio_venta: Optional[Decimal] = Field(default=None, gt=0)

class DetalleSalvamentoOut(DetalleSalvamentoBase): 
    id_detalle: int 

class salvamentoProductosOut(BaseModel):
    id_salvamento: int
    raza: str
    descripcion: str