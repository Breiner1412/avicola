from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from app.schemas.permisos import PermisoCreate, PermisoOut, PermisoUpdate
from app.schemas.users import UserOut
from app.crud import modulo_permisos as modulo_permisos
from app.crud.permisos import verify_permissions  # tu función actual de verificación
from app.router.dependencies import get_current_user
from core.database import get_db

router = APIRouter()
modulo = 2  # ID asignados

# Obtener todos los permisos
@router.get("/todas", response_model=List[PermisoOut])
def get_all_permisos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    id_rol = user_token.id_rol
    if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
        raise HTTPException(status_code=401, detail="Usuario no autorizado para ver permisos")
    try:
        permisos = modulo_permisos.get_all_permisos(db)
        return permisos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Crear permiso
@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_permiso(
    permiso_data: PermisoCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    id_rol = user_token.id_rol
    if not verify_permissions(db, id_rol, modulo, 'insertar'):
        raise HTTPException(status_code=401, detail="Usuario no autorizado para crear permisos")
    try:
        modulo_permisos.create_permiso(db, permiso_data)
        return {"message": "Permiso creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Obtener permiso por id_modulo e id_rol
@router.get("/{id_modulo}/{id_rol}", response_model=PermisoOut)
def get_permiso_by_ids(
    id_modulo: int,
    id_rol: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    id_rol_user = user_token.id_rol
    if not verify_permissions(db, id_rol_user, modulo, 'seleccionar'):
        raise HTTPException(status_code=401, detail="Usuario no autorizado para ver permisos")
    try:
        permiso = modulo_permisos.get_permiso_by_ids(db, id_modulo, id_rol)
        if not permiso:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")
        return permiso
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Actualizar permiso
@router.put("/{id_modulo}/{id_rol}")
def update_permiso(
    id_modulo: int,
    id_rol: int,
    permiso_data: PermisoUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    id_rol_user = user_token.id_rol
    if not verify_permissions(db, id_rol_user, modulo, 'actualizar'):
        raise HTTPException(status_code=401, detail="Usuario no autorizado para actualizar permisos")
    try:
        success = modulo_permisos.update_permiso(db, id_modulo, id_rol, permiso_data)
        if not success:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")
        return {"message": "Permiso actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")