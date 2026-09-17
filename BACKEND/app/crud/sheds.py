from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Optional
import logging

from app.schemas.sheds import ShedCreate, ShedUpdate

logger = logging.getLogger(__name__)

def create_shed(db: Session, shed: ShedCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO galpones (
                id_finca, nombre,
                capacidad, cant_actual,
                estado
            ) VALUES (
                :id_finca, :nombre,
                :capacidad, :cant_actual,
                :estado
            )
        """)
        db.execute(sentencia, shed.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el galpón: {e}")
        raise Exception("Error de base de datos al crear el galpón")

def get_shed_by_id(db: Session, id: int):
    try:
        query = text("""
                     SELECT g.id_galpon, g.id_finca, g.nombre,
                     g.capacidad, g.cant_actual, g.estado, f.nombre as nombre_finca
                     FROM galpones g 
                     JOIN fincas f ON g.id_finca = f.id_finca
                     WHERE g.id_galpon = :id_galpon
                     """)
        result = db.execute(query, {"id_galpon": id}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener galpón por el id: {e}")
        raise Exception("Error de base de datos al obtener el galpón")

def get_active_sheds(db: Session):
    try:
        query = text("""
            SELECT id_galpon, nombre
            FROM galpones
            WHERE estado = true
            ORDER BY nombre
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener galpones activos: {e}")
        raise Exception("Error de base de datos al obtener los galpones activos")
    
def get_all_sheds(db: Session):
    try:
        query = text("""
            SELECT g.id_galpon, g.id_finca, g.nombre,
            g.capacidad, g.cant_actual, g.estado, f.nombre as nombre_finca
            FROM galpones g 
            JOIN fincas f ON g.id_finca = f.id_finca
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener tipos de galpones: {e}")
        raise Exception("Error de base de datos al obtener los galpones")
    
def get_active_lands(db: Session):
    try:
        query = text("""
            SELECT id_finca, nombre
            FROM fincas
            WHERE estado = true
        """)
        result = db.execute(query).mappings().all()
        return result

    except SQLAlchemyError as e:
        logger.error(f"Error al obtener fincas activas: {e}")
        raise Exception("Error de base de datos al obtener las fincas activas")

def get_sheds_by_lands(db: Session, id_finca: int):
    try:
        query = text("""
            SELECT g.id_galpon, g.id_finca, g.nombre,
                   g.capacidad, g.cant_actual, g.estado, f.nombre as nombre_finca
            FROM galpones g
            JOIN fincas f ON g.id_finca = f.id_finca
            WHERE g.id_finca = :id_finca
        """)
        result = db.execute(query, {"id_finca": id_finca}).mappings().all()

        if not result:
            return {"message": "La finca no tiene galpones asignados"}
        return result

    except SQLAlchemyError as e:
        logger.error(f"Error al obtener galpones por finca: {e}")
        raise Exception("Error de base de datos al obtener los galpones por finca") 

def update_shed_by_id(db: Session, shed_id: int, shed: ShedUpdate) -> Optional[bool]:
    try:
        shed_data = shed.model_dump(exclude_unset=True)
        if not shed_data:
            raise Exception("No se enviaron campos para actualizar")

        set_clauses = ", ".join([f"{key} = :{key}" for key in shed_data.keys()])
        sentencia = text(f"""
            UPDATE galpones 
            SET {set_clauses}
            WHERE id_galpon = :id_galpon
        """)

        # Agregar el id_galpon
        shed_data["id_galpon"] = shed_id

        result = db.execute(sentencia, shed_data)
        db.commit()

        return result.rowcount > 0
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar galpón {shed_id}: {e}")
        raise Exception("Error de base de datos al actualizar el galpón")
    
def change_shed_status(db: Session, id_galpon: int, nuevo_estado: bool) -> bool:
    try:
        sentencia = text("""
            UPDATE galpones
            SET estado = :estado
            WHERE id_galpon = :id_galpon
        """)
        result = db.execute(sentencia, {"estado": nuevo_estado, "id_galpon": id_galpon})
        db.commit()

        return result.rowcount > 0

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar el estado del galpón {id_galpon}: {e}")
        raise Exception("Error de base de datos al cambiar el estado del galpón")
