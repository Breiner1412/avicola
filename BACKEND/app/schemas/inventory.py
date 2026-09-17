from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class InventoryBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    cantidad: float = Field(default=None, gt=0)
    unidad_medida: str = Field(min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    id_categoria: int = Field(default=None, gt=0)
    id_finca: int = Field(default=None, gt=0)

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    cantidad: Optional[float] = Field(default=None, ge=0)
    unidad_medida: Optional[str] = Field(default=None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    id_categoria: Optional[int] = Field(default=None, gt=0)
    id_finca: Optional[int] = Field(default=None, gt=0)

class InventoryOut(InventoryBase):
    id_inventario: int
    nombre_categoria: Optional[str] = None
    nombre_finca: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
