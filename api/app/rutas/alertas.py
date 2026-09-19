"""Los avisos que salen en la campana."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import no_encontrado
from app.esquemas.alertas import AlertaSalida, ResumenAlertas
from app.esquemas.comunes import Mensaje
from app.modelos.alertas import Alerta
from app.servicios.alcance import cuenta_filtro
from app.servicios.alertas import recalcular

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("", response_model=ResumenAlertas, summary="Que hay que mirar")
def listar(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("panel", "ver"))):
    alertas = recalcular(db, ctx)
    db.commit()

    return ResumenAlertas(
        total=len(alertas),
        sin_leer=sum(1 for a in alertas if not a.leida),
        criticas=sum(1 for a in alertas if a.nivel == "critico"),
        alertas=[AlertaSalida.model_validate(a) for a in alertas],
    )


@router.post("/leidas", response_model=Mensaje, summary="Marcar todo como visto")
def marcar_todas(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("panel", "ver"))):
    cuenta_id = cuenta_filtro(ctx)
    if cuenta_id is not None:
        db.execute(
            update(Alerta)
            .where(Alerta.cuenta_id == cuenta_id, Alerta.activa.is_(True), Alerta.leida.is_(False))
            .values(leida=True, actualizado_en=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        db.commit()
    return Mensaje(mensaje="Avisos marcados como vistos")


@router.post("/{alerta_id}/leida", response_model=AlertaSalida, summary="Marcar un aviso como visto")
def marcar(
    alerta_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("panel", "ver")),
):
    alerta = db.get(Alerta, alerta_id)
    if alerta is None or alerta.cuenta_id != cuenta_filtro(ctx):
        raise no_encontrado("El aviso no existe")

    alerta.leida = True
    alerta.actualizado_en = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(alerta)
    return AlertaSalida.model_validate(alerta)
