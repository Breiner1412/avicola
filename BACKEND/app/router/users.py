from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.crud import users as crud_users
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()
modulo = 4             # Módulo de usuarios
MODULO_ADMINS = 10     # Módulo para gestionar administradores
ROL_SUPERADMIN = 1
ROL_ADMIN = 2
ROLES_ADMIN = (ROL_SUPERADMIN, ROL_ADMIN)


def _verificar_gestion_usuario(db: Session, user_token, id_rol_destino: int, accion: str):
    """
    Valida que quien hace la petición pueda gestionar a un usuario del rol indicado.
    - Usuarios normales: permiso del módulo 4.
    - Administradores (rol 1 y 2): permiso del módulo 10.
    - Un superadmin solo puede ser gestionado por otro superadmin.
    """
    if id_rol_destino == ROL_SUPERADMIN and user_token.id_rol != ROL_SUPERADMIN:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")

    modulo_requerido = MODULO_ADMINS if id_rol_destino in ROLES_ADMIN else modulo
    if not verify_permissions(db, user_token.id_rol, modulo_requerido, accion):
        raise HTTPException(status_code=401, detail="Usuario no autorizado")


def _obtener_usuario_destino(db: Session, user_id: int):
    destino = crud_users.get_user_by_id(db, user_id)
    if not destino:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return destino


@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        _verificar_gestion_usuario(db, user_token, user.id_rol, 'insertar')
        crud_users.create_user(db, user)
        return {"message": "Usuario creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al crear el usuario")


@router.get("/by-email", response_model=UserOut)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if email.lower() != (user_token.email or "").lower():
            if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
                raise HTTPException(status_code=401, detail='Usuario no autorizado')

        user = crud_users.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el usuario")


@router.get("/all-except-admins", response_model=List[UserOut])
def get_users(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        return crud_users.get_all_user_except_admins(db)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener los usuarios")


@router.put("/by-id/{user_id}")
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        destino = _obtener_usuario_destino(db, user_id)
        # Cada usuario puede editar sus propios datos (perfil);
        # para editar a otros se validan permisos según el rol del destino.
        if user_id != user_token.id_usuario:
            _verificar_gestion_usuario(db, user_token, destino.id_rol, 'actualizar')

        success = crud_users.update_user_by_id(db, user_id, user)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el usuario")
        return {"message": "Usuario actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al actualizar el usuario")


@router.get("/by-document", response_model=UserOut)
def get_user_by_document(
    document: str,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        user = crud_users.get_user_by_document_number(db, document)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el usuario")


@router.get("/by-role", response_model=List[UserOut])
def get_users_by_role(
    role: str,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        return crud_users.get_user_by_role(db, role)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener los usuarios")


@router.put("/cambiar-estado/{user_id}", status_code=status.HTTP_200_OK)
def change_user_status(
    user_id: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    if user_id == user_token.id_usuario and not nuevo_estado:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario")

    destino = _obtener_usuario_destino(db, user_id)
    _verificar_gestion_usuario(db, user_token, destino.id_rol, 'actualizar')

    success = crud_users.change_user_status(db, user_id, nuevo_estado)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"message": f"Estado del usuario actualizado a {nuevo_estado}"}


@router.get("/all-users-except-superadmins", response_model=List[UserOut])
def get_users_except_superadmins(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, MODULO_ADMINS, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        return crud_users.get_all_user_except_superadmins(db)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener los usuarios")
