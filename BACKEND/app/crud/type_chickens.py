from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.type_chickens import TypeChickenCreate, TypeChickenUpdate

logger = logging.getLogger(__name__)

def create_type_chicken(db: Session, type_chicken: TypeChickenCreate) -> Optional[bool]:
    try:
        # Validar si ya existe la misma raza + descripción
        check_query = text("""
            SELECT COUNT(*) AS total
            FROM tipo_gallinas
            WHERE raza = :raza AND descripcion = :descripcion
        """)

        result = db.execute(check_query, {
            "raza": type_chicken.raza,
            "descripcion": type_chicken.descripcion
        }).scalar()

        if result > 0:
            return False  # Ya existe, no crear

        # Crear nuevo registro
        insert_query = text("""
            INSERT INTO tipo_gallinas (raza, descripcion)
            VALUES (:raza, :descripcion)
        """)

        db.execute(insert_query, type_chicken.model_dump())
        db.commit()

        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el tipo de gallina: {e}")
        raise Exception("Error de base de datos al crear el tipo de gallina")


def get_type_chicken_by_id(db: Session, id_tipo_gallinas: int):
    try:
        query = text("""SELECT * FROM tipo_gallinas
                    WHERE id_tipo_gallinas = :id_tipo_gallinas""")
        result = db.execute(query, {"id_tipo_gallinas": id_tipo_gallinas}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el tipo de gallina por id: {e}")
        raise Exception("Error de base de datos al obtener el tipo de gallina")

def get_all_type_chickens(db: Session):
    try:
        query = text("""SELECT * FROM tipo_gallinas""")
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los tipos de gallinas: {e}")
        raise Exception("Error de base de datos al obtener los tipos de gallinas")

def update_type_chicken_by_id(db: Session, id_tipo_gallinas: int, type_chicken: TypeChickenUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        type_chicken_data = type_chicken.model_dump(exclude_unset=True)
        if not type_chicken_data:
            return False  # nada que actualizar
        
        check_query = text("""
            SELECT COUNT(*) AS total
            FROM tipo_gallinas
            WHERE raza = :raza 
            AND descripcion = :descripcion
            AND id_tipo_gallinas != :id_tipo_gallinas
        """)

        result = db.execute(check_query, {
            "id_tipo_gallinas": id_tipo_gallinas,
            "raza": type_chicken.raza,
            "descripcion": type_chicken.descripcion
        }).scalar()

        if result > 0:
            return False  # Ya existe, no crear

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in type_chicken_data.keys()])
        sentencia = text(f"""
            UPDATE tipo_gallinas 
            SET {set_clauses}
            WHERE id_tipo_gallinas = :id_tipo_gallinas
        """)

        type_chicken_data["id_tipo_gallinas"] = id_tipo_gallinas

        result = db.execute(sentencia, type_chicken_data)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el tipo de gallina {id_tipo_gallinas}: {e}")
        raise Exception("Error de base de datos al actualizar el tipo de gallina")
    

    
