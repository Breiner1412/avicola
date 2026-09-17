from pydantic import BaseModel
from typing import Optional

class TypeChickenBase(BaseModel):
    raza: str 
    descripcion: str 
  
class TypeChickenCreate(TypeChickenBase):
    pass

class TypeChickenUpdate(BaseModel):
    raza: Optional[str] = None
    descripcion: Optional[str] = None
    
class TypeChickenOut(TypeChickenBase):
    id_tipo_gallinas: int
