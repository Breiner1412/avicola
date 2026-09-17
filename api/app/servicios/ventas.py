"""Reglas de la caja y de las ventas."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto
from app.core.errores import datos_invalidos, no_encontrado, sin_permiso
from app.esquemas.ventas import VentaCrear
from app.modelos.aves import Lote, MovimientoAves
from app.modelos.organizacion import Cuenta
from app.modelos.ventas import (
    MetodoPago,
    Precio,
    ProductoVenta,
    PuntoVenta,
    TurnoCaja,
    UsuarioPuntoVenta,
    Venta,
    VentaDetalle,
    VentaPago,
)
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles
from app.servicios.aves import mover_ocupacion, mover_stock_huevos

CERO = Decimal("0")
CENTAVO = Decimal("0.01")
# Roles que no pueden pasarse del tope de descuento de la cuenta
CON_TOPE = ("cajero", "operario", "supervisor")


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


def pesos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO)


# --- Puntos de venta ---
def puntos_visibles(db: Session, ctx: Contexto, incluir_inactivos: bool = False):
    consulta = select(PuntoVenta)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(PuntoVenta.cuenta_id == cuenta)
    if not incluir_inactivos:
        consulta = consulta.where(PuntoVenta.activo.is_(True))

    if ctx.finca_id is not None:
        consulta = consulta.where((PuntoVenta.finca_id.is_(None)) | (PuntoVenta.finca_id == ctx.finca_id))
    else:
        visibles = ids_fincas_visibles(db, ctx) or [0]
        consulta = consulta.where((PuntoVenta.finca_id.is_(None)) | (PuntoVenta.finca_id.in_(visibles)))

    puntos = db.scalars(consulta.order_by(PuntoVenta.nombre)).all()

    # Si al cajero le asignaron puntos, solo esos
    asignados = set(
        db.scalars(
            select(UsuarioPuntoVenta.punto_venta_id).where(UsuarioPuntoVenta.usuario_id == ctx.usuario.id)
        ).all()
    )
    if asignados:
        puntos = [p for p in puntos if p.id in asignados]
    return puntos


def punto_de(db: Session, ctx: Contexto, punto_id: int) -> PuntoVenta:
    punto = db.get(PuntoVenta, punto_id)
    cuenta = cuenta_filtro(ctx)
    if punto is None or (cuenta is not None and punto.cuenta_id != cuenta):
        raise no_encontrado("El punto de venta no existe")
    if punto.finca_id is not None and punto.finca_id not in ids_fincas_visibles(db, ctx):
        raise sin_permiso("Ese punto de venta es de otra finca")
    return punto


# --- Precios ---
def precio_vigente(db: Session, producto_id: int, punto_venta_id: int | None) -> Decimal | None:
    consulta = (
        select(Precio)
        .where(Precio.producto_id == producto_id, Precio.hasta.is_(None))
        .order_by(Precio.punto_venta_id.is_(None), Precio.id.desc())
    )
    if punto_venta_id is not None:
        consulta = consulta.where((Precio.punto_venta_id.is_(None)) | (Precio.punto_venta_id == punto_venta_id))
    else:
        consulta = consulta.where(Precio.punto_venta_id.is_(None))

    fila = db.scalars(consulta).first()
    return dec(fila.precio) if fila else None


def guardar_precio(
    db: Session, ctx: Contexto, producto_id: int, precio: float, punto_venta_id: int | None, desde: date | None
) -> Precio:
    hoy = desde or date.today()

    anteriores = db.scalars(
        select(Precio).where(
            Precio.producto_id == producto_id,
            Precio.hasta.is_(None),
            (Precio.punto_venta_id == punto_venta_id)
            if punto_venta_id is not None
            else Precio.punto_venta_id.is_(None),
        )
    ).all()
    for anterior in anteriores:
        anterior.hasta = hoy

    nuevo = Precio(
        producto_id=producto_id,
        punto_venta_id=punto_venta_id,
        precio=dec(precio),
        desde=hoy,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(nuevo)
    db.flush()
    registrar(db, ctx, "editar", "precios", nuevo.id, f"Precio nuevo: {precio}", {"producto": producto_id})
    return nuevo


# --- Turnos de caja ---
def turno_abierto(db: Session, ctx: Contexto, punto_venta_id: int | None = None) -> TurnoCaja | None:
    consulta = select(TurnoCaja).where(TurnoCaja.usuario_id == ctx.usuario.id, TurnoCaja.estado == "abierto")
    if punto_venta_id is not None:
        consulta = consulta.where(TurnoCaja.punto_venta_id == punto_venta_id)
    return db.scalars(consulta.order_by(TurnoCaja.id.desc())).first()


def totales_turno(db: Session, turno: TurnoCaja) -> dict:
    ventas, total = db.execute(
        select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0)).where(
            Venta.turno_id == turno.id, Venta.estado == "activa"
        )
    ).one()

    efectivo = db.scalar(
        select(func.coalesce(func.sum(VentaPago.monto), 0))
        .join(Venta, VentaPago.venta_id == Venta.id)
        .where(Venta.turno_id == turno.id, Venta.estado == "activa", VentaPago.es_efectivo.is_(True))
    ) or 0

    return {
        "ventas": int(ventas or 0),
        "total_vendido": float(total or 0),
        "total_efectivo": float(efectivo or 0),
        "esperado_en_caja": float(dec(turno.base_inicial) + dec(efectivo)),
    }


def abrir_turno(db: Session, ctx: Contexto, punto: PuntoVenta, base: float, observaciones: str | None) -> TurnoCaja:
    if turno_abierto(db, ctx) is not None:
        raise datos_invalidos("Ya tienes un turno abierto. Cierralo antes de abrir otro.")

    turno = TurnoCaja(
        cuenta_id=punto.cuenta_id,
        punto_venta_id=punto.id,
        usuario_id=ctx.usuario.id,
        usuario_nombre=ctx.usuario.nombre_completo,
        estado="abierto",
        base_inicial=dec(base),
        abierto_en=ahora(),
        observaciones=observaciones,
    )
    db.add(turno)
    db.flush()
    registrar(db, ctx, "abrir", "turnos_caja", turno.id, f"Abrio la caja en {punto.nombre} con base {base}")
    return turno


def cerrar_turno(db: Session, ctx: Contexto, turno: TurnoCaja, contado: float, observaciones: str | None) -> dict:
    if turno.estado == "cerrado":
        raise datos_invalidos("Ese turno ya esta cerrado")

    totales = totales_turno(db, turno)
    turno.estado = "cerrado"
    turno.cerrado_en = ahora()
    turno.efectivo_contado = dec(contado)
    turno.diferencia = dec(contado) - dec(totales["esperado_en_caja"])
    if observaciones:
        turno.observaciones = observaciones

    registrar(
        db, ctx, "cerrar", "turnos_caja", turno.id,
        f"Cerro la caja: esperado {totales['esperado_en_caja']}, contado {contado}",
        {"diferencia": float(turno.diferencia)},
    )
    return totales


# --- Ventas ---
def siguiente_numero(db: Session, punto_id: int) -> tuple[str, PuntoVenta]:
    punto = db.execute(select(PuntoVenta).where(PuntoVenta.id == punto_id).with_for_update()).scalar_one()
    punto.consecutivo += 1
    prefijo = punto.prefijo or punto.codigo
    return f"{prefijo}-{punto.consecutivo:06d}", punto


def _descontar_item(db: Session, ctx: Contexto, venta: Venta, producto: ProductoVenta, item, cantidad: Decimal):
    """Saca del inventario lo que se vendio y devuelve (unidades, peso, lote, movimiento)."""
    unidades = 0
    peso = None
    lote_id = None
    movimiento_id = None

    if producto.clase == "huevo":
        if producto.tipo_huevo_id is None:
            raise datos_invalidos(f"El producto {producto.nombre} no tiene tipo de huevo configurado")
        if venta.finca_id is None:
            raise datos_invalidos("Para vender huevos, el punto de venta debe estar en una finca")
        unidades = int(cantidad * producto.factor)
        mover_stock_huevos(db, venta.finca_id, producto.tipo_huevo_id, -unidades)

    elif producto.clase in ("ave_descarte", "ave_engorde"):
        if item.lote_id is None:
            raise datos_invalidos(f"Indica de que lote salen las aves de {producto.nombre}")

        lote = db.get(Lote, item.lote_id)
        if lote is None or lote.cuenta_id != venta.cuenta_id:
            raise no_encontrado("El lote no existe")

        aves = int(item.aves if item.aves is not None else cantidad)
        if aves <= 0:
            raise datos_invalidos("Indica cuantas aves se venden")

        if producto.clase == "ave_descarte":
            if lote.aves_descarte < aves:
                raise datos_invalidos(f"El lote {lote.codigo} solo tiene {lote.aves_descarte} aves de descarte")
            lote.aves_descarte -= aves
            desde_descarte = True
        else:
            if lote.aves_actuales < aves:
                raise datos_invalidos(f"El lote {lote.codigo} solo tiene {lote.aves_actuales} aves")
            lote.aves_actuales -= aves
            desde_descarte = False

        mover_ocupacion(db, lote.galpon_id, -aves)
        peso = cantidad if producto.cobro_por == "kg" else None

        movimiento = MovimientoAves(
            lote_id=lote.id,
            fecha=venta.fecha,
            tipo="venta",
            cantidad=aves,
            peso_kg=peso,
            motivo=f"venta {venta.numero}",
            desde_descarte=desde_descarte,
            usuario_id=ctx.usuario.id,
            usuario_nombre=ctx.usuario.nombre_completo,
            creado_en=ahora(),
        )
        db.add(movimiento)
        db.flush()
        movimiento_id = movimiento.id
        lote_id = lote.id
        unidades = aves

    return unidades, peso, lote_id, movimiento_id


def crear_venta(db: Session, ctx: Contexto, punto: PuntoVenta, turno: TurnoCaja, datos: VentaCrear) -> Venta:
    numero, punto = siguiente_numero(db, punto.id)

    venta = Venta(
        cuenta_id=punto.cuenta_id,
        finca_id=punto.finca_id or ctx.finca_id,
        punto_venta_id=punto.id,
        turno_id=turno.id,
        numero=numero,
        fecha=date.today(),
        estado="activa",
        observaciones=datos.observaciones,
        usuario_id=ctx.usuario.id,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(venta)
    db.flush()

    subtotal = CERO
    for item in datos.items:
        producto = db.get(ProductoVenta, item.producto_id)
        if producto is None or producto.cuenta_id != punto.cuenta_id or not producto.activo:
            raise datos_invalidos("Ese producto no esta disponible")

        cantidad = dec(item.cantidad)
        precio = dec(item.precio_unitario) if item.precio_unitario is not None else precio_vigente(db, producto.id, punto.id)
        if precio is None:
            raise datos_invalidos(f"El producto {producto.nombre} no tiene precio")

        unidades, peso, lote_id, movimiento_id = _descontar_item(db, ctx, venta, producto, item, cantidad)
        linea = pesos(cantidad * precio)
        subtotal += linea

        db.add(
            VentaDetalle(
                venta_id=venta.id,
                producto_id=producto.id,
                descripcion=producto.nombre,
                clase=producto.clase,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=linea,
                unidades=unidades,
                peso_kg=peso,
                tipo_huevo_id=producto.tipo_huevo_id,
                lote_id=lote_id,
                movimiento_aves_id=movimiento_id,
            )
        )

    descuento = dec(datos.descuento)
    if descuento > subtotal:
        raise datos_invalidos("El descuento no puede ser mayor que la venta")

    cuenta = db.get(Cuenta, punto.cuenta_id)
    tope = int(cuenta.descuento_maximo or 0) if cuenta else 0
    if ctx.rol in CON_TOPE and descuento > CERO:
        maximo = pesos(subtotal * dec(tope) / dec(100))
        if descuento > maximo:
            raise datos_invalidos(f"El descuento maximo que puedes dar es {tope}% ({maximo})")

    venta.subtotal = pesos(subtotal)
    venta.descuento = pesos(descuento)
    venta.total = pesos(subtotal - descuento)

    # Pagos: si no los indican, se asume efectivo
    pagos = datos.pagos
    if not pagos:
        efectivo = db.scalars(
            select(MetodoPago)
            .where(
                (MetodoPago.cuenta_id.is_(None)) | (MetodoPago.cuenta_id == punto.cuenta_id),
                MetodoPago.es_efectivo.is_(True),
                MetodoPago.activo.is_(True),
            )
            .order_by(MetodoPago.id)
        ).first()
        if efectivo is None:
            raise datos_invalidos("No hay forma de pago configurada")
        db.add(
            VentaPago(
                venta_id=venta.id,
                metodo_pago_id=efectivo.id,
                metodo_nombre=efectivo.nombre,
                es_efectivo=True,
                monto=venta.total,
            )
        )
    else:
        suma = CERO
        for pago in pagos:
            metodo = db.get(MetodoPago, pago.metodo_pago_id)
            if metodo is None or (metodo.cuenta_id is not None and metodo.cuenta_id != punto.cuenta_id):
                raise datos_invalidos("Forma de pago no valida")
            suma += dec(pago.monto)
            db.add(
                VentaPago(
                    venta_id=venta.id,
                    metodo_pago_id=metodo.id,
                    metodo_nombre=metodo.nombre,
                    es_efectivo=metodo.es_efectivo,
                    monto=dec(pago.monto),
                    referencia=pago.referencia,
                )
            )
        if pesos(suma) != venta.total:
            raise datos_invalidos(f"Los pagos suman {pesos(suma)} y la venta es de {venta.total}")

    registrar(
        db, ctx, "crear", "ventas", venta.id,
        f"Venta {venta.numero} por {venta.total}",
        {"punto": punto.nombre, "items": len(datos.items), "descuento": float(venta.descuento)},
    )
    return venta


def anular_venta(db: Session, ctx: Contexto, venta: Venta, motivo: str) -> None:
    if venta.estado == "anulada":
        raise datos_invalidos("Esa venta ya esta anulada")

    # El cajero solo anula lo de su turno abierto
    if ctx.rol == "cajero":
        turno = turno_abierto(db, ctx)
        if turno is None or venta.turno_id != turno.id:
            raise sin_permiso("Solo puedes anular ventas de tu turno abierto")

    for detalle in venta.detalles:
        if detalle.clase == "huevo" and detalle.tipo_huevo_id and venta.finca_id:
            mover_stock_huevos(db, venta.finca_id, detalle.tipo_huevo_id, detalle.unidades)

        elif detalle.clase in ("ave_descarte", "ave_engorde") and detalle.lote_id:
            lote = db.get(Lote, detalle.lote_id)
            movimiento = (
                db.get(MovimientoAves, detalle.movimiento_aves_id) if detalle.movimiento_aves_id else None
            )
            if lote is None:
                continue
            if detalle.clase == "ave_descarte":
                lote.aves_descarte += detalle.unidades
            else:
                lote.aves_actuales += detalle.unidades
            mover_ocupacion(db, lote.galpon_id, detalle.unidades)

            if movimiento is not None and not movimiento.anulado:
                movimiento.anulado = True
                movimiento.anulado_en = ahora()
                movimiento.anulado_por = ctx.usuario.nombre_completo
                movimiento.motivo_anulacion = f"Venta {venta.numero} anulada"

    venta.estado = "anulada"
    venta.anulada_en = ahora()
    venta.anulada_por = ctx.usuario.nombre_completo
    venta.motivo_anulacion = motivo

    registrar(
        db, ctx, "anular", "ventas", venta.id,
        f"Anulo la venta {venta.numero} por {venta.total}", {"motivo": motivo},
    )
