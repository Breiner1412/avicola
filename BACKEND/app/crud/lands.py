from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Optional
from app.schemas.lands import LandCreate, LandUpdate

logger = logging.getLogger(__name__)

def create_land(db: Session, finca: LandCreate) -> Optional[bool]:
    try:
        query = text("""
            INSERT INTO fincas (nombre, longitud, latitud, estado)
            VALUES (:nombre, :longitud, :latitud, :estado)
        """)
        db.execute(query, finca.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear finca: {e}")
        raise Exception("Error de base de datos al crear finca")

def get_all_lands(db: Session):
    try:
        query = text("""
            SELECT id_finca, nombre, longitud, latitud, estado
            FROM fincas
            ORDER BY id_finca DESC
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener fincas: {e}")
        raise Exception("Error de base de datos al listar fincas")
    
def get_land_by_id(db: Session, id_finca: int):
    try:
        query = text("""
            SELECT id_finca, nombre, longitud, latitud, estado
            FROM fincas
            WHERE id_finca = :id_finca
        """)
        result = db.execute(query, {"id_finca": id_finca}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener finca {id_finca}: {e}")
        raise Exception("Error de base de datos al consultar finca")


def update_land_by_id(db: Session, id_finca: int, finca: LandUpdate) -> Optional[bool]:
    try:
        fields = finca.model_dump(exclude_unset=True)
        if not fields:
            return False

        set_clause = ", ".join([f"{key} = :{key}" for key in fields.keys()])
        query = text(f"""
            UPDATE fincas
            SET {set_clause}
            WHERE id_finca = :id_finca
        """)

        fields["id_finca"] = id_finca
        result = db.execute(query, fields)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar finca {id_finca}: {e}")
        raise Exception("Error de base de datos al actualizar finca")

def toggle_estado_finca(db: Session, id_finca: int) -> bool:
    try:
        query = text("""
            UPDATE fincas
            SET estado = NOT estado
            WHERE id_finca = :id_finca
        """)
        result = db.execute(query, {"id_finca": id_finca})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar estado de finca {id_finca}: {e}")
        raise Exception("Error de base de datos al cambiar estado de la finca")