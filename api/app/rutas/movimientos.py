"""Entradas, salidas, traslados y ajustes de inventario."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import no_encontrado
from app.esquemas.comunes import Pagina
from app.esquemas.inventario import (
    AnularMovimiento,
    ItemSalida,
    MovimientoCrear,
    MovimientoSalida,
)
from app.modelos.inventario import MovimientoInventario, MovimientoItem
from app.servicios.alcance import cuenta_filtro
from app.servicios.inventario import anular_movimiento, bodegas_visibles, crear_movimiento

router = APIRouter(prefix="/movimientos", tags=["Movimientos de inventario"])


def _salida(movimiento: MovimientoInventario) -> MovimientoSalida:
    return MovimientoSalida(
        id=movimiento.id,
        tipo=movimiento.tipo,
        fecha=movimiento.fecha,
        bodega_id=movimiento.bodega_id,
        bodega_nombre=movimiento.bodega.nombre if movimiento.bodega else "",
        bodega_destino_id=movimiento.bodega_destino_id,
        bodega_destino_nombre=movimiento.bodega_destino.nombre if movimiento.bodega_destino else None,
        proveedor_id=movimiento.proveedor_id,
        proveedor_nombre=movimiento.proveedor.nombre if movimiento.proveedor else None,
        motivo=movimiento.motivo,
        documento=movimiento.documento,
        observaciones=movimiento.observaciones,
        total=float(movimiento.total or 0),
        usuario_nombre=movimiento.usuario_nombre,
        anulado=movimiento.anulado,
        anulado_en=movimiento.anulado_en,
        anulado_por=movimiento.anulado_por,
        motivo_anulacion=movimiento.motivo_anulacion,
        creado_en=movimiento.creado_en,
        items=[
            ItemSalida(
                id=item.id,
                articulo_id=item.articulo_id,
                articulo_codigo=item.articulo.codigo if item.articulo else "",
                articulo_nombre=item.articulo.nombre if item.articulo else "",
                unidad=item.articulo.unidad if item.articulo else "",
                cantidad=float(item.cantidad or 0),
                cantidad_aplicada=float(item.cantidad_aplicada or 0),
                costo_unitario=float(item.costo_unitario or 0),
                lote=item.lote,
                vencimiento=item.vencimiento,
            )
            for item in movimiento.items
        ],
    )


def _movimiento_de(db: Session, ctx: Contexto, movimiento_id: int) -> MovimientoInventario:
    movimiento = db.get(MovimientoInventario, movimiento_id)
    if movimiento is None:
        raise no_encontrado("El movimiento no existe")
    if not ctx.es_plataforma and movimiento.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("El movimiento no existe")

    visibles = {b.id for b in bodegas_visibles(db, ctx, todas=True, incluir_inactivas=True)}
    if movimiento.bodega_id not in visibles and movimiento.bodega_destino_id not in visibles:
        raise no_encontrado("El movimiento no existe")
    return movimiento


@router.get("", response_model=Pagina[MovimientoSalida], summary="Movimientos de inventario")
def listar(
    tipo: str | None = Query(None, pattern="^(entrada|salida|traslado|ajuste)$"),
    bodega_id: int | None = Query(None),
    articulo_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    incluir_anulados: bool = Query(True),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(25, ge=1, le=200),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_inventario", "ver")),
):
    visibles = [b.id for b in bodegas_visibles(db, ctx, todas=True, incluir_inactivas=True)]
    if not visibles:
        return Pagina[MovimientoSalida](total=0, pagina=pagina, tamano=tamano, datos=[])

    consulta = select(MovimientoInventario).where(
        MovimientoInventario.bodega_id.in_(visibles)
        | MovimientoInventario.bodega_destino_id.in_(visibles)
    )
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(MovimientoInventario.cuenta_id == cuenta)
    if tipo:
        consulta = consulta.where(MovimientoInventario.tipo == tipo)
    if bodega_id:
        consulta = consulta.where(
            (MovimientoInventario.bodega_id == bodega_id)
            | (MovimientoInventario.bodega_destino_id == bodega_id)
        )
    if desde:
        consulta = consulta.where(MovimientoInventario.fecha >= desde)
    if hasta:
        consulta = consulta.where(MovimientoInventario.fecha <= hasta)
    if not incluir_anulados:
        consulta = consulta.where(MovimientoInventario.anulado.is_(False))
    if articulo_id:
        consulta = consulta.where(
            MovimientoInventario.id.in_(
                select(MovimientoItem.movimiento_id).where(MovimientoItem.articulo_id == articulo_id)
            )
        )

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.scalars(
        consulta.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).unique().all()

    return Pagina[MovimientoSalida](
        total=total, pagina=pagina, tamano=tamano, datos=[_salida(m) for m in filas]
    )


@router.post("", response_model=MovimientoSalida, status_code=201, summary="Registrar movimiento")
def crear(
    datos: MovimientoCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_inventario", "crear")),
):
    movimiento = crear_movimiento(db, ctx, datos)
    db.commit()
    db.refresh(movimiento)
    return _salida(movimiento)


@router.get("/{movimiento_id}", response_model=MovimientoSalida, summary="Ver un movimiento")
def ver(
    movimiento_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_inventario", "ver")),
):
    return _salida(_movimiento_de(db, ctx, movimiento_id))


@router.post("/{movimiento_id}/anular", response_model=MovimientoSalida, summary="Anular un movimiento")
def anular(
    movimiento_id: int,
    datos: AnularMovimiento,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_inventario", "editar")),
):
    movimiento = _movimiento_de(db, ctx, movimiento_id)
    anular_movimiento(db, ctx, movimiento, datos.motivo)
    db.commit()
    db.refresh(movimiento)
    return _salida(movimiento)
