from pydantic import BaseModel, Field
from typing import List, Optional

class RolBase(BaseModel):
    nombre_rol: str = Field(min_length=3, max_length=30)
    descripcion: str = Field(min_length=3, max_length=500)
    estado: bool


class RolCreate(RolBase):
    pass


class RolUpdate(BaseModel):
    nombre_rol: Optional[str] = Field(default=None, min_length=3, max_length=30)
    descripcion: Optional[str] = Field(default=None, min_length=3, max_length=500)


class RolEstado(BaseModel):
    estado: Optional[bool] = None


class RolOut(RolBase):
    id_rol: int
    
    
class RolPag(BaseModel):
    page: int
    page_size: int
    total_roles: int
    total_pages: int
    roles: List[RolOut]