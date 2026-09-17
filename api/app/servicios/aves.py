"""Reglas de los lotes de aves: ocupacion del galpon, movimientos y produccion."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto
from app.core.errores import datos_invalidos, no_encontrado, sin_permiso
from app.esquemas.aves import MovimientoAvesCrear
from app.modelos.aves import Lote, MovimientoAves, StockHuevos, TipoHuevo
from app.modelos.organizacion import Galpon
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles

# Movimientos que sacan aves del galpon
SALEN_DEL_GALPON = ("muerte", "fuga", "robo", "venta", "consumo", "regalo")


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


def edad_dias(lote: Lote, hasta: date | None = None) -> int:
    referencia = hasta or (lote.fecha_cierre or date.today())
    return max(0, (referencia - lote.fecha_ingreso).days + lote.edad_dias_ingreso)


# --- Alcance ---
def lotes_visibles(db: Session, ctx: Contexto, solo_activos: bool = False, todas_las_fincas: bool = False):
    consulta = select(Lote)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Lote.cuenta_id == cuenta)
    if todas_las_fincas or ctx.finca_id is None:
        consulta = consulta.where(Lote.finca_id.in_(ids_fincas_visibles(db, ctx) or [0]))
    else:
        consulta = consulta.where(Lote.finca_id == ctx.finca_id)
    if solo_activos:
        consulta = consulta.where(Lote.estado == "activo")
    return db.scalars(consulta.order_by(Lote.estado, Lote.fecha_ingreso.desc())).all()


def lote_de(db: Session, ctx: Contexto, lote_id: int) -> Lote:
    lote = db.get(Lote, lote_id)
    if lote is None:
        raise no_encontrado("El lote no existe")
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None and lote.cuenta_id != cuenta:
        raise no_encontrado("El lote no existe")
    if lote.finca_id not in ids_fincas_visibles(db, ctx):
        raise sin_permiso("Ese lote es de otra finca")
    return lote


def galpon_de_finca(db: Session, ctx: Contexto, galpon_id: int, finca_id: int) -> Galpon:
    galpon = db.get(Galpon, galpon_id)
    if galpon is None or galpon.finca_id != finca_id:
        raise datos_invalidos("El galpon no existe en esta finca")
    return galpon


# --- Ocupacion del galpon ---
def mover_ocupacion(db: Session, galpon_id: int, delta: int) -> None:
    galpon = db.execute(select(Galpon).where(Galpon.id == galpon_id).with_for_update()).scalar_one_or_none()
    if galpon is None:
        raise datos_invalidos("El galpon no existe")

    nueva = galpon.aves_actuales + delta
    if nueva < 0:
        raise datos_invalidos(f"El galpon {galpon.nombre} no tiene esa cantidad de aves")
    if galpon.capacidad and nueva > galpon.capacidad:
        raise datos_invalidos(
            f"El galpon {galpon.nombre} solo tiene capacidad para {galpon.capacidad} aves "
            f"y quedarian {nueva}"
        )
    galpon.aves_actuales = nueva


# --- Lotes ---
def crear_lote(db: Session, ctx: Contexto, datos) -> Lote:
    if ctx.finca_id is None:
        raise datos_invalidos("Primero elige la finca en la que vas a trabajar")

    galpon = galpon_de_finca(db, ctx, datos.galpon_id, ctx.finca_id)
    if not galpon.activo:
        raise datos_invalidos("Ese galpon esta inactivo")

    repetido = db.scalars(
        select(Lote.id).where(Lote.finca_id == ctx.finca_id, Lote.codigo == datos.codigo)
    ).first()
    if repetido:
        raise datos_invalidos(f"Ya existe un lote con el codigo {datos.codigo} en esta finca")

    lote = Lote(
        cuenta_id=ctx.cuenta_activa_id or ctx.cuenta_id,
        finca_id=ctx.finca_id,
        galpon_id=galpon.id,
        raza_id=datos.raza_id,
        codigo=datos.codigo,
        proposito=datos.proposito,
        fecha_ingreso=datos.fecha_ingreso,
        edad_dias_ingreso=datos.edad_dias_ingreso,
        aves_iniciales=datos.aves_iniciales,
        aves_actuales=datos.aves_iniciales,
        aves_descarte=0,
        costo_ave=dec(datos.costo_ave),
        observaciones=datos.observaciones,
    )
    db.add(lote)
    db.flush()

    mover_ocupacion(db, galpon.id, datos.aves_iniciales)
    db.add(
        MovimientoAves(
            lote_id=lote.id,
            fecha=datos.fecha_ingreso,
            tipo="ingreso",
            cantidad=datos.aves_iniciales,
            motivo="ingreso del lote",
            usuario_id=ctx.usuario.id,
            usuario_nombre=ctx.usuario.nombre_completo,
            creado_en=ahora(),
        )
    )
    registrar(
        db, ctx, "crear", "lotes", lote.id,
        f"Ingreso el lote {lote.codigo} con {lote.aves_iniciales} aves",
        {"galpon": galpon.nombre, "aves": lote.aves_iniciales},
    )
    return lote


def cerrar_lote(db: Session, ctx: Contexto, lote: Lote, fecha: date, observaciones: str | None) -> None:
    if lote.estado == "cerrado":
        raise datos_invalidos("Ese lote ya esta cerrado")
    if lote.aves_actuales > 0 or lote.aves_descarte > 0:
        raise datos_invalidos(
            f"Todavia quedan {lote.aves_actuales + lote.aves_descarte} aves. "
            "Registra su salida (venta, descarte o mortalidad) antes de cerrar el lote."
        )
    lote.estado = "cerrado"
    lote.fecha_cierre = fecha
    if observaciones:
        lote.observaciones = observaciones
    registrar(db, ctx, "cerrar", "lotes", lote.id, f"Cerro el lote {lote.codigo}")


# --- Movimientos de aves ---
def _aplicar(db: Session, lote: Lote, tipo: str, cantidad: int, desde_descarte: bool, galpon_destino: int | None):
    if tipo == "ingreso":
        lote.aves_actuales += cantidad
        mover_ocupacion(db, lote.galpon_id, cantidad)

    elif tipo == "descarte":
        if lote.aves_actuales < cantidad:
            raise datos_invalidos(f"El lote solo tiene {lote.aves_actuales} aves en produccion")
        lote.aves_actuales -= cantidad
        lote.aves_descarte += cantidad  # siguen en el galpon hasta venderse

    elif tipo == "traslado":
        if galpon_destino is None:
            raise datos_invalidos("Indica el galpon al que se traslada el lote")
        total = lote.aves_actuales + lote.aves_descarte
        if cantidad != total:
            raise datos_invalidos(f"El traslado mueve el lote completo: son {total} aves")
        mover_ocupacion(db, lote.galpon_id, -total)
        mover_ocupacion(db, galpon_destino, total)
        lote.galpon_id = galpon_destino

    elif tipo in SALEN_DEL_GALPON:
        if desde_descarte:
            if lote.aves_descarte < cantidad:
                raise datos_invalidos(f"Solo hay {lote.aves_descarte} aves de descarte en el lote")
            lote.aves_descarte -= cantidad
        else:
            if lote.aves_actuales < cantidad:
                raise datos_invalidos(f"El lote solo tiene {lote.aves_actuales} aves")
            lote.aves_actuales -= cantidad
        mover_ocupacion(db, lote.galpon_id, -cantidad)

    else:  # pragma: no cover
        raise datos_invalidos("Tipo de movimiento desconocido")


def crear_movimiento_aves(db: Session, ctx: Contexto, datos: MovimientoAvesCrear) -> MovimientoAves:
    lote = lote_de(db, ctx, datos.lote_id)
    if lote.estado == "cerrado":
        raise datos_invalidos("El lote esta cerrado")

    desde_descarte = datos.tipo == "venta" and lote.aves_descarte >= datos.cantidad
    galpon_destino = None
    if datos.tipo == "traslado":
        galpon_destino = galpon_de_finca(db, ctx, datos.galpon_destino_id or 0, lote.finca_id).id

    _aplicar(db, lote, datos.tipo, datos.cantidad, desde_descarte, galpon_destino)

    movimiento = MovimientoAves(
        lote_id=lote.id,
        fecha=datos.fecha,
        tipo=datos.tipo,
        cantidad=datos.cantidad,
        galpon_destino_id=galpon_destino,
        peso_kg=dec(datos.peso_kg) if datos.peso_kg is not None else None,
        motivo=datos.motivo,
        observaciones=datos.observaciones,
        desde_descarte=desde_descarte,
        usuario_id=ctx.usuario.id,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(movimiento)
    db.flush()

    registrar(
        db, ctx, "crear", "movimientos_aves", movimiento.id,
        f"{datos.tipo.capitalize()} de {datos.cantidad} aves en el lote {lote.codigo}",
        {"tipo": datos.tipo, "cantidad": datos.cantidad, "motivo": datos.motivo},
    )
    return movimiento


def anular_movimiento_aves(db: Session, ctx: Contexto, movimiento: MovimientoAves, motivo: str) -> None:
    if movimiento.anulado:
        raise datos_invalidos("Ese movimiento ya estaba anulado")

    lote = db.get(Lote, movimiento.lote_id)
    if lote is None:
        raise no_encontrado("El lote no existe")

    cantidad = movimiento.cantidad
    tipo = movimiento.tipo

    if tipo == "ingreso":
        if lote.aves_actuales < cantidad:
            raise datos_invalidos("Ya no estan esas aves en el lote, no se puede anular el ingreso")
        lote.aves_actuales -= cantidad
        mover_ocupacion(db, lote.galpon_id, -cantidad)

    elif tipo == "descarte":
        if lote.aves_descarte < cantidad:
            raise datos_invalidos("Esas aves de descarte ya salieron del lote")
        lote.aves_descarte -= cantidad
        lote.aves_actuales += cantidad

    elif tipo == "traslado":
        raise datos_invalidos("Para deshacer un traslado, registra otro traslado al galpon anterior")

    else:
        if movimiento.desde_descarte:
            lote.aves_descarte += cantidad
        else:
            lote.aves_actuales += cantidad
        mover_ocupacion(db, lote.galpon_id, cantidad)

    movimiento.anulado = True
    movimiento.anulado_en = ahora()
    movimiento.anulado_por = ctx.usuario.nombre_completo
    movimiento.motivo_anulacion = motivo
    registrar(
        db, ctx, "anular", "movimientos_aves", movimiento.id,
        f"Anulo un movimiento de {movimiento.tipo} del lote {lote.codigo}", {"motivo": motivo},
    )


# --- Stock de huevos ---
def mover_stock_huevos(db: Session, finca_id: int, tipo_huevo_id: int, delta: int) -> None:
    fila = db.execute(
        select(StockHuevos)
        .where(StockHuevos.finca_id == finca_id, StockHuevos.tipo_huevo_id == tipo_huevo_id)
        .with_for_update()
    ).scalar_one_or_none()

    if fila is None:
        fila = StockHuevos(finca_id=finca_id, tipo_huevo_id=tipo_huevo_id, cantidad=0)
        db.add(fila)
        db.flush()

    if fila.cantidad + delta < 0:
        raise datos_invalidos("No hay esa cantidad de huevos disponibles")
    fila.cantidad += delta
    fila.actualizado_en = ahora()


def tipos_huevo_de(db: Session, ctx: Contexto) -> list[TipoHuevo]:
    cuenta = cuenta_filtro(ctx)
    return db.scalars(
        select(TipoHuevo)
        .where((TipoHuevo.cuenta_id.is_(None)) | (TipoHuevo.cuenta_id == cuenta))
        .order_by(TipoHuevo.orden, TipoHuevo.nombre)
    ).all()
