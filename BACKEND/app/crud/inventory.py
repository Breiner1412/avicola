from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
import logging

from app.schemas.inventory import InventoryCreate, InventoryUpdate

logger = logging.getLogger(__name__)

def create_inventory(db: Session, inventory: InventoryCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO inventario_finca(
                nombre, cantidad, unidad_medida, 
                descripcion, id_categoria, id_finca
            ) VALUES (
                :nombre, :cantidad, :unidad_medida,
                :descripcion, :id_categoria, :id_finca
            )
        """)
        db.execute(sentencia, inventory.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear item de inventario: {e}")
        raise Exception("Error de base de datos al crear el item de inventario")

def get_all_inventory(db: Session) -> List[dict]:
    try:
        query = text("""
            SELECT 
                i.id_inventario,
                i.nombre,
                i.cantidad,
                i.unidad_medida,
                i.descripcion,
                i.id_categoria,
                i.id_finca,
                c.nombre as nombre_categoria,
                f.nombre as nombre_finca
            FROM inventario_finca i
            INNER JOIN categoria_inventario c ON i.id_categoria = c.id_categoria
            INNER JOIN fincas f ON i.id_finca = f.id_finca
            ORDER BY i.id_inventario
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener inventario: {e}")
        raise Exception("Error de base de datos al obtener el inventario")

def get_inventory_by_id(db: Session, inventory_id: int) -> Optional[dict]:
    try:
        query = text("""
            SELECT 
                i.id_inventario,
                i.nombre,
                i.cantidad,
                i.unidad_medida,
                i.descripcion,
                i.id_categoria,
                i.id_finca,
                c.nombre as nombre_categoria,
                f.nombre as nombre_finca
            FROM inventario_finca i
            INNER JOIN categoria_inventario c ON i.id_categoria = c.id_categoria
            INNER JOIN fincas f ON i.id_finca = f.id_finca
            WHERE i.id_inventario = :inventory_id
        """)
        result = db.execute(query, {"inventory_id": inventory_id}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener item de inventario por ID: {e}")
        raise Exception("Error de base de datos al obtener el item de inventario")

def get_inventory_by_land(db: Session, land_id: int) -> List[dict]:
    try:
        query = text("""
            SELECT 
                i.id_inventario,
                i.nombre,
                i.cantidad,
                i.unidad_medida,
                i.descripcion,
                i.id_categoria,
                i.id_finca,
                c.nombre as nombre_categoria,
                f.nombre as nombre_finca
            FROM inventario_finca i
            INNER JOIN categoria_inventario c ON i.id_categoria = c.id_categoria
            INNER JOIN fincas f ON i.id_finca = f.id_finca
            WHERE i.id_finca = :land_id
            ORDER BY i.id_inventario
        """)
        result = db.execute(query, {"land_id": land_id}).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener inventario por finca: {e}")
        raise Exception("Error de base de datos al obtener el inventario por finca")

def update_inventory_by_id(db: Session, inventory_id: int, inventory: InventoryUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        inventory_data = inventory.model_dump(exclude_unset=True)
        if not inventory_data:
            return False  # nada que actualizar

        # Construir dinámicamente la sentencia UPDATE
        set_clauses = ", ".join([f"{key} = :{key}" for key in inventory_data.keys()])
        sentencia = text(f"""
            UPDATE inventario_finca 
            SET {set_clauses}
            WHERE id_inventario = :id_inventario
        """)

        # Agregar el id_inventario
        inventory_data["id_inventario"] = inventory_id

        result = db.execute(sentencia, inventory_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar item de inventario {inventory_id}: {e}")
        raise Exception("Error de base de datos al actualizar el item de inventario")

def delete_inventory_by_id(db: Session, inventory_id: int) -> Optional[bool]:
    try:
        query = text("""
            DELETE FROM inventario_finca
            WHERE id_inventario = :inventory_id
        """)
        result = db.execute(query, {"inventory_id": inventory_id})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar item de inventario {inventory_id}: {e}")
        raise Exception("Error de base de datos al eliminar el item de inventario")