from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.sensor_types import SensorTypeCreate, SensorTypeOut, SensorTypeUpdate
from app.schemas.users import UserOut
from app.crud import sensor_types as crud_sensor_types

router = APIRouter()
modulo = 17

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_sensor_type(
    tipo: SensorTypeCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "insertar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para crear tipos de sensores")
        crud_sensor_types.create_sensor_type(db, tipo)
        return {"message": "Tipo de sensor creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id/{id_tipo}", response_model=SensorTypeOut)
def get_sensor_type(
    id_tipo: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para ver tipos de sensores")
        tipo = crud_sensor_types.get_sensor_type_by_id(db, id_tipo)
        if not tipo:
            raise HTTPException(status_code=404, detail="Tipo de sensor no encontrado")
        return tipo
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/activos")
def get_active_sensor_types(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        tipos_activos = crud_sensor_types.get_active_sensor_types(db)
        return tipos_activos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all", response_model=List[SensorTypeOut])
def get_all_sensor_types(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para consultar tipos de sensores")
        tipos = crud_sensor_types.get_all_sensor_types(db)
        return tipos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{id_tipo}")
def update_sensor_type(
    id_tipo: int,
    tipo: SensorTypeUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para actualizar tipos de sensores")
        success = crud_sensor_types.update_sensor_type_by_id(db, id_tipo, tipo)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el tipo de sensor")
        return {"message": "Tipo de sensor actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/cambiar-estado/{id_tipo}", status_code=status.HTTP_200_OK)
def change_sensor_type_status(
    id_tipo: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        success = crud_sensor_types.change_sensor_type_status(db, id_tipo, nuevo_estado)
        if not success:
            raise HTTPException(status_code=404, detail="Tipo de sensor no encontrado")
        return {"message": f"Estado del tipo de sensor actualizado a {nuevo_estado}"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
