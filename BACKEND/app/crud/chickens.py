from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Optional
import logging

from app.schemas.chickens import ChickenCreate, ChickenUpdate

logger = logging.getLogger(__name__)

def get_galpon_info(db: Session, id_galpon: int):
    try:
        query = text("""SELECT id_galpon, capacidad, cant_actual
                    FROM galpones WHERE id_galpon = :id
                """)
        result = db.execute(query, {"id": id_galpon}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener la información del galpón: {e}")
        raise Exception("Error de base de datos al obtener la información del galpón")


def create_chicken(db: Session, chicken: ChickenCreate) -> Optional[bool]:
    try:

        sentencia = text("""
            INSERT INTO ingreso_gallinas (
                id_galpon, fecha,
                id_tipo_gallina, cantidad_gallinas
            ) VALUES (
                :id_galpon, :fecha,
                :id_tipo_gallina, :cantidad_gallinas
            )
        """)
        db.execute(sentencia, chicken.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el registro de gallinas: {e}")
        raise Exception("Error de base de datos al crear el registro")


def get_chicken_by_id(db: Session, id_ingreso: int):
    try:
        query = text("""SELECT id_ingreso, ingreso_gallinas.id_galpon, fecha, id_tipo_gallina, raza, cantidad_gallinas,galpones.nombre AS nombre_galpon
                     FROM ingreso_gallinas
                     JOIN tipo_gallinas ON ingreso_gallinas.id_tipo_gallina = tipo_gallinas.id_tipo_gallinas
                     JOIN galpones ON ingreso_gallinas.id_galpon = galpones.id_galpon
                     WHERE id_ingreso = :ingreso
                """)
        result = db.execute(query, {"ingreso": id_ingreso}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el registro por id: {e}")
        raise Exception("Error de base de datos al obtener el registro")


def get_chicken_by_galpon(db: Session, skip: int = 0, limit: int = 10, id_galpon: int = 0):
    try:
        count_query = text("""
            SELECT COUNT(id_ingreso) AS total 
            FROM ingreso_gallinas
            WHERE id_galpon = :galpon
        """)
        total_result = db.execute(count_query, {"galpon": id_galpon}).scalar()

        query = text("""SELECT id_ingreso, ingreso_gallinas.id_galpon, fecha, id_tipo_gallina, raza, cantidad_gallinas, galpones.nombre AS nombre_galpon
                     FROM ingreso_gallinas
                     JOIN tipo_gallinas ON ingreso_gallinas.id_tipo_gallina = tipo_gallinas.id_tipo_gallinas
                     JOIN galpones ON ingreso_gallinas.id_galpon = galpones.id_galpon
                     WHERE ingreso_gallinas.id_galpon = :galpon
                     ORDER BY id_ingreso
                     LIMIT :limit OFFSET :skip
                """)
        result = db.execute(query, {"galpon": id_galpon, "skip": skip, "limit": limit}).mappings().all()
        return {
            "total": total_result or 0,
            "chickens": result
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el registro por galpon: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener el registro")


def get_all_chickens_pag(db: Session, skip: int = 0, limit: int = 10):
    try:
        count_query = text("""
            SELECT COUNT(id_ingreso) AS total 
            FROM ingreso_gallinas
        """)
        total_result = db.execute(count_query).scalar()

        query = text("""SELECT id_ingreso, ingreso_gallinas.id_galpon, fecha, id_tipo_gallina, raza, cantidad_gallinas, galpones.nombre AS nombre_galpon
                     FROM ingreso_gallinas
                     JOIN tipo_gallinas ON ingreso_gallinas.id_tipo_gallina = tipo_gallinas.id_tipo_gallinas
                     JOIN galpones ON ingreso_gallinas.id_galpon = galpones.id_galpon
                     ORDER BY id_ingreso
                     LIMIT :limit OFFSET :skip
                """)
        result = db.execute(query, {"skip": skip, "limit": limit}).mappings().all()
        return {
            "total": total_result or 0,
            "chickens": result
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los registros: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener los registros")


def update_chickens_by_id(db: Session, id_ingreso: int, chicken: ChickenUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        chicken_data = chicken.model_dump(exclude_unset=True)
        if not chicken_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in chicken_data.keys()])
        sentencia = text(f"""
            UPDATE ingreso_gallinas 
            SET {set_clauses}
            WHERE id_ingreso = :id_ingreso
        """)

        # Agregar el id_usuario
        chicken_data["id_ingreso"] = id_ingreso

        result = db.execute(sentencia, chicken_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el registro {id_ingreso}: {e}")
        raise Exception("Error de base de datos al actualizar el registro")


def delete_chicken_by_id(db: Session, id_ingreso: int) -> bool:
    try:
        sentencia = text("""
            DELETE FROM ingreso_gallinas
            WHERE id_ingreso = :id
        """)
        result = db.execute(sentencia, {"id": id_ingreso})
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar el registro {id_ingreso}: {e}")
        raise Exception("Error de base de datos al eliminar el registro")


def get_chihckens_by_date_range(db: Session, skip: int = 0, limit: int = 10, fecha_inicio: date = None, fecha_fin: date = None):
    try:
        count_query = text("""
            SELECT COUNT(id_ingreso) AS total 
            FROM ingreso_gallinas
            WHERE fecha BETWEEN :fecha_inicio AND :fecha_fin
        """)
        total_result = db.execute(count_query, {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
            }).scalar()

        query = text("""
            SELECT id_ingreso, ingreso_gallinas.id_galpon, fecha, id_tipo_gallina, raza, cantidad_gallinas, galpones.nombre AS nombre_galpon
                    FROM ingreso_gallinas
                    JOIN tipo_gallinas ON ingreso_gallinas.id_tipo_gallina = tipo_gallinas.id_tipo_gallinas
                    JOIN galpones ON ingreso_gallinas.id_galpon = galpones.id_galpon
                    WHERE fecha BETWEEN :fecha_inicio AND :fecha_fin
                    ORDER BY fecha ASC
                    LIMIT :limit OFFSET :skip
            """)

        result = db.execute(query, {
            "skip": skip, 
            "limit": limit,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }).mappings().all()

        return {
            "total": total_result or 0,
            "chickens": result
        }

    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los registros: {e}", exc_info=True)
        raise Exception("Error de base de datos al consultar el registro de gallinas")
