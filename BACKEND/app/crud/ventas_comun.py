"""Reglas compartidas por las ventas y sus detalles."""
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def verificar_venta_activa(db: Session, id_venta: int) -> None:
    """
    Bloquea la fila de la venta durante la transacción y exige que esté activa.
    Una venta anulada conserva sus detalles como historial y ya no se modifica.
    """
    venta = db.execute(
        text("SELECT estado FROM ventas WHERE id_venta = :id FOR UPDATE"),
        {"id": id_venta},
    ).mappings().first()
    if not venta:
        db.rollback()
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if not venta["estado"]:
        db.rollback()
        raise HTTPException(status_code=400, detail="La venta está anulada y no se puede modificar")
