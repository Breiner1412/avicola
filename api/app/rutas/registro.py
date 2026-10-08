"""Consulta del registro de cambios."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.tiempo import fin_del_dia, inicio_del_dia
from app.esquemas.comunes import Pagina
from app.esquemas.registro import AuditoriaSalida
from app.modelos.registro import Auditoria
from app.servicios.alcance import ids_fincas_visibles

router = APIRouter(prefix="/auditoria", tags=["Registro de cambios"])


@router.get("", response_model=Pagina[AuditoriaSalida], summary="Ver el registro de cambios")
def listar(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    entidad: str | None = Query(None),
    accion: str | None = Query(None),
    usuario_id: int | None = Query(None),
    solo_finca_activa: bool = Query(False),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(50, ge=1, le=200),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("auditoria", "ver")),
):
    consulta = select(Auditoria)
    if not ctx.es_plataforma:
        consulta = consulta.where(Auditoria.cuenta_id == ctx.cuenta_id)
        if not ctx.ve_toda_la_cuenta:
            # Quien no ve toda la cuenta solo ve lo que paso en sus fincas
            consulta = consulta.where(Auditoria.finca_id.in_(ids_fincas_visibles(db, ctx) or [0]))
    if solo_finca_activa and ctx.finca_id is not None:
        consulta = consulta.where(Auditoria.finca_id == ctx.finca_id)
    # Los dias son de la granja; el registro guarda la hora en UTC
    if desde:
        consulta = consulta.where(Auditoria.creado_en >= inicio_del_dia(desde))
    if hasta:
        consulta = consulta.where(Auditoria.creado_en <= fin_del_dia(hasta))
    if entidad:
        consulta = consulta.where(Auditoria.entidad == entidad)
    if accion:
        consulta = consulta.where(Auditoria.accion == accion)
    if usuario_id:
        consulta = consulta.where(Auditoria.usuario_id == usuario_id)

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.scalars(
        consulta.order_by(Auditoria.id.desc()).offset((pagina - 1) * tamano).limit(tamano)
    ).all()

    return Pagina[AuditoriaSalida](
        total=total, pagina=pagina, tamano=tamano,
        datos=[AuditoriaSalida.model_validate(f) for f in filas],
    )
