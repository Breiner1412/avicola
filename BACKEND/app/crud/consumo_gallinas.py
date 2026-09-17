from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Optional
import logging

from app.schemas.consumo_gallinas import ConsumoCreate, ConsumoUpdate

logger = logging.getLogger(__name__)

def create_consumo(db: Session, consumo: ConsumoCreate) -> Optional[bool]:
    try:
        # Crear nuevo registro
        insert_query = text("""
            INSERT INTO consumo_gallinas (id_alimento, cantidad_alimento,
                                         id_galpon, fecha_registro)
            VALUES (:id_alimento, :cantidad_alimento, :id_galpon, :fecha_registro)
        """)

        db.execute(insert_query, consumo.model_dump())
        db.commit()

        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el consumo: {e}")
        raise Exception("Error de base de datos al crear el consumo")

def get_consumo_by_id(db: Session, id_consumo: int):
    try:
        query = text("""SELECT 
                cg.id_consumo, 
                cg.id_alimento, 
                a.nombre AS alimento, 
                cg.cantidad_alimento, 
                cg.fecha_registro, 
                cg.id_galpon, 
                g.nombre AS galpon
            FROM consumo_gallinas cg
            JOIN alimento a ON cg.id_alimento = a.id_alimento
            LEFT JOIN galpones g ON cg.id_galpon = g.id_galpon
            WHERE cg.id_consumo = :id_consumo
                """)
        result = db.execute(query, {"id_consumo": id_consumo}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el consumo por id: {e}")
        raise Exception("Error de base de datos al obtener el consumo")

def get_all_consumo_pag(db: Session, skip: int = 0, limit: int = 10):
    try:
        count_query = text("""
            SELECT COUNT(id_consumo) AS total 
            FROM consumo_gallinas
        """)
        total_result = db.execute(count_query).scalar()

        query = text("""SELECT 
                cg.id_consumo, 
                cg.id_alimento, 
                a.nombre AS alimento, 
                cg.cantidad_alimento,
                cg.fecha_registro, 
                cg.id_galpon, 
                g.nombre AS galpon
            FROM consumo_gallinas cg
            JOIN alimento a ON cg.id_alimento = a.id_alimento
            LEFT JOIN galpones g ON cg.id_galpon = g.id_galpon
            ORDER BY fecha_registro DESC
            LIMIT :limit OFFSET :skip
                """)
        
        result = db.execute(query, {"skip": skip, "limit": limit}).mappings().all()
        return {
            "total": total_result or 0,
            "consumo": result
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los consumos: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener los consumos")

def get_all_consumo(db: Session):
    try:
        query = text("""SELECT 
                cg.id_consumo, 
                cg.id_alimento, 
                a.nombre AS alimento, 
                cg.cantidad_alimento,
                cg.fecha_registro, 
                cg.id_galpon, 
                g.nombre AS galpon
            FROM consumo_gallinas cg
            JOIN alimento a ON cg.id_alimento = a.id_alimento
            LEFT JOIN galpones g ON cg.id_galpon = g.id_galpon
            ORDER BY fecha_registro DESC
                """)
        
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los consumos: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener los consumos")



def get_consumo_by_galpon(db: Session, skip: int = 0, limit: int = 10, id_galpon: int = 0):
    try:
        count_query = text("""
            SELECT COUNT(id_consumo) AS total 
            FROM consumo_gallinas
            WHERE id_galpon = :id_galpon
        """)
        total_result = db.execute(count_query, {"id_galpon": id_galpon}).scalar()

        query = text("""SELECT 
                cg.id_consumo, 
                cg.id_alimento, 
                a.nombre AS alimento, 
                cg.cantidad_alimento,
                cg.fecha_registro,  
                cg.id_galpon, 
                g.nombre AS galpon
            FROM consumo_gallinas cg
            JOIN alimento a ON cg.id_alimento = a.id_alimento
            LEFT JOIN galpones g ON cg.id_galpon = g.id_galpon
            WHERE cg.id_galpon = :id_galpon
            ORDER BY cg.fecha_registro DESC, cg.id_consumo DESC
            LIMIT :limit OFFSET :skip
                """)
        result = db.execute(query, {"id_galpon": id_galpon, "skip": skip, "limit": limit}).mappings().all()
        return {
            "total": total_result or 0,
            "consumo": result
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el consumo por galpon: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener el registro")

def update_consumo_by_id(db: Session, id_consumo: int, consumo: ConsumoUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        consumo_data = consumo.model_dump(exclude_unset=True)
        if not consumo_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in consumo_data.keys()])
        sentencia = text(f"""
            UPDATE consumo_gallinas
            SET {set_clauses}
            WHERE id_consumo = :id_consumo
        """)

        # Agregar el id_consumo
        consumo_data["id_consumo"] = id_consumo

        result = db.execute(sentencia, consumo_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el consumo {id_consumo}: {e}")
        raise Exception("Error de base de datos al actualizar el consumo")

def delete_consumo_by_id(db: Session, id_consumo: int) -> bool:
    try:
        sentencia = text("""
            DELETE FROM consumo_gallinas
            WHERE id_consumo = :id_consumo
        """)
        result = db.execute(sentencia, {"id_consumo": id_consumo})
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar el consumo {id_consumo}: {e}")
        raise Exception("Error de base de datos al eliminar el consumo")

def get_galpon_info(db: Session, id_galpon: int):
    try:
        query = text("""SELECT id_galpon
                    FROM galpones WHERE id_galpon = :id_galpon
                """)
        result = db.execute(query, {"id_galpon": id_galpon}).scalar()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener la información del galpón: {e}")
        raise Exception("Error de base de datos al obtener la información del galpón")

def get_alimento_info(db: Session, id_alimento: int):
    try:
        query = text("""SELECT id_alimento
                    FROM alimento WHERE id_alimento = :id_alimento
                """)
        result = db.execute(query, {"id_alimento": id_alimento}).scalar()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener la información del alimento: {e}")
        raise Exception("Error de base de datos al obtener la información del alimento")

def get_consumo_by_date_range(db: Session, fecha_inicio: str, fecha_fin: str):
    """
    Obtiene las tareas cuya fecha de inicio o fin esté dentro de un rango de fechas.
    Ignora las horas (usa DATE(fecha_hora_init) y DATE(fecha_hora_fin)).
    """
    try:
        query = text("""
            SELECT cg.id_consumo, 
                cg.id_alimento, 
                a.nombre AS alimento, 
                cg.cantidad_alimento,
                cg.fecha_registro,  
                cg.id_galpon, 
                g.nombre AS galpon
            FROM consumo_gallinas cg
            JOIN alimento a ON cg.id_alimento = a.id_alimento
            LEFT JOIN galpones g ON cg.id_galpon = g.id_galpon
            WHERE DATE(fecha_registro) BETWEEN :fecha_inicio AND :fecha_fin
            ORDER BY fecha_registro DESC
        """)
        result = db.execute(query, {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }).mappings().all()
        
        return [dict(row) for row in result]

    except SQLAlchemyError as e:
        raise Exception(f"Error al consultar los consumos por rango de fechas: {e}")


def get_cantidad_disponible(db: Session, id_alimento: int) -> int:
    query = text("""
        SELECT cantidad 
        FROM alimento
        WHERE id_alimento = :id_alimento
    """)

    result = db.execute(query, {"id_alimento": id_alimento}).scalar()

    return result if result is not None else 0


