from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import logging
from app.schemas.metodo_pago import MetodoPagoCreate, MetodoPagoUpdate 
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def create_metodoPago(db: Session, metodoPago: MetodoPagoCreate) -> Optional[bool]:
    try:
        sentencia = text("""
            INSERT INTO metodo_pago (
                nombre, descripcion, estado
            ) VALUES (
                :nombre, :descripcion, :estado
            )
        """)
        db.execute(sentencia, metodoPago.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el metodo de pago: {e}")

        
        error_msg = str(e.__cause__)

        if "Duplicate entry" in error_msg and "nombre" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El nombre del método de pago ya existe."
            )

        raise HTTPException(
            status_code=500,
            detail="Error interno al crear el método de pago."
        )
        # raise Exception("Error de base de datos al crear el metodo de pago")
    


def get_metodoPago_by_id(db: Session, id: int):
    try:
        query = text("""SELECT id_tipo, metodo_pago.nombre, descripcion, metodo_pago.estado
                     FROM metodo_pago
                     WHERE id_tipo = :id_tipo_query
                     """)
        result = db.execute(query, {"id_tipo_query": id}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener el metodo de pago por el id: {e}")
        raise Exception("Error de base de datos al obtener el metodo de pago")


def get_metodosPago(db: Session):
    try:
        query = text("""SELECT id_tipo, nombre, descripcion, estado
                        FROM metodo_pago
                     """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los metodos de pago: {e}")
        raise Exception("Error de base de datos al obtener los metodos de pago")
    

    
def update_metodoPago_by_id(db: Session, id: int, metodoPago: MetodoPagoUpdate) -> Optional[bool]:
    try:
        metodoPago_data = metodoPago.model_dump(exclude_unset=True)
        if not metodoPago_data:
            return False 

        set_clauses = ", ".join([f"{key} = :{key}" for key in metodoPago_data.keys()])
        sentencia = text(f"""
            UPDATE metodo_pago
            SET {set_clauses}
            WHERE id_tipo = :id_tipo
        """)

        metodoPago_data["id_tipo"] = id

        result = db.execute(sentencia, metodoPago_data)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el metodo de pago {id}: {e}")
        error_msg = str(e.__cause__)

        if "Duplicate entry" in error_msg and "nombre" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="El nombre del método de pago ya existe."
            )

        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el método de pago."
        )
    
def change_metodoPago_status(db: Session, id: int, nuevo_estado: bool) -> bool:
    try:
        sentencia = text("""
            UPDATE metodo_pago
            SET estado = :estado
            WHERE id_tipo = :id_tipo
        """)
        result = db.execute(sentencia, {"estado": nuevo_estado, "id_tipo": id})
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar el estado del metodo de pago {id}: {e}")
        raise Exception("Error de base de datos al cambiar el estado del metodo de pago")
