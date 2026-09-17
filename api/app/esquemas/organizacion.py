"""Cuentas, fincas y galpones."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.modelos.organizacion import TIPOS_CUENTA, TIPOS_GALPON  # noqa: F401  (documenta los valores)


class CuentaCrear(BaseModel):
    tipo: Literal["empresa", "persona"] = "empresa"
    nombre: str = Field(min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    email_contacto: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=30)


class CuentaActualizar(BaseModel):
    tipo: Literal["empresa", "persona"] | None = None
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    email_contacto: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=30)
    activo: bool | None = None


class CuentaSalida(BaseModel):
    id: int
    tipo: str
    nombre: str
    documento: str | None
    email_contacto: str | None
    telefono: str | None
    activo: bool

    model_config = {"from_attributes": True}


class FincaCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=2, max_length=150)
    municipio: str | None = Field(default=None, max_length=100)
    departamento: str | None = Field(default=None, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    cuenta_id: int | None = None  # solo lo usa el rol de plataforma


class FincaActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    municipio: str | None = Field(default=None, max_length=100)
    departamento: str | None = Field(default=None, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    activo: bool | None = None


class FincaSalida(BaseModel):
    id: int
    cuenta_id: int
    codigo: str
    nombre: str
    municipio: str | None
    departamento: str | None
    direccion: str | None
    telefono: str | None
    activo: bool

    model_config = {"from_attributes": True}


class GalponCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=2, max_length=100)
    tipo: Literal["postura", "levante", "engorde", "cria"] = "postura"
    capacidad: int = Field(ge=0, le=1_000_000)
    observaciones: str | None = Field(default=None, max_length=255)


class GalponActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    tipo: Literal["postura", "levante", "engorde", "cria"] | None = None
    capacidad: int | None = Field(default=None, ge=0, le=1_000_000)
    observaciones: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class GalponSalida(BaseModel):
    id: int
    finca_id: int
    codigo: str
    nombre: str
    tipo: str
    capacidad: int
    aves_actuales: int
    observaciones: str | None
    activo: bool

    model_config = {"from_attributes": True}
