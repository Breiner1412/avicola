import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

from enum import Enum

class TipoIncidenteGallina(str, Enum):
    enfermedad = "Enfermedad"
    herida = "Herida"
    muerte = "Muerte"
    fuga = "Fuga"
    ataque_depredador = "Ataque Depredador"
    produccion = "Produccion"
    alimentacion = "Alimentacion"
    plaga = "Plaga"
    estres_termico = "Estres termico"
    otro = "Otro"


class incidentChickenBase(BaseModel):
    galpon_origen : int
    tipo_incidente : TipoIncidenteGallina
    cantidad : int
    descripcion : str
    esta_resuelto: bool

class incidentChickenCreate(incidentChickenBase):
    fecha_hora:datetime.datetime = Field(..., description="Fecha y hora del aislamiento")

class incidentChickenUpdate(BaseModel):
    galpon_origen : Optional[int] = None
    tipo_incidente : Optional[TipoIncidenteGallina] = None
    cantidad : Optional[int] = None
    descripcion : Optional[str] = None
    fecha_hora: Optional[datetime.datetime] = None
   
class incidentChickenEstado(BaseModel):
    esta_resuelto: Optional[bool] = None
   

class incidentChickenOut(incidentChickenBase):
    id_inc_gallina: int
    nombre: str
    fecha_hora:datetime.datetime = Field(..., description="Fecha y hora del aislamiento")
     
class PaginatedChickenIncidents(BaseModel):
    page: int
    page_size: int
    total_incidents: int
    total_pages: int
    incidents: List[incidentChickenOut] 
