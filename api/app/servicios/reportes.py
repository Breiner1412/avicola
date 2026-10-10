"""Calculos de los reportes: numeros del periodo y filas de cada CSV."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto
from app.core.errores import datos_invalidos
from app.core.tiempo import hoy
from app.modelos.aves import ConsumoAlimento, Lote, MovimientoAves, ProduccionHuevos, TipoHuevo
from app.modelos.inventario import Articulo, Bodega, Existencia
from app.modelos.trabajo import Novedad, Tarea
from app.modelos.ventas import Venta, VentaDetalle, VentaPago
from app.servicios.alcance import ids_fincas_visibles
from app.servicios.ventas import puntos_visibles


@dataclass(frozen=True)
class Periodo:
    """Lo que necesita cada parte de un reporte: fechas, fincas y quien pregunta."""

    db: Session
    ctx: Contexto
    inicio: date
    fin: date
    fincas: list[int]

    @property
    def dias(self) -> int:
        return (self.fin - self.inicio).days + 1

    def lotes(self) -> list[Lote]:
        return list(self.db.scalars(select(Lote).where(Lote.finca_id.in_(self.fincas))).all())

    def ids_lotes(self) -> list[int]:
        return [lote.id for lote in self.lotes()] or [0]

    def puntos(self) -> list[int]:
        return [p.id for p in puntos_visibles(self.db, self.ctx, incluir_inactivos=True)] or [0]


def periodo(db: Session, ctx: Contexto, desde: date | None, hasta: date | None) -> Periodo:
    fin = hasta or hoy()
    inicio = desde or (fin - timedelta(days=29))
    if inicio > fin:
        raise datos_invalidos("La fecha inicial no puede ser mayor que la final")
    fincas = [ctx.finca_id] if ctx.finca_id is not None else (ids_fincas_visibles(db, ctx) or [0])
    return Periodo(db=db, ctx=ctx, inicio=inicio, fin=fin, fincas=fincas)


# ------------------------------- Resumen -------------------------------
def _produccion(p: Periodo) -> dict:
    huevos, dias_con_registro = p.db.execute(
        select(
            func.coalesce(func.sum(ProduccionHuevos.cantidad), 0),
            func.count(func.distinct(ProduccionHuevos.fecha)),
        ).where(ProduccionHuevos.finca_id.in_(p.fincas), ProduccionHuevos.fecha.between(p.inicio, p.fin))
    ).one()
    por_tipo = p.db.execute(
        select(TipoHuevo.nombre, func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
        .join(ProduccionHuevos, ProduccionHuevos.tipo_huevo_id == TipoHuevo.id)
        .where(ProduccionHuevos.finca_id.in_(p.fincas), ProduccionHuevos.fecha.between(p.inicio, p.fin))
        .group_by(TipoHuevo.nombre)
        .order_by(func.sum(ProduccionHuevos.cantidad).desc())
    ).all()
    return {
        "huevos": int(huevos or 0),
        "promedio_diario": round(int(huevos or 0) / p.dias, 1),
        "dias_con_registro": int(dias_con_registro or 0),
        "por_tipo": [{"tipo": nombre, "cantidad": int(cantidad or 0)} for nombre, cantidad in por_tipo],
    }


def _aves(p: Periodo, lotes: list[Lote]) -> dict:
    movimientos = p.db.execute(
        select(MovimientoAves.tipo, func.coalesce(func.sum(MovimientoAves.cantidad), 0))
        .where(
            MovimientoAves.lote_id.in_([lote.id for lote in lotes] or [0]),
            MovimientoAves.fecha.between(p.inicio, p.fin),
            MovimientoAves.anulado.is_(False),
        )
        .group_by(MovimientoAves.tipo)
    ).all()
    por_movimiento = {tipo: int(cantidad or 0) for tipo, cantidad in movimientos}
    muertes = por_movimiento.get("muerte", 0)
    aves_iniciales = sum(lote.aves_iniciales for lote in lotes)
    return {
        "vivas": sum(lote.aves_actuales for lote in lotes),
        "descarte": sum(lote.aves_descarte for lote in lotes),
        "muertes": muertes,
        "descartadas": por_movimiento.get("descarte", 0),
        "vendidas": por_movimiento.get("venta", 0),
        "mortalidad_porcentaje": round(muertes * 100 / aves_iniciales, 2) if aves_iniciales else 0.0,
    }


def _alimento(p: Periodo, lotes: list[Lote]) -> dict:
    kilos, costo = p.db.execute(
        select(
            func.coalesce(func.sum(ConsumoAlimento.cantidad), 0),
            func.coalesce(func.sum(ConsumoAlimento.costo), 0),
        ).where(
            ConsumoAlimento.lote_id.in_([lote.id for lote in lotes] or [0]),
            ConsumoAlimento.fecha.between(p.inicio, p.fin),
        )
    ).one()
    vivas = sum(lote.aves_actuales for lote in lotes)
    return {
        "kg": float(kilos or 0),
        "costo": float(costo or 0),
        "kg_por_ave": round(float(kilos or 0) / vivas, 3) if vivas else 0.0,
    }


def _ventas(p: Periodo) -> dict:
    puntos = p.puntos()
    activas = (
        select(Venta)
        .where(Venta.punto_venta_id.in_(puntos), Venta.fecha.between(p.inicio, p.fin), Venta.estado == "activa")
        .subquery()
    )
    cantidad, total = p.db.execute(
        select(func.count(activas.c.id), func.coalesce(func.sum(activas.c.total), 0))
    ).one()
    efectivo = p.db.scalar(
        select(func.coalesce(func.sum(VentaPago.monto), 0))
        .join(activas, VentaPago.venta_id == activas.c.id)
        .where(VentaPago.es_efectivo.is_(True))
    ) or 0
    anuladas = p.db.scalar(
        select(func.count(Venta.id)).where(
            Venta.punto_venta_id.in_(puntos), Venta.fecha.between(p.inicio, p.fin), Venta.estado == "anulada"
        )
    ) or 0
    por_clase = p.db.execute(
        select(VentaDetalle.clase, func.coalesce(func.sum(VentaDetalle.subtotal), 0))
        .join(activas, VentaDetalle.venta_id == activas.c.id)
        .group_by(VentaDetalle.clase)
    ).all()
    return {
        "cantidad": int(cantidad or 0),
        "total": float(total or 0),
        "efectivo": float(efectivo),
        "otros_medios": float((total or 0) - efectivo),
        "anuladas": int(anuladas),
        "por_clase": [{"clase": clase, "total": float(suma or 0)} for clase, suma in por_clase],
    }


def _bajo_minimo(p: Periodo) -> list[dict]:
    """Articulos por debajo del minimo, solo con las bodegas de la cuenta que ve el usuario."""
    cuenta = p.ctx.cuenta_activa_id or 0
    bodegas = p.db.scalars(
        select(Bodega.id).where(
            Bodega.cuenta_id == cuenta,
            or_(Bodega.finca_id.is_(None), Bodega.finca_id.in_(p.fincas)),
        )
    ).all()
    if not bodegas:
        return []
    filas = p.db.execute(
        select(Articulo.nombre, Articulo.unidad, Articulo.stock_minimo, func.coalesce(func.sum(Existencia.cantidad), 0))
        .join(
            Existencia,
            and_(Existencia.articulo_id == Articulo.id, Existencia.bodega_id.in_(bodegas)),
            isouter=True,
        )
        .where(Articulo.cuenta_id == cuenta, Articulo.activo.is_(True), Articulo.stock_minimo > 0)
        .group_by(Articulo.id, Articulo.nombre, Articulo.unidad, Articulo.stock_minimo)
    ).all()
    return [
        {"articulo": nombre, "unidad": unidad, "hay": float(hay or 0), "minimo": float(minimo)}
        for nombre, unidad, minimo, hay in filas
        if float(hay or 0) < float(minimo)
    ][:10]


def _trabajo(p: Periodo) -> dict:
    tareas = p.db.scalar(
        select(func.count(Tarea.id)).where(Tarea.finca_id.in_(p.fincas), Tarea.estado.in_(("pendiente", "en_proceso")))
    ) or 0
    novedades = p.db.scalar(
        select(func.count(Novedad.id)).where(
            Novedad.finca_id.in_(p.fincas), Novedad.estado.in_(("abierta", "en_proceso"))
        )
    ) or 0
    return {"tareas_pendientes": int(tareas), "novedades_abiertas": int(novedades)}


def resumen(p: Periodo) -> dict:
    lotes = p.lotes()
    return {
        "desde": p.inicio,
        "hasta": p.fin,
        "dias": p.dias,
        "produccion": _produccion(p),
        "aves": _aves(p, lotes),
        "alimento": _alimento(p, lotes),
        "ventas": _ventas(p),
        "inventario": {"bajo_minimo": _bajo_minimo(p)},
        "trabajo": _trabajo(p),
    }


# ------------------------------- CSV -------------------------------
# Cada reporte devuelve (nombre del archivo, encabezados, filas)
ArchivoCsv = tuple[str, list[str], list[list]]


def _csv_produccion(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(ProduccionHuevos.fecha, Lote.codigo, TipoHuevo.nombre, ProduccionHuevos.cantidad)
        .join(Lote, ProduccionHuevos.lote_id == Lote.id)
        .join(TipoHuevo, ProduccionHuevos.tipo_huevo_id == TipoHuevo.id)
        .where(ProduccionHuevos.finca_id.in_(p.fincas), ProduccionHuevos.fecha.between(p.inicio, p.fin))
        .order_by(ProduccionHuevos.fecha)
    ).all()
    return "produccion", ["Fecha", "Lote", "Tipo", "Huevos"], [list(f) for f in filas]


def _csv_ventas(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(
            Venta.fecha, Venta.numero, VentaDetalle.descripcion, VentaDetalle.cantidad,
            VentaDetalle.precio_unitario, VentaDetalle.subtotal, Venta.estado, Venta.usuario_nombre,
        )
        .join(VentaDetalle, VentaDetalle.venta_id == Venta.id)
        .where(Venta.punto_venta_id.in_(p.puntos()), Venta.fecha.between(p.inicio, p.fin))
        .order_by(Venta.fecha, Venta.id)
    ).all()
    encabezados = ["Fecha", "Numero", "Producto", "Cantidad", "Precio", "Subtotal", "Estado", "Vendio"]
    return "ventas", encabezados, [list(f) for f in filas]


def _csv_aves(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(MovimientoAves.fecha, Lote.codigo, MovimientoAves.tipo, MovimientoAves.cantidad,
               MovimientoAves.motivo, MovimientoAves.anulado, MovimientoAves.usuario_nombre)
        .join(Lote, MovimientoAves.lote_id == Lote.id)
        .where(MovimientoAves.lote_id.in_(p.ids_lotes()), MovimientoAves.fecha.between(p.inicio, p.fin))
        .order_by(MovimientoAves.fecha)
    ).all()
    return (
        "movimientos_aves",
        ["Fecha", "Lote", "Tipo", "Cantidad", "Motivo", "Anulado", "Registro"],
        [[f[0], f[1], f[2], f[3], f[4] or "", "si" if f[5] else "no", f[6] or ""] for f in filas],
    )


def _csv_alimento(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(ConsumoAlimento.fecha, Lote.codigo, Articulo.nombre, ConsumoAlimento.cantidad, ConsumoAlimento.costo)
        .join(Lote, ConsumoAlimento.lote_id == Lote.id)
        .join(Articulo, ConsumoAlimento.articulo_id == Articulo.id)
        .where(ConsumoAlimento.lote_id.in_(p.ids_lotes()), ConsumoAlimento.fecha.between(p.inicio, p.fin))
        .order_by(ConsumoAlimento.fecha)
    ).all()
    return "alimento", ["Fecha", "Lote", "Alimento", "Cantidad", "Costo"], [list(f) for f in filas]


def _csv_existencias(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(Bodega.nombre, Articulo.codigo, Articulo.nombre, Articulo.unidad, Existencia.cantidad,
               Existencia.costo_promedio, Articulo.stock_minimo)
        .join(Articulo, Existencia.articulo_id == Articulo.id)
        .join(Bodega, Existencia.bodega_id == Bodega.id)
        .where(
            Bodega.cuenta_id == (p.ctx.cuenta_activa_id or 0),
            or_(Bodega.finca_id.is_(None), Bodega.finca_id.in_(p.fincas)),
        )
        .order_by(Bodega.nombre, Articulo.nombre)
    ).all()
    encabezados = ["Bodega", "Codigo", "Articulo", "Unidad", "Cantidad", "Costo promedio", "Minimo"]
    return "existencias", encabezados, [list(f) for f in filas]


def _csv_novedades(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(Novedad.fecha, Novedad.categoria, Novedad.subtipo, Novedad.titulo, Novedad.gravedad,
               Novedad.estado, Novedad.aves_afectadas, Novedad.costo_estimado, Novedad.reportado_por)
        .where(Novedad.finca_id.in_(p.fincas), Novedad.fecha.between(p.inicio, p.fin))
        .order_by(Novedad.fecha)
    ).all()
    return (
        "novedades",
        ["Fecha", "Categoria", "Subtipo", "Novedad", "Gravedad", "Estado", "Aves afectadas", "Costo", "Reporto"],
        [[f[0], f[1], f[2] or "", f[3], f[4], f[5], f[6], f[7], f[8] or ""] for f in filas],
    )


def _csv_tareas(p: Periodo) -> ArchivoCsv:
    filas = p.db.execute(
        select(Tarea.fecha, Tarea.titulo, Tarea.prioridad, Tarea.estado, Tarea.asignado_nombre,
               Tarea.terminada_por, Tarea.notas)
        .where(Tarea.finca_id.in_(p.fincas), Tarea.fecha.between(p.inicio, p.fin))
        .order_by(Tarea.fecha)
    ).all()
    return (
        "tareas",
        ["Fecha", "Tarea", "Prioridad", "Estado", "Asignada a", "Termino", "Notas"],
        [[f[0], f[1], f[2], f[3], f[4] or "", f[5] or "", f[6] or ""] for f in filas],
    )


CSV_POR_TIPO = {
    "produccion": _csv_produccion,
    "ventas": _csv_ventas,
    "aves": _csv_aves,
    "alimento": _csv_alimento,
    "existencias": _csv_existencias,
    "novedades": _csv_novedades,
    "tareas": _csv_tareas,
}
