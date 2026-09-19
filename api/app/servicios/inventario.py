"""Reglas del inventario: existencias que nunca quedan negativas y movimientos que se anulan, no se borran."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto
from app.core.errores import datos_invalidos, no_encontrado, sin_permiso
from app.esquemas.inventario import MovimientoCrear
from app.modelos.inventario import (
    Articulo,
    Bodega,
    Existencia,
    MovimientoInventario,
    MovimientoItem,
)
from app.servicios.alcance import cuenta_filtro, ids_fincas_visibles

CERO = Decimal("0")


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dec(valor: float | Decimal | None) -> Decimal:
    return Decimal(str(valor or 0))


# --- Consultas con alcance ---
def bodegas_visibles(db: Session, ctx: Contexto, todas: bool = False, incluir_inactivas: bool = False):
    """Bodegas de la finca activa mas las centrales de la cuenta."""
    consulta = select(Bodega)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Bodega.cuenta_id == cuenta)
    if not incluir_inactivas:
        consulta = consulta.where(Bodega.activo.is_(True))

    if todas or ctx.finca_id is None:
        visibles = ids_fincas_visibles(db, ctx)
        consulta = consulta.where((Bodega.finca_id.is_(None)) | (Bodega.finca_id.in_(visibles or [0])))
    else:
        consulta = consulta.where((Bodega.finca_id.is_(None)) | (Bodega.finca_id == ctx.finca_id))

    return db.scalars(consulta.order_by(Bodega.finca_id.is_(None).desc(), Bodega.nombre)).all()


def bodega_de(db: Session, ctx: Contexto, bodega_id: int) -> Bodega:
    bodega = db.get(Bodega, bodega_id)
    if bodega is None:
        raise no_encontrado("La bodega no existe")
    if not ctx.es_plataforma and bodega.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("La bodega no existe")
    if bodega.finca_id is not None and bodega.finca_id not in ids_fincas_visibles(db, ctx):
        raise sin_permiso("Esa bodega es de otra finca")
    return bodega


def articulo_de(db: Session, ctx: Contexto, articulo_id: int) -> Articulo:
    articulo = db.get(Articulo, articulo_id)
    if articulo is None:
        raise no_encontrado("El articulo no existe")
    if not ctx.es_plataforma and articulo.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("El articulo no existe")
    return articulo


# --- Existencias ---
def existencia(db: Session, bodega_id: int, articulo_id: int) -> Existencia:
    """Trae (o crea) la existencia y la bloquea hasta terminar la operacion."""
    fila = db.execute(
        select(Existencia)
        .where(Existencia.bodega_id == bodega_id, Existencia.articulo_id == articulo_id)
        .with_for_update()
    ).scalar_one_or_none()

    if fila is None:
        fila = Existencia(bodega_id=bodega_id, articulo_id=articulo_id, cantidad=CERO, costo_promedio=CERO)
        db.add(fila)
        db.flush()
    return fila


def mover(db: Session, bodega_id: int, articulo: Articulo, delta: Decimal, costo: Decimal = CERO) -> None:
    """Suma o resta en una bodega. No deja la existencia por debajo de cero."""
    fila = existencia(db, bodega_id, articulo.id)
    nueva = dec(fila.cantidad) + delta

    if nueva < CERO:
        raise datos_invalidos(
            f"No hay suficiente {articulo.nombre}: hay {dec(fila.cantidad):f} {articulo.unidad} "
            f"y se necesitan {abs(delta):f}"
        )

    if delta > CERO and costo > CERO:
        # Costo promedio ponderado
        valor_actual = dec(fila.cantidad) * dec(fila.costo_promedio)
        fila.costo_promedio = ((valor_actual + delta * costo) / nueva).quantize(Decimal("0.01")) if nueva else costo
    fila.cantidad = nueva
    fila.actualizado_en = ahora()


# --- Movimientos ---
def _validar_cabecera(db: Session, ctx: Contexto, datos: MovimientoCrear) -> tuple[Bodega, Bodega | None]:
    origen = bodega_de(db, ctx, datos.bodega_id)
    destino = None

    if datos.tipo == "traslado":
        if datos.bodega_destino_id is None:
            raise datos_invalidos("Indica la bodega a la que se traslada")
        if datos.bodega_destino_id == datos.bodega_id:
            raise datos_invalidos("La bodega de origen y la de destino no pueden ser la misma")
        destino = bodega_de(db, ctx, datos.bodega_destino_id)
    elif datos.bodega_destino_id is not None:
        raise datos_invalidos("Solo los traslados llevan bodega de destino")

    if datos.tipo == "ajuste" and not datos.motivo:
        raise datos_invalidos("Explica el motivo del ajuste")

    return origen, destino


def crear_movimiento(db: Session, ctx: Contexto, datos: MovimientoCrear) -> MovimientoInventario:
    origen, destino = _validar_cabecera(db, ctx, datos)

    movimiento = MovimientoInventario(
        cuenta_id=origen.cuenta_id,
        finca_id=ctx.finca_id,
        tipo=datos.tipo,
        fecha=datos.fecha,
        bodega_id=origen.id,
        bodega_destino_id=destino.id if destino else None,
        proveedor_id=datos.proveedor_id if datos.tipo == "entrada" else None,
        motivo=datos.motivo,
        documento=datos.documento,
        observaciones=datos.observaciones,
        usuario_id=ctx.usuario.id,
        usuario_nombre=ctx.usuario.nombre_completo,
        creado_en=ahora(),
    )
    db.add(movimiento)
    db.flush()

    total = CERO
    vistos: set[int] = set()

    for entrada in datos.items:
        if entrada.articulo_id in vistos:
            raise datos_invalidos("Un articulo aparece dos veces en el mismo movimiento")
        vistos.add(entrada.articulo_id)

        articulo = articulo_de(db, ctx, entrada.articulo_id)
        cantidad = dec(entrada.cantidad)
        costo = dec(entrada.costo_unitario)
        if datos.tipo != "entrada" and costo <= CERO:
            # Lo que sale, se traslada o se ajusta se valora al costo promedio de la bodega
            costo = dec(existencia(db, origen.id, articulo.id).costo_promedio)

        if datos.tipo == "ajuste":
            actual = dec(existencia(db, origen.id, articulo.id).cantidad)
            aplicada = cantidad - actual  # la cantidad enviada es el conteo real
        else:
            if cantidad <= CERO:
                raise datos_invalidos(f"La cantidad de {articulo.nombre} debe ser mayor que cero")
            aplicada = cantidad if datos.tipo == "entrada" else -cantidad

        if datos.tipo == "traslado":
            mover(db, origen.id, articulo, -cantidad)
            mover(db, destino.id, articulo, cantidad, costo)
        else:
            mover(db, origen.id, articulo, aplicada, costo)

        total += cantidad * costo
        db.add(
            MovimientoItem(
                movimiento_id=movimiento.id,
                articulo_id=articulo.id,
                cantidad=cantidad,
                cantidad_aplicada=aplicada,
                costo_unitario=costo,
                lote=entrada.lote,
                vencimiento=entrada.vencimiento,
            )
        )

    movimiento.total = total
    registrar(
        db, ctx, "crear", "movimientos_inventario", movimiento.id,
        f"{datos.tipo.capitalize()} en {origen.nombre} con {len(datos.items)} articulo(s)",
        {"tipo": datos.tipo, "bodega": origen.nombre, "total": float(total)},
    )
    return movimiento


def anular_movimiento(db: Session, ctx: Contexto, movimiento: MovimientoInventario, motivo: str) -> None:
    """Devuelve las existencias como estaban y deja el movimiento marcado como anulado."""
    if movimiento.anulado:
        raise datos_invalidos("Ese movimiento ya estaba anulado")

    for item in movimiento.items:
        articulo = db.get(Articulo, item.articulo_id)
        if articulo is None:
            continue
        if movimiento.tipo == "traslado":
            mover(db, movimiento.bodega_destino_id, articulo, -dec(item.cantidad))
            mover(db, movimiento.bodega_id, articulo, dec(item.cantidad))
        else:
            mover(db, movimiento.bodega_id, articulo, -dec(item.cantidad_aplicada))

    movimiento.anulado = True
    movimiento.anulado_en = ahora()
    movimiento.anulado_por = ctx.usuario.nombre_completo
    movimiento.motivo_anulacion = motivo

    registrar(
        db, ctx, "anular", "movimientos_inventario", movimiento.id,
        f"Anulo un movimiento de tipo {movimiento.tipo}", {"motivo": motivo},
    )
