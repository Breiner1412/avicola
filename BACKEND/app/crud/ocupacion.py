"""
Ocupación de los galpones (galpones.cant_actual).

- Los ingresos de gallinas la suman/restan con triggers en la base de datos.
- El salvamento (gallinas de descarte) y los incidentes de tipo Muerte o Fuga
  retiran gallinas del galpón; eso se maneja aquí, dentro de la misma
  transacción del registro. Las funciones no hacen commit.
"""
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

# Incidentes que sacan gallinas del galpón
TIPOS_QUE_RETIRAN = {"Muerte", "Fuga"}


def gallinas_retiradas_por_incidente(tipo_incidente, cantidad) -> int:
    tipo = getattr(tipo_incidente, "value", tipo_incidente)
    return int(cantidad or 0) if tipo in TIPOS_QUE_RETIRAN else 0


def retirar_gallinas(db: Session, id_galpon: int, cantidad: int) -> None:
    """Resta gallinas del galpón; falla con 400 si no hay suficientes."""
    if not cantidad or cantidad <= 0:
        return
    result = db.execute(text("""
        UPDATE galpones
        SET cant_actual = cant_actual - :cantidad
        WHERE id_galpon = :id_galpon AND cant_actual >= :cantidad
    """), {"cantidad": cantidad, "id_galpon": id_galpon})
    if result.rowcount:
        return
    actual = db.execute(
        text("SELECT cant_actual FROM galpones WHERE id_galpon = :id"), {"id": id_galpon}
    ).scalar()
    db.rollback()
    if actual is None:
        raise HTTPException(status_code=404, detail="El galpón especificado no existe")
    raise HTTPException(
        status_code=400,
        detail=f"El galpón solo tiene {actual} gallinas; no se pueden retirar {cantidad}",
    )


def devolver_gallinas(db: Session, id_galpon: int, cantidad: int) -> None:
    """Vuelve a sumar gallinas al galpón (al corregir o eliminar un registro)."""
    if not cantidad or cantidad <= 0:
        return
    db.execute(text("""
        UPDATE galpones
        SET cant_actual = cant_actual + :cantidad
        WHERE id_galpon = :id_galpon
    """), {"cantidad": cantidad, "id_galpon": id_galpon})
