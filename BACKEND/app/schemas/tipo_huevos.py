from pydantic import BaseModel, Field
from typing import Optional

class TipoHuevosBase(BaseModel):
    Color: str = Field(..., min_length=1, max_length=30)
    Tamaño: str = Field(..., min_length=1, max_length=30)

class TipoHuevosCreate(TipoHuevosBase):
    pass

class TipoHuevosUpdate(BaseModel):
    Color: Optional[str] = Field(default=None, min_length=1, max_length=30)
    Tamaño: Optional[str] = Field(default=None, min_length=1, max_length=30)

class TipoHuevosOut(TipoHuevosBase):
    id_tipo_huevo: int
