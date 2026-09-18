"""Tareas del dia, rutinas que se repiten y novedades de la finca."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import datos_invalidos, no_encontrado, sin_permiso
from app.esquemas.comunes import Mensaje
from app.esquemas.trabajo import (
    CerrarNovedad,
    GenerarTareas,
    NovedadActualizar,
    NovedadCrear,
    NovedadSalida,
    RutinaActualizar,
    RutinaCrear,
    RutinaSalida,
    TareaActualizar,
    TareaCrear,
    TareaSalida,
)
from app.modelos.acceso import Usuario
from app.modelos.aves import Lote, MovimientoAves
from app.modelos.organizacion import Galpon
from app.modelos.trabajo import Novedad, Rutina, Tarea
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles
from app.servicios.aves import mover_ocupacion

router = APIRouter(tags=["Tareas y novedades"])

# Roles que solo manejan sus propias tareas
SOLO_LO_SUYO = ("operario", "cajero")


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fincas(db: Session, ctx: Contexto) -> list[int]:
    if ctx.finca_id is not None:
        return [ctx.finca_id]
    return ids_fincas_visibles(db, ctx) or [0]


def _tarea_salida(tarea: Tarea) -> TareaSalida:
    return TareaSalida(
        id=tarea.id,
        finca_id=tarea.finca_id,
        titulo=tarea.titulo,
        descripcion=tarea.descripcion,
        prioridad=tarea.prioridad,
        estado=tarea.estado,
        fecha=tarea.fecha,
        hora=tarea.hora,
        asignado_a=tarea.asignado_a,
        asignado_nombre=tarea.asignado_nombre,
        galpon_id=tarea.galpon_id,
        lote_id=tarea.lote_id,
        rutina_id=tarea.rutina_id,
        creado_por=tarea.creado_por,
        terminada_en=tarea.terminada_en,
        terminada_por=tarea.terminada_por,
        notas=tarea.notas,
        creado_en=tarea.creado_en,
    )


def _usuario_de_la_cuenta(db: Session, ctx: Contexto, usuario_id: int | None) -> Usuario | None:
    if usuario_id is None:
        return None
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or (ctx.cuenta_activa_id and usuario.cuenta_id != ctx.cuenta_activa_id):
        raise datos_invalidos("Ese usuario no es de la cuenta")
    return usuario


def _tarea_de(db: Session, ctx: Contexto, tarea_id: int) -> Tarea:
    tarea = db.get(Tarea, tarea_id)
    if tarea is None or tarea.finca_id not in ids_fincas_visibles(db, ctx):
        raise no_encontrado("La tarea no existe")
    return tarea


# ------------------------------- Tareas -------------------------------
@router.get("/tareas", response_model=list[TareaSalida], summary="Tareas de la finca")
def listar_tareas(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    estado: str | None = Query(None),
    solo_mias: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "ver")),
):
    consulta = select(Tarea).where(Tarea.finca_id.in_(_fincas(db, ctx)))
    if desde:
        consulta = consulta.where(Tarea.fecha >= desde)
    if hasta:
        consulta = consulta.where(Tarea.fecha <= hasta)
    if estado:
        consulta = consulta.where(Tarea.estado == estado)
    if solo_mias or ctx.rol in SOLO_LO_SUYO:
        consulta = consulta.where(Tarea.asignado_a == ctx.usuario.id)

    filas = db.scalars(
        consulta.order_by(Tarea.fecha.desc(), Tarea.prioridad.desc(), Tarea.id.desc()).limit(500)
    ).unique().all()
    return [_tarea_salida(t) for t in filas]


@router.post("/tareas", response_model=TareaSalida, status_code=201, summary="Crear una tarea")
def crear_tarea(
    datos: TareaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "crear", con_finca=True)),
):
    asignado = _usuario_de_la_cuenta(db, ctx, datos.asignado_a)
    if datos.galpon_id and db.get(Galpon, datos.galpon_id) is None:
        raise datos_invalidos("El galpon no existe")
    if datos.lote_id and db.get(Lote, datos.lote_id) is None:
        raise datos_invalidos("El lote no existe")

    tarea = Tarea(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        prioridad=datos.prioridad,
        fecha=datos.fecha,
        hora=datos.hora,
        asignado_a=asignado.id if asignado else None,
        asignado_nombre=asignado.nombre_completo if asignado else None,
        galpon_id=datos.galpon_id,
        lote_id=datos.lote_id,
        creado_por=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(tarea)
    db.flush()
    registrar(db, ctx, "crear", "tareas", tarea.id, f"Creo la tarea {tarea.titulo}")
    db.commit()
    db.refresh(tarea)
    return _tarea_salida(tarea)


@router.patch("/tareas/{tarea_id}", response_model=TareaSalida, summary="Editar o mover una tarea")
def editar_tarea(
    tarea_id: int,
    datos: TareaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "editar")),
):
    tarea = _tarea_de(db, ctx, tarea_id)
    cambios = datos.model_dump(exclude_unset=True)

    # El operario y el cajero solo tocan sus tareas, y solo el estado y las notas
    if ctx.rol in SOLO_LO_SUYO:
        if tarea.asignado_a != ctx.usuario.id:
            raise sin_permiso("Esa tarea no es tuya")
        permitidos = {"estado", "notas"}
        if set(cambios) - permitidos:
            raise sin_permiso("Solo puedes cambiar el estado de tus tareas")

    if "asignado_a" in cambios:
        asignado = _usuario_de_la_cuenta(db, ctx, cambios["asignado_a"])
        tarea.asignado_a = asignado.id if asignado else None
        tarea.asignado_nombre = asignado.nombre_completo if asignado else None
        cambios.pop("asignado_a")

    if cambios.get("estado") == "hecha" and tarea.estado != "hecha":
        tarea.terminada_en = ahora()
        tarea.terminada_por = ctx.usuario.nombre_completo
    if cambios.get("estado") in ("pendiente", "en_proceso"):
        tarea.terminada_en = None
        tarea.terminada_por = None

    for campo, valor in cambios.items():
        setattr(tarea, campo, valor)

    registrar(db, ctx, "editar", "tareas", tarea.id, f"Actualizo la tarea {tarea.titulo}", cambios)
    db.commit()
    db.refresh(tarea)
    return _tarea_salida(tarea)


@router.delete("/tareas/{tarea_id}", response_model=Mensaje, summary="Borrar una tarea")
def borrar_tarea(
    tarea_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "borrar")),
):
    tarea = _tarea_de(db, ctx, tarea_id)
    registrar(db, ctx, "borrar", "tareas", tarea.id, f"Borro la tarea {tarea.titulo}")
    db.delete(tarea)
    db.commit()
    return Mensaje(mensaje="Tarea borrada")


# ------------------------------- Rutinas -------------------------------
def _rutina_salida(rutina: Rutina) -> RutinaSalida:
    return RutinaSalida(
        id=rutina.id,
        finca_id=rutina.finca_id,
        titulo=rutina.titulo,
        descripcion=rutina.descripcion,
        frecuencia=rutina.frecuencia,
        dias_semana=rutina.dias_semana or [],
        dia_mes=rutina.dia_mes,
        hora=rutina.hora,
        prioridad=rutina.prioridad,
        asignado_a=rutina.asignado_a,
        galpon_id=rutina.galpon_id,
        activo=rutina.activo,
        ultima_generacion=rutina.ultima_generacion,
    )


@router.get("/rutinas", response_model=list[RutinaSalida], summary="Tareas que se repiten")
def listar_rutinas(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("tareas", "ver"))):
    filas = db.scalars(select(Rutina).where(Rutina.finca_id.in_(_fincas(db, ctx))).order_by(Rutina.titulo)).all()
    return [_rutina_salida(r) for r in filas]


@router.post("/rutinas", response_model=RutinaSalida, status_code=201, summary="Crear una rutina")
def crear_rutina(
    datos: RutinaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "crear", con_finca=True)),
):
    if datos.frecuencia == "semanal" and not datos.dias_semana:
        raise datos_invalidos("Indica en que dias de la semana se hace")
    if datos.frecuencia == "mensual" and not datos.dia_mes:
        raise datos_invalidos("Indica que dia del mes se hace")

    asignado = _usuario_de_la_cuenta(db, ctx, datos.asignado_a)
    rutina = Rutina(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        frecuencia=datos.frecuencia,
        dias_semana=datos.dias_semana,
        dia_mes=datos.dia_mes,
        hora=datos.hora,
        prioridad=datos.prioridad,
        asignado_a=asignado.id if asignado else None,
        galpon_id=datos.galpon_id,
        creado_en=ahora(),
    )
    db.add(rutina)
    db.flush()
    registrar(db, ctx, "crear", "rutinas", rutina.id, f"Creo la rutina {rutina.titulo}")
    db.commit()
    db.refresh(rutina)
    return _rutina_salida(rutina)


@router.patch("/rutinas/{rutina_id}", response_model=RutinaSalida, summary="Editar una rutina")
def editar_rutina(
    rutina_id: int,
    datos: RutinaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "editar")),
):
    rutina = db.get(Rutina, rutina_id)
    if rutina is None or rutina.finca_id not in ids_fincas_visibles(db, ctx):
        raise no_encontrado("La rutina no existe")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(rutina, campo, valor)
    registrar(db, ctx, "editar", "rutinas", rutina.id, f"Edito la rutina {rutina.titulo}", cambios)
    db.commit()
    db.refresh(rutina)
    return _rutina_salida(rutina)


def _toca_hoy(rutina: Rutina, dia: date) -> bool:
    if rutina.frecuencia == "diaria":
        return True
    if rutina.frecuencia == "semanal":
        return dia.weekday() in (rutina.dias_semana or [])
    return dia.day == (rutina.dia_mes or 0)


@router.post("/rutinas/generar", summary="Crear las tareas de las rutinas del dia")
def generar(
    datos: GenerarTareas,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("tareas", "crear", con_finca=True)),
):
    dia = datos.fecha or date.today()
    rutinas = db.scalars(
        select(Rutina).where(Rutina.finca_id == ctx.finca_id, Rutina.activo.is_(True))
    ).all()

    creadas = 0
    for rutina in rutinas:
        if not _toca_hoy(rutina, dia):
            continue
        existe = db.scalars(
            select(Tarea.id).where(Tarea.rutina_id == rutina.id, Tarea.fecha == dia)
        ).first()
        if existe:
            continue

        asignado = db.get(Usuario, rutina.asignado_a) if rutina.asignado_a else None
        db.add(
            Tarea(
                cuenta_id=rutina.cuenta_id,
                finca_id=rutina.finca_id,
                titulo=rutina.titulo,
                descripcion=rutina.descripcion,
                prioridad=rutina.prioridad,
                fecha=dia,
                hora=rutina.hora,
                asignado_a=asignado.id if asignado else None,
                asignado_nombre=asignado.nombre_completo if asignado else None,
                galpon_id=rutina.galpon_id,
                rutina_id=rutina.id,
                creado_por="Rutina",
                creado_en=ahora(),
            )
        )
        rutina.ultima_generacion = dia
        creadas += 1

    if creadas:
        registrar(db, ctx, "crear", "tareas", None, f"Genero {creadas} tarea(s) de rutina para el {dia}")
    db.commit()
    return {"fecha": dia, "creadas": creadas}


# ------------------------------ Novedades ------------------------------
def _novedad_salida(novedad: Novedad) -> NovedadSalida:
    return NovedadSalida(
        id=novedad.id,
        finca_id=novedad.finca_id,
        fecha=novedad.fecha,
        categoria=novedad.categoria,
        subtipo=novedad.subtipo,
        titulo=novedad.titulo,
        descripcion=novedad.descripcion,
        gravedad=novedad.gravedad,
        estado=novedad.estado,
        galpon_id=novedad.galpon_id,
        lote_id=novedad.lote_id,
        aves_afectadas=novedad.aves_afectadas,
        costo_estimado=float(novedad.costo_estimado or 0),
        acciones=novedad.acciones,
        reportado_por=novedad.reportado_por,
        cerrada_en=novedad.cerrada_en,
        cerrada_por=novedad.cerrada_por,
        creado_en=novedad.creado_en,
    )


@router.get("/novedades", response_model=list[NovedadSalida], summary="Novedades e incidentes")
def listar_novedades(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria: str | None = Query(None),
    estado: str | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("novedades", "ver")),
):
    consulta = select(Novedad).where(Novedad.finca_id.in_(_fincas(db, ctx)))
    if desde:
        consulta = consulta.where(Novedad.fecha >= desde)
    if hasta:
        consulta = consulta.where(Novedad.fecha <= hasta)
    if categoria:
        consulta = consulta.where(Novedad.categoria == categoria)
    if estado:
        consulta = consulta.where(Novedad.estado == estado)

    filas = db.scalars(consulta.order_by(Novedad.fecha.desc(), Novedad.id.desc()).limit(500)).all()
    return [_novedad_salida(n) for n in filas]


@router.post("/novedades", response_model=NovedadSalida, status_code=201, summary="Reportar una novedad")
def crear_novedad(
    datos: NovedadCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("novedades", "crear", con_finca=True)),
):
    lote = db.get(Lote, datos.lote_id) if datos.lote_id else None
    if datos.lote_id and (lote is None or lote.finca_id != ctx.finca_id):
        raise datos_invalidos("El lote no existe en esta finca")

    movimiento_id = None
    if datos.descontar_aves and datos.aves_afectadas:
        if lote is None:
            raise datos_invalidos("Para descontar aves indica de que lote son")
        if lote.aves_actuales < datos.aves_afectadas:
            raise datos_invalidos(f"El lote solo tiene {lote.aves_actuales} aves")

        lote.aves_actuales -= datos.aves_afectadas
        mover_ocupacion(db, lote.galpon_id, -datos.aves_afectadas)
        movimiento = MovimientoAves(
            lote_id=lote.id,
            fecha=datos.fecha,
            tipo="muerte",
            cantidad=datos.aves_afectadas,
            motivo=f"{datos.categoria}: {datos.titulo}"[:80],
            usuario_id=ctx.usuario.id,
            usuario_nombre=ctx.usuario.nombre_completo,
            creado_en=ahora(),
        )
        db.add(movimiento)
        db.flush()
        movimiento_id = movimiento.id

    novedad = Novedad(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        fecha=datos.fecha,
        categoria=datos.categoria,
        subtipo=datos.subtipo,
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        gravedad=datos.gravedad,
        galpon_id=datos.galpon_id or (lote.galpon_id if lote else None),
        lote_id=lote.id if lote else None,
        aves_afectadas=datos.aves_afectadas,
        movimiento_aves_id=movimiento_id,
        costo_estimado=datos.costo_estimado,
        acciones=datos.acciones,
        reportado_por=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(novedad)
    db.flush()
    registrar(
        db, ctx, "crear", "novedades", novedad.id,
        f"Reporto: {novedad.titulo}", {"categoria": novedad.categoria, "gravedad": novedad.gravedad},
    )
    db.commit()
    db.refresh(novedad)
    return _novedad_salida(novedad)


@router.patch("/novedades/{novedad_id}", response_model=NovedadSalida, summary="Editar una novedad")
def editar_novedad(
    novedad_id: int,
    datos: NovedadActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("novedades", "editar")),
):
    novedad = db.get(Novedad, novedad_id)
    if novedad is None or novedad.finca_id not in ids_fincas_visibles(db, ctx):
        raise no_encontrado("La novedad no existe")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(novedad, campo, valor)
    registrar(db, ctx, "editar", "novedades", novedad.id, f"Actualizo la novedad {novedad.titulo}", cambios)
    db.commit()
    db.refresh(novedad)
    return _novedad_salida(novedad)


@router.post("/novedades/{novedad_id}/cerrar", response_model=NovedadSalida, summary="Cerrar una novedad")
def cerrar_novedad(
    novedad_id: int,
    datos: CerrarNovedad,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("novedades", "editar")),
):
    novedad = db.get(Novedad, novedad_id)
    if novedad is None or novedad.finca_id not in ids_fincas_visibles(db, ctx):
        raise no_encontrado("La novedad no existe")
    if novedad.estado == "cerrada":
        raise datos_invalidos("Esa novedad ya esta cerrada")

    novedad.estado = "cerrada"
    novedad.cerrada_en = ahora()
    novedad.cerrada_por = ctx.usuario.nombre_completo
    if datos.acciones:
        novedad.acciones = datos.acciones

    registrar(db, ctx, "cerrar", "novedades", novedad.id, f"Cerro la novedad {novedad.titulo}")
    db.commit()
    db.refresh(novedad)
    return _novedad_salida(novedad)
