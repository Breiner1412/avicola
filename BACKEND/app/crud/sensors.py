from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging
from app.schemas.sensors import SensorCreate, SensorUpdate

logger = logging.getLogger(__name__)

def create_sensor(db: Session, sensor: SensorCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO sensores(
                nombre, id_tipo_sensor, id_galpon, descripcion, estado
            ) VALUES (
                :nombre, :id_tipo_sensor, :id_galpon, :descripcion, :estado
            )
        """)
        db.execute(sentencia, sensor.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear sensor: {e}")
        raise Exception("Error de base de datos al crear el sensor")


def get_sensor_by_id(db: Session, id_sensor: int):
    try:
        query = text("""
            SELECT 
                s.id_sensor, s.nombre, s.id_tipo_sensor, s.id_galpon, s.descripcion, s.estado,
                t.nombre AS nombre_tipo, t.modelo AS modelo_tipo, g.nombre AS nombre_galpon
            FROM sensores s
            INNER JOIN tipo_sensores t ON s.id_tipo_sensor = t.id_tipo
            INNER JOIN galpones g ON s.id_galpon = g.id_galpon
            WHERE s.id_sensor = :id
        """)
        result = db.execute(query, {"id": id_sensor}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener sensor: {e}")
        raise Exception("Error de base de datos al obtener el sensor")


def get_all_sensores(db: Session):
    try:
        query = text("""
            SELECT 
                s.id_sensor, s.nombre, s.id_tipo_sensor, s.id_galpon, s.descripcion, s.estado,
                t.nombre AS nombre_tipo, t.modelo AS modelo_tipo, g.nombre AS nombre_galpon
            FROM sensores s
            INNER JOIN tipo_sensores t ON s.id_tipo_sensor = t.id_tipo
            INNER JOIN galpones g ON s.id_galpon = g.id_galpon
            ORDER BY s.nombre
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener sensores: {e}")
        raise Exception("Error de base de datos al obtener los sensores")


def get_sensores_by_galpon(db: Session, id_galpon: int):
    try:
        query = text("""
            SELECT 
                s.id_sensor, s.nombre, s.id_tipo_sensor, s.id_galpon, s.descripcion, s.estado,
                t.nombre AS nombre_tipo, t.modelo AS modelo_tipo, g.nombre AS nombre_galpon
            FROM sensores s
            INNER JOIN tipo_sensores t ON s.id_tipo_sensor = t.id_tipo
            INNER JOIN galpones g ON s.id_galpon = g.id_galpon
            WHERE s.id_galpon = :id_galpon
            ORDER BY s.nombre
        """)
        result = db.execute(query, {"id_galpon": id_galpon}).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener sensores por galpón: {e}")
        raise Exception("Error de base de datos al obtener los sensores")


def update_sensor_by_id(db: Session, id_sensor: int, sensor: SensorUpdate) -> Optional[bool]:
    try:
        sensor_data = sensor.model_dump(exclude_unset=True)
        if not sensor_data:
            return False

        set_clauses = ", ".join([f"{key} = :{key}" for key in sensor_data.keys()])
        sentencia = text(f"""
            UPDATE sensores 
            SET {set_clauses}
            WHERE id_sensor = :id_sensor
        """)

        sensor_data["id_sensor"] = id_sensor
        result = db.execute(sentencia, sensor_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar sensor {id_sensor}: {e}")
        raise Exception("Error de base de datos al actualizar el sensor")


def change_sensor_status(db: Session, id_sensor: int, nuevo_estado: bool) -> bool:
    try:
        sentencia = text("""
            UPDATE sensores
            SET estado = :estado
            WHERE id_sensor = :id_sensor
        """)
        result = db.execute(sentencia, {"estado": nuevo_estado, "id_sensor": id_sensor})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        mensaje_error = str(e)
        if "45000" in mensaje_error or "No se puede activar" in mensaje_error:
            raise Exception("No se puede activar un sensor de un tipo de sensor inactivo")
        raise Exception("Error de base de datos al cambiar el estado del sensor")
