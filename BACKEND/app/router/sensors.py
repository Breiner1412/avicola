from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.sensors import SensorCreate, SensorOut, SensorUpdate
from app.schemas.users import UserOut
from app.crud import sensors as crud_sensors

router = APIRouter()
modulo = 16

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_sensor(
    sensor: SensorCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "insertar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para crear sensores")
        crud_sensors.create_sensor(db, sensor)
        return {"message": "Sensor creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id/{id_sensor}", response_model=SensorOut)
def get_sensor(
    id_sensor: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para ver sensores")
        sensor = crud_sensors.get_sensor_by_id(db, id_sensor)
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        return sensor
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all", response_model=List[SensorOut])
def get_all_sensores(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para consultar sensores")
        sensores = crud_sensors.get_all_sensores(db)
        return sensores
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-galpon/{id_galpon}", response_model=List[SensorOut])
def get_sensores_by_galpon(
    id_galpon: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para consultar sensores")
        sensores = crud_sensors.get_sensores_by_galpon(db, id_galpon)
        return sensores
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{id_sensor}")
def update_sensor(
    id_sensor: int,
    sensor: SensorUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para actualizar sensores")
        success = crud_sensors.update_sensor_by_id(db, id_sensor, sensor)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el sensor")
        return {"message": "Sensor actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/cambiar-estado/{id_sensor}", status_code=status.HTTP_200_OK)
def change_sensor_status(
    id_sensor: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        success = crud_sensors.change_sensor_status(db, id_sensor, nuevo_estado)
        if not success:
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
        return {"message": f"Estado del sensor actualizado a {nuevo_estado}"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
