from app.schemas.modulos import ModuloCreate, ModuloOut, ModuloUpdate
from app.schemas.users import UserOut
from app.crud import modulos as crud_modulos
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from sqlalchemy.exc import SQLAlchemyError

from typing import List

router = APIRouter()
modulo = 1  # ID del módulo 


@router.get("/todas", response_model=List[ModuloOut])
def get_all_modulos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para ver módulos")

        modulos = crud_modulos.get_all_modulos(db)
        return modulos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_modulo(
    modulo_data: ModuloCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para crear módulos")

        crud_modulos.create_modulo(db, modulo_data)
        return {"message": "Módulo creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Obtener módulo por ID
@router.get("/{id_modulo}", response_model=ModuloOut)
def get_modulo_by_id(
    id_modulo: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        modulo_data = crud_modulos.get_modulo_by_id(db, id_modulo)
        if not modulo_data:
            raise HTTPException(status_code=404, detail="Módulo no encontrado")
        return modulo_data
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Actualizar módulo
@router.put("/{id_modulo}")
def update_modulo(
    id_modulo: int,
    modulo_data: ModuloUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para editar módulos")

        success = crud_modulos.update_modulo(db, id_modulo, modulo_data)
        if not success:
            raise HTTPException(status_code=404, detail="No se encontró el módulo")
        return {"message": "Módulo actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.put("/cambiar-estado/{modulo_id}", status_code=status.HTTP_200_OK)
def change_module_status(
    modulo_id: int,
    activo: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_modulos.change_modulo_status(db, modulo_id, activo)
        if not success:
            raise HTTPException(status_code=404, detail="Módulo no encontrado")

        estado_texto = "activado" if activo else "desactivado"
        return {"message": f"Módulo {estado_texto} correctamente"}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")