from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.incidentes_generales import IncidenteGeneralCreate, IncidenteGeneralUpdate

logger = logging.getLogger(__name__)

# Crear incidente general
def create_incidente(db: Session, incidente: IncidenteGeneralCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO incidentes_generales (
                descripcion, fecha_hora, id_finca, esta_resuelta
            ) VALUES (
                :descripcion, :fecha_hora, :id_finca, :esta_resuelta
            )
        """)
        db.execute(sentencia, incidente.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear incidente general: {e}")
        raise Exception("Error de base de datos al crear incidente general")
        
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

# Obtener incidente por ID
def get_incidente_by_id(db: Session, id_incidente: int):
    try:
        query = text("""
            SELECT 
                ig.id_incidente, 
                ig.descripcion, 
                ig.fecha_hora, 
                ig.id_finca, 
                ig.esta_resuelta,
                f.nombre AS nombre_finca
            FROM incidentes_generales ig
            LEFT JOIN fincas f ON ig.id_finca = f.id_finca
            WHERE ig.id_incidente = :id_incidente
        """)
        result = db.execute(query, {"id_incidente": id_incidente}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener incidente general por ID: {e}")
        raise Exception("Error al consultar incidente general por ID")

# Obtener todos los incidentes con paginación
def get_all_incidentes(db: Session, skip: int = 0, limit: int = 100):
    try:
        # Consulta para obtener el total de registros
        count_query = text("""
            SELECT COUNT(*) as total
            FROM incidentes_generales ig
            LEFT JOIN fincas f ON ig.id_finca = f.id_finca
        """)
        total = db.execute(count_query).scalar()

        # Consulta principal con paginación
        query = text("""
            SELECT 
                ig.id_incidente, 
                ig.descripcion, 
                ig.fecha_hora, 
                ig.id_finca, 
                ig.esta_resuelta,
                f.nombre AS nombre_finca
            FROM incidentes_generales ig
            LEFT JOIN fincas f ON ig.id_finca = f.id_finca
            ORDER BY ig.fecha_hora DESC
            LIMIT :limit OFFSET :skip
        """)
        result = db.execute(query, {"skip": skip, "limit": limit}).mappings().all()
        
        # Convertir a lista de diccionarios para compatibilidad con Pydantic
        incidentes_list = [dict(incidente) for incidente in result]
        
        return {
            "incidentes": incidentes_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener incidentes generales: {e}")
        raise Exception("Error al listar incidentes generales")

# Obtener incidentes filtrados por estado (activos/inactivos)
def get_incidentes_by_estado(db: Session, esta_resuelta: bool, skip: int = 0, limit: int = 100):
    try:
        # Consulta para obtener el total de registros filtrados
        count_query = text("""
            SELECT COUNT(*) as total
            FROM incidentes_generales ig
            LEFT JOIN fincas f ON ig.id_finca = f.id_finca
            WHERE ig.esta_resuelta = :esta_resuelta
        """)
        total = db.execute(count_query, {"esta_resuelta": esta_resuelta}).scalar()

        # Consulta principal con paginación y filtro
        query = text("""
            SELECT 
                ig.id_incidente, 
                ig.descripcion, 
                ig.fecha_hora, 
                ig.id_finca, 
                ig.esta_resuelta,
                f.nombre AS nombre_finca
            FROM incidentes_generales ig
            LEFT JOIN fincas f ON ig.id_finca = f.id_finca
            WHERE ig.esta_resuelta = :esta_resuelta
            ORDER BY ig.fecha_hora DESC
            LIMIT :limit OFFSET :skip
        """)
        result = db.execute(query, {
            "esta_resuelta": esta_resuelta,
            "skip": skip, 
            "limit": limit
        }).mappings().all()
        
        # Convertir a lista de diccionarios para compatibilidad con Pydantic
        incidentes_list = [dict(incidente) for incidente in result]
        
        return {
            "incidentes": incidentes_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener incidentes generales filtrados por estado: {e}")
        raise Exception("Error al listar incidentes generales filtrados por estado")

# Actualizar incidente
def update_incidente_by_id(db: Session, id_incidente: int, incidente: IncidenteGeneralUpdate) -> Optional[bool]:
    try:
        fields = incidente.model_dump(exclude_unset=True)
        if not fields:
            return False
        set_clause = ", ".join([f"{key} = :{key}" for key in fields.keys()])
        sentencia = text(f"""
            UPDATE incidentes_generales
            SET {set_clause}
            WHERE id_incidente = :id_incidente
        """)
        fields["id_incidente"] = id_incidente
        result = db.execute(sentencia, fields)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar incidente general {id_incidente}: {e}")
        raise Exception("Error de base de datos al actualizar incidente general")

# Eliminar incidente
def delete_incidente_by_id(db: Session, id_incidente: int) -> Optional[bool]:
    try:
        sentencia = text("""
            DELETE FROM incidentes_generales
            WHERE id_incidente = :id_incidente
        """)
        result = db.execute(sentencia, {"id_incidente": id_incidente})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar incidente general {id_incidente}: {e}")
        raise Exception("Error de base de datos al eliminar incidente general")

# Cambiar estado del incidente
def toggle_estado_incidente(db: Session, id_incidente: int):
    try:
        query = text("""
            UPDATE incidentes_generales
            SET esta_resuelta = NOT esta_resuelta
            WHERE id_incidente = :id_incidente
        """)
        result = db.execute(query, {"id_incidente": id_incidente})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar estado del incidente general: {e}")
        raise Exception("Error de base de datos al actualizar estado del incidente")
