from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.isolation import IsolationCreate, IsolationUpdate

logger = logging.getLogger(__name__)

def create_isolation(db: Session, isolation: IsolationCreate) -> Optional[bool]:
    try:
        query = text("""
            INSERT INTO aislamiento (
                id_incidente_gallina, fecha_hora, id_galpon
            ) VALUES (
                :id_incidente_gallina, :fecha_hora, :id_galpon
            )
        """)
        db.execute(query, isolation.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el aislamiento: {e}")
        raise Exception("Error de base de datos al crear el aislamiento")


def get_isolation_by_id(db: Session, id_isolation: int):
    try:
        query = text("""SELECT id_aislamiento, id_incidente_gallina, fecha_hora, aislamiento.id_galpon, galpones.nombre                    
                    FROM aislamiento
                    INNER JOIN galpones ON galpones.id_galpon = aislamiento.id_galpon   
                    WHERE id_aislamiento = :aislamiento_id""")
        result = db.execute(query, {"aislamiento_id": id_isolation}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener aislamiento por id: {e}")
        raise Exception("Error de base de datos al obtener el aislamiento")

def get_all_isolations(db: Session):
    try:
        query = text("""SELECT id_aislamiento, id_incidente_gallina, fecha_hora, aislamiento.id_galpon, galpones.nombre
                    FROM aislamiento
                    INNER JOIN galpones ON galpones.id_galpon = aislamiento.id_galpon
                    """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los aislamientos: {e}")
        raise Exception("Error de base de datos al obtener los aislamientos")
    
def get_aislamiento_by_date_range(db: Session, fecha_inicio: str, fecha_fin: str):
    """
    Obtiene las tareas cuya fecha de inicio o fin esté dentro de un rango de fechas.
    Ignora las horas (usa DATE(fecha_hora_init) y DATE(fecha_hora_fin)).
    """
    try:
        query = text("""
            SELECT id_aislamiento, id_incidente_gallina, fecha_hora, aislamiento.id_galpon, galpones.nombre
            FROM aislamiento
            INNER JOIN galpones ON galpones.id_galpon = aislamiento.id_galpon
            WHERE DATE(fecha_hora) BETWEEN :fecha_inicio AND :fecha_fin
            ORDER BY fecha_hora DESC
        """)
        result = db.execute(query, {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }).mappings().all()
        
        return [dict(row) for row in result]

    except SQLAlchemyError as e:
        raise Exception(f"Error al consultar los aislamientos por rango de fechas: {e}")

def get_all_isolations_pag(db: Session, skip:int = 0, limit = 10):
    """
    Obtiene los aislamientos con paginación.
    También realizar una segunda consulta para contar total de aislamientos.
    compatible con PostgreSQL, MySQL y SQLite 
    """
    try:  #Try statement must have at
            #1. Contar total de aislamientos
        count_query = text("""SELECT COUNT(id_aislamiento) AS total 
                     FROM aislamiento 
                     """)
        total_result = db.execute(count_query).scalar()

        #2 Consultar aislamientos 
        data_query = text("""SELECT id_aislamiento, id_incidente_gallina, fecha_hora, aislamiento.id_galpon, galpones.nombre
                    FROM aislamiento
                    LEFT JOIN galpones ON galpones.id_galpon = aislamiento.id_galpon
                     ORDER BY fecha_hora DESC
                     LIMIT :limit OFFSET :skip
        """)
        isolation_list = db.execute(data_query,{"skip": skip, "limit": limit}).mappings().all()
        
        return {
                "total": total_result or 0,
                "isolation": isolation_list
            }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los aislamientos: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener los aislamientos")

   
def update_isolation_by_id(db: Session, isolation_id: int, isolation: IsolationUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        isolation_data = isolation.model_dump(exclude_unset=True)
        if not isolation_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in isolation_data.keys()])
        sentencia = text(f"""
            UPDATE aislamiento 
            SET {set_clauses}
            WHERE id_aislamiento = :id_aislamiento
        """)

        isolation_data["id_aislamiento"] = isolation_id

        result = db.execute(sentencia, isolation_data)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar aislamiento {isolation_id}: {e}")
        raise Exception("Error de base de datos al actualizar el aislamiento")
    
