from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.detalle_salvamento import CreateDetalleSalvamento, DetalleSalvamentoUpdate
from app.crud.ventas_comun import verificar_venta_activa

# app./crud/detalle_salvamento
logger = logging.getLogger(__name__) # Agarra la ubicación del archivo con el que estamos trabajando

def _descontar_salvamento(db: Session, id_salvamento: int, cantidad: int, mensaje: str) -> None:
    """Descuenta gallinas de salvamento de forma atómica (solo si alcanza la cantidad)."""
    if cantidad <= 0:
        return
    result = db.execute(text("""
        UPDATE salvamento
        SET cantidad_gallinas = cantidad_gallinas - :cantidad
        WHERE id_salvamento = :id_producto
          AND cantidad_gallinas >= :cantidad
    """), {"cantidad": cantidad, "id_producto": id_salvamento})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail=mensaje)


def _devolver_salvamento(db: Session, id_salvamento: int, cantidad: int) -> None:
    if cantidad <= 0:
        return
    db.execute(text("""
        UPDATE salvamento
        SET cantidad_gallinas = cantidad_gallinas + :cantidad
        WHERE id_salvamento = :id_producto
    """), {"cantidad": cantidad, "id_producto": id_salvamento})


def create_detalle_salvamento(db: Session, detalle_salvamento: CreateDetalleSalvamento) -> dict:
    try:
        verificar_venta_activa(db, detalle_salvamento.id_venta)
        _descontar_salvamento(
            db, detalle_salvamento.id_producto, detalle_salvamento.cantidad,
            "Cantidad insuficiente para completar la operación"
        )

        sentencia = text("""
            INSERT INTO detalle_salvamento(
                id_producto, cantidad, id_venta,
                valor_descuento, precio_venta
            ) VALUES (
                :id_producto, :cantidad, :id_venta,
                :valor_descuento, :precio_venta
            )
        """)
        result = db.execute(sentencia, detalle_salvamento.model_dump())
        id_creado = result.lastrowid

        db.commit()  # Guardar cambios permanentemente
        return {"id_detalle_salvamento": id_creado}
    except SQLAlchemyError as e:
        db.rollback() 
        logger.error(f"Error al crear detalle salvamento: {e}")
        raise Exception("Error de base de datos al crear el detalle de salvamento")
    
def get_detalle_by_id(db: Session, id_detalle: int):
    try:
        query = text("""SELECT id_detalle, id_producto, cantidad, id_venta, 
                        valor_descuento, precio_venta
                    FROM detalle_salvamento
                    WHERE id_detalle = :id_detalle
                """)
        result = db.execute(query, {"id_detalle": id_detalle}).mappings().first()
        return result
    except SQLAlchemyError as e:  
        logger.error(f"Error de BD al obtener detalle {e}")
        raise Exception("Error de base de datos al obtener el detalle")
    
def get_detalle_by_id_venta(db: Session, id_venta: int):
    try:
        query = text("""SELECT id_detalle, id_producto, cantidad, id_venta, 
                        valor_descuento, precio_venta
                    FROM detalle_salvamento
                    WHERE id_venta = :id_venta
                """)
        result = db.execute(query, {"id_venta": id_venta}).mappings().all()
        return result
    except SQLAlchemyError as e:  
        logger.error(f"Error de BD al obtener detalle por id de venta {id_venta}: {e}")
        raise Exception("Error de base de datos al obtener el detalle por id de venta")
    
