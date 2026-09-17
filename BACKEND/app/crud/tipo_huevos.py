from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Optional
from app.schemas.tipo_huevos import TipoHuevosCreate, TipoHuevosUpdate


def create_tipo_huevo(db: Session, tipo_huevo: TipoHuevosCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO tipo_huevos (
                Color, Tamaño
            ) VALUES (
                :Color, :Tamaño
            )
        """)
        db.execute(sentencia, tipo_huevo.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Error de base de datos al crear tipo_huevo: {e}")

def get_tipo_huevo_by_id(db: Session, id_tipo_huevo: int):
    try:
        query = text("""
            SELECT id_tipo_huevo, Color, Tamaño
            FROM tipo_huevos
            WHERE id_tipo_huevo = :id_tipo_huevo
        """)
        result = db.execute(query, {"id_tipo_huevo": id_tipo_huevo}).mappings().first()
        return result
    except SQLAlchemyError as e:
        raise Exception(f"Error de base de datos al obtener tipo_huevo por ID: {e}")

def get_all_tipo_huevos(db: Session):
    try:
        query = text("""
            SELECT id_tipo_huevo, Color, Tamaño
            FROM tipo_huevos
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        raise Exception(f"Error de base de datos al obtener todos los tipos de huevo: {e}")

def update_tipo_huevo_by_id(db: Session, id_tipo_huevo: int, tipo_huevo: TipoHuevosUpdate) -> Optional[bool]:
    try:
        tipo_data = tipo_huevo.model_dump(exclude_unset=True)
        if not tipo_data:
            return False
        
        set_clauses = ", ".join([f"{key} = :{key}" for key in tipo_data.keys()])
        sentencia = text(f"""
            UPDATE tipo_huevos
            SET {set_clauses}
            WHERE id_tipo_huevo = :id_tipo_huevo
        """)
        tipo_data["id_tipo_huevo"] = id_tipo_huevo
        result = db.execute(sentencia, tipo_data)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Error de base de datos al actualizar tipo_huevo {id_tipo_huevo}: {e}")
