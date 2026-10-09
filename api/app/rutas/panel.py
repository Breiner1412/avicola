"""Resumen para la pantalla de inicio."""

from datetime import date, timedelta

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


def _galpones_de_la_finca(db: Session, finca_id: int | None) -> tuple[int, int, int]:
    """(galpones activos, aves, capacidad) de la finca activa."""
    if finca_id is None:
        return 0, 0, 0
    galpones, aves, capacidad = db.execute(
        select(
            func.count(Galpon.id),
            func.coalesce(func.sum(Galpon.aves_actuales), 0),
            func.coalesce(func.sum(Galpon.capacidad), 0),
        ).where(Galpon.finca_id == finca_id, Galpon.activo.is_(True))
    ).one()
    return int(galpones or 0), int(aves or 0), int(capacidad or 0)


def _usuarios_activos(db: Session, ctx: Contexto, fincas: list[int]) -> int:
    if ctx.cuenta_activa_id is None:
        return 0
    consulta = select(func.count(Usuario.id)).where(Usuario.cuenta_id == ctx.cuenta_activa_id, Usuario.activo.is_(True))
    if not ctx.ve_toda_la_cuenta:
        consulta = consulta.where(
            Usuario.id.in_(select(UsuarioFinca.usuario_id).where(UsuarioFinca.finca_id.in_(fincas or [0])))
        )
    return int(db.scalar(consulta) or 0)


def _serie_diaria(filas, inicio: date, dias: int, tipo=int) -> list[dict]:
    """Un punto por dia del periodo (los dias sin datos quedan en cero)."""
    por_dia = {fecha: tipo(valor or 0) for fecha, valor in filas}
    return [
        {"fecha": (inicio + timedelta(days=i)).isoformat(), "valor": por_dia.get(inicio + timedelta(days=i), tipo(0))}
        for i in range(dias)
    ]


def _trabajo(db: Session, fincas: list[int], hoy: date) -> tuple[int, int, int]:
    """(tareas de hoy, tareas atrasadas, novedades abiertas)."""
    pendientes = Tarea.estado.in_(("pendiente", "en_proceso"))
    tareas_hoy = db.scalar(select(func.count(Tarea.id)).where(Tarea.finca_id.in_(fincas), Tarea.fecha == hoy, pendientes))
    atrasadas = db.scalar(select(func.count(Tarea.id)).where(Tarea.finca_id.in_(fincas), Tarea.fecha < hoy, pendientes))
    novedades = db.scalar(
        select(func.count(Novedad.id)).where(Novedad.finca_id.in_(fincas), Novedad.estado.in_(("abierta", "en_proceso")))
    )
    return int(tareas_hoy or 0), int(atrasadas or 0), int(novedades or 0)


def _sensores(db: Session, fincas: list[int]) -> tuple[int, int]:
    """(sensores activos, cuantos tienen la ultima medicion fuera de rango), en dos consultas."""
    ids = list(db.scalars(select(Sensor.id).where(Sensor.finca_id.in_(fincas), Sensor.activo.is_(True))).all())
    if not ids:
        return 0, 0
    # La ultima por fecha de medicion (las lecturas pueden llegar desordenadas)
    orden = (
        func.row_number()
        .over(partition_by=LecturaSensor.sensor_id, order_by=(LecturaSensor.medido_en.desc(), LecturaSensor.id.desc()))
        .label("orden")
    )
    ultimas = (
        select(LecturaSensor.fuera_rango, orden).where(LecturaSensor.sensor_id.in_(ids)).subquery()
    )
    fuera = db.scalar(
        select(func.count()).select_from(ultimas).where(ultimas.c.orden == 1, ultimas.c.fuera_rango.is_(True))
    )
    return len(ids), int(fuera or 0)


def _avisos(db: Session, ctx: Contexto, fincas: list[int]) -> int:
    cuenta = cuenta_filtro(ctx)
    if cuenta is None:
        return 0
    consulta = select(func.count(Alerta.id)).where(Alerta.cuenta_id == cuenta, Alerta.activa.is_(True))
    if not ctx.ve_toda_la_cuenta:
        consulta = consulta.where(or_(Alerta.finca_id.is_(None), Alerta.finca_id.in_(fincas or [0])))
    return int(db.scalar(consulta) or 0)


@router.get("/resumen", summary="Numeros generales de la cuenta y de la finca activa")
def resumen(
    dias: int = Query(14, ge=7, le=60),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("panel", "ver")),
):
    fincas = ids_fincas_visibles(db, ctx)
    hoy = hoy_en_la_granja()
    inicio = hoy - timedelta(days=dias - 1)
    finca = db.get(Finca, ctx.finca_id) if ctx.finca_id else None
    fincas_consulta = [ctx.finca_id] if ctx.finca_id is not None else (fincas or [0])

    galpones, aves, capacidad = _galpones_de_la_finca(db, ctx.finca_id)
    produccion = _serie_diaria(
        db.execute(
            select(ProduccionHuevos.fecha, func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
            .where(ProduccionHuevos.finca_id.in_(fincas_consulta), ProduccionHuevos.fecha.between(inicio, hoy))
            .group_by(ProduccionHuevos.fecha)
        ).all(),
        inicio,
        dias,
    )
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)] or [0]
    ventas = _serie_diaria(
        db.execute(
            select(Venta.fecha, func.coalesce(func.sum(Venta.total), 0))
            .where(Venta.punto_venta_id.in_(puntos), Venta.estado == "activa", Venta.fecha.between(inicio, hoy))
            .group_by(Venta.fecha)
        ).all(),
        inicio,
        dias,
        tipo=float,
    )
    disponibles = 0
    if ctx.finca_id is not None:
        disponibles = db.scalar(
            select(func.coalesce(func.sum(StockHuevos.cantidad), 0)).where(StockHuevos.finca_id == ctx.finca_id)
        ) or 0
    lotes = db.scalars(select(Lote).where(Lote.finca_id.in_(fincas_consulta), Lote.estado == "activo")).all()
    tareas_hoy, tareas_atrasadas, novedades = _trabajo(db, fincas_consulta, hoy)
    sensores, sensores_alerta = _sensores(db, fincas_consulta)
    huevos_periodo = sum(d["valor"] for d in produccion)

    return {
        "finca_activa": {"id": finca.id, "nombre": finca.nombre} if finca else None,
        "fincas_visibles": len(fincas),
        "usuarios_activos": _usuarios_activos(db, ctx, fincas),
        "galpones_activos": galpones,
        "aves_en_finca": aves,
        "capacidad_finca": capacidad,
        "ocupacion": round(aves * 100 / capacidad, 1) if capacidad else 0.0,
        "solo_lectura": ctx.solo_lectura,
        "dias": dias,
        "huevos_periodo": huevos_periodo,
        "huevos_promedio": round(huevos_periodo / dias, 1),
        "huevos_disponibles": int(disponibles),
        "ventas_periodo": sum(d["valor"] for d in ventas),
        "produccion": produccion,
        "ventas": ventas,
        "lotes_activos": len(lotes),
        "aves_descarte": sum(lote.aves_descarte for lote in lotes),
        "tareas_hoy": tareas_hoy,
        "tareas_atrasadas": tareas_atrasadas,
        "novedades_abiertas": novedades,
        "sensores": sensores,
        "sensores_alerta": sensores_alerta,
        "alertas": _avisos(db, ctx, fincas),
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
