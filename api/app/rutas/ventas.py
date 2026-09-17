"""Puntos de venta, productos, precios, caja y ventas."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado, sin_permiso
from app.esquemas.comunes import Mensaje, Pagina
from app.esquemas.ventas import (
    AbrirTurno,
    AnularVenta,
    CerrarTurno,
    DetalleSalida,
    MetodoPagoSalida,
    PagoSalida,
    PrecioCrear,
    PrecioSalida,
    ProductoActualizar,
    ProductoCrear,
    ProductoSalida,
    PuntoVentaActualizar,
    PuntoVentaCrear,
    PuntoVentaSalida,
    ResumenVentas,
    TurnoSalida,
    VentaCrear,
    VentaSalida,
)
from app.modelos.aves import StockHuevos
from app.modelos.ventas import (
    UNIDADES_POR_PRESENTACION,
    MetodoPago,
    Precio,
    ProductoVenta,
    PuntoVenta,
    TurnoCaja,
    Venta,
    VentaDetalle,
    VentaPago,
)
from app.servicios.alcance import cuenta_filtro, cuenta_objetivo, ids_fincas_visibles
from app.servicios.ventas import (
    abrir_turno,
    anular_venta,
    cerrar_turno,
    crear_venta,
    guardar_precio,
    precio_vigente,
    punto_de,
    puntos_visibles,
    totales_turno,
    turno_abierto,
)

router = APIRouter(tags=["Ventas"])


# --------------------------- Puntos de venta ---------------------------
def _punto_salida(punto: PuntoVenta) -> PuntoVentaSalida:
    datos = PuntoVentaSalida.model_validate(punto)
    datos.es_central = punto.finca_id is None
    return datos


@router.get("/puntos-venta", response_model=list[PuntoVentaSalida], summary="Puntos de venta")
def listar_puntos(
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("puntos_venta", "ver")),
):
    return [_punto_salida(p) for p in puntos_visibles(db, ctx, incluir_inactivos)]


@router.post("/puntos-venta", response_model=PuntoVentaSalida, status_code=201, summary="Crear punto de venta")
def crear_punto(
    datos: PuntoVentaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("puntos_venta", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    if datos.finca_id is not None and datos.finca_id not in ids_fincas_visibles(db, ctx):
        raise datos_invalidos("Esa finca no es tuya o no tienes acceso")
    if db.scalars(
        select(PuntoVenta.id).where(PuntoVenta.cuenta_id == cuenta_id, PuntoVenta.codigo == datos.codigo)
    ).first():
        raise conflicto(f"Ya existe un punto de venta con el codigo {datos.codigo}")

    punto = PuntoVenta(
        cuenta_id=cuenta_id,
        finca_id=datos.finca_id,
        codigo=datos.codigo,
        nombre=datos.nombre,
        direccion=datos.direccion,
        prefijo=datos.prefijo or datos.codigo,
    )
    db.add(punto)
    db.flush()
    registrar(db, ctx, "crear", "puntos_venta", punto.id, f"Creo el punto de venta {punto.nombre}")
    db.commit()
    db.refresh(punto)
    return _punto_salida(punto)


@router.patch("/puntos-venta/{punto_id}", response_model=PuntoVentaSalida, summary="Editar punto de venta")
def editar_punto(
    punto_id: int,
    datos: PuntoVentaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("puntos_venta", "editar")),
):
    punto = punto_de(db, ctx, punto_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "codigo" in cambios and db.scalars(
        select(PuntoVenta.id).where(
            PuntoVenta.cuenta_id == punto.cuenta_id, PuntoVenta.codigo == cambios["codigo"], PuntoVenta.id != punto.id
        )
    ).first():
        raise conflicto("Ya existe otro punto con ese codigo")

    for campo, valor in cambios.items():
        setattr(punto, campo, valor)
    registrar(db, ctx, "editar", "puntos_venta", punto.id, f"Edito el punto {punto.nombre}", cambios)
    db.commit()
    db.refresh(punto)
    return _punto_salida(punto)


# ------------------------------ Productos ------------------------------
def _producto_salida(db: Session, producto: ProductoVenta, punto_id: int | None, disponible: float | None = None):
    precio = precio_vigente(db, producto.id, punto_id)
    return ProductoSalida(
        id=producto.id,
        cuenta_id=producto.cuenta_id,
        nombre=producto.nombre,
        clase=producto.clase,
        tipo_huevo_id=producto.tipo_huevo_id,
        tipo_huevo=producto.tipo_huevo.nombre if producto.tipo_huevo else None,
        presentacion=producto.presentacion,
        factor=producto.factor,
        cobro_por=producto.cobro_por,
        orden=producto.orden,
        activo=producto.activo,
        precio=float(precio) if precio is not None else None,
        disponible=disponible,
    )


@router.get("/productos-venta", response_model=list[ProductoSalida], summary="Productos que se venden")
def listar_productos(
    punto_venta_id: int | None = Query(None),
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("productos_venta", "ver")),
):
    consulta = select(ProductoVenta)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(ProductoVenta.cuenta_id == cuenta)
    if not incluir_inactivos:
        consulta = consulta.where(ProductoVenta.activo.is_(True))

    productos = db.scalars(consulta.order_by(ProductoVenta.orden, ProductoVenta.nombre)).unique().all()

    # Cuantos huevos hay disponibles en la finca activa
    stock: dict[int, int] = {}
    if ctx.finca_id is not None:
        stock = {
            tipo_id: cantidad
            for tipo_id, cantidad in db.execute(
                select(StockHuevos.tipo_huevo_id, StockHuevos.cantidad).where(StockHuevos.finca_id == ctx.finca_id)
            ).all()
        }

    salida = []
    for producto in productos:
        disponible = None
        if producto.clase == "huevo" and producto.tipo_huevo_id:
            unidades = stock.get(producto.tipo_huevo_id, 0)
            disponible = round(unidades / producto.factor, 2) if producto.factor else unidades
        salida.append(_producto_salida(db, producto, punto_venta_id, disponible))
    return salida


@router.post("/productos-venta", response_model=ProductoSalida, status_code=201, summary="Crear producto")
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("productos_venta", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    if db.scalars(
        select(ProductoVenta.id).where(ProductoVenta.cuenta_id == cuenta_id, ProductoVenta.nombre == datos.nombre)
    ).first():
        raise conflicto("Ya existe un producto con ese nombre")
    if datos.clase == "huevo" and datos.tipo_huevo_id is None:
        raise datos_invalidos("Indica que tipo de huevo se vende")

    cobro = "kg" if datos.presentacion == "kg" else datos.cobro_por
    producto = ProductoVenta(
        cuenta_id=cuenta_id,
        nombre=datos.nombre,
        clase=datos.clase,
        tipo_huevo_id=datos.tipo_huevo_id,
        presentacion=datos.presentacion,
        factor=UNIDADES_POR_PRESENTACION.get(datos.presentacion, 1),
        cobro_por=cobro,
        orden=datos.orden,
    )
    db.add(producto)
    db.flush()

    if datos.precio is not None:
        guardar_precio(db, ctx, producto.id, datos.precio, None, None)

    registrar(db, ctx, "crear", "productos_venta", producto.id, f"Creo el producto {producto.nombre}")
    db.commit()
    db.refresh(producto)
    return _producto_salida(db, producto, None)


@router.patch("/productos-venta/{producto_id}", response_model=ProductoSalida, summary="Editar producto")
def editar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("productos_venta", "editar")),
):
    producto = db.get(ProductoVenta, producto_id)
    cuenta = cuenta_filtro(ctx)
    if producto is None or (cuenta is not None and producto.cuenta_id != cuenta):
        raise no_encontrado("El producto no existe")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    registrar(db, ctx, "editar", "productos_venta", producto.id, f"Edito el producto {producto.nombre}", cambios)
    db.commit()
    db.refresh(producto)
    return _producto_salida(db, producto, None)


@router.get("/precios", response_model=list[PrecioSalida], summary="Historial de precios")
def listar_precios(
    producto_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("precios", "ver")),
):
    producto = db.get(ProductoVenta, producto_id)
    cuenta = cuenta_filtro(ctx)
    if producto is None or (cuenta is not None and producto.cuenta_id != cuenta):
        raise no_encontrado("El producto no existe")

    filas = db.scalars(select(Precio).where(Precio.producto_id == producto_id).order_by(Precio.id.desc())).all()
    return [
        PrecioSalida(
            id=p.id,
            producto_id=p.producto_id,
            punto_venta_id=p.punto_venta_id,
            precio=float(p.precio),
            desde=p.desde,
            hasta=p.hasta,
            usuario_nombre=p.usuario_nombre,
        )
        for p in filas
    ]


@router.post("/precios", response_model=PrecioSalida, status_code=201, summary="Cambiar el precio")
def poner_precio(
    datos: PrecioCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("precios", "editar")),
):
    producto = db.get(ProductoVenta, datos.producto_id)
    cuenta = cuenta_filtro(ctx)
    if producto is None or (cuenta is not None and producto.cuenta_id != cuenta):
        raise no_encontrado("El producto no existe")
    if datos.punto_venta_id is not None:
        punto_de(db, ctx, datos.punto_venta_id)

    precio = guardar_precio(db, ctx, producto.id, datos.precio, datos.punto_venta_id, datos.desde)
    db.commit()
    db.refresh(precio)
    return PrecioSalida(
        id=precio.id,
        producto_id=precio.producto_id,
        punto_venta_id=precio.punto_venta_id,
        precio=float(precio.precio),
        desde=precio.desde,
        hasta=precio.hasta,
        usuario_nombre=precio.usuario_nombre,
    )


@router.get("/metodos-pago", response_model=list[MetodoPagoSalida], summary="Formas de pago")
def listar_metodos(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("ventas", "ver"))):
    cuenta = cuenta_filtro(ctx)
    return db.scalars(
        select(MetodoPago)
        .where(or_(MetodoPago.cuenta_id.is_(None), MetodoPago.cuenta_id == cuenta), MetodoPago.activo.is_(True))
        .order_by(MetodoPago.id)
    ).all()


# -------------------------------- Caja --------------------------------
def _turno_salida(db: Session, turno: TurnoCaja) -> TurnoSalida:
    punto = db.get(PuntoVenta, turno.punto_venta_id)
    totales = totales_turno(db, turno)
    return TurnoSalida(
        id=turno.id,
        punto_venta_id=turno.punto_venta_id,
        punto_venta_nombre=punto.nombre if punto else "",
        usuario_id=turno.usuario_id,
        usuario_nombre=turno.usuario_nombre,
        estado=turno.estado,
        base_inicial=float(turno.base_inicial or 0),
        abierto_en=turno.abierto_en,
        cerrado_en=turno.cerrado_en,
        efectivo_contado=float(turno.efectivo_contado) if turno.efectivo_contado is not None else None,
        diferencia=float(turno.diferencia) if turno.diferencia is not None else None,
        observaciones=turno.observaciones,
        **totales,
    )


@router.get("/caja/turno", response_model=TurnoSalida | None, summary="Mi turno abierto")
def mi_turno(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("caja", "ver"))):
    turno = turno_abierto(db, ctx)
    return _turno_salida(db, turno) if turno else None


@router.post("/caja/abrir", response_model=TurnoSalida, status_code=201, summary="Abrir la caja")
def abrir(
    datos: AbrirTurno,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("caja", "crear")),
):
    punto = punto_de(db, ctx, datos.punto_venta_id)
    turno = abrir_turno(db, ctx, punto, datos.base_inicial, datos.observaciones)
    db.commit()
    db.refresh(turno)
    return _turno_salida(db, turno)


@router.post("/caja/cerrar", response_model=TurnoSalida, summary="Cerrar la caja")
def cerrar(
    datos: CerrarTurno,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("caja", "editar")),
):
    turno = turno_abierto(db, ctx)
    if turno is None:
        raise datos_invalidos("No tienes ningun turno abierto")

    cerrar_turno(db, ctx, turno, datos.efectivo_contado, datos.observaciones)
    db.commit()
    db.refresh(turno)
    return _turno_salida(db, turno)


@router.get("/caja/turnos", response_model=list[TurnoSalida], summary="Turnos anteriores")
def turnos(
    punto_venta_id: int | None = Query(None),
    limite: int = Query(30, ge=1, le=200),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("caja", "ver")),
):
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)]
    if not puntos:
        return []

    consulta = select(TurnoCaja).where(TurnoCaja.punto_venta_id.in_(puntos))
    if punto_venta_id:
        consulta = consulta.where(TurnoCaja.punto_venta_id == punto_venta_id)
    if ctx.rol in ("cajero", "operario"):
        consulta = consulta.where(TurnoCaja.usuario_id == ctx.usuario.id)

    filas = db.scalars(consulta.order_by(TurnoCaja.id.desc()).limit(limite)).all()
    return [_turno_salida(db, t) for t in filas]


# ------------------------------- Ventas -------------------------------
def _venta_salida(venta: Venta) -> VentaSalida:
    return VentaSalida(
        id=venta.id,
        numero=venta.numero,
        punto_venta_id=venta.punto_venta_id,
        punto_venta_nombre=venta.punto.nombre if venta.punto else "",
        turno_id=venta.turno_id,
        fecha=venta.fecha,
        subtotal=float(venta.subtotal),
        descuento=float(venta.descuento),
        total=float(venta.total),
        estado=venta.estado,
        observaciones=venta.observaciones,
        usuario_nombre=venta.usuario_nombre,
        anulada_en=venta.anulada_en,
        anulada_por=venta.anulada_por,
        motivo_anulacion=venta.motivo_anulacion,
        creado_en=venta.creado_en,
        detalles=[
            DetalleSalida(
                id=d.id,
                producto_id=d.producto_id,
                descripcion=d.descripcion,
                clase=d.clase,
                cantidad=float(d.cantidad),
                precio_unitario=float(d.precio_unitario),
                subtotal=float(d.subtotal),
                unidades=d.unidades,
                peso_kg=float(d.peso_kg) if d.peso_kg is not None else None,
                lote_id=d.lote_id,
            )
            for d in venta.detalles
        ],
        pagos=[
            PagoSalida(
                metodo_pago_id=p.metodo_pago_id,
                metodo_nombre=p.metodo_nombre,
                es_efectivo=p.es_efectivo,
                monto=float(p.monto),
                referencia=p.referencia,
            )
            for p in venta.pagos
        ],
    )


def _venta_de(db: Session, ctx: Contexto, venta_id: int) -> Venta:
    venta = db.get(Venta, venta_id)
    cuenta = cuenta_filtro(ctx)
    if venta is None or (cuenta is not None and venta.cuenta_id != cuenta):
        raise no_encontrado("La venta no existe")
    if venta.punto_venta_id not in {p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)}:
        raise sin_permiso("Esa venta es de otro punto de venta")
    return venta


@router.get("/ventas", response_model=Pagina[VentaSalida], summary="Ventas")
def listar_ventas(
    punto_venta_id: int | None = Query(None),
    turno_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    incluir_anuladas: bool = Query(True),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(25, ge=1, le=200),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("ventas", "ver")),
):
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)]
    if not puntos:
        return Pagina[VentaSalida](total=0, pagina=pagina, tamano=tamano, datos=[])

    consulta = select(Venta).where(Venta.punto_venta_id.in_(puntos))
    if punto_venta_id:
        consulta = consulta.where(Venta.punto_venta_id == punto_venta_id)
    if turno_id:
        consulta = consulta.where(Venta.turno_id == turno_id)
    if desde:
        consulta = consulta.where(Venta.fecha >= desde)
    if hasta:
        consulta = consulta.where(Venta.fecha <= hasta)
    if not incluir_anuladas:
        consulta = consulta.where(Venta.estado == "activa")

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.scalars(
        consulta.order_by(Venta.id.desc()).offset((pagina - 1) * tamano).limit(tamano)
    ).unique().all()

    return Pagina[VentaSalida](total=total, pagina=pagina, tamano=tamano, datos=[_venta_salida(v) for v in filas])


@router.post("/ventas", response_model=VentaSalida, status_code=201, summary="Registrar una venta")
def vender(
    datos: VentaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("ventas", "crear")),
):
    turno = turno_abierto(db, ctx)
    if turno is None:
        raise datos_invalidos("Primero abre la caja")

    punto = punto_de(db, ctx, turno.punto_venta_id)
    venta = crear_venta(db, ctx, punto, turno, datos)
    db.commit()
    db.refresh(venta)
    return _venta_salida(venta)


@router.get("/ventas/resumen", response_model=ResumenVentas, summary="Resumen de ventas")
def resumen(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("ventas", "ver")),
):
    puntos = [p.id for p in puntos_visibles(db, ctx, incluir_inactivos=True)]
    if not puntos:
        return ResumenVentas(ventas=0, total=0, efectivo=0, otros_medios=0, anuladas=0, huevos_vendidos=0, aves_vendidas=0)

    base = select(Venta).where(Venta.punto_venta_id.in_(puntos))
    if desde:
        base = base.where(Venta.fecha >= desde)
    if hasta:
        base = base.where(Venta.fecha <= hasta)

    activas = base.where(Venta.estado == "activa").subquery()

    ventas, total = db.execute(
        select(func.count(activas.c.id), func.coalesce(func.sum(activas.c.total), 0))
    ).one()
    anuladas = db.scalar(
        select(func.count()).select_from(base.where(Venta.estado == "anulada").subquery())
    ) or 0

    efectivo = db.scalar(
        select(func.coalesce(func.sum(VentaPago.monto), 0))
        .join(activas, VentaPago.venta_id == activas.c.id)
        .where(VentaPago.es_efectivo.is_(True))
    ) or 0
    otros = db.scalar(
        select(func.coalesce(func.sum(VentaPago.monto), 0))
        .join(activas, VentaPago.venta_id == activas.c.id)
        .where(VentaPago.es_efectivo.is_(False))
    ) or 0

    huevos = db.scalar(
        select(func.coalesce(func.sum(VentaDetalle.unidades), 0))
        .join(activas, VentaDetalle.venta_id == activas.c.id)
        .where(VentaDetalle.clase == "huevo")
    ) or 0
    aves = db.scalar(
        select(func.coalesce(func.sum(VentaDetalle.unidades), 0))
        .join(activas, VentaDetalle.venta_id == activas.c.id)
        .where(VentaDetalle.clase.in_(("ave_descarte", "ave_engorde")))
    ) or 0

    return ResumenVentas(
        ventas=int(ventas or 0),
        total=float(total or 0),
        efectivo=float(efectivo or 0),
        otros_medios=float(otros or 0),
        anuladas=int(anuladas),
        huevos_vendidos=int(huevos),
        aves_vendidas=int(aves),
    )


@router.get("/ventas/{venta_id}", response_model=VentaSalida, summary="Ver una venta")
def ver_venta(venta_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("ventas", "ver"))):
    return _venta_salida(_venta_de(db, ctx, venta_id))


@router.post("/ventas/{venta_id}/anular", response_model=VentaSalida, summary="Anular una venta")
def anular(
    venta_id: int,
    datos: AnularVenta,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("ventas", "editar")),
):
    venta = _venta_de(db, ctx, venta_id)
    anular_venta(db, ctx, venta, datos.motivo)
    db.commit()
    db.refresh(venta)
    return _venta_salida(venta)


@router.delete("/ventas/{venta_id}", response_model=Mensaje, summary="Borrar una venta anulada")
def borrar(
    venta_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("ventas", "borrar")),
):
    venta = _venta_de(db, ctx, venta_id)
    if venta.estado != "anulada":
        raise datos_invalidos("Solo se puede borrar una venta que ya fue anulada")

    registrar(db, ctx, "borrar", "ventas", venta.id, f"Borro la venta anulada {venta.numero}")
    db.delete(venta)
    db.commit()
    return Mensaje(mensaje="Venta borrada")
