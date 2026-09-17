from datetime import date
from pydantic import BaseModel, Field
from typing import List, Optional



class RescueBase(BaseModel):
    id_galpon: int
    fecha: date
    id_tipo_gallina: int
    cantidad_gallinas: int

class RescueCreate(RescueBase):
    id_galpon: int = Field(gt=0)
    id_tipo_gallina: int = Field(gt=0)
    cantidad_gallinas: int = Field(gt=0)

class RescueUpdate(BaseModel):
    id_galpon: Optional[int] = Field(default=None, gt=0)
    fecha: Optional[date] = None
    id_tipo_gallina: Optional[int] = Field(default=None, gt=0)
    cantidad_gallinas: Optional[int] = Field(default=None, ge=0)

class RescueOut(RescueBase):
    id_salvamento: int
    nombre: str
    raza: str

class RescuePaginatedResponse(BaseModel):
    page: int
    page_size: int
    total_rescues: int
    total_pages: int
    rescues: List[RescueOut]