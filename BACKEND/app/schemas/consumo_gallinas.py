from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class ConsumoBase(BaseModel):
    id_alimento: int = Field(gt=0)
    cantidad_alimento: int = Field(gt=0)
    fecha_registro: date
    id_galpon: int = Field(gt=0)
    
class ConsumoCreate(ConsumoBase):
    pass

class ConsumoUpdate(BaseModel):
    id_alimento: Optional[int] = Field(default=None, gt=0)
    cantidad_alimento: Optional[int] = Field(default=None, gt=0)
    fecha_registro: Optional[date] = None
    id_galpon: Optional[int] = Field(default=None, gt=0)

class ConsumoOut(ConsumoBase):
    id_consumo: int
    alimento: str
    galpon: str
    fecha_registro: date

class ConsumoPaginated(BaseModel):
    page: int
    page_size: int
    total_consumos: int
    total_pages: int
    consumos: List[ConsumoOut]

class ConsumoAllOut(BaseModel):
    consumos: List[ConsumoOut]

