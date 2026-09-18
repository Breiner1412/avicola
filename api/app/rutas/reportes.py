"""Reportes: numeros del periodo y descarga en CSV."""

import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import datos_invalidos
from app.modelos.aves import ConsumoAlimento, Lote, MovimientoAves, ProduccionHuevos, TipoHuevo
from app.modelos.inventario import Articulo, Bodega, Existencia
from app.modelos.trabajo import Novedad, Tarea
from app.modelos.ventas import Venta, VentaDetalle, VentaPago
from app.servicios.alcance import ids_fincas_visibles
from app.servicios.ventas import puntos_visibles

router = APIRouter(prefix="/reportes", tags=["Reportes"])

TIPOS_CSV = ("produccion", "ventas", "aves", "alimento", "existencias", "novedades", "tareas")


def _rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    fin = hasta or date.today()
    inicio = desde or (fin - timedelta(days=29))
    if inicio > fin:
        raise datos_invalidos("La fecha inicial no puede ser mayor que la final")
    return inicio, fin


def _fincas(db: Session, ctx: Contexto) -> list[int]:
    if ctx.finca_id is not None:
        return [ctx.finca_id]
    return ids_fincas_visibles(db, ctx) or [0]


@router.get("/resumen", summary="Numeros del periodo")
def resumen(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("reportes", "ver")),
):
    inicio, fin = _rango(desde, hasta)
    fincas = _fincas(db, ctx)
    dias = (fin - inicio).days + 1

    # --- Produccion ---
    huevos, dias_con_registro = db.execute(
        select(
            func.coalesce(func.sum(ProduccionHuevos.cantidad), 0),
            func.count(func.distinct(ProduccionHuevos.fecha)),
        ).where(
            ProduccionHuevos.finca_id.in_(fincas),
            ProduccionHuevos.fecha.between(inicio, fin),
        )
    ).one()

    por_tipo = db.execute(
        select(TipoHuevo.nombre, func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
        .join(ProduccionHuevos, ProduccionHuevos.tipo_huevo_id == TipoHuevo.id)
        .where(ProduccionHuevos.finca_id.in_(fincas), ProduccionHuevos.fecha.between(inicio, fin))
        .group_by(TipoHuevo.nombre)
        .order_by(func.sum(ProduccionHuevos.cantidad).desc())
    ).all()

    # --- Aves ---
    lotes = db.scalars(select(Lote).where(Lote.finca_id.in_(fincas))).all()
    ids_lotes = [l.id for l in lotes] or [0]
    aves_vivas = sum(l.aves_actuales for l in lotes)
    descarte = sum(l.aves_descarte for l in lotes)

    movimientos = db.execute(
        select(MovimientoAves.tipo, func.coalesce(func.sum(MovimientoAves.cantidad), 0))
        .where(
            MovimientoAves.lote_id.in_(ids_lotes),
            MovimientoAves.fecha.between(inicio, fin),
            MovimientoAves.anulado.is_(False),
        )
        .group_by(MovimientoAves.tipo)
    ).all()
    por_movimiento = {tipo: int(cantidad or 0) for tipo, cantidad in movimientos}

    # --- Alimento ---
    alimento_kg, alimento_costo = db.execute(
        select(
            func.coalesce(func.sum(ConsumoAlimento.cantidad), 0),
            func.coalesce(func.sum(ConsumoAlimento.costo), 0),
        ).where(ConsumoAlimento.lote_id.in_(ids_lotes), ConsumoAlimento.fecha.between(inicio, fin))
    ).one()

    # --- Ventas ---
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)] or [0]
    ventas_activas = (
        select(Venta)
        .where(Venta.punto_venta_id.in_(puntos), Venta.fecha.between(inicio, fin), Venta.estado == "activa")
        .subquery()
    )
    cantidad_ventas, total_ventas = db.execute(
        select(func.count(ventas_activas.c.id), func.coalesce(func.sum(ventas_activas.c.total), 0))
    ).one()
    efectivo = db.scalar(
        select(func.coalesce(func.sum(VentaPago.monto), 0))
        .join(ventas_activas, VentaPago.venta_id == ventas_activas.c.id)
        .where(VentaPago.es_efectivo.is_(True))
    ) or 0
    anuladas = db.scalar(
        select(func.count(Venta.id)).where(
            Venta.punto_venta_id.in_(puntos), Venta.fecha.between(inicio, fin), Venta.estado == "anulada"
        )
    ) or 0
    por_clase = db.execute(
        select(VentaDetalle.clase, func.coalesce(func.sum(VentaDetalle.subtotal), 0))
        .join(ventas_activas, VentaDetalle.venta_id == ventas_activas.c.id)
        .group_by(VentaDetalle.clase)
    ).all()

    # --- Inventario bajo minimo ---
    bodegas = [b.id for b in db.scalars(select(Bodega).where(Bodega.cuenta_id == (ctx.cuenta_activa_id or 0))).all()]
    bajos = []
    if bodegas:
        filas = db.execute(
            select(Articulo.nombre, Articulo.unidad, Articulo.stock_minimo, func.coalesce(func.sum(Existencia.cantidad), 0))
            .join(Existencia, Existencia.articulo_id == Articulo.id, isouter=True)
            .where(Articulo.activo.is_(True), Articulo.stock_minimo > 0)
            .group_by(Articulo.id, Articulo.nombre, Articulo.unidad, Articulo.stock_minimo)
        ).all()
        bajos = [
            {"articulo": nombre, "unidad": unidad, "hay": float(hay or 0), "minimo": float(minimo)}
            for nombre, unidad, minimo, hay in filas
            if float(hay or 0) < float(minimo)
        ][:10]

    # --- Trabajo ---
    tareas_pendientes = db.scalar(
        select(func.count(Tarea.id)).where(
            Tarea.finca_id.in_(fincas), Tarea.estado.in_(("pendiente", "en_proceso"))
        )
    ) or 0
    novedades_abiertas = db.scalar(
        select(func.count(Novedad.id)).where(
            Novedad.finca_id.in_(fincas), Novedad.estado.in_(("abierta", "en_proceso"))
        )
    ) or 0

    muertes = por_movimiento.get("muerte", 0)
    aves_iniciales = sum(l.aves_iniciales for l in lotes) or 0

    return {
        "desde": inicio,
        "hasta": fin,
        "dias": dias,
        "produccion": {
            "huevos": int(huevos or 0),
            "promedio_diario": round(int(huevos or 0) / dias, 1),
            "dias_con_registro": int(dias_con_registro or 0),
            "por_tipo": [{"tipo": nombre, "cantidad": int(cantidad or 0)} for nombre, cantidad in por_tipo],
        },
        "aves": {
            "vivas": aves_vivas,
            "descarte": descarte,
            "muertes": muertes,
            "descartadas": por_movimiento.get("descarte", 0),
            "vendidas": por_movimiento.get("venta", 0),
            "mortalidad_porcentaje": round(muertes * 100 / aves_iniciales, 2) if aves_iniciales else 0.0,
        },
        "alimento": {
            "kg": float(alimento_kg or 0),
            "costo": float(alimento_costo or 0),
            "kg_por_ave": round(float(alimento_kg or 0) / aves_vivas, 3) if aves_vivas else 0.0,
        },
        "ventas": {
            "cantidad": int(cantidad_ventas or 0),
            "total": float(total_ventas or 0),
            "efectivo": float(efectivo or 0),
            "otros_medios": float((total_ventas or 0) - (efectivo or 0)),
            "anuladas": int(anuladas),
            "por_clase": [{"clase": clase, "total": float(total or 0)} for clase, total in por_clase],
        },
        "inventario": {"bajo_minimo": bajos},
        "trabajo": {"tareas_pendientes": int(tareas_pendientes), "novedades_abiertas": int(novedades_abiertas)},
    }


