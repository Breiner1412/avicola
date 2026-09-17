from pydantic import BaseModel, Field
from typing import Optional

class ShedBase(BaseModel):
    id_finca: int
    nombre: str = Field(min_length=3, max_length=70)
    capacidad: float
    cant_actual: float
    estado: bool

class ShedCreate(ShedBase):
    pass

class ShedUpdate(BaseModel):
    id_finca: Optional[int] = Field(default=None)
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=70)
    capacidad: Optional[float] = Field(default=None)
    cant_actual: Optional[float] = Field(default=None)

class ShedEstado(BaseModel):
    estado: Optional[bool] = None

class ShedOut(ShedBase):
    id_galpon: int
    nombre_finca: Optional[str] = None
