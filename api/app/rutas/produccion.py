"""Recoleccion de huevos y existencias de huevos por finca."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos
from app.esquemas.aves import (
    ProduccionCrear,
    ProduccionDia,
    StockHuevosSalida,
    TipoHuevoCrear,
    TipoHuevoSalida,
)
from app.modelos.aves import ProduccionHuevos, StockHuevos, TipoHuevo
from app.servicios.alcance import cuenta_objetivo
from app.servicios.aves import lote_de, lotes_visibles, mover_stock_huevos, tipos_huevo_de

router = APIRouter(tags=["Produccion de huevos"])

HUEVOS_POR_PANAL = 30


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/tipos-huevo", response_model=list[TipoHuevoSalida], summary="Tipos de huevo")
def listar_tipos(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("produccion", "ver"))):
    return tipos_huevo_de(db, ctx)


@router.post("/tipos-huevo", response_model=TipoHuevoSalida, status_code=201, summary="Agregar un tipo de huevo")
def crear_tipo(
    datos: TipoHuevoCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("produccion", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    if any(t.nombre.lower() == datos.nombre.lower() for t in tipos_huevo_de(db, ctx)):
        raise conflicto("Ya existe un tipo de huevo con ese nombre")

    tipo = TipoHuevo(cuenta_id=cuenta_id, nombre=datos.nombre, orden=datos.orden, comercial=datos.comercial)
    db.add(tipo)
    db.flush()
    registrar(db, ctx, "crear", "tipos_huevo", tipo.id, f"Agrego el tipo de huevo {tipo.nombre}")
    db.commit()
    db.refresh(tipo)
    return tipo


@router.get("/produccion", response_model=list[ProduccionDia], summary="Recoleccion por dia")
def listar(
    lote_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("produccion", "ver")),
):
    lotes = {lote.id: lote for lote in lotes_visibles(db, ctx, todas_las_fincas=True)}
    ids = [lote_id] if lote_id else list(lotes.keys())
    if lote_id:
        lote_de(db, ctx, lote_id)
    if not ids:
        return []

    consulta = select(ProduccionHuevos).where(ProduccionHuevos.lote_id.in_(ids))
    if desde:
        consulta = consulta.where(ProduccionHuevos.fecha >= desde)
    if hasta:
        consulta = consulta.where(ProduccionHuevos.fecha <= hasta)

    filas = db.scalars(consulta.order_by(ProduccionHuevos.fecha.desc()).limit(2000)).unique().all()

    agrupado: dict[tuple[int, date], ProduccionDia] = {}
    for fila in filas:
        clave = (fila.lote_id, fila.fecha)
        lote = lotes.get(fila.lote_id)
        if clave not in agrupado:
            aves = (lote.aves_actuales if lote else 0) or 0
            agrupado[clave] = ProduccionDia(
                fecha=fila.fecha,
                lote_id=fila.lote_id,
                lote_codigo=lote.codigo if lote else "",
                aves=aves,
                total=0,
                comercial=0,
                porcentaje_postura=0.0,
                detalles={},
            )
        dia = agrupado[clave]
        dia.detalles[fila.tipo.nombre] = fila.cantidad
        dia.total += fila.cantidad
        if fila.tipo.comercial:
            dia.comercial += fila.cantidad

    for dia in agrupado.values():
        dia.porcentaje_postura = round(dia.total * 100 / dia.aves, 1) if dia.aves else 0.0

    return sorted(agrupado.values(), key=lambda d: (d.fecha, d.lote_codigo), reverse=True)


@router.post("/produccion", response_model=ProduccionDia, status_code=201, summary="Registrar la recoleccion del dia")
def registrar_produccion(
    datos: ProduccionCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("produccion", "crear")),
):
    lote = lote_de(db, ctx, datos.lote_id)
    if lote.estado == "cerrado":
        raise datos_invalidos("El lote esta cerrado")
    if datos.fecha > date.today():
        raise datos_invalidos("No se puede registrar produccion de una fecha futura")

    tipos = {t.id: t for t in tipos_huevo_de(db, ctx)}
    salida = ProduccionDia(
        fecha=datos.fecha,
        lote_id=lote.id,
        lote_codigo=lote.codigo,
        aves=lote.aves_actuales,
        total=0,
        comercial=0,
        porcentaje_postura=0.0,
        detalles={},
    )

    for detalle in datos.detalles:
        tipo = tipos.get(detalle.tipo_huevo_id)
        if tipo is None:
            raise datos_invalidos("Ese tipo de huevo no existe")

        fila = db.scalars(
            select(ProduccionHuevos).where(
                ProduccionHuevos.lote_id == lote.id,
                ProduccionHuevos.fecha == datos.fecha,
                ProduccionHuevos.tipo_huevo_id == tipo.id,
            )
        ).first()

        anterior = fila.cantidad if fila else 0
        if fila is None:
            fila = ProduccionHuevos(
                cuenta_id=lote.cuenta_id,
                finca_id=lote.finca_id,
                lote_id=lote.id,
                tipo_huevo_id=tipo.id,
                fecha=datos.fecha,
                cantidad=detalle.cantidad,
                usuario_nombre=ctx.usuario.nombre_completo,
                creado_en=ahora(),
            )
            db.add(fila)
        else:
            fila.cantidad = detalle.cantidad
            fila.usuario_nombre = ctx.usuario.nombre_completo

        # Solo los huevos que se venden entran al stock
        if tipo.comercial:
            mover_stock_huevos(db, lote.finca_id, tipo.id, detalle.cantidad - anterior)

        salida.detalles[tipo.nombre] = detalle.cantidad
        salida.total += detalle.cantidad
        if tipo.comercial:
            salida.comercial += detalle.cantidad

    salida.porcentaje_postura = round(salida.total * 100 / lote.aves_actuales, 1) if lote.aves_actuales else 0.0

    registrar(
        db, ctx, "crear", "produccion_huevos", lote.id,
        f"Recoleccion del {datos.fecha} en el lote {lote.codigo}: {salida.total} huevos",
        salida.detalles,
    )
    db.commit()
    return salida


@router.get("/stock-huevos", response_model=list[StockHuevosSalida], summary="Huevos disponibles en la finca")
def stock(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("produccion", "ver", con_finca=True))):
    filas = db.execute(
        select(StockHuevos, TipoHuevo)
        .join(TipoHuevo, StockHuevos.tipo_huevo_id == TipoHuevo.id)
        .where(StockHuevos.finca_id == ctx.finca_id)
        .order_by(TipoHuevo.orden)
    ).all()

    return [
        StockHuevosSalida(
            tipo_huevo_id=tipo.id,
            tipo=tipo.nombre,
            comercial=tipo.comercial,
            cantidad=fila.cantidad,
            panales=round(fila.cantidad / HUEVOS_POR_PANAL, 2),
        )
        for fila, tipo in filas
    ]


@router.get("/produccion/resumen", summary="Totales de produccion de la finca activa")
def resumen(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("produccion", "ver", con_finca=True)),
):
    consulta = select(
        func.coalesce(func.sum(ProduccionHuevos.cantidad), 0),
        func.count(func.distinct(ProduccionHuevos.fecha)),
    ).where(ProduccionHuevos.finca_id == ctx.finca_id)
    if desde:
        consulta = consulta.where(ProduccionHuevos.fecha >= desde)
    if hasta:
        consulta = consulta.where(ProduccionHuevos.fecha <= hasta)

    total, dias = db.execute(consulta).one()
    disponibles = db.scalar(
        select(func.coalesce(func.sum(StockHuevos.cantidad), 0)).where(StockHuevos.finca_id == ctx.finca_id)
    ) or 0

    return {
        "huevos_recolectados": int(total or 0),
        "dias_con_registro": int(dias or 0),
        "promedio_diario": round(int(total or 0) / int(dias), 1) if dias else 0,
        "huevos_disponibles": int(disponibles),
        "panales_disponibles": round(int(disponibles) / HUEVOS_POR_PANAL, 2),
    }
