"""Lo que hace la importacion en la base de datos, y como deshacerla."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto
from app.core.errores import datos_invalidos
from app.core.tiempo import hoy
from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.modelos.aves import AplicacionSanitaria, Lote, ProduccionHuevos, TipoHuevo
from app.modelos.importacion import FilaImportacion, Importacion
from app.modelos.inventario import Articulo, CategoriaArticulo, Existencia, MovimientoInventario, Proveedor
from app.modelos.organizacion import Galpon
from app.servicios.aves import ahora, mover_stock_huevos
from app.servicios.importacion import normalizar
from app.servicios.inventario import anular_movimiento, bodega_de, crear_movimiento

UNIDADES_VALIDAS = ("unidad", "kg", "litro", "bulto", "dosis", "metro")
TIPOS_SANIDAD = ("vacuna", "medicamento", "vitamina", "desinfeccion", "otro")
VIAS = ("agua", "ocular", "aspersion", "inyectado", "alimento", "otro")

# Clave en los datos de la fila: cuanto habia ese dia antes de importar
CANTIDAD_ANTERIOR = "_cantidad_anterior"


def dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


def _categoria(db: Session, cuenta_id: int, nombre: str | None) -> CategoriaArticulo:
    categorias = db.scalars(
        select(CategoriaArticulo).where(
            (CategoriaArticulo.cuenta_id.is_(None)) | (CategoriaArticulo.cuenta_id == cuenta_id)
        )
    ).all()

    if nombre:
        buscado = normalizar(nombre)
        for categoria in categorias:
            if normalizar(categoria.nombre) == buscado:
                return categoria
        for categoria in categorias:
            if buscado and (buscado in normalizar(categoria.nombre) or normalizar(categoria.clase) == buscado):
                return categoria

    otros = next((c for c in categorias if normalizar(c.nombre) == "otros"), None)
    return otros or categorias[0]


def _unidad(valor: str | None) -> str:
    if not valor:
        return "unidad"
    plano = normalizar(valor)
    equivalencias = {
        "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogramo": "kg", "kilogramos": "kg",
        "unidad": "unidad", "und": "unidad", "un": "unidad", "unidades": "unidad", "u": "unidad",
        "litro": "litro", "litros": "litro", "lt": "litro", "l": "litro",
        "bulto": "bulto", "bultos": "bulto", "saco": "bulto", "sacos": "bulto",
        "dosis": "dosis", "ds": "dosis",
        "metro": "metro", "metros": "metro", "m": "metro",
    }
    return equivalencias.get(plano, "unidad")


def _articulo(db: Session, cuenta_id: int, valores: dict, crear: bool, creados: list[int] | None = None) -> Articulo | None:
    codigo = valores.get("codigo")
    nombre = valores.get("articulo") or valores.get("nombre")

    articulo = None
    if codigo:
        articulo = db.scalars(
            select(Articulo).where(Articulo.cuenta_id == cuenta_id, Articulo.codigo == str(codigo))
        ).first()
    if articulo is None and nombre:
        buscado = normalizar(nombre)
        for candidato in db.scalars(select(Articulo).where(Articulo.cuenta_id == cuenta_id)).all():
            if normalizar(candidato.nombre) == buscado:
                articulo = candidato
                break

    if articulo is None and crear and nombre:
        categoria = _categoria(db, cuenta_id, valores.get("categoria"))
        codigo_final = str(codigo) if codigo else None
        if not codigo_final:
            siguiente = (db.scalar(select(func.count(Articulo.id)).where(Articulo.cuenta_id == cuenta_id)) or 0) + 1
            codigo_final = f"IMP-{siguiente:04d}"
        articulo = Articulo(
            cuenta_id=cuenta_id,
            categoria_id=categoria.id,
            codigo=codigo_final,
            nombre=str(nombre),
            unidad=_unidad(valores.get("unidad")),
        )
        db.add(articulo)
        db.flush()
        if creados is not None:
            creados.append(articulo.id)

    return articulo


def _proveedor(db: Session, cuenta_id: int, nombre: str | None) -> Proveedor | None:
    if not nombre:
        return None
    buscado = normalizar(nombre)
    for candidato in db.scalars(select(Proveedor).where(Proveedor.cuenta_id == cuenta_id)).all():
        if normalizar(candidato.nombre) == buscado:
            return candidato
    proveedor = Proveedor(cuenta_id=cuenta_id, nombre=str(nombre))
    db.add(proveedor)
    db.flush()
    return proveedor


# ------------------------------- Aplicar -------------------------------
Filas = list[tuple[FilaImportacion, dict]]


def _aplicar_articulos(
    db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict, resumen: dict
) -> None:
    """Crea los articulos nuevos; los codigos que ya existen se omiten."""
    cuenta_id = importacion.cuenta_id
    for fila, valores in filas:
        existe = db.scalars(
            select(Articulo.id).where(Articulo.cuenta_id == cuenta_id, Articulo.codigo == str(valores["codigo"]))
        ).first()
        if existe:
            fila.estado = "error"
            fila.error = "Ya existe un articulo con ese codigo"
            resumen["omitidos"] += 1
            continue

        categoria = _categoria(db, cuenta_id, valores.get("categoria"))
        articulo = Articulo(
            cuenta_id=cuenta_id,
            categoria_id=categoria.id,
            codigo=str(valores["codigo"]),
            nombre=str(valores["nombre"]),
            unidad=_unidad(valores.get("unidad")),
            kg_por_bulto=valores.get("kg_por_bulto"),
            stock_minimo=dec(valores.get("stock_minimo")),
            observaciones=valores.get("observaciones"),
        )
        db.add(articulo)
        db.flush()
        fila.estado, fila.entidad, fila.entidad_id, fila.creado = "aplicada", "articulos", articulo.id, True
        resumen["creados"] += 1


def _aplicar_entradas(
    db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict, resumen: dict
) -> None:
    """Una entrada de inventario por cada fecha, documento y proveedor del archivo."""
    cuenta_id = importacion.cuenta_id
    try:
        bodega_id = int(opciones.get("bodega_id") or 0)
    except (TypeError, ValueError) as error:
        raise datos_invalidos("Elige la bodega a la que entra el inventario") from error
    bodega = bodega_de(db, ctx, bodega_id)
    crear_articulos = bool(opciones.get("crear_articulos", True))

    articulos_creados: list[int] = []
    grupos = _agrupar_entradas(db, cuenta_id, filas, crear_articulos, articulos_creados, resumen)

    resumen["movimientos"] = 0
    for clave, filas_grupo in grupos.items():
        movimiento = _crear_entrada(db, ctx, importacion, bodega.id, clave, filas_grupo)
        resumen["movimientos"] += 1
        for fila, _valores in filas_grupo:
            fila.estado = "aplicada"
            fila.entidad = "movimientos_inventario"
            fila.entidad_id = movimiento.id
            fila.creado = True
            resumen["creados"] += 1

    resumen["articulos_creados"] = articulos_creados


def _agrupar_entradas(
    db: Session, cuenta_id: int, filas: Filas, crear_articulos: bool, articulos_creados: list[int], resumen: dict
) -> dict[tuple, Filas]:
    """Agrupa las filas por fecha, documento y proveedor (una entrada por grupo)."""
    grupos: dict[tuple, Filas] = {}
    for fila, valores in filas:
        articulo = _articulo(db, cuenta_id, valores, crear_articulos, articulos_creados)
        if articulo is None:
            fila.estado = "error"
            fila.error = "El articulo no existe en el inventario"
            resumen["omitidos"] += 1
            continue
        valores["_articulo_id"] = articulo.id
        clave = (
            valores.get("fecha") or hoy(),
            str(valores.get("documento") or ""),
            str(valores.get("proveedor") or ""),
        )
        grupos.setdefault(clave, []).append((fila, valores))
    return grupos


def _crear_entrada(
    db: Session, ctx: Contexto, importacion: Importacion, bodega_id: int, clave: tuple, filas_grupo: Filas
) -> MovimientoInventario:
    fecha_mov, documento, proveedor_nombre = clave
    proveedor = _proveedor(db, importacion.cuenta_id, proveedor_nombre or None)
    items = [
        ItemEntrada(
            articulo_id=valores["_articulo_id"],
            cantidad=float(valores["cantidad"]),
            costo_unitario=float(valores.get("costo_unitario") or 0),
            lote=valores.get("lote"),
            vencimiento=valores.get("vencimiento"),
        )
        for _fila, valores in filas_grupo
    ]
    return crear_movimiento(
        db,
        ctx,
        MovimientoCrear(
            tipo="entrada",
            fecha=fecha_mov,
            bodega_id=bodega_id,
            proveedor_id=proveedor.id if proveedor else None,
            documento=documento or None,
            observaciones=f"Importado del archivo {importacion.archivo}",
            items=items,
        ),
    )


def _aplicar_proveedores(
    db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict, resumen: dict
) -> None:
    """Crea los proveedores nuevos; los nombres que ya existen se omiten."""
    cuenta_id = importacion.cuenta_id
    for fila, valores in filas:
        buscado = normalizar(str(valores["nombre"]))
        existe = any(
            normalizar(p.nombre) == buscado
            for p in db.scalars(select(Proveedor).where(Proveedor.cuenta_id == cuenta_id)).all()
        )
        if existe:
            fila.estado = "error"
            fila.error = "Ya existe un proveedor con ese nombre"
            resumen["omitidos"] += 1
            continue

        proveedor = Proveedor(
            cuenta_id=cuenta_id,
            nombre=str(valores["nombre"]),
            documento=valores.get("documento"),
            telefono=valores.get("telefono"),
            email=valores.get("email"),
            direccion=valores.get("direccion"),
        )
        db.add(proveedor)
        db.flush()
        fila.estado, fila.entidad, fila.entidad_id, fila.creado = "aplicada", "proveedores", proveedor.id, True
        resumen["creados"] += 1


def _aplicar_sanidad(
    db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict, resumen: dict
) -> None:
    """Registra las vacunas y tratamientos de los lotes y galpones de la finca."""
    cuenta_id = importacion.cuenta_id
    lotes = {normalizar(l.codigo): l for l in db.scalars(select(Lote).where(Lote.finca_id == importacion.finca_id)).all()}
    galpones = {
        normalizar(g.codigo): g
        for g in db.scalars(select(Galpon).where(Galpon.finca_id == importacion.finca_id)).all()
    }
    galpones.update(
        {
            normalizar(g.nombre): g
            for g in db.scalars(select(Galpon).where(Galpon.finca_id == importacion.finca_id)).all()
        }
    )

    for fila, valores in filas:
        lote = lotes.get(normalizar(valores.get("lote") or ""))
        galpon = galpones.get(normalizar(valores.get("galpon") or "")) if valores.get("galpon") else None
        if valores.get("lote") and lote is None:
            fila.estado = "error"
            fila.error = f"No existe el lote {valores['lote']} en esta finca"
            resumen["omitidos"] += 1
            continue

        tipo_valor = normalizar(valores.get("tipo") or "vacuna")
        via_valor = normalizar(valores.get("via") or "agua")
        aplicacion = AplicacionSanitaria(
            cuenta_id=cuenta_id,
            finca_id=importacion.finca_id,
            lote_id=lote.id if lote else None,
            galpon_id=galpon.id if galpon else (lote.galpon_id if lote else None),
            fecha=valores["fecha"],
            tipo=tipo_valor if tipo_valor in TIPOS_SANIDAD else "vacuna",
            producto=str(valores["producto"]),
            lote_producto=valores.get("lote_producto"),
            dosis=valores.get("dosis"),
            via=via_valor if via_valor in VIAS else "otro",
            aves_tratadas=int(valores["aves_tratadas"]) if valores.get("aves_tratadas") else None,
            responsable=valores.get("responsable"),
            proximo_refuerzo=valores.get("proximo_refuerzo"),
            observaciones=valores.get("observaciones"),
            usuario_nombre=ctx.usuario.nombre_completo,
            creado_en=ahora(),
        )
        db.add(aplicacion)
        db.flush()
        fila.estado, fila.entidad, fila.entidad_id, fila.creado = (
            "aplicada",
            "aplicaciones_sanitarias",
            aplicacion.id,
            True,
        )
        resumen["creados"] += 1


def _aplicar_produccion(
    db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict, resumen: dict
) -> None:
    """Registra o sobrescribe la produccion del dia y mueve el stock de huevos."""
    cuenta_id = importacion.cuenta_id
    lotes = {
        normalizar(l.codigo): l
        for l in db.scalars(select(Lote).where(Lote.finca_id == importacion.finca_id)).all()
    }
    tipos_huevo = {
        normalizar(t.nombre): t
        for t in db.scalars(
            select(TipoHuevo).where((TipoHuevo.cuenta_id.is_(None)) | (TipoHuevo.cuenta_id == cuenta_id))
        ).all()
    }

    for fila, valores in filas:
        lote = lotes.get(normalizar(str(valores["lote"])))
        tipo_huevo = tipos_huevo.get(normalizar(str(valores["tipo_huevo"])))
        if lote is None:
            fila.estado, fila.error = "error", f"No existe el lote {valores['lote']} en esta finca"
            resumen["omitidos"] += 1
            continue
        if tipo_huevo is None:
            fila.estado, fila.error = "error", f"No existe el tipo de huevo {valores['tipo_huevo']}"
            resumen["omitidos"] += 1
            continue

        registro = _guardar_dia(db, ctx, cuenta_id, lote, tipo_huevo, fila, valores)
        fila.estado, fila.entidad, fila.entidad_id, fila.creado = (
            "aplicada",
            "produccion_huevos",
            registro.id,
            True,
        )
        resumen["creados"] += 1


def _guardar_dia(
    db: Session,
    ctx: Contexto,
    cuenta_id: int,
    lote: Lote,
    tipo_huevo: TipoHuevo,
    fila: FilaImportacion,
    valores: dict,
) -> ProduccionHuevos:
    """Crea o sobrescribe la produccion del dia y ajusta el stock por la diferencia."""
    cantidad = int(valores["cantidad"])
    registro = db.scalars(
        select(ProduccionHuevos).where(
            ProduccionHuevos.lote_id == lote.id,
            ProduccionHuevos.fecha == valores["fecha"],
            ProduccionHuevos.tipo_huevo_id == tipo_huevo.id,
        )
    ).first()
    anterior = registro.cantidad if registro else 0

    if registro is None:
        registro = ProduccionHuevos(
            cuenta_id=cuenta_id,
            finca_id=lote.finca_id,
            lote_id=lote.id,
            tipo_huevo_id=tipo_huevo.id,
            fecha=valores["fecha"],
            cantidad=cantidad,
            usuario_nombre=ctx.usuario.nombre_completo,
            creado_en=ahora(),
        )
        db.add(registro)
        db.flush()
    else:
        # Se guarda lo que habia para poder volver a dejarlo al revertir
        fila.datos = {**fila.datos, CANTIDAD_ANTERIOR: anterior}
        registro.cantidad = cantidad

    if tipo_huevo.comercial:
        mover_stock_huevos(db, lote.finca_id, tipo_huevo.id, cantidad - anterior)
    return registro


APLICAR_POR_TIPO = {
    "articulos": _aplicar_articulos,
    "entrada_inventario": _aplicar_entradas,
    "proveedores": _aplicar_proveedores,
    "sanidad": _aplicar_sanidad,
    "produccion": _aplicar_produccion,
}


def aplicar(db: Session, ctx: Contexto, importacion: Importacion, filas: Filas, opciones: dict) -> dict:
    """Guarda las filas validas segun el tipo de importacion y devuelve el resumen."""
    aplicar_tipo = APLICAR_POR_TIPO.get(importacion.tipo)
    if aplicar_tipo is None:  # pragma: no cover
        raise datos_invalidos("Ese tipo de importacion no existe")
    resumen: dict = {"creados": 0, "omitidos": 0}
    aplicar_tipo(db, ctx, importacion, filas, opciones, resumen)
    return resumen


# ------------------------------- Revertir -------------------------------
def _revertir_articulo(db: Session, fila: FilaImportacion, resumen: dict) -> None:
    articulo = db.get(Articulo, fila.entidad_id)
    if articulo is None:
        return
    hay = db.scalar(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(Existencia.articulo_id == articulo.id)
    )
    if hay and float(hay) > 0:
        articulo.activo = False
        resumen["no_se_pudo"] += 1
    else:
        db.delete(articulo)
        resumen["deshechos"] += 1


def _revertir_produccion(db: Session, fila: FilaImportacion) -> None:
    """Si el dia ya existia, vuelve a su cantidad anterior; si lo creo la importacion, se borra."""
    registro = db.get(ProduccionHuevos, fila.entidad_id)
    if registro is None:
        return
    anterior = (fila.datos or {}).get(CANTIDAD_ANTERIOR)
    queda = int(anterior) if anterior is not None else 0
    tipo_huevo = db.get(TipoHuevo, registro.tipo_huevo_id)
    if tipo_huevo is not None and tipo_huevo.comercial:
        mover_stock_huevos(db, registro.finca_id, registro.tipo_huevo_id, queda - registro.cantidad)
    if anterior is None:
        db.delete(registro)
        db.flush()
    else:
        registro.cantidad = queda


def _borrar(db: Session, modelo, registro_id: int) -> None:
    registro = db.get(modelo, registro_id)
    if registro is not None:
        db.delete(registro)


def _desactivar_creados_al_vuelo(db: Session, articulo_ids: list[int], resumen: dict) -> None:
    """Los articulos que se crearon solos con la importacion se desactivan si quedaron
    sin existencias (no se borran porque su movimiento anulado los menciona)."""
    db.flush()  # para que la consulta vea las existencias ya devueltas
    for articulo_id in articulo_ids:
        articulo = db.get(Articulo, articulo_id)
        if articulo is None:
            continue
        hay = db.scalar(
            select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(Existencia.articulo_id == articulo.id)
        )
        if not hay or float(hay) == 0:
            articulo.activo = False
            resumen["deshechos"] += 1
        else:
            resumen["no_se_pudo"] += 1


def revertir(db: Session, ctx: Contexto, importacion: Importacion) -> dict:
    resumen = {"deshechos": 0, "no_se_pudo": 0}
    # De la ultima fila a la primera: si dos filas tocaron el mismo dia de produccion,
    # cada una deja lo que encontro y el dia termina como estaba antes de importar
    filas = db.scalars(
        select(FilaImportacion)
        .where(FilaImportacion.importacion_id == importacion.id, FilaImportacion.creado.is_(True))
        .order_by(FilaImportacion.numero.desc())
    ).all()

    movimientos_anulados: set[int] = set()
    for fila in filas:
        if not fila.entidad_id:
            continue
        if fila.entidad == "movimientos_inventario":
            if fila.entidad_id not in movimientos_anulados:
                movimiento = db.get(MovimientoInventario, fila.entidad_id)
                if movimiento is not None and not movimiento.anulado:
                    anular_movimiento(db, ctx, movimiento, f"Se deshizo la importacion {importacion.id}")
                movimientos_anulados.add(fila.entidad_id)
            resumen["deshechos"] += 1
        elif fila.entidad == "articulos":
            _revertir_articulo(db, fila, resumen)
        elif fila.entidad == "proveedores":
            _borrar(db, Proveedor, fila.entidad_id)
            resumen["deshechos"] += 1
        elif fila.entidad == "aplicaciones_sanitarias":
            _borrar(db, AplicacionSanitaria, fila.entidad_id)
            resumen["deshechos"] += 1
        elif fila.entidad == "produccion_huevos":
            _revertir_produccion(db, fila)
            resumen["deshechos"] += 1
        fila.estado, fila.creado = "revertida", False

    _desactivar_creados_al_vuelo(db, list((importacion.resumen or {}).get("articulos_creados") or []), resumen)
    return resumen
