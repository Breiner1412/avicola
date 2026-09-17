from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging
from app.schemas.sensor_types import SensorTypeCreate, SensorTypeUpdate

logger = logging.getLogger(__name__)

def create_sensor_type(db: Session, tipo: SensorTypeCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO tipo_sensores(
                nombre, descripcion, modelo, estado
            ) VALUES (
                :nombre, :descripcion, :modelo, :estado
            )
        """)
        db.execute(sentencia, tipo.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear tipo de sensor: {e}")
        raise Exception("Error de base de datos al crear el tipo de sensor")


def get_sensor_type_by_id(db: Session, id_tipo: int):
    try:
        query = text("""
            SELECT id_tipo, nombre, descripcion, modelo, estado
            FROM tipo_sensores
            WHERE id_tipo = :id
        """)
        result = db.execute(query, {"id": id_tipo}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener tipo de sensor: {e}")
        raise Exception("Error de base de datos al obtener el tipo de sensor")
        
def get_active_sensor_types(db: Session):
    try:
        query = text("""
            SELECT id_tipo, nombre, modelo
            FROM tipo_sensores
            WHERE estado = true
            ORDER BY nombre
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener tipos de sensores activos: {e}")
        raise Exception("Error de base de datos al obtener los tipos de sensores activos")

def get_all_sensor_types(db: Session):
    try:
        query = text("""
            SELECT id_tipo, nombre, descripcion, modelo, estado
            FROM tipo_sensores
            ORDER BY nombre
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener tipos de sensores: {e}")
        raise Exception("Error de base de datos al obtener los tipos de sensores")


def update_sensor_type_by_id(db: Session, id_tipo: int, tipo: SensorTypeUpdate) -> Optional[bool]:
    try:
        tipo_data = tipo.model_dump(exclude_unset=True)
        if not tipo_data:
            return False

        set_clauses = ", ".join([f"{key} = :{key}" for key in tipo_data.keys()])
        sentencia = text(f"""
            UPDATE tipo_sensores 
            SET {set_clauses}
            WHERE id_tipo = :id_tipo
        """)

        tipo_data["id_tipo"] = id_tipo
        result = db.execute(sentencia, tipo_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar tipo de sensor {id_tipo}: {e}")
        raise Exception("Error de base de datos al actualizar el tipo de sensor")


def change_sensor_type_status(db: Session, id_tipo: int, nuevo_estado: bool) -> bool:
    try:
        sentencia_tipo = text("""
            UPDATE tipo_sensores
            SET estado = :estado
            WHERE id_tipo = :id_tipo
        """)
        result_tipo = db.execute(sentencia_tipo, {"estado": nuevo_estado, "id_tipo": id_tipo})

        if not nuevo_estado:
            sentencia_sensores = text("""
                UPDATE sensores
                SET estado = FALSE
                WHERE id_tipo_sensor = :id_tipo
            """)
            db.execute(sentencia_sensores, {"id_tipo": id_tipo})

        db.commit()
        return result_tipo.rowcount > 0

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar estado del tipo de sensor {id_tipo}: {e}")
        raise Exception("Error de base de datos al cambiar el estado del tipo de sensor")
