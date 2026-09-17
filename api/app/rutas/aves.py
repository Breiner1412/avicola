"""Razas, lotes, movimientos de aves, pesajes, alimentacion y balance."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado
from app.esquemas.aves import (
    AnularMovimientoAves,
    BalanceLote,
    CerrarLote,
    ConsumoCrear,
    ConsumoSalida,
    LoteActualizar,
    LoteCrear,
    LoteSalida,
    MovimientoAvesCrear,
    MovimientoAvesSalida,
    PesajeCrear,
    PesajeSalida,
    RazaCrear,
    RazaSalida,
)
from app.esquemas.comunes import Mensaje
from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.modelos.aves import (
    AplicacionSanitaria,
    TipoHuevo,
    ConsumoAlimento,
    Lote,
    MovimientoAves,
    Pesaje,
    ProduccionHuevos,
    Raza,
)
from app.modelos.organizacion import Galpon
from app.servicios.alcance import cuenta_filtro, cuenta_objetivo
from app.servicios.aves import (
    ahora,
    anular_movimiento_aves,
    cerrar_lote,
    crear_lote,
    crear_movimiento_aves,
    dec,
    edad_dias,
    lote_de,
    lotes_visibles,
)
from app.servicios.inventario import articulo_de, bodega_de, crear_movimiento, existencia

router = APIRouter(tags=["Aves"])


def _lote_salida(db: Session, lote: Lote) -> LoteSalida:
    galpon = db.get(Galpon, lote.galpon_id)
    dias = edad_dias(lote)
    mortalidad = max(0, lote.aves_iniciales - lote.aves_actuales - lote.aves_descarte)
    return LoteSalida(
        id=lote.id,
        cuenta_id=lote.cuenta_id,
        finca_id=lote.finca_id,
        galpon_id=lote.galpon_id,
        galpon_nombre=galpon.nombre if galpon else "",
        raza_id=lote.raza_id,
        raza_nombre=lote.raza.nombre if lote.raza else None,
        codigo=lote.codigo,
        proposito=lote.proposito,
        fecha_ingreso=lote.fecha_ingreso,
        edad_dias=dias,
        edad_semanas=dias // 7,
        aves_iniciales=lote.aves_iniciales,
        aves_actuales=lote.aves_actuales,
        aves_descarte=lote.aves_descarte,
        mortalidad=mortalidad,
        mortalidad_porcentaje=round(mortalidad * 100 / lote.aves_iniciales, 2) if lote.aves_iniciales else 0.0,
        costo_ave=float(lote.costo_ave or 0),
        estado=lote.estado,
        fecha_cierre=lote.fecha_cierre,
        observaciones=lote.observaciones,
    )


# ------------------------------ Razas ------------------------------
@router.get("/razas", response_model=list[RazaSalida], summary="Razas disponibles")
def listar_razas(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("lotes", "ver"))):
    cuenta = cuenta_filtro(ctx)
    return db.scalars(
        select(Raza).where(or_(Raza.cuenta_id.is_(None), Raza.cuenta_id == cuenta)).order_by(Raza.nombre)
    ).all()


@router.post("/razas", response_model=RazaSalida, status_code=201, summary="Agregar una raza")
def crear_raza(
    datos: RazaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("lotes", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    if db.scalars(
        select(Raza.id).where(or_(Raza.cuenta_id.is_(None), Raza.cuenta_id == cuenta_id), Raza.nombre == datos.nombre)
    ).first():
        raise conflicto("Ya existe una raza con ese nombre")

    raza = Raza(cuenta_id=cuenta_id, nombre=datos.nombre, proposito=datos.proposito)
    db.add(raza)
    db.flush()
    registrar(db, ctx, "crear", "razas", raza.id, f"Agrego la raza {raza.nombre}")
    db.commit()
    db.refresh(raza)
    return raza


# ------------------------------ Lotes ------------------------------
@router.get("/lotes", response_model=list[LoteSalida], summary="Lotes de la finca activa")
def listar_lotes(
    solo_activos: bool = Query(False),
    todas_las_fincas: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("lotes", "ver")),
):
    return [_lote_salida(db, lote) for lote in lotes_visibles(db, ctx, solo_activos, todas_las_fincas)]


@router.post("/lotes", response_model=LoteSalida, status_code=201, summary="Ingresar un lote")
def nuevo_lote(
    datos: LoteCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("lotes", "crear", con_finca=True)),
):
    lote = crear_lote(db, ctx, datos)
    db.commit()
    db.refresh(lote)
    return _lote_salida(db, lote)


@router.get("/lotes/{lote_id}", response_model=LoteSalida, summary="Ver un lote")
def ver_lote(lote_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("lotes", "ver"))):
    return _lote_salida(db, lote_de(db, ctx, lote_id))


@router.patch("/lotes/{lote_id}", response_model=LoteSalida, summary="Editar un lote")
def editar_lote(
    lote_id: int,
    datos: LoteActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("lotes", "editar")),
):
    lote = lote_de(db, ctx, lote_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "codigo" in cambios and db.scalars(
        select(Lote.id).where(Lote.finca_id == lote.finca_id, Lote.codigo == cambios["codigo"], Lote.id != lote.id)
    ).first():
        raise conflicto("Ya existe otro lote con ese codigo en la finca")

    for campo, valor in cambios.items():
        setattr(lote, campo, dec(valor) if campo == "costo_ave" else valor)
    registrar(db, ctx, "editar", "lotes", lote.id, f"Edito el lote {lote.codigo}", cambios)
    db.commit()
    db.refresh(lote)
    return _lote_salida(db, lote)


@router.post("/lotes/{lote_id}/cerrar", response_model=LoteSalida, summary="Cerrar un lote")
def cerrar(
    lote_id: int,
    datos: CerrarLote,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("lotes", "editar")),
):
    lote = lote_de(db, ctx, lote_id)
    cerrar_lote(db, ctx, lote, datos.fecha, datos.observaciones)
    db.commit()
    db.refresh(lote)
    return _lote_salida(db, lote)


# ----------------------- Movimientos de aves -----------------------
@router.get("/movimientos-aves", response_model=list[MovimientoAvesSalida], summary="Movimientos de aves")
def listar_movimientos(
    lote_id: int | None = Query(None),
    tipo: str | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_aves", "ver")),
):
    lotes = {lote.id: lote for lote in lotes_visibles(db, ctx, todas_las_fincas=True)}
    if lote_id is not None:
        lote_de(db, ctx, lote_id)
        ids = [lote_id]
    else:
        ids = list(lotes.keys())
    if not ids:
        return []

    consulta = select(MovimientoAves).where(MovimientoAves.lote_id.in_(ids))
    if tipo:
        consulta = consulta.where(MovimientoAves.tipo == tipo)
    if desde:
        consulta = consulta.where(MovimientoAves.fecha >= desde)
    if hasta:
        consulta = consulta.where(MovimientoAves.fecha <= hasta)

    filas = db.scalars(
        consulta.order_by(MovimientoAves.fecha.desc(), MovimientoAves.id.desc()).limit(500)
    ).unique().all()

    return [
        MovimientoAvesSalida(
            id=m.id,
            lote_id=m.lote_id,
            lote_codigo=m.lote.codigo if m.lote else "",
            fecha=m.fecha,
            tipo=m.tipo,
            cantidad=m.cantidad,
            galpon_destino_id=m.galpon_destino_id,
            peso_kg=float(m.peso_kg) if m.peso_kg is not None else None,
            motivo=m.motivo,
            observaciones=m.observaciones,
            usuario_nombre=m.usuario_nombre,
            anulado=m.anulado,
            anulado_por=m.anulado_por,
            motivo_anulacion=m.motivo_anulacion,
            creado_en=m.creado_en,
        )
        for m in filas
    ]


@router.post("/movimientos-aves", response_model=MovimientoAvesSalida, status_code=201, summary="Registrar aves que entran o salen")
def nuevo_movimiento(
    datos: MovimientoAvesCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_aves", "crear")),
):
    movimiento = crear_movimiento_aves(db, ctx, datos)
    db.commit()
    db.refresh(movimiento)
    return MovimientoAvesSalida(
        id=movimiento.id,
        lote_id=movimiento.lote_id,
        lote_codigo=movimiento.lote.codigo if movimiento.lote else "",
        fecha=movimiento.fecha,
        tipo=movimiento.tipo,
        cantidad=movimiento.cantidad,
        galpon_destino_id=movimiento.galpon_destino_id,
        peso_kg=float(movimiento.peso_kg) if movimiento.peso_kg is not None else None,
        motivo=movimiento.motivo,
        observaciones=movimiento.observaciones,
        usuario_nombre=movimiento.usuario_nombre,
        anulado=movimiento.anulado,
        anulado_por=movimiento.anulado_por,
        motivo_anulacion=movimiento.motivo_anulacion,
        creado_en=movimiento.creado_en,
    )


@router.post("/movimientos-aves/{movimiento_id}/anular", response_model=Mensaje, summary="Anular un movimiento de aves")
def anular(
    movimiento_id: int,
    datos: AnularMovimientoAves,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("movimientos_aves", "editar")),
):
    movimiento = db.get(MovimientoAves, movimiento_id)
    if movimiento is None:
        raise no_encontrado("El movimiento no existe")
    lote_de(db, ctx, movimiento.lote_id)

    anular_movimiento_aves(db, ctx, movimiento, datos.motivo)
    db.commit()
    return Mensaje(mensaje="Movimiento anulado y aves devueltas al lote")


# ----------------------------- Pesajes -----------------------------
@router.get("/pesajes", response_model=list[PesajeSalida], summary="Pesajes del lote")
def listar_pesajes(
    lote_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("pesajes", "ver")),
):
    lote_de(db, ctx, lote_id)
    filas = db.scalars(
        select(Pesaje).where(Pesaje.lote_id == lote_id).order_by(Pesaje.fecha.desc())
    ).all()
    return [
        PesajeSalida(
            id=p.id,
            lote_id=p.lote_id,
            fecha=p.fecha,
            aves_muestra=p.aves_muestra,
            peso_total_kg=float(p.peso_total_kg),
            peso_promedio_kg=float(p.peso_promedio_kg),
            edad_dias=p.edad_dias,
            observaciones=p.observaciones,
            usuario_nombre=p.usuario_nombre,
        )
        for p in filas
    ]


@router.post("/pesajes", response_model=PesajeSalida, status_code=201, summary="Registrar un pesaje")
def nuevo_pesaje(
    datos: PesajeCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("pesajes", "crear")),
):
    lote = lote_de(db, ctx, datos.lote_id)
    promedio = dec(datos.peso_total_kg) / dec(datos.aves_muestra)

    pesaje = Pesaje(
        lote_id=lote.id,
        fecha=datos.fecha,
        aves_muestra=datos.aves_muestra,
        peso_total_kg=dec(datos.peso_total_kg),
        peso_promedio_kg=promedio,
        edad_dias=edad_dias(lote, datos.fecha),
        observaciones=datos.observaciones,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(pesaje)
    db.flush()
    registrar(
        db, ctx, "crear", "pesajes", pesaje.id,
        f"Pesaje del lote {lote.codigo}: {float(promedio):.3f} kg por ave",
    )
    db.commit()
    db.refresh(pesaje)
    return PesajeSalida(
        id=pesaje.id,
        lote_id=pesaje.lote_id,
        fecha=pesaje.fecha,
        aves_muestra=pesaje.aves_muestra,
        peso_total_kg=float(pesaje.peso_total_kg),
        peso_promedio_kg=float(pesaje.peso_promedio_kg),
        edad_dias=pesaje.edad_dias,
        observaciones=pesaje.observaciones,
        usuario_nombre=pesaje.usuario_nombre,
    )


# ------------------------ Consumo de alimento ------------------------
@router.get("/consumo-alimento", response_model=list[ConsumoSalida], summary="Alimento entregado al lote")
def listar_consumo(
    lote_id: int,
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("alimentacion", "ver")),
):
    lote_de(db, ctx, lote_id)
    consulta = select(ConsumoAlimento).where(ConsumoAlimento.lote_id == lote_id)
    if desde:
        consulta = consulta.where(ConsumoAlimento.fecha >= desde)
    if hasta:
        consulta = consulta.where(ConsumoAlimento.fecha <= hasta)

    filas = db.scalars(consulta.order_by(ConsumoAlimento.fecha.desc(), ConsumoAlimento.id.desc())).unique().all()
    return [
        ConsumoSalida(
            id=c.id,
            lote_id=c.lote_id,
            fecha=c.fecha,
            articulo_id=c.articulo_id,
            articulo_nombre=c.articulo.nombre if c.articulo else "",
            unidad=c.articulo.unidad if c.articulo else "",
            bodega_id=c.bodega_id,
            cantidad=float(c.cantidad),
            costo=float(c.costo or 0),
            observaciones=c.observaciones,
            usuario_nombre=c.usuario_nombre,
        )
        for c in filas
    ]


@router.post("/consumo-alimento", response_model=ConsumoSalida, status_code=201, summary="Registrar alimento entregado")
def nuevo_consumo(
    datos: ConsumoCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("alimentacion", "crear")),
):
    lote = lote_de(db, ctx, datos.lote_id)
    articulo = articulo_de(db, ctx, datos.articulo_id)
    bodega = bodega_de(db, ctx, datos.bodega_id)

    costo_unitario = dec(existencia(db, bodega.id, articulo.id).costo_promedio)

    # Sale de la bodega como cualquier otra salida, para que el kardex cuadre
    movimiento = crear_movimiento(
        db,
        ctx,
        MovimientoCrear(
            tipo="salida",
            fecha=datos.fecha,
            bodega_id=bodega.id,
            motivo="alimentacion",
            observaciones=f"Lote {lote.codigo}",
            items=[ItemEntrada(articulo_id=articulo.id, cantidad=datos.cantidad, costo_unitario=0)],
        ),
    )

    consumo = ConsumoAlimento(
        lote_id=lote.id,
        fecha=datos.fecha,
        articulo_id=articulo.id,
        bodega_id=bodega.id,
        cantidad=dec(datos.cantidad),
        costo=dec(datos.cantidad) * costo_unitario,
        movimiento_id=movimiento.id,
        observaciones=datos.observaciones,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(consumo)
    db.flush()
    registrar(
        db, ctx, "crear", "consumos_alimento", consumo.id,
        f"Entrego {datos.cantidad} {articulo.unidad} de {articulo.nombre} al lote {lote.codigo}",
    )
    db.commit()
    db.refresh(consumo)
    return ConsumoSalida(
        id=consumo.id,
        lote_id=consumo.lote_id,
        fecha=consumo.fecha,
        articulo_id=consumo.articulo_id,
        articulo_nombre=articulo.nombre,
        unidad=articulo.unidad,
        bodega_id=consumo.bodega_id,
        cantidad=float(consumo.cantidad),
        costo=float(consumo.costo or 0),
        observaciones=consumo.observaciones,
        usuario_nombre=consumo.usuario_nombre,
    )


# ----------------------------- Balance -----------------------------
@router.get("/lotes/{lote_id}/balance", response_model=BalanceLote, summary="Balance del lote")
def balance(lote_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("lotes", "ver"))):
    lote = lote_de(db, ctx, lote_id)
    salida = _lote_salida(db, lote)

    dias = max(1, (  (lote.fecha_cierre or date.today()) - lote.fecha_ingreso).days)

    alimento_kg, alimento_costo = db.execute(
        select(
            func.coalesce(func.sum(ConsumoAlimento.cantidad), 0),
            func.coalesce(func.sum(ConsumoAlimento.costo), 0),
        ).where(ConsumoAlimento.lote_id == lote.id)
    ).one()

    huevos_total = db.scalar(
        select(func.coalesce(func.sum(ProduccionHuevos.cantidad), 0)).where(ProduccionHuevos.lote_id == lote.id)
    ) or 0
    huevos_comerciales = db.scalar(
        select(func.coalesce(func.sum(ProduccionHuevos.cantidad), 0))
        .join(TipoHuevo, ProduccionHuevos.tipo_huevo_id == TipoHuevo.id)
        .where(ProduccionHuevos.lote_id == lote.id, TipoHuevo.comercial.is_(True))
    ) or 0

    pesaje = db.scalars(
        select(Pesaje).where(Pesaje.lote_id == lote.id).order_by(Pesaje.fecha.desc()).limit(1)
    ).first()

    costo_sanidad = float(
        db.scalar(
            select(func.coalesce(func.sum(AplicacionSanitaria.costo), 0)).where(
                AplicacionSanitaria.lote_id == lote.id
            )
        )
        or 0
    )

    aves_vivas = lote.aves_actuales + lote.aves_descarte
    costo_aves = float(dec(lote.costo_ave) * lote.aves_iniciales)
    costo_total = costo_aves + float(alimento_costo or 0) + costo_sanidad
    peso_total_estimado = float(pesaje.peso_promedio_kg) * aves_vivas if pesaje and aves_vivas else 0

    return BalanceLote(
        lote=salida,
        dias_en_granja=dias,
        alimento_kg=float(alimento_kg or 0),
        alimento_costo=float(alimento_costo or 0),
        alimento_por_ave_kg=round(float(alimento_kg or 0) / aves_vivas, 3) if aves_vivas else 0.0,
        huevos_total=int(huevos_total),
        huevos_comerciales=int(huevos_comerciales),
        huevos_por_dia=round(int(huevos_total) / dias, 1),
        porcentaje_postura=round(int(huevos_total) * 100 / (aves_vivas * dias), 2) if aves_vivas else 0.0,
        peso_promedio_kg=float(pesaje.peso_promedio_kg) if pesaje else None,
        peso_fecha=pesaje.fecha if pesaje else None,
        costo_aves=costo_aves,
        costo_sanidad=costo_sanidad,
        costo_total=costo_total,
        costo_por_ave=round(costo_total / lote.aves_iniciales, 2) if lote.aves_iniciales else 0.0,
        conversion_alimenticia=(
            round(float(alimento_kg or 0) / peso_total_estimado, 3) if peso_total_estimado else None
        ),
    )
