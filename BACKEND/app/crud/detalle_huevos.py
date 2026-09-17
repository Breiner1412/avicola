from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from fastapi import HTTPException
import logging

from app.schemas.detalle_huevos import DetalleHuevosCreate, DetalleHuevosUpdate
from app.crud.ventas_comun import verificar_venta_activa

logger = logging.getLogger(__name__)

def _descontar_stock(db: Session, id_producto: int, cantidad: int, mensaje: str) -> None:
    """
    Descuenta stock de forma atómica: el UPDATE solo se aplica si hay cantidad
    suficiente, así dos ventas simultáneas no pueden dejar el stock en negativo.
    """
    if cantidad <= 0:
        return
    result = db.execute(text("""
        UPDATE stock
        SET cantidad_disponible = cantidad_disponible - :cantidad
        WHERE id_producto = :id_producto
          AND cantidad_disponible >= :cantidad
    """), {"cantidad": cantidad, "id_producto": id_producto})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail=mensaje)


def _devolver_stock(db: Session, id_producto: int, cantidad: int) -> None:
    if cantidad <= 0:
        return
    db.execute(text("""
        UPDATE stock
        SET cantidad_disponible = cantidad_disponible + :cantidad
        WHERE id_producto = :id_producto
    """), {"cantidad": cantidad, "id_producto": id_producto})


def create_detalle_huevos(db: Session, detalle_h: DetalleHuevosCreate) -> dict:
    try:
        verificar_venta_activa(db, detalle_h.id_venta)
        _descontar_stock(
            db, detalle_h.id_producto, detalle_h.cantidad,
            "Stock insuficiente para completar la operación"
        )

        sentencia = text("""
            INSERT INTO detalle_huevos(
                id_producto, cantidad, id_venta,
                valor_descuento, precio_venta
            ) VALUES (
                :id_producto, :cantidad, :id_venta,
                :valor_descuento, :precio_venta
            )
        """)
        result = db.execute(sentencia, detalle_h.model_dump())
        id_creado = result.lastrowid
        db.commit()
        return {"id_detalle_huevo": id_creado}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear detalle_huevos: {e}")
        raise Exception("Error de base de datos al crear el detalle_huevos")
    

