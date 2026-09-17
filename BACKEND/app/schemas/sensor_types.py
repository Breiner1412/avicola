from pydantic import BaseModel, Field
from typing import Optional

class SensorTypeBase(BaseModel):
    nombre: str = Field(min_length=3, max_length=70)
    descripcion: str = Field(min_length=10, max_length=255)
    modelo: str = Field(min_length=3, max_length=70)
    estado: bool

class SensorTypeCreate(SensorTypeBase):
    pass

class SensorTypeUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=70)
    descripcion: Optional[str] = Field(default=None, min_length=10, max_length=255)
    modelo: Optional[str] = Field(default=None, min_length=3, max_length=70)
    
class SensorTypeEstado(BaseModel):
    estado: Optional[bool] = None    

class SensorTypeOut(SensorTypeBase):
    id_tipo: int

