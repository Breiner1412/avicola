"""Vacunas, medicamentos y tratamientos."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import datos_invalidos, no_encontrado
from app.esquemas.aves import SanidadCrear, SanidadSalida
from app.esquemas.comunes import Mensaje
from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.modelos.aves import AplicacionSanitaria, Lote
from app.modelos.organizacion import Galpon
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles
from app.servicios.aves import dec, lote_de, refuerzos_pendientes
from app.servicios.inventario import articulo_de, bodega_de, crear_movimiento, existencia

router = APIRouter(prefix="/sanidad", tags=["Vacunas y tratamientos"])


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _salida(db: Session, aplicacion: AplicacionSanitaria) -> SanidadSalida:
    lote = db.get(Lote, aplicacion.lote_id) if aplicacion.lote_id else None
    galpon = db.get(Galpon, aplicacion.galpon_id) if aplicacion.galpon_id else None
    return SanidadSalida(
        id=aplicacion.id,
        fecha=aplicacion.fecha,
        tipo=aplicacion.tipo,
        producto=aplicacion.producto,
        lote_id=aplicacion.lote_id,
        lote_codigo=lote.codigo if lote else None,
        galpon_id=aplicacion.galpon_id,
        galpon_nombre=galpon.nombre if galpon else None,
        articulo_id=aplicacion.articulo_id,
        cantidad_usada=float(aplicacion.cantidad_usada) if aplicacion.cantidad_usada is not None else None,
        lote_producto=aplicacion.lote_producto,
        dosis=aplicacion.dosis,
        via=aplicacion.via,
        aves_tratadas=aplicacion.aves_tratadas,
        responsable=aplicacion.responsable,
        proximo_refuerzo=aplicacion.proximo_refuerzo,
        observaciones=aplicacion.observaciones,
        usuario_nombre=aplicacion.usuario_nombre,
        creado_en=aplicacion.creado_en,
    )


@router.get("", response_model=list[SanidadSalida], summary="Aplicaciones registradas")
def listar(
    lote_id: int | None = Query(None),
    tipo: str | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sanidad", "ver")),
):
    consulta = select(AplicacionSanitaria)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(AplicacionSanitaria.cuenta_id == cuenta)
    if ctx.finca_id is not None:
        consulta = consulta.where(AplicacionSanitaria.finca_id == ctx.finca_id)
    else:
        consulta = consulta.where(AplicacionSanitaria.finca_id.in_(ids_fincas_visibles(db, ctx) or [0]))
    if lote_id:
        lote_de(db, ctx, lote_id)
        consulta = consulta.where(AplicacionSanitaria.lote_id == lote_id)
    if tipo:
        consulta = consulta.where(AplicacionSanitaria.tipo == tipo)
    if desde:
        consulta = consulta.where(AplicacionSanitaria.fecha >= desde)
    if hasta:
        consulta = consulta.where(AplicacionSanitaria.fecha <= hasta)

    filas = db.scalars(consulta.order_by(AplicacionSanitaria.fecha.desc(), AplicacionSanitaria.id.desc()).limit(500)).all()
    return [_salida(db, fila) for fila in filas]


@router.get("/proximas", response_model=list[SanidadSalida], summary="Refuerzos que vienen")
def proximas(
    dias: int = Query(30, ge=1, le=365),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sanidad", "ver")),
):
    limite = date.today() + timedelta(days=dias)
    consulta = select(AplicacionSanitaria).where(
        AplicacionSanitaria.proximo_refuerzo.is_not(None),
        AplicacionSanitaria.proximo_refuerzo <= limite,
    )
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(AplicacionSanitaria.cuenta_id == cuenta)
    if ctx.finca_id is not None:
        consulta = consulta.where(AplicacionSanitaria.finca_id == ctx.finca_id)

    filas = db.scalars(consulta.order_by(AplicacionSanitaria.proximo_refuerzo)).all()
    return [_salida(db, fila) for fila in refuerzos_pendientes(db, list(filas))]


@router.post("", response_model=SanidadSalida, status_code=201, summary="Registrar una vacuna o tratamiento")
def crear(
    datos: SanidadCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sanidad", "crear", con_finca=True)),
):
    lote = lote_de(db, ctx, datos.lote_id) if datos.lote_id else None

    galpon_id = datos.galpon_id or (lote.galpon_id if lote else None)
    if galpon_id is not None:
        galpon = db.get(Galpon, galpon_id)
        if galpon is None or galpon.finca_id != ctx.finca_id:
            raise datos_invalidos("El galpon no existe en esta finca")

    movimiento_id = None
    costo = dec(0)

    # Si se indica el articulo, tambien se descuenta de la bodega
    if datos.articulo_id and datos.cantidad_usada:
        if not datos.bodega_id:
            raise datos_invalidos("Indica de que bodega sale el producto")
        articulo = articulo_de(db, ctx, datos.articulo_id)
        bodega = bodega_de(db, ctx, datos.bodega_id)
        costo = dec(datos.cantidad_usada) * dec(existencia(db, bodega.id, articulo.id).costo_promedio)

        movimiento = crear_movimiento(
            db,
            ctx,
            MovimientoCrear(
                tipo="salida",
                fecha=datos.fecha,
                bodega_id=bodega.id,
                motivo=datos.tipo,
                observaciones=f"{datos.producto}{f' - lote {lote.codigo}' if lote else ''}",
                items=[ItemEntrada(articulo_id=articulo.id, cantidad=datos.cantidad_usada, costo_unitario=0)],
            ),
        )
        movimiento_id = movimiento.id

    aplicacion = AplicacionSanitaria(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        lote_id=lote.id if lote else None,
        galpon_id=galpon_id,
        fecha=datos.fecha,
        tipo=datos.tipo,
        producto=datos.producto,
        articulo_id=datos.articulo_id,
        cantidad_usada=dec(datos.cantidad_usada) if datos.cantidad_usada is not None else None,
        costo=costo,
        bodega_id=datos.bodega_id,
        movimiento_id=movimiento_id,
        lote_producto=datos.lote_producto,
        dosis=datos.dosis,
        via=datos.via,
        aves_tratadas=datos.aves_tratadas or (lote.aves_actuales if lote else None),
        responsable=datos.responsable or ctx.usuario.nombre_completo,
        proximo_refuerzo=datos.proximo_refuerzo,
        observaciones=datos.observaciones,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(aplicacion)
    db.flush()
    registrar(
        db, ctx, "crear", "aplicaciones_sanitarias", aplicacion.id,
        f"{datos.tipo.capitalize()} {datos.producto}" + (f" en el lote {lote.codigo}" if lote else ""),
        {"via": datos.via, "dosis": datos.dosis},
    )
    db.commit()
    db.refresh(aplicacion)
    return _salida(db, aplicacion)


@router.delete("/{aplicacion_id}", response_model=Mensaje, summary="Borrar un registro mal hecho")
def borrar(
    aplicacion_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("sanidad", "borrar")),
):
    aplicacion = db.get(AplicacionSanitaria, aplicacion_id)
    cuenta = cuenta_filtro(ctx)
    if aplicacion is None or (cuenta is not None and aplicacion.cuenta_id != cuenta):
        raise no_encontrado("El registro no existe")
    if aplicacion.movimiento_id:
        raise datos_invalidos(
            "Ese registro descontó producto de la bodega. Anula primero el movimiento de inventario."
        )

    registrar(db, ctx, "borrar", "aplicaciones_sanitarias", aplicacion.id, f"Borro el registro de {aplicacion.producto}")
    db.delete(aplicacion)
    db.commit()
    return Mensaje(mensaje="Registro borrado")
