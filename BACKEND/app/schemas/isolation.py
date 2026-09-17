import datetime

from pydantic import BaseModel, Field
from typing import List, Optional

class IsolationBase(BaseModel):
    id_incidente_gallina : int
    id_galpon: int

class IsolationCreate(IsolationBase):
    fecha_hora: datetime.datetime = Field(..., description="Fecha y hora del aislamiento")

class IsolationUpdate(BaseModel):
    id_incidente_gallina: Optional[int] = None
    id_galpon: Optional[int] = None
    

class IsolationEstado(BaseModel):
    pass

class IsolationOut(IsolationBase):
    fecha_hora: datetime.datetime = Field(..., description="Fecha y hora del aislamiento")
    id_aislamiento: int
    nombre: str

class PaginatedIsolations(BaseModel):
    page: int
    page_size: int
    total_isolation: int
    total_pages: int
    isolation: List[IsolationOut]
    
   