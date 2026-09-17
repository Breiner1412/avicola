from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from core.database import get_db
from app.schemas.dashboard import (
    DashboardComplete, 
    DashboardMetrics,
    ProduccionSemanal,
    TipoGallinaDistribucion,
    GalponOcupacion,
    IncidenteReciente,
    SensorData,
    ActividadReciente
)

logger = logging.getLogger(__name__)
from app.schemas.users import UserOut
from app.router.dependencies import get_current_user
from app.crud import dashboard as crud_dashboard
from typing import List

router = APIRouter()

@router.get("/metricas", response_model=DashboardMetrics)
def get_dashboard_metricas(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene las métricas principales del dashboard:
    - Total de gallinas
    - Producción de hoy
    - Galpones activos
    - Alertas activas
    - Tendencias
    """
    try:
        tendencias = crud_dashboard.calcular_tendencias(db)
        
        metricas = DashboardMetrics(
            total_gallinas=crud_dashboard.get_total_gallinas(db),
            produccion_hoy=crud_dashboard.get_produccion_hoy(db),
            galpones_activos=crud_dashboard.get_galpones_activos(db),
            alertas_activas=crud_dashboard.get_alertas_activas(db),
            gallinas_trend=tendencias['gallinas_trend'],
            produccion_trend=tendencias['produccion_trend']
        )
        
        return metricas
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/produccion-semanal", response_model=ProduccionSemanal)
def get_produccion_semanal(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene los datos de producción de huevos de los últimos 7 días
    comparados con la semana anterior
    """
    try:
        data = crud_dashboard.get_produccion_semanal(db)
        return ProduccionSemanal(**data)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/produccion-rango")
def get_produccion_rango(
    dias: int = 7,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene los datos de producción de huevos para un rango específico de días
    Parámetros:
    - dias: número de días (7, 30, 90, 180)
    """
    try:
        # Validar rango
        if dias not in [7, 30, 90, 180]:
            raise HTTPException(status_code=400, detail="Rango inválido. Usa 7, 30, 90 o 180 días")
        
        logger.info(f"Solicitando producción para {dias} días")
        data = crud_dashboard.get_produccion_por_rango(db, dias)
        logger.info(f"Datos obtenidos: {data}")
        return data
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/distribucion-tipos", response_model=List[TipoGallinaDistribucion])
def get_distribucion_tipos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene la distribución de gallinas por tipo/raza
    """
    try:
        data = crud_dashboard.get_distribucion_tipos(db)
        return [TipoGallinaDistribucion(**item) for item in data]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/ocupacion-galpones", response_model=List[GalponOcupacion])
def get_ocupacion_galpones(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene el porcentaje de ocupación de cada galpón
    """
    try:
        data = crud_dashboard.get_ocupacion_galpones(db)
        return [GalponOcupacion(**item) for item in data]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/incidentes-recientes", response_model=List[IncidenteReciente])
def get_incidentes_recientes(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene los últimos incidentes registrados
    """
    try:
        data = crud_dashboard.get_incidentes_recientes(db, limit=5)
        return [IncidenteReciente(**item) for item in data]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/sensores", response_model=SensorData)
def get_sensores_data(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene los últimos datos de los sensores ambientales
    """
    try:
        data = crud_dashboard.get_ultimos_registros_sensores(db)
        return SensorData(**data)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/actividad-reciente", response_model=List[ActividadReciente])
def get_actividad_reciente(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene la actividad reciente del sistema
    """
    try:
        data = crud_dashboard.get_actividad_reciente(db, limit=10)
        return [ActividadReciente(**item) for item in data]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/completo", response_model=DashboardComplete)
def get_dashboard_completo(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene todos los datos del dashboard en una sola llamada
    """
    try:
        # Obtener todas las métricas
        tendencias = crud_dashboard.calcular_tendencias(db)
        
        metricas = DashboardMetrics(
            total_gallinas=crud_dashboard.get_total_gallinas(db),
            produccion_hoy=crud_dashboard.get_produccion_hoy(db),
            galpones_activos=crud_dashboard.get_galpones_activos(db),
            alertas_activas=crud_dashboard.get_alertas_activas(db),
            gallinas_trend=tendencias['gallinas_trend'],
            produccion_trend=tendencias['produccion_trend']
        )
        
        produccion_data = crud_dashboard.get_produccion_semanal(db)
        produccion_semanal = ProduccionSemanal(**produccion_data)
        
        distribucion_data = crud_dashboard.get_distribucion_tipos(db)
        distribucion_tipos = [TipoGallinaDistribucion(**item) for item in distribucion_data]
        
        ocupacion_data = crud_dashboard.get_ocupacion_galpones(db)
        ocupacion_galpones = [GalponOcupacion(**item) for item in ocupacion_data]
        
        incidentes_data = crud_dashboard.get_incidentes_recientes(db, limit=5)
        incidentes_recientes = [IncidenteReciente(**item) for item in incidentes_data]
        
        sensores_data = crud_dashboard.get_ultimos_registros_sensores(db)
        sensores = SensorData(**sensores_data)
        
        actividad_data = crud_dashboard.get_actividad_reciente(db, limit=10)
        actividad_reciente = [ActividadReciente(**item) for item in actividad_data]
        
        return DashboardComplete(
            metricas=metricas,
            produccion_semanal=produccion_semanal,
            distribucion_tipos=distribucion_tipos,
            ocupacion_galpones=ocupacion_galpones,
            incidentes_recientes=incidentes_recientes,
            sensores=sensores,
            actividad_reciente=actividad_reciente
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