def _csv(nombre: str, encabezados: list[str], filas: list[list]) -> StreamingResponse:
    memoria = io.StringIO()
    escritor = csv.writer(memoria, delimiter=";")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    memoria.seek(0)
    # BOM para que Excel abra bien las tildes
    contenido = io.BytesIO(("﻿" + memoria.getvalue()).encode("utf-8"))
    return StreamingResponse(
        contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'},
    )


@router.get("/csv", summary="Descargar un reporte en CSV")
def descargar(
    tipo: str = Query(..., description="produccion, ventas, aves, alimento, existencias, novedades o tareas"),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("reportes", "ver")),
):
    if tipo not in TIPOS_CSV:
        raise datos_invalidos(f"Reporte no valido. Opciones: {', '.join(TIPOS_CSV)}")

    inicio, fin = _rango(desde, hasta)
    fincas = _fincas(db, ctx)
    ids_lotes = [l.id for l in db.scalars(select(Lote).where(Lote.finca_id.in_(fincas))).all()] or [0]

    if tipo == "produccion":
        filas = db.execute(
            select(ProduccionHuevos.fecha, Lote.codigo, TipoHuevo.nombre, ProduccionHuevos.cantidad)
            .join(Lote, ProduccionHuevos.lote_id == Lote.id)
            .join(TipoHuevo, ProduccionHuevos.tipo_huevo_id == TipoHuevo.id)
            .where(ProduccionHuevos.finca_id.in_(fincas), ProduccionHuevos.fecha.between(inicio, fin))
            .order_by(ProduccionHuevos.fecha)
        ).all()
        return _csv("produccion", ["Fecha", "Lote", "Tipo", "Huevos"], [list(f) for f in filas])

    if tipo == "ventas":
        puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)] or [0]
        filas = db.execute(
            select(
                Venta.fecha, Venta.numero, VentaDetalle.descripcion, VentaDetalle.cantidad,
                VentaDetalle.precio_unitario, VentaDetalle.subtotal, Venta.estado, Venta.usuario_nombre,
            )
            .join(VentaDetalle, VentaDetalle.venta_id == Venta.id)
            .where(Venta.punto_venta_id.in_(puntos), Venta.fecha.between(inicio, fin))
            .order_by(Venta.fecha, Venta.id)
        ).all()
        return _csv(
            "ventas",
            ["Fecha", "Numero", "Producto", "Cantidad", "Precio", "Subtotal", "Estado", "Vendio"],
            [list(f) for f in filas],
        )

    if tipo == "aves":
        filas = db.execute(
            select(MovimientoAves.fecha, Lote.codigo, MovimientoAves.tipo, MovimientoAves.cantidad,
                   MovimientoAves.motivo, MovimientoAves.anulado, MovimientoAves.usuario_nombre)
            .join(Lote, MovimientoAves.lote_id == Lote.id)
            .where(MovimientoAves.lote_id.in_(ids_lotes), MovimientoAves.fecha.between(inicio, fin))
            .order_by(MovimientoAves.fecha)
        ).all()
        return _csv(
            "movimientos_aves",
            ["Fecha", "Lote", "Tipo", "Cantidad", "Motivo", "Anulado", "Registro"],
            [[f[0], f[1], f[2], f[3], f[4] or "", "si" if f[5] else "no", f[6] or ""] for f in filas],
        )

    if tipo == "alimento":
        filas = db.execute(
            select(ConsumoAlimento.fecha, Lote.codigo, Articulo.nombre, ConsumoAlimento.cantidad, ConsumoAlimento.costo)
            .join(Lote, ConsumoAlimento.lote_id == Lote.id)
            .join(Articulo, ConsumoAlimento.articulo_id == Articulo.id)
            .where(ConsumoAlimento.lote_id.in_(ids_lotes), ConsumoAlimento.fecha.between(inicio, fin))
            .order_by(ConsumoAlimento.fecha)
        ).all()
        return _csv("alimento", ["Fecha", "Lote", "Alimento", "Cantidad", "Costo"], [list(f) for f in filas])

    if tipo == "existencias":
        filas = db.execute(
            select(Bodega.nombre, Articulo.codigo, Articulo.nombre, Articulo.unidad, Existencia.cantidad,
                   Existencia.costo_promedio, Articulo.stock_minimo)
            .join(Articulo, Existencia.articulo_id == Articulo.id)
            .join(Bodega, Existencia.bodega_id == Bodega.id)
            .where(Bodega.cuenta_id == (ctx.cuenta_activa_id or 0))
            .order_by(Bodega.nombre, Articulo.nombre)
        ).all()
        return _csv(
            "existencias",
            ["Bodega", "Codigo", "Articulo", "Unidad", "Cantidad", "Costo promedio", "Minimo"],
            [list(f) for f in filas],
        )

    if tipo == "novedades":
        filas = db.execute(
            select(Novedad.fecha, Novedad.categoria, Novedad.subtipo, Novedad.titulo, Novedad.gravedad,
                   Novedad.estado, Novedad.aves_afectadas, Novedad.costo_estimado, Novedad.reportado_por)
            .where(Novedad.finca_id.in_(fincas), Novedad.fecha.between(inicio, fin))
            .order_by(Novedad.fecha)
        ).all()
        return _csv(
            "novedades",
            ["Fecha", "Categoria", "Subtipo", "Novedad", "Gravedad", "Estado", "Aves afectadas", "Costo", "Reporto"],
            [[f[0], f[1], f[2] or "", f[3], f[4], f[5], f[6], f[7], f[8] or ""] for f in filas],
        )

    filas = db.execute(
        select(Tarea.fecha, Tarea.titulo, Tarea.prioridad, Tarea.estado, Tarea.asignado_nombre,
               Tarea.terminada_por, Tarea.notas)
        .where(Tarea.finca_id.in_(fincas), Tarea.fecha.between(inicio, fin))
        .order_by(Tarea.fecha)
    ).all()
    return _csv(
        "tareas",
        ["Fecha", "Tarea", "Prioridad", "Estado", "Asignada a", "Termino", "Notas"],
        [[f[0], f[1], f[2], f[3], f[4] or "", f[5] or "", f[6] or ""] for f in filas],
    )
