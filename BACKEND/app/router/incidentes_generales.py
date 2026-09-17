from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud import incidentes_generales as crud_incidentes
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from app.schemas.users import UserOut
from app.schemas.incidentes_generales import (
    IncidenteGeneralCreate, IncidenteGeneralUpdate, 
    IncidenteGeneralOut, IncidenteGeneralPaginado
)
from core.database import get_db

router = APIRouter()
modulo = 13

# Crear incidente general
@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_incidente(
    incidente: IncidenteGeneralCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "insertar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        crud_incidentes.create_incidente(db, incidente)
        return {"message": "Incidente general creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Obtener incidente por ID
@router.get("/by-id/{id_incidente}", response_model=IncidenteGeneralOut)
def get_incidente(
    id_incidente: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        incidente = crud_incidentes.get_incidente_by_id(db, id_incidente)
        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")
        return incidente

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
        
@router.get("/fincas/activas")
def listar_fincas_activas(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        lands = crud_incidentes.get_active_lands(db)
        return lands
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Listar todos los incidentes CON PAGINACIÓN
@router.get("/all", response_model=IncidenteGeneralPaginado)
def get_all_incidentes(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        result = crud_incidentes.get_all_incidentes(db, skip=skip, limit=limit)
        return result
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Listar incidentes filtrados por estado (activos/inactivos)
@router.get("/by-estado/{esta_resuelta}", response_model=IncidenteGeneralPaginado)
def get_incidentes_by_estado(
    esta_resuelta: bool,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        result = crud_incidentes.get_incidentes_by_estado(db, esta_resuelta, skip=skip, limit=limit)
        return result
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Actualizar incidente
@router.put("/by-id/{id_incidente}")
def update_incidente(
    id_incidente: int,
    incidente: IncidenteGeneralUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_incidentes.update_incidente_by_id(db, id_incidente, incidente)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el incidente")

        return {"message": "Incidente actualizado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Eliminar incidente
@router.delete("/by-id/{id_incidente}")
def delete_incidente(
    id_incidente: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "borrar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_incidentes.delete_incidente_by_id(db, id_incidente)
        if not success:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        return {"message": "Incidente eliminado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Cambiar estado del incidente
@router.put("/cambiar-estado/{id_incidente}")
def cambiar_estado_incidente_general(
    id_incidente: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        actualizado = crud_incidentes.toggle_estado_incidente(db, id_incidente)
        if not actualizado:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        return {"message": "Estado del incidente general cambiado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
