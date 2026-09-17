"""Usuarios, roles y permisos."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FincaAsignada(BaseModel):
    finca_id: int
    solo_lectura: bool = False


class UsuarioCrear(BaseModel):
    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(default="", max_length=80)
    email: EmailStr
    documento: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    rol: str = Field(min_length=3, max_length=30)
    clave: str = Field(min_length=8, max_length=72)
    debe_cambiar_clave: bool = True
    fincas: list[FincaAsignada] = []
    cuenta_id: int | None = None  # solo lo usa el rol de plataforma


class UsuarioActualizar(BaseModel):
    nombres: str | None = Field(default=None, min_length=2, max_length=80)
    apellidos: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    documento: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    rol: str | None = Field(default=None, min_length=3, max_length=30)
    activo: bool | None = None
    fincas: list[FincaAsignada] | None = None


class ClaveNueva(BaseModel):
    clave: str = Field(min_length=8, max_length=72)
    debe_cambiar_clave: bool = True


class UsuarioSalida(BaseModel):
    id: int
    cuenta_id: int | None
    nombres: str
    apellidos: str
    email: EmailStr
    documento: str | None
    telefono: str | None
    rol: str
    rol_nombre: str
    activo: bool
    debe_cambiar_clave: bool
    ultimo_ingreso: datetime | None
    fincas: list[FincaAsignada] = []


class RolSalida(BaseModel):
    id: int
    clave: str
    nombre: str
    descripcion: str | None
    nivel: int
    de_plataforma: bool

    model_config = {"from_attributes": True}


class ModuloSalida(BaseModel):
    id: int
    clave: str
    nombre: str
    grupo: str
    orden: int

    model_config = {"from_attributes": True}


class PermisoEntrada(BaseModel):
    ver: bool = False
    crear: bool = False
    editar: bool = False
    borrar: bool = False


class PermisoSalida(PermisoEntrada):
    rol: str
    modulo: str
