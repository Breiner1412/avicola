from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.schemas.permisos import PermisoCreate, PermisoUpdate

logger = logging.getLogger(__name__)

# Crear permiso
def create_permiso(db: Session, permiso: PermisoCreate):
    try:
        query = text("""
            INSERT INTO permisos (id_modulo, id_rol, insertar, actualizar, seleccionar, borrar)
            VALUES (:id_modulo, :id_rol, :insertar, :actualizar, :seleccionar, :borrar)
        """)
        db.execute(query, permiso.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear permiso: {e}")
        raise Exception("Error al crear permiso")

# Obtener todos los permisos
def get_all_permisos(db: Session):
    try:
        query = text("SELECT * FROM permisos ORDER BY id_modulo ASC, id_rol ASC")
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener permisos: {e}")
        raise Exception("Error al obtener permisos")

# Obtener un permiso por módulo y rol
def get_permiso_by_ids(db: Session, id_modulo: int, id_rol: int):
    try:
        query = text("""
            SELECT * FROM permisos
            WHERE id_modulo = :id_modulo AND id_rol = :id_rol
        """)
        result = db.execute(query, {"id_modulo": id_modulo, "id_rol": id_rol}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener permiso ({id_modulo}, {id_rol}): {e}")
        raise Exception("Error al obtener permiso")

# Actualizar permiso
def update_permiso(db: Session, id_modulo: int, id_rol: int, permiso: PermisoUpdate):
    try:
        fields = permiso.model_dump(exclude_unset=True)
        if not fields:
            return False

        set_clause = ", ".join([f"{key} = :{key}" for key in fields.keys()])
        fields["id_modulo"] = id_modulo
        fields["id_rol"] = id_rol

        query = text(f"""
            UPDATE permisos SET {set_clause}
            WHERE id_modulo = :id_modulo AND id_rol = :id_rol
        """)
        result = db.execute(query, fields)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar permiso ({id_modulo}, {id_rol}): {e}")
        raise Exception("Error al actualizar permiso")