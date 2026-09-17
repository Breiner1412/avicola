from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.schemas.stock import StockCreate  # Ajusta si usas también StockUpdate

def create_or_increment_stock(db: Session, stock: StockCreate):
    try:
        # --- Buscar existencia considerando si `tipo` es None ---
        if stock.tipo is None:
            query = text("""
                SELECT id_producto, cantidad_disponible
                FROM stock
                WHERE nombre_producto = :nombre_producto
                  AND unidad_medida = :unidad_medida
                  AND tipo IS NULL
                LIMIT 1
            """)
            params = {
                "nombre_producto": stock.nombre_producto,
                "unidad_medida": stock.unidad_medida
            }
        else:
            query = text("""
                SELECT id_producto, cantidad_disponible
                FROM stock
                WHERE nombre_producto = :nombre_producto
                  AND unidad_medida = :unidad_medida
                  AND tipo = :tipo
                LIMIT 1
            """)
            params = {
                "nombre_producto": stock.nombre_producto,
                "unidad_medida": stock.unidad_medida,
                "tipo": stock.tipo
            }

        existing = db.execute(query, params).mappings().first()

        # --- Si existe: incrementar ---
        if existing:
            update_query = text("""
                UPDATE stock
                SET cantidad_disponible = cantidad_disponible + :cantidad_disponible
                WHERE id_producto = :id_producto
            """)
            db.execute(update_query, {
                "cantidad_disponible": stock.cantidad_disponible,
                "id_producto": existing["id_producto"]
            })
            db.commit()

            # retornar registro actualizado
            return get_stock_by_id(db, existing["id_producto"])

        # --- Si NO existe: insertar nuevo registro ---
        insert_query = text("""
            INSERT INTO stock (nombre_producto, tipo, unidad_medida, cantidad_disponible)
            VALUES (:nombre_producto, :tipo, :unidad_medida, :cantidad_disponible)
        """)
        db.execute(insert_query, {
            "nombre_producto": stock.nombre_producto,
            "tipo": stock.tipo,
            "unidad_medida": stock.unidad_medida,
            "cantidad_disponible": stock.cantidad_disponible
        })
        db.commit()

        # --- Obtener el registro insertado de forma segura ---
        # Buscamos el registro con esos mismos campos y tomamos el de id más alto
        if stock.tipo is None:
            fetch_new = text("""
                SELECT nombre_producto, tipo, id_producto, unidad_medida, cantidad_disponible
                FROM stock
                WHERE nombre_producto = :nombre_producto
                  AND unidad_medida = :unidad_medida
                  AND tipo IS NULL
                ORDER BY id_producto DESC
                LIMIT 1
            """)
            fetch_params = {
                "nombre_producto": stock.nombre_producto,
                "unidad_medida": stock.unidad_medida
            }
        else:
            fetch_new = text("""
                SELECT nombre_producto, tipo, id_producto, unidad_medida, cantidad_disponible
                FROM stock
                WHERE nombre_producto = :nombre_producto
                  AND unidad_medida = :unidad_medida
                  AND tipo = :tipo
                ORDER BY id_producto DESC
                LIMIT 1
            """)
            fetch_params = {
                "nombre_producto": stock.nombre_producto,
                "unidad_medida": stock.unidad_medida,
                "tipo": stock.tipo
            }

        new_row = db.execute(fetch_new, fetch_params).mappings().first()
        return new_row

    except SQLAlchemyError as e:
        # rollback por seguridad y lanzar excepción clara
        db.rollback()
        raise Exception(f"Error creando o incrementando el stock: {e}")

def get_stock_by_id(db: Session, id_producto: int):
    try:
        query = text("""
            SELECT nombre_producto, tipo, id_producto, unidad_medida, cantidad_disponible
            FROM stock
            WHERE id_producto = :id_producto
        """)
        result = db.execute(query, {"id_producto": id_producto}).mappings().first()
        return result
    except SQLAlchemyError as e:
        raise Exception(f"Error de base de datos al obtener stock por ID: {e}")

def get_all_stock(db: Session, skip: int = 0, limit: int = 100):
    try:
        query = text("""
            SELECT 
                id_producto,
                nombre_producto,
                unidad_medida,
                tipo,
                cantidad_disponible
            FROM stock
            ORDER BY id_producto
            LIMIT :limit OFFSET :skip
        """)
        result = db.execute(query, {"skip": skip, "limit": limit}).mappings().all()
        return result
    except SQLAlchemyError as e:
        raise Exception(f"Error de base de datos al obtener todos los stocks: {e}")
    
    
# def update_stock_by_id(db: Session, id_producto: int, stock: StockUpdate) -> Optional[bool]:
#     try:
#         stock_data = stock.model_dump(exclude_unset=True)
#         if not stock_data:
#             return False
#         set_clauses = ", ".join([f"{key} = :{key}" for key in stock_data.keys()])
#         sentencia = text(f"""
#             UPDATE stock
#             SET {set_clauses}
#             WHERE id_producto = :id_producto
#         """)
#         stock_data["id_producto"] = id_producto
#         result = db.execute(sentencia, stock_data)
#         db.commit()
#         return result.rowcount > 0
#     except SQLAlchemyError as e:
#         db.rollback()
#         raise Exception(f"Error de base de datos al actualizar stock {id_producto}: {e}")
