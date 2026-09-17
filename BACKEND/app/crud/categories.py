from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
import logging

from app.schemas.categories import CategoryCreate, CategoryUpdate

logger = logging.getLogger(__name__)

def create_category(db: Session, category: CategoryCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO categoria_inventario(
                nombre, descripcion
            ) VALUES (
                :nombre, :descripcion
            )
        """)
        db.execute(sentencia, category.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear categoría: {e}")
        raise Exception("Error de base de datos al crear la categoría")

def get_all_categories(db: Session) -> List[dict]:
    try:
        query = text("""
            SELECT id_categoria, nombre, descripcion
            FROM categoria_inventario
            ORDER BY id_categoria
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener categorías: {e}")
        raise Exception("Error de base de datos al obtener las categorías")

def get_category_by_id(db: Session, category_id: int) -> Optional[dict]:
    try:
        query = text("""
            SELECT id_categoria, nombre, descripcion
            FROM categoria_inventario
            WHERE id_categoria = :category_id
        """)
        result = db.execute(query, {"category_id": category_id}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener categoría por ID: {e}")
        raise Exception("Error de base de datos al obtener la categoría")

def update_category_by_id(db: Session, category_id: int, category: CategoryUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        category_data = category.model_dump(exclude_unset=True)
        if not category_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in category_data.keys()])
        sentencia = text(f"""
            UPDATE categoria_inventario 
            SET {set_clauses}
            WHERE id_categoria = :id_categoria
        """)

        # Agregar el id_categoria
        category_data["id_categoria"] = category_id

        result = db.execute(sentencia, category_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar categoría {category_id}: {e}")
        raise Exception("Error de base de datos al actualizar la categoría")

def delete_category_by_id(db: Session, category_id: int) -> Optional[bool]:
    try:
        query = text("""
            DELETE FROM categoria_inventario
            WHERE id_categoria = :category_id
        """)
        result = db.execute(query, {"category_id": category_id})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar categoría {category_id}: {e}")
        raise Exception("Error de base de datos al eliminar la categoría")