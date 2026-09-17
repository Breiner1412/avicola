from sqlalchemy.exc import SQLAlchemyError
from fastapi.exceptions import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
 
logger = logging.getLogger(__name__)

def verify_permissions(db: Session, id_rol: int, id_modulo: int, accion: str):
    try:
        query = text("""
                     SELECT insertar, actualizar, seleccionar, borrar
                     FROM permisos
                     WHERE id_rol = :rol AND id_modulo = :modulo
                     """)
        result = db.execute(query, {"rol": id_rol, "modulo": id_modulo}).mappings().first()

        if result is None:
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        permiso = 0
        
        if result.insertar == 1 and accion == 'insertar':
            permiso = 1
        if result.actualizar == 1 and accion == 'actualizar':
            permiso = 1
        if result.seleccionar == 1 and accion == 'seleccionar':
            permiso = 1
        if result.borrar == 1 and accion == 'borrar':
            permiso = 1 
        
        
        return permiso
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener permisos: {e}")
        raise Exception("Error de base de datos al obtener permisos")
    