def update_detalle_huevos_by_id(db: Session, detalle_id: int, detalle_h: DetalleHuevosUpdate) -> Optional[bool]:
    try:
        # Solo los campos enviados por el cliente
        detalle_huevos_data = detalle_h.model_dump(exclude_unset=True)
        if not detalle_huevos_data:
            return False  # nada que actualizar

        # Se bloquea la fila mientras dura la transacción
        datos_anteriores = db.execute(text("""
            SELECT id_producto, cantidad, id_venta
            FROM detalle_huevos
            WHERE id_detalle = :id_detalle
            FOR UPDATE
        """), {"id_detalle": detalle_id}).mappings().first()

        if not datos_anteriores:
            db.rollback()
            raise HTTPException(status_code=404, detail="Detalle no encontrado")

        verificar_venta_activa(db, datos_anteriores['id_venta'])
        nueva_venta = detalle_huevos_data.get('id_venta')
        if nueva_venta and nueva_venta != datos_anteriores['id_venta']:
            verificar_venta_activa(db, nueva_venta)

        id_producto_anterior = datos_anteriores['id_producto']
        cantidad_anterior = datos_anteriores['cantidad']

        id_producto_nuevo = detalle_huevos_data.get('id_producto', id_producto_anterior)
        cantidad_nueva = detalle_huevos_data.get('cantidad', cantidad_anterior)

        if id_producto_nuevo != id_producto_anterior:
            # Devolver lo del producto anterior y descontar del nuevo
            _devolver_stock(db, id_producto_anterior, cantidad_anterior)
            _descontar_stock(db, id_producto_nuevo, cantidad_nueva, "Stock insuficiente en este producto")
        else:
            diferencia = cantidad_nueva - cantidad_anterior
            if diferencia > 0:
                _descontar_stock(db, id_producto_nuevo, diferencia, "Stock insuficiente")
            elif diferencia < 0:
                _devolver_stock(db, id_producto_nuevo, -diferencia)

        # Construir dinámicamente la sentencia UPDATE (las claves vienen del esquema)
        set_clauses = ", ".join([f"{key} = :{key}" for key in detalle_huevos_data.keys()])
        sentencia = text(f"""
            UPDATE detalle_huevos
            SET {set_clauses}
            WHERE id_detalle = :id_detalle
        """)
        detalle_huevos_data["id_detalle"] = detalle_id

        result = db.execute(sentencia, detalle_huevos_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar detalle_huevos {detalle_id}: {e}")
        raise Exception("Error de base de datos al actualizar el detalle_huevos")


def get_detalle_huevos_by_id(db: Session, id_detalle: int):
    try:
        query = text("""SELECT id_detalle, id_producto, cantidad, id_venta, 
                        valor_descuento, precio_venta
                    FROM detalle_huevos
                    WHERE id_detalle = :id_detalle
                """)
        result = db.execute(query, {"id_detalle": id_detalle}).mappings().first()
        return result
    except SQLAlchemyError as e:  
        logger.error(f"Error de BD al obtener detalle {e}")
        raise Exception("Error de base de datos al obtener el detalle") 

def get_detalle_huevos_by_id_venta(db:Session, id:int):
    try:
        query = text("""SELECT * FROM detalle_huevos INNER JOIN ventas ON detalle_huevos.id_venta=ventas.id_venta
                     WHERE detalle_huevos.id_venta = :id_venta
                """)
        result = db.execute(query, {"id_venta": id}).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener detalle_huevos por id_venta: {e}")
        raise Exception("Error de base de datos al obtener el detalle_huevos por id_venta")
    

def delete_detalle_huevos_by_id(db: Session, detalle_id: int):
    try:
        data = db.execute(text("""
            SELECT id_producto, cantidad, id_venta FROM detalle_huevos
            WHERE id_detalle = :id_detalle
            FOR UPDATE
        """), {"id_detalle": detalle_id}).mappings().first()

        if not data:
            db.rollback()
            return False

        verificar_venta_activa(db, data["id_venta"])

        result = db.execute(text("""
            DELETE FROM detalle_huevos
            WHERE id_detalle = :id_detalle
        """), {"id_detalle": detalle_id})

        _devolver_stock(db, data["id_producto"], data["cantidad"])

        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al eliminar detalle_huevos {detalle_id}: {e}")
        raise Exception("Error de base de datos al eliminar el detalle_huevos")
    
def devolver_stock_venta(db: Session, id_venta: int) -> None:
    """Devuelve al stock lo vendido en una venta (al anularla). No borra los detalles."""
    db.execute(text("""
        UPDATE stock s
        JOIN (
            SELECT id_producto, SUM(cantidad) AS total
            FROM detalle_huevos
            WHERE id_venta = :id_venta
            GROUP BY id_producto
        ) d ON d.id_producto = s.id_producto
        SET s.cantidad_disponible = s.cantidad_disponible + d.total
    """), {"id_venta": id_venta})
    # *Sin commit*: la transacción la maneja la función llamadora.


def delete_all_detalle_huevos_by_id_venta(db: Session, id_venta: int, devolver_stock: bool = True) -> bool:
    """
    Borra los detalles de una venta. Si devolver_stock es False (venta ya anulada,
    cuyo stock se devolvió al anularla) solo elimina los registros.
    *Sin commit*: la transacción la maneja la función llamadora.
    """
    try:
        if devolver_stock:
            devolver_stock_venta(db, id_venta)
        db.execute(text("DELETE FROM detalle_huevos WHERE id_venta = :id_venta"), {"id_venta": id_venta})
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error al eliminar detalles de venta con id_venta {id_venta}: {e}")
        raise Exception("Error al eliminar los detalles de venta")


def get_all_products_stock(db: Session):
    try:
        # Obtener los detalles de la venta
        data = text("""
            SELECT 
                stock.id_producto,
                stock.unidad_medida,
                tipo_huevos.color,
                tipo_huevos.tamaño AS tamanio
            FROM 
                stock
            INNER JOIN  
                tipo_huevos ON tipo_huevos.id_tipo_huevo = stock.tipo 
        """)
        result = db.execute(data).mappings().all()

        # *No commit aquí*. La función solo realiza las acciones SQL, y la transacción se maneja en la función llamadora.
        return result

    except SQLAlchemyError as e:
        logger.error(f"Error al obtener productos: {e}")
        raise Exception("Error de base datos al obtener productos")


