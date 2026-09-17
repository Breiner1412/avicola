"""Resumen para la pantalla de inicio."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.modelos.acceso import Usuario
from app.modelos.organizacion import Finca, Galpon
from app.servicios.alcance import ids_fincas_visibles

router = APIRouter(prefix="/panel", tags=["Panel"])


@router.get("/resumen", summary="Numeros generales de la cuenta y de la finca activa")
def resumen(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("panel", "ver"))):
    fincas = ids_fincas_visibles(db, ctx)

    galpones = 0
    aves = 0
    capacidad = 0
    if ctx.finca_id is not None:
        galpones, aves, capacidad = db.execute(
            select(
                func.count(Galpon.id),
                func.coalesce(func.sum(Galpon.aves_actuales), 0),
                func.coalesce(func.sum(Galpon.capacidad), 0),
            ).where(Galpon.finca_id == ctx.finca_id, Galpon.activo.is_(True))
        ).one()

    usuarios = 0
    if ctx.cuenta_id is not None:
        usuarios = db.scalar(
            select(func.count(Usuario.id)).where(Usuario.cuenta_id == ctx.cuenta_id, Usuario.activo.is_(True))
        )

    finca = db.get(Finca, ctx.finca_id) if ctx.finca_id else None

    return {
        "finca_activa": {"id": finca.id, "nombre": finca.nombre} if finca else None,
        "fincas_visibles": len(fincas),
        "usuarios_activos": int(usuarios or 0),
        "galpones_activos": int(galpones or 0),
        "aves_en_finca": int(aves or 0),
        "capacidad_finca": int(capacidad or 0),
        "ocupacion": round(int(aves or 0) * 100 / int(capacidad), 1) if capacidad else 0.0,
        "solo_lectura": ctx.solo_lectura,
    }
