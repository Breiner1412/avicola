from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
import logging
import secrets
from datetime import datetime, timedelta
from core.security import get_hashed_password
from app.schemas.users import UserCreate, UserUpdate
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def create_user(db: Session, user: UserCreate) -> Optional[bool]:
    try:
        pass_encript = get_hashed_password(user.pass_hash)
        user.pass_hash = pass_encript
        sentencia = text("""
            INSERT INTO usuarios (
                nombre, documento, id_rol,
                email, pass_hash,
                telefono, estado
            ) VALUES (
                :nombre, :documento, :id_rol,
                :email, :pass_hash,
                :telefono, :estado
            )
        """)
        db.execute(sentencia, user.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear usuario: {e}")


        error_msg = str(e.__cause__)


        if "Duplicate entry" in error_msg and "email" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El correo ya está registrado."
            )
        if "Duplicate entry" in error_msg and "documento" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El número de documento ya existe."
            )

        raise HTTPException(
            status_code=500,
            detail="Error interno al crear el usuario."
        )
        # raise Exception("Error de base de datos al crear el usuario")

def get_user_by_email_for_login(db: Session, email: str):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, pass_hash, roles.descripcion as descripcion_rol
                     FROM usuarios
                     JOIN roles ON usuarios.id_rol = roles.id_rol
                     WHERE email = :correo
                     """)
        result = db.execute(query, {"correo": email}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por email: {e}")
        raise Exception("Error de base de datos al obtener el usuario")



def get_user_by_email(db: Session, email: str):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, roles.descripcion as descripcion_rol
                     FROM usuarios
                     JOIN roles ON usuarios.id_rol = roles.id_rol
                     WHERE email = :correo
                     """)
        result = db.execute(query, {"correo": email}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por email: {e}")
        raise Exception("Error de base de datos al obtener el usuario")



def get_all_user_except_admins(db: Session):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, roles.descripcion as descripcion_rol 
                     FROM usuarios
                     JOIN roles ON usuarios.id_rol = roles.id_rol
                     WHERE usuarios.id_rol NOT IN (1,2)
                     """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los usuarios: {e}")
        raise Exception("Error de base de datos al obtener los usuarios")
    


def update_user_by_id(db: Session, user_id: int, user: UserUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        user_data = user.model_dump(exclude_unset=True)
        if not user_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in user_data.keys()])
        sentencia = text(f"""
            UPDATE usuarios 
            SET {set_clauses}
            WHERE id_usuario = :id_usuario
        """)

        # Agregar el id_usuario
        user_data["id_usuario"] = user_id

        result = db.execute(sentencia, user_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar usuario {user_id}: {e}")
        error_msg = str(e.__cause__)
        if "Duplicate entry" in error_msg and "email" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El correo ya está registrado."
            )
        if "Duplicate entry" in error_msg and "documento" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El número de documento ya existe."
            )

        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el usuario."
        )
        # raise Exception("Error de base de datos al actualizar el usuario")


def get_user_by_id(db: Session, id: int):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol
                     FROM usuarios
                     JOIN roles ON usuarios.id_rol = roles.id_rol
                     WHERE id_usuario = :id_user
                     """)
        result = db.execute(query, {"id_user": id}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por id: {e}")
        raise Exception("Error de base de datos al obtener el usuario")
    
def get_user_by_document_number(db: Session, document: str):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, roles.descripcion as descripcion_rol 
                     FROM usuarios INNER JOIN roles ON usuarios.id_rol=roles.id_rol
                     WHERE usuarios.documento = :document
                """)
        result = db.execute(query, {"document": document}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por su documento: {e}")
        raise Exception("Error de base de datos al obtener el usuario")

def get_user_by_role(db: Session, role: str):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, roles.descripcion as descripcion_rol
                     FROM usuarios INNER JOIN roles ON usuarios.id_rol=roles.id_rol
                     WHERE LOWER(roles.nombre_rol) = LOWER(:role)
                """)
        result = db.execute(query, {"role": role}).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por rol: {e}")
        raise Exception("Error de base de datos al obtener los usuarios")

def change_user_status(db: Session, id_usuario: int, nuevo_estado: bool) -> bool:
    try:
        sentencia = text("""
            UPDATE usuarios
            SET estado = :estado
            WHERE id_usuario = :id_usuario
        """)
        result = db.execute(sentencia, {"estado": nuevo_estado, "id_usuario": id_usuario})
        db.commit()

        return result.rowcount > 0

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar el estado del usuario {id_usuario}: {e}")
        raise Exception("Error de base de datos al cambiar el estado del usuario")

def get_all_user_except_superadmins(db: Session):
    try:
        query = text("""SELECT id_usuario, nombre, documento, usuarios.id_rol, email, telefono, usuarios.estado, nombre_rol, roles.descripcion as descripcion_rol
                     FROM usuarios
                     JOIN roles ON usuarios.id_rol = roles.id_rol
                     WHERE usuarios.id_rol NOT IN (1)
                     """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los usuarios: {e}")
        raise Exception("Error de base de datos al obtener los usuarios")

def save_reset_token(db: Session, email: str) -> Optional[str]:
    try:
        reset_token = f"{secrets.randbelow(1_000_000):06d}"
        token_expiry = datetime.now() + timedelta(hours=1)
        
        query = text("""
            UPDATE usuarios 
            SET reset_token = :token, 
                reset_token_expiry = :expiry
            WHERE email = :email
        """)
        
        result = db.execute(query, {
            "token": reset_token,
            "expiry": token_expiry,
            "email": email
        })
        db.commit()
        
        if result.rowcount > 0:
            return reset_token
        return None
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al guardar token de recuperación: {e}")
        raise Exception("Error al generar token de recuperación")
    
def get_user_by_reset_token(db: Session, email: str, token: str):
    try:
        query = text("""
            SELECT id_usuario, email, reset_token, reset_token_expiry
            FROM usuarios
            WHERE email = :email
            AND reset_token = :token 
            AND reset_token_expiry > :now
        """)
        
        result = db.execute(query, {
            "email": email,
            "token": token,
            "now": datetime.now()
        }).mappings().first()
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener usuario por token: {e}")
        raise Exception("Error al validar token de recuperación")


def update_password_with_token(db: Session, email: str, token: str, new_password: str) -> bool:
    """Cambia la contraseña solo si el código corresponde a ESE correo y no ha expirado."""
    try:
        user = get_user_by_reset_token(db, email, token)
        if not user:
            return False
        
        hashed_password = get_hashed_password(new_password)
        
        query = text("""
            UPDATE usuarios 
            SET pass_hash = :new_password,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id_usuario = :id_usuario
              AND reset_token = :token
        """)
        
        result = db.execute(query, {
            "new_password": hashed_password,
            "id_usuario": user["id_usuario"],
            "token": token
        })
        db.commit()
        
        return result.rowcount > 0
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar contraseña: {e}")
        raise Exception("Error al actualizar la contraseña")


def clear_reset_token(db: Session, email: str) -> None:
    """Invalida el código de recuperación pendiente de un correo."""
    try:
        db.execute(text("""
            UPDATE usuarios
            SET reset_token = NULL, reset_token_expiry = NULL
            WHERE email = :email
        """), {"email": email})
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al invalidar token de recuperación: {e}")
        raise Exception("Error al invalidar el código de recuperación")
