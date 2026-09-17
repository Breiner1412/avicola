from pydantic import BaseModel
from typing import Optional

class PermisoBase(BaseModel):
    id_modulo: int
    id_rol: int
    insertar: bool
    actualizar: bool
    seleccionar: bool
    borrar: bool

class PermisoCreate(PermisoBase):
    pass

class PermisoUpdate(BaseModel):
    insertar: Optional[bool] = None
    actualizar: Optional[bool] = None
    seleccionar: Optional[bool] = None
    borrar: Optional[bool] = None

class PermisoOut(PermisoBase):
    pass