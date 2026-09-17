from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

# Definimos un Enum para estado y esto se hace antes  porque primero se necesite reconocer las opciones para poder luego utilizarlas


class EstadoTarea(str, Enum):
    asignada = "Asignada"
    pendiente = "Pendiente"
    en_proceso = "En proceso"
    completada = "Completada"
    cancelada = "Cancelada"



class TareaBase(BaseModel):
    id_usuario: int
    descripcion: str = Field(min_length=3, max_length=180)
    fecha_hora_init: datetime
    estado: EstadoTarea
    fecha_hora_fin: datetime

class TareaCreate(TareaBase):
    pass

class TareaUpdate(BaseModel):    
    id_usuario: Optional[int] = Field(default=None, gt=0)
    descripcion: Optional[str] = Field(default=None, min_length=3, max_length=255)
    fecha_hora_init: Optional[datetime] = None
    estado: Optional[EstadoTarea] = None
    fecha_hora_fin: Optional[datetime] = None



class TareaOut(TareaBase):
    id_tarea: int
    # nombre_usuario: str
    nombre_usuario: Optional[str] = None
    documento: Optional[str] = None
