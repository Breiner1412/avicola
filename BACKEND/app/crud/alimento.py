from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.alimento import AlimentoCreate, AlimentoUpdate

logger = logging.getLogger(__name__)

def create_type_alimento(db: Session, alimento: AlimentoCreate) -> Optional[bool]:
    try:
        # Crear nuevo registro
        insert_query = text("""
            INSERT INTO alimento (nombre, cantidad, fecha_ingreso)
            VALUES (:nombre, :cantidad, :fecha_ingreso)
        """)

        db.execute(insert_query, alimento.model_dump())
        db.commit()

        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el tipo de alimento: {e}")
        raise Exception("Error de base de datos al crear el tipo de alimento")

def get_type_alimento_by_id(db: Session, id_alimento: int):
    try:
        query = text("""SELECT * FROM alimento
                    WHERE id_alimento = :id_alimento""")
        result = db.execute(query, {"id_alimento": id_alimento}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el tipo de alimento por id: {e}")
        raise Exception("Error de base de datos al obtener el tipo de alimento")

def get_all_alimentos(db: Session):
    try:
        query = text("""SELECT id_alimento, nombre, cantidad, fecha_ingreso
                     FROM alimento
                     ORDER BY nombre""")
        return db.execute(query).mappings().all()
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los alimentos: {e}")
        raise Exception("Error de base de datos al obtener los alimentos")

def get_all_type_alimentos_pag(db: Session, skip:int = 0, limit = 10):
    try:
        count_query = text("""SELECT COUNT(id_alimento) AS total 
                     FROM alimento 
                     """)
        total_result = db.execute(count_query).scalar()
        
        query = text("""SELECT * FROM alimento
                     ORDER BY fecha_ingreso DESC
                     LIMIT :limit OFFSET :skip""")
        alimento_list = db.execute(query,{"skip": skip, "limit": limit}).mappings().all()
        
        return {
                "total": total_result or 0,
                "alimento": alimento_list
            }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los tipos de alimentos: {e}")
        raise Exception("Error de base de datos al obtener los tipos de alimentos")

def update_type_alimento_by_id(db: Session, id_alimento: int, alimento: AlimentoUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        alimento_data = alimento.model_dump(exclude_unset=True)
        if not alimento_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in alimento_data.keys()])
        sentencia = text(f"""
            UPDATE alimento 
            SET {set_clauses}
            WHERE id_alimento = :id_alimento
        """)

        alimento_data["id_alimento"] = id_alimento

        result = db.execute(sentencia, alimento_data)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el tipo de alimento {id_alimento}: {e}")
        raise Exception("Error de base de datos al actualizar el tipo de alimento")
    
def get_alimento_by_date_range(db: Session, fecha_inicio: str, fecha_fin: str):
    """
    Obtiene las tareas cuya fecha de inicio o fin esté dentro de un rango de fechas.
    Ignora las horas (usa DATE(fecha_hora_init) y DATE(fecha_hora_fin)).
    """
    try:
        query = text("""
            SELECT id_alimento, alimento.nombre, cantidad, alimento.fecha_ingreso
                FROM alimento
                WHERE DATE(fecha_ingreso) BETWEEN :fecha_inicio AND :fecha_fin
                ORDER BY fecha_ingreso DESC
        """)
        result = db.execute(query, {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }).mappings().all()
        
        return [dict(row) for row in result]

    except SQLAlchemyError as e:
        raise Exception(f"Error al consultar los aislamientos por rango de fechas: {e}")

