from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from app.schemas.users import UserOut
from app.schemas.tipo_huevos import TipoHuevosCreate, TipoHuevosUpdate, TipoHuevosOut
from core.database import get_db
from app.crud import tipo_huevos as crud_tipo_huevos



router = APIRouter()
modulo = 25  # tipo_huevos (ver database/02_seed.sql)

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_tipo_huevo(
    tipo_huevo: TipoHuevosCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        crud_tipo_huevos.create_tipo_huevo(db, tipo_huevo)
        return {"message": "Tipo de huevo creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-id/{id_tipo_huevo}", response_model=TipoHuevosOut)
def get_tipo_huevo(
    id_tipo_huevo: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        tipo_huevo = crud_tipo_huevos.get_tipo_huevo_by_id(db, id_tipo_huevo)
        if not tipo_huevo:
            raise HTTPException(status_code=404, detail="Tipo de huevo no encontrado")
        return tipo_huevo
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all", response_model=List[TipoHuevosOut])
def get_all_tipo_huevos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        tipos = crud_tipo_huevos.get_all_tipo_huevos(db)
        return tipos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.put("/by-id/{id_tipo_huevo}")
def update_tipo_huevo(
    id_tipo_huevo: int,
    tipo_huevo: TipoHuevosUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_tipo_huevos.update_tipo_huevo_by_id(db, id_tipo_huevo, tipo_huevo)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el tipo de huevo")
        return {"message": "Tipo de huevo actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
