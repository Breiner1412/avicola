from pydantic import BaseModel, Field
from typing import Optional

class LandBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=30)
    longitud: float
    latitud: float
    estado: bool

class LandCreate(LandBase):
    """Modelo usado para crear una finca"""

class LandUpdate(BaseModel):
    """Modelo usado para actualizar una finca"""
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=30)
    longitud: Optional[float] = None
    latitud: Optional[float] = None
    estado: Optional[bool] = None

class LandEstado(BaseModel):
    """Modelo usado para cambiar el estado de una finca"""
    estado: Optional[bool] = None

class LandOut(LandBase):
    """Modelo de salida (lectura)"""
    id_finca: int
