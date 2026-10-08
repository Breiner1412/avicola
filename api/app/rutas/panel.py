"""Resumen para la pantalla de inicio."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.tiempo import hoy as hoy_en_la_granja
from app.modelos.acceso import Usuario, UsuarioFinca
from app.modelos.alertas import Alerta
from app.modelos.aves import Lote, ProduccionHuevos, StockHuevos
from app.modelos.organizacion import Finca, Galpon
from app.modelos.sensores import LecturaSensor, Sensor
from app.modelos.trabajo import Novedad, Tarea
from app.modelos.ventas import Venta
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles
from app.servicios.ventas import puntos_visibles

router = APIRouter(prefix="/panel", tags=["Panel"])


@router.get("/resumen", summary="Numeros generales de la cuenta y de la finca activa")
def resumen(
    dias: int = Query(14, ge=7, le=60),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("panel", "ver")),
):
    fincas = ids_fincas_visibles(db, ctx)
    hoy = hoy_en_la_granja()
    inicio = hoy - timedelta(days=dias - 1)

    galpones = aves = capacidad = 0
    if ctx.finca_id is not None:
        galpones, aves, capacidad = db.execute(
            select(
                func.count(Galpon.id),
                func.coalesce(func.sum(Galpon.aves_actuales), 0),
                func.coalesce(func.sum(Galpon.capacidad), 0),
            ).where(Galpon.finca_id == ctx.finca_id, Galpon.activo.is_(True))
        ).one()

    usuarios = 0
    if ctx.cuenta_activa_id is not None:
        consulta_usuarios = select(func.count(Usuario.id)).where(
            Usuario.cuenta_id == ctx.cuenta_activa_id, Usuario.activo.is_(True)
        )
        if not ctx.ve_toda_la_cuenta:
            consulta_usuarios = consulta_usuarios.where(
                Usuario.id.in_(select(UsuarioFinca.usuario_id).where(UsuarioFinca.finca_id.in_(fincas or [0])))
            )
        usuarios = db.scalar(consulta_usuarios)

    finca = db.get(Finca, ctx.finca_id) if ctx.finca_id else None
    fincas_consulta = [ctx.finca_id] if ctx.finca_id is not None else (fincas or [0])

    # --- Produccion por dia ---
    filas = db.execute(
        select(ProduccionHuevos.fecha, func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
        .where(ProduccionHuevos.finca_id.in_(fincas_consulta), ProduccionHuevos.fecha.between(inicio, hoy))
        .group_by(ProduccionHuevos.fecha)
    ).all()
    por_dia = {fecha: int(cantidad or 0) for fecha, cantidad in filas}
    produccion = [
        {"fecha": (inicio + timedelta(days=i)).isoformat(), "valor": por_dia.get(inicio + timedelta(days=i), 0)}
        for i in range(dias)
    ]

    # --- Ventas por dia ---
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)] or [0]
    filas = db.execute(
        select(Venta.fecha, func.coalesce(func.sum(Venta.total), 0))
        .where(Venta.punto_venta_id.in_(puntos), Venta.estado == "activa", Venta.fecha.between(inicio, hoy))
        .group_by(Venta.fecha)
    ).all()
    ventas_dia = {fecha: float(total or 0) for fecha, total in filas}
    ventas = [
        {"fecha": (inicio + timedelta(days=i)).isoformat(), "valor": ventas_dia.get(inicio + timedelta(days=i), 0.0)}
        for i in range(dias)
    ]

    # --- Huevos disponibles ---
    disponibles = 0
    if ctx.finca_id is not None:
        disponibles = db.scalar(
            select(func.coalesce(func.sum(StockHuevos.cantidad), 0)).where(StockHuevos.finca_id == ctx.finca_id)
        ) or 0

    # --- Lotes ---
    lotes = db.scalars(
        select(Lote).where(Lote.finca_id.in_(fincas_consulta), Lote.estado == "activo")
    ).all()

    # --- Trabajo de hoy ---
    tareas_hoy = db.scalar(
        select(func.count(Tarea.id)).where(
            Tarea.finca_id.in_(fincas_consulta), Tarea.fecha == hoy, Tarea.estado.in_(("pendiente", "en_proceso"))
        )
    ) or 0
    tareas_atrasadas = db.scalar(
        select(func.count(Tarea.id)).where(
            Tarea.finca_id.in_(fincas_consulta), Tarea.fecha < hoy, Tarea.estado.in_(("pendiente", "en_proceso"))
        )
    ) or 0
    novedades = db.scalar(
        select(func.count(Novedad.id)).where(
            Novedad.finca_id.in_(fincas_consulta), Novedad.estado.in_(("abierta", "en_proceso"))
        )
    ) or 0

    # --- Sensores ---
    sensores = db.scalars(
        select(Sensor).where(Sensor.finca_id.in_(fincas_consulta), Sensor.activo.is_(True))
    ).unique().all()
    sensores_alerta = 0
    for sensor in sensores:
        ultima = db.scalars(
            select(LecturaSensor)
            .where(LecturaSensor.sensor_id == sensor.id)
            .order_by(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc())
            .limit(1)
        ).first()
        if ultima is not None and ultima.fuera_rango:
            sensores_alerta += 1

    # --- Avisos ---
    cuenta = cuenta_filtro(ctx)
    alertas = 0
    if cuenta is not None:
        consulta_alertas = select(func.count(Alerta.id)).where(Alerta.cuenta_id == cuenta, Alerta.activa.is_(True))
        if not ctx.ve_toda_la_cuenta:
            consulta_alertas = consulta_alertas.where(
                or_(Alerta.finca_id.is_(None), Alerta.finca_id.in_(fincas or [0]))
            )
        alertas = db.scalar(consulta_alertas) or 0

    huevos_periodo = sum(d["valor"] for d in produccion)
    ventas_periodo = sum(d["valor"] for d in ventas)

    return {
        "finca_activa": {"id": finca.id, "nombre": finca.nombre} if finca else None,
        "fincas_visibles": len(fincas),
        "usuarios_activos": int(usuarios or 0),
        "galpones_activos": int(galpones or 0),
        "aves_en_finca": int(aves or 0),
        "capacidad_finca": int(capacidad or 0),
        "ocupacion": round(int(aves or 0) * 100 / int(capacidad), 1) if capacidad else 0.0,
        "solo_lectura": ctx.solo_lectura,
        "dias": dias,
        "huevos_periodo": huevos_periodo,
        "huevos_promedio": round(huevos_periodo / dias, 1),
        "huevos_disponibles": int(disponibles),
        "ventas_periodo": ventas_periodo,
        "produccion": produccion,
        "ventas": ventas,
        "lotes_activos": len(lotes),
        "aves_descarte": sum(l.aves_descarte for l in lotes),
        "tareas_hoy": int(tareas_hoy),
        "tareas_atrasadas": int(tareas_atrasadas),
        "novedades_abiertas": int(novedades),
        "sensores": len(sensores),
        "sensores_alerta": sensores_alerta,
        "alertas": int(alertas),
        "otras_fincas": _otras_fincas(db, ctx, fincas, inicio, hoy) if ctx.rol == "supervisor" else [],
    }


def _otras_fincas(db: Session, ctx: Contexto, propias: list[int], inicio: date, hoy: date) -> list[dict]:
    """Resumen de las fincas de la empresa que el supervisor no tiene a cargo.

    Solo numeros generales (aves, huevos del periodo, lotes activos): el detalle
    queda para quien trabaja en esas fincas.
    """
    otras = db.scalars(
        select(Finca)
        .where(Finca.cuenta_id == ctx.cuenta_id, Finca.activo.is_(True), Finca.id.not_in(propias or [0]))
        .order_by(Finca.nombre)
    ).all()
    if not otras:
        return []
    ids = [f.id for f in otras]
    aves = dict(
        db.execute(
            select(Galpon.finca_id, func.coalesce(func.sum(Galpon.aves_actuales), 0))
            .where(Galpon.finca_id.in_(ids), Galpon.activo.is_(True))
            .group_by(Galpon.finca_id)
        ).all()
    )
    huevos = dict(
        db.execute(
            select(ProduccionHuevos.finca_id, func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
            .where(ProduccionHuevos.finca_id.in_(ids), ProduccionHuevos.fecha.between(inicio, hoy))
            .group_by(ProduccionHuevos.finca_id)
        ).all()
    )
    lotes = dict(
        db.execute(
            select(Lote.finca_id, func.count(Lote.id))
            .where(Lote.finca_id.in_(ids), Lote.estado == "activo")
            .group_by(Lote.finca_id)
        ).all()
    )
    return [
        {
            "id": f.id,
            "nombre": f.nombre,
            "aves": int(aves.get(f.id, 0)),
            "huevos_periodo": int(huevos.get(f.id, 0)),
            "lotes_activos": int(lotes.get(f.id, 0)),
        }
        for f in otras
    ]
