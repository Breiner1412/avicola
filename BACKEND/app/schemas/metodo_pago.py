from pydantic import BaseModel, Field
from typing import Optional

class MetodoPagoBase(BaseModel):
    nombre: str = Field(min_length=3, max_length=30)
    descripcion: str = Field(max_length=100)
    estado: bool

class MetodoPagoCreate(MetodoPagoBase):
    pass

class MetodoPagoUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=30)
    descripcion: Optional[str] = Field(default=None, max_length=100)


class MetodoPagoEstado(BaseModel):
    estado: Optional[bool] = None

class MetodoPagoOut(MetodoPagoBase):
    id_tipo: int
