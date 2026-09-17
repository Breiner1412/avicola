from datetime import date
from pydantic import BaseModel, Field
from typing import List, Optional

class ChickenBase(BaseModel):
    id_galpon: int
    fecha: date
    id_tipo_gallina: int
    cantidad_gallinas: int

class ChickenCreate(ChickenBase):
    id_galpon: int = Field(gt=0)
    id_tipo_gallina: int = Field(gt=0)
    cantidad_gallinas: int = Field(gt=0)

class ChickenUpdate(BaseModel):
    id_galpon: Optional[int] = Field(default=None, gt=0)
    fecha: Optional[date] = None
    id_tipo_gallina: Optional[int] = Field(default=None, gt=0)
    cantidad_gallinas: Optional[int] = Field(default=None, gt=0)

class ChickenOut(ChickenBase):
    id_ingreso: int
    raza: str
    nombre_galpon: str

class ChickenPaginated(BaseModel):
    page: int
    page_size: int
    total_record_chickens: int
    total_pages: int
    record_chickens: List[ChickenOut]