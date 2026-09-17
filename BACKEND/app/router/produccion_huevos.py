from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query 
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from app.schemas.users import UserOut
from app.schemas.produccion_huevos import ProduccionHuevosCreate, ProduccionHuevosUpdate, ProduccionHuevosOut
from core.database import get_db
from app.crud import produccion_huevos as crud_produccion

router = APIRouter()
modulo = 24  # Módulo 4 = produccion_huevos (ajusta si tienes otro ID)

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_produccion_huevos(
    produccion: ProduccionHuevosCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        crud_produccion.create_produccion_huevos(db, produccion)
        return {"message": "Producción de huevos creada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-id/{produccion_id}", response_model=ProduccionHuevosOut)
def get_produccion_huevos(
    produccion_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        produccion = crud_produccion.get_produccion_huevos_by_id(db, produccion_id)
        if not produccion:
            raise HTTPException(status_code=404, detail="Producción de huevos no encontrada")
        return produccion
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.get("/all", response_model=List[ProduccionHuevosOut])
def get_all_produccion_huevos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user),
    limit: int = Query(10, ge=1, description="Cantidad máxima de registros por página"),
    offset: int = Query(0, ge=0, description="Número de registros a saltar para paginación"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: Optional[str] = Query(None, description="Fecha final en formato YYYY-MM-DD")
):
    """
    Obtiene todas las producciones de huevos con JOINs a galpones y tipo_huevos,
    con paginación y filtrado por rango de fechas.
    """
    try:
        # Verificar permisos del usuario
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        producciones = crud_produccion.get_all_produccion_huevos(
            db,
            limit=limit,
            offset=offset,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        return producciones

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{produccion_id}")
def update_produccion_huevos(
    produccion_id: int,
    produccion: ProduccionHuevosUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_produccion.update_produccion_huevos_by_id(db, produccion_id, produccion)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar la producción de huevos")
        return {"message": "Producción de huevos actualizada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.delete("/by-id/{produccion_id}")
def delete_produccion_huevos(
    produccion_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Elimina una producción de huevos por ID
    """
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'borrar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        # Eliminar la producción
        success = crud_produccion.delete_produccion_huevos_by_id(db, produccion_id)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo eliminar la producción de huevos")
        
        return {"message": "Producción de huevos eliminada correctamente"}
        
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")