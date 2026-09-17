"""Inicio de sesion, eleccion de finca y contrasenas."""

from pydantic import BaseModel, EmailStr, Field


class FincaResumen(BaseModel):
    id: int
    codigo: str
    nombre: str
    municipio: str | None = None
    solo_lectura: bool = False

    model_config = {"from_attributes": True}


class UsuarioSesion(BaseModel):
    id: int
    nombres: str
    apellidos: str
    email: EmailStr
    rol: str
    rol_nombre: str
    cuenta_id: int | None = None
    cuenta_nombre: str | None = None
    debe_cambiar_clave: bool = False


class SesionSalida(BaseModel):
    token: str
    expira_en_minutos: int
    usuario: UsuarioSesion
    finca_activa: FincaResumen | None = None
    fincas: list[FincaResumen] = []
    permisos: dict[str, dict[str, bool]] = {}


class LoginEntrada(BaseModel):
    email: EmailStr
    clave: str = Field(min_length=1, max_length=72)
    finca_id: int | None = None


class ElegirFinca(BaseModel):
    finca_id: int


class CambiarClave(BaseModel):
    clave_actual: str = Field(min_length=1, max_length=72)
    clave_nueva: str = Field(min_length=8, max_length=72)


class PedirCodigo(BaseModel):
    email: EmailStr


class RestablecerClave(BaseModel):
    email: EmailStr
    codigo: str = Field(min_length=6, max_length=6)
    clave_nueva: str = Field(min_length=8, max_length=72)