def update_detalle_salvamento_by_id(db: Session, detalle_id: int, detalle: DetalleSalvamentoUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        detalle_salvamento_data = detalle.model_dump(exclude_unset=True)
        if not detalle_salvamento_data:
            return False  # nada que actualizar
        
        # Obtener (y bloquear) el detalle actual
        detalle_anterior = db.execute(text("""
            SELECT id_producto, cantidad, id_venta FROM detalle_salvamento
            WHERE id_detalle = :id_detalle
            FOR UPDATE
        """), {"id_detalle": detalle_id}).mappings().first()

        if not detalle_anterior:
            db.rollback()
            raise HTTPException(status_code=404, detail="Detalle no encontrado")

        verificar_venta_activa(db, detalle_anterior["id_venta"])

        id_producto_ant = detalle_anterior["id_producto"]
        cantidad_ant = detalle_anterior["cantidad"]
        
        # Determinar nuevos valores (si no vienen, usar los antiguos)
        id_producto_nuevo = detalle_salvamento_data.get("id_producto", id_producto_ant)
        cantidad_nueva = detalle_salvamento_data.get("cantidad", cantidad_ant)

        if id_producto_nuevo != id_producto_ant:
            _devolver_salvamento(db, id_producto_ant, cantidad_ant)
            _descontar_salvamento(db, id_producto_nuevo, cantidad_nueva, "Cantidad insuficiente en este producto")
        else:
            diferencia = cantidad_nueva - cantidad_ant
            if diferencia > 0:
                _descontar_salvamento(db, id_producto_nuevo, diferencia, "Cantidad insuficiente")
            elif diferencia < 0:
                _devolver_salvamento(db, id_producto_nuevo, -diferencia)
                
        # Construir dinámicamente la sentencia UPDATE (las claves vienen del esquema)
        set_clauses = ", ".join([f"{key} = :{key}" for key in detalle_salvamento_data.keys()])
        detalle_salvamento_data["id_detalle"] = detalle_id
        sentencia = text(f"""
            UPDATE detalle_salvamento
            SET {set_clauses}
            WHERE id_detalle = :id_detalle  
        """)
        result = db.execute(sentencia, detalle_salvamento_data)
        
        db.commit()
        return result.rowcount > 0
    
    except SQLAlchemyError as e:  
        db.rollback()
        logger.error(f"Error al actualizar el detalle de salvamento {e}")
        raise Exception("Error de base de datos al actualizar el detalle de salvamento")

def delete_detalle_salvamento_by_id(db: Session, id_detalle: int) -> Optional[bool]:
    try:
        # Obtener cantidad e id_producto antes de borrar
        data = db.execute(text("""
            SELECT id_producto, cantidad, id_venta FROM detalle_salvamento
            WHERE id_detalle = :id_detalle
            FOR UPDATE
        """), {"id_detalle": id_detalle}).mappings().first()
        if not data:
            db.rollback()
            return False

        verificar_venta_activa(db, data["id_venta"])
        
        result = db.execute(
            text("DELETE FROM detalle_salvamento WHERE id_detalle = :id_detalle"),
            {"id_detalle": id_detalle}
        )
        
        # Devolver la cantidad al salvamento
        _devolver_salvamento(db, data["id_producto"], data["cantidad"])
        
        db.commit()
        return result.rowcount > 0  
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar detalle salvamento {e}")
        raise Exception("Error de base de datos al eliminar el detalle de salvamento")

def devolver_salvamento_venta(db: Session, id_venta: int) -> None:
    """Devuelve al salvamento las gallinas vendidas en una venta (al anularla). No borra los detalles."""
    db.execute(text("""
        UPDATE salvamento s
        JOIN (
            SELECT id_producto, SUM(cantidad) AS total
            FROM detalle_salvamento
            WHERE id_venta = :id_venta
            GROUP BY id_producto
        ) d ON d.id_producto = s.id_salvamento
        SET s.cantidad_gallinas = s.cantidad_gallinas + d.total
    """), {"id_venta": id_venta})
    # *Sin commit*: la transacción la maneja la función llamadora.


def delete_all_detalle_salvamento_by_id_venta(db: Session, id_venta: int, devolver_stock: bool = True) -> bool:
    """
    Borra los detalles de salvamento de una venta. Si devolver_stock es False
    (venta ya anulada) solo elimina los registros.
    *Sin commit*: la transacción la maneja la función llamadora.
    """
    try:
        if devolver_stock:
            devolver_salvamento_venta(db, id_venta)
        db.execute(text("DELETE FROM detalle_salvamento WHERE id_venta = :id_venta"), {"id_venta": id_venta})
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error al eliminar detalles de venta {id_venta}: {e}")
        raise Exception("Error de base de datos al eliminar el detalle de la venta")


def get_all_products_salvamento(db: Session):
    try:
        # Obtener los detalles de la venta
        data = text("""
            SELECT 
                salvamento.id_salvamento,
                tipo_gallinas.raza,
                tipo_gallinas.descripcion
            FROM salvamento
            INNER JOIN tipo_gallinas ON salvamento.id_tipo_gallina = tipo_gallinas.id_tipo_gallinas 
        """)
        result = db.execute(data).mappings().all()

        # *No commit aquí*. La función solo realiza las acciones SQL, y la transacción se maneja en la función llamadora.
        return result

    except SQLAlchemyError as e:
        logger.error(f"Error al obtener productos: {e}")
        raise Exception("Error de base datos al obtener productos")