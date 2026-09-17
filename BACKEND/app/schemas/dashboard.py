from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class DashboardMetrics(BaseModel):
    """Métricas principales del dashboard"""
    total_gallinas: int
    produccion_hoy: int
    galpones_activos: int
    alertas_activas: int
    gallinas_trend: str
    produccion_trend: str

class ProduccionSemanal(BaseModel):
    """Datos de producción semanal"""
    labels: List[str]
    data_actual: List[int]
    data_anterior: List[int]

class TipoGallinaDistribucion(BaseModel):
    """Distribución de gallinas por tipo"""
    tipo: str
    cantidad: int
    porcentaje: float

class GalponOcupacion(BaseModel):
    """Ocupación de cada galpón"""
    nombre: str
    ocupacion_porcentaje: int
    capacidad: int
    cantidad_actual: int
    tipos: List[TipoGallinaDistribucion]

class IncidenteReciente(BaseModel):
    """Incidente reciente"""
    id: int
    tipo: str
    severidad: str
    descripcion: str
    tiempo: str
    fecha: date

class SensorData(BaseModel):
    """Datos de sensores"""
    temperatura: Optional[float] = 25.0
    humedad: Optional[float] = 60.0
    co2: Optional[int] = 450
    luminosidad: Optional[int] = 750

class ActividadReciente(BaseModel):
    """Actividad reciente del sistema"""
    tipo: str
    descripcion: str
    tiempo: str
    color: str

class DashboardComplete(BaseModel):
    """Respuesta completa del dashboard"""
    metricas: DashboardMetrics
    produccion_semanal: ProduccionSemanal
    distribucion_tipos: List[TipoGallinaDistribucion]
    ocupacion_galpones: List[GalponOcupacion]
    incidentes_recientes: List[IncidenteReciente]
    sensores: SensorData
    actividad_reciente: List[ActividadReciente]
