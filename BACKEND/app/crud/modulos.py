from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.schemas.modulos import ModuloCreate, ModuloUpdate

logger = logging.getLogger(__name__)


def create_modulo(db: Session, modulo: ModuloCreate):
    try:
        sentencia = text("""
            INSERT INTO modulos (nombre_modulo)
            VALUES (:nombre_modulo)
        """)
        db.execute(sentencia, {"nombre_modulo": modulo.nombre_modulo})
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear módulo: {e}")
        raise Exception("Error al crear el módulo")


def get_all_modulos(db: Session):
    try:
        query = text("SELECT * FROM modulos ORDER BY id_modulo ASC")
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener módulos: {e}")
        raise Exception("Error al obtener los módulos")

def get_modulo_by_id(db: Session, id_modulo: int):
    try:
        query = text("SELECT * FROM modulos WHERE id_modulo = :id_modulo")
        result = db.execute(query, {"id_modulo": id_modulo}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener módulo {id_modulo}: {e}")
        raise Exception("Error al obtener el módulo")


def update_modulo(db: Session, id_modulo: int, modulo: ModuloUpdate):
    try:
        fields = modulo.model_dump(exclude_unset=True)
        if not fields:
            return False

        set_clause = ", ".join([f"{key} = :{key}" for key in fields.keys()])
        fields["id_modulo"] = id_modulo

        query = text(f"UPDATE modulos SET {set_clause} WHERE id_modulo = :id_modulo")
        result = db.execute(query, fields)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar módulo {id_modulo}: {e}")
        raise Exception("Error al actualizar el módulo")

def change_modulo_status(db: Session, id_modulo: int, estado: bool) -> bool:
    try:
        sentencia = text("""
            UPDATE modulos
            SET estado = :estado
            WHERE id_modulo = :id_modulo
        """)
        result = db.execute(sentencia, {"estado": estado, "id_modulo": id_modulo})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar estado del módulo {id_modulo}: {e}")
        raise Exception("Error de base de datos al cambiar estado del módulo")