"""Lo que hace la importacion en la base de datos, y como deshacerla."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto
from app.core.errores import datos_invalidos
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
def aplicar(
    db: Session,
    ctx: Contexto,
    importacion: Importacion,
    filas: list[tuple[FilaImportacion, dict]],
    opciones: dict,
) -> dict:
    tipo = importacion.tipo
    cuenta_id = importacion.cuenta_id
    resumen: dict = {"creados": 0, "omitidos": 0}

    if tipo == "articulos":
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

    elif tipo == "entrada_inventario":
        bodega = bodega_de(db, ctx, int(opciones.get("bodega_id") or 0))
        crear_articulos = bool(opciones.get("crear_articulos", True))

        articulos_creados: list[int] = []
        grupos: dict[tuple, list[tuple[FilaImportacion, dict]]] = {}
        for fila, valores in filas:
            articulo = _articulo(db, cuenta_id, valores, crear_articulos, articulos_creados)
            if articulo is None:
                fila.estado = "error"
                fila.error = "El articulo no existe en el inventario"
                resumen["omitidos"] += 1
                continue
            valores["_articulo_id"] = articulo.id
            clave = (
                valores.get("fecha") or date.today(),
                str(valores.get("documento") or ""),
                str(valores.get("proveedor") or ""),
            )
            grupos.setdefault(clave, []).append((fila, valores))

        resumen["movimientos"] = 0
        for (fecha_mov, documento, proveedor_nombre), filas_grupo in grupos.items():
            proveedor = _proveedor(db, cuenta_id, proveedor_nombre or None)
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
            movimiento = crear_movimiento(
                db,
                ctx,
                MovimientoCrear(
                    tipo="entrada",
                    fecha=fecha_mov,
                    bodega_id=bodega.id,
                    proveedor_id=proveedor.id if proveedor else None,
                    documento=documento or None,
                    observaciones=f"Importado del archivo {importacion.archivo}",
                    items=items,
                ),
            )
            resumen["movimientos"] += 1
            for fila, _valores in filas_grupo:
                fila.estado = "aplicada"
                fila.entidad = "movimientos_inventario"
                fila.entidad_id = movimiento.id
                fila.creado = True
                resumen["creados"] += 1

        resumen["articulos_creados"] = articulos_creados

    elif tipo == "proveedores":
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

    elif tipo == "sanidad":
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

    elif tipo == "produccion":
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
                registro.cantidad = cantidad

            if tipo_huevo.comercial:
                mover_stock_huevos(db, lote.finca_id, tipo_huevo.id, cantidad - anterior)

            fila.estado, fila.entidad, fila.entidad_id, fila.creado = (
                "aplicada",
                "produccion_huevos",
                registro.id,
                True,
            )
            resumen["creados"] += 1

    else:  # pragma: no cover
        raise datos_invalidos("Ese tipo de importacion no existe")

    return resumen


# ------------------------------- Revertir -------------------------------
def revertir(db: Session, ctx: Contexto, importacion: Importacion) -> dict:
    resumen = {"deshechos": 0, "no_se_pudo": 0}
    filas = db.scalars(
        select(FilaImportacion).where(
            FilaImportacion.importacion_id == importacion.id, FilaImportacion.creado.is_(True)
        )
    ).all()

    movimientos_anulados: set[int] = set()
    creados_al_vuelo = list((importacion.resumen or {}).get("articulos_creados") or [])

    for fila in filas:
        if fila.entidad == "movimientos_inventario" and fila.entidad_id:
            if fila.entidad_id not in movimientos_anulados:
                movimiento = db.get(MovimientoInventario, fila.entidad_id)
                if movimiento is not None and not movimiento.anulado:
                    anular_movimiento(db, ctx, movimiento, f"Se deshizo la importacion {importacion.id}")
                movimientos_anulados.add(fila.entidad_id)
            fila.estado, fila.creado = "revertida", False
            resumen["deshechos"] += 1

        elif fila.entidad == "articulos" and fila.entidad_id:
            articulo = db.get(Articulo, fila.entidad_id)
            if articulo is None:
                fila.estado, fila.creado = "revertida", False
                continue
            hay = db.scalar(
                select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(Existencia.articulo_id == articulo.id)
            )
            if hay and float(hay) > 0:
                articulo.activo = False
                resumen["no_se_pudo"] += 1
            else:
                db.delete(articulo)
                resumen["deshechos"] += 1
            fila.estado, fila.creado = "revertida", False

        elif fila.entidad == "proveedores" and fila.entidad_id:
            proveedor = db.get(Proveedor, fila.entidad_id)
            if proveedor is not None:
                db.delete(proveedor)
            fila.estado, fila.creado = "revertida", False
            resumen["deshechos"] += 1

        elif fila.entidad == "aplicaciones_sanitarias" and fila.entidad_id:
            aplicacion = db.get(AplicacionSanitaria, fila.entidad_id)
            if aplicacion is not None:
                db.delete(aplicacion)
            fila.estado, fila.creado = "revertida", False
            resumen["deshechos"] += 1

        elif fila.entidad == "produccion_huevos" and fila.entidad_id:
            registro = db.get(ProduccionHuevos, fila.entidad_id)
            if registro is not None:
                tipo_huevo = db.get(TipoHuevo, registro.tipo_huevo_id)
                if tipo_huevo is not None and tipo_huevo.comercial:
                    mover_stock_huevos(db, registro.finca_id, registro.tipo_huevo_id, -registro.cantidad)
                db.delete(registro)
            fila.estado, fila.creado = "revertida", False
            resumen["deshechos"] += 1

    # Los articulos que se crearon solos con la importacion se desactivan si
    # quedaron sin existencias (no se borran porque su movimiento anulado los menciona).
    db.flush()  # para que la consulta vea las existencias ya devueltas
    for articulo_id in creados_al_vuelo:
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

    return resumen
