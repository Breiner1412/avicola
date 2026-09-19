"""Sensores y lecturas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TipoSensorCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    unidad: str = Field(default="", max_length=20)
    min_ok: float | None = None
    max_ok: float | None = None


class TipoSensorSalida(BaseModel):
    id: int
    cuenta_id: int | None
    nombre: str
    unidad: str
    min_ok: float | None
    max_ok: float | None

    model_config = {"from_attributes": True}


class SensorCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=2, max_length=100)
    tipo_id: int
    galpon_id: int | None = None
    ubicacion: str | None = Field(default=None, max_length=120)
    min_ok: float | None = None
    max_ok: float | None = None


class SensorActualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    galpon_id: int | None = None
    ubicacion: str | None = Field(default=None, max_length=120)
    min_ok: float | None = None
    max_ok: float | None = None
    activo: bool | None = None


class LecturaCrear(BaseModel):
    valor: float
    medido_en: datetime | None = None


class LecturaEquipo(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    valor: float
    medido_en: datetime | None = None


class LoteLecturas(BaseModel):
    """Varias mediciones de una vez, identificando cada sensor por su codigo."""

    lecturas: list[LecturaEquipo] = Field(min_length=1, max_length=500)


class ResultadoLecturas(BaseModel):
    guardadas: int
    codigos_desconocidos: list[str] = []


class LecturaSalida(BaseModel):
    id: int
    sensor_id: int
    valor: float
    medido_en: datetime
    fuera_rango: bool
    origen: str
    usuario_nombre: str | None


class SensorSalida(BaseModel):
    id: int
    finca_id: int
    galpon_id: int | None
    galpon_nombre: str | None
    tipo_id: int
    tipo: str
    unidad: str
    codigo: str
    nombre: str
    ubicacion: str | None
    min_ok: float | None
    max_ok: float | None
    activo: bool
    # Estado segun la ultima lectura: ok, alto, bajo o sin_datos
    estado: str = "sin_datos"
    ultimo_valor: float | None = None
    ultima_medicion: datetime | None = None
    historial: list[float] = []
