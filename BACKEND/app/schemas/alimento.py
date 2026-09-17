from datetime import date
from typing import List, Optional
from pydantic import BaseModel

class AlimentoBase(BaseModel):
    nombre: str
    cantidad: int
    fecha_ingreso: date
  
class AlimentoCreate(AlimentoBase):
    pass

class AlimentoUpdate(BaseModel):
    nombre: Optional[str] = None
    cantidad: Optional[int] = None
    fecha_ingreso: Optional[date] = None
    
class AlimentoOut(AlimentoBase):
    id_alimento: int
    fecha_ingreso: date

class PaginatedAlimento(BaseModel):
    page: int
    page_size: int
    total_alimento: int
    total_pages: int
    alimento: List[AlimentoOut]
