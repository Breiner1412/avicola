"""Bodegas, categorias, articulos, proveedores y existencias."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos, no_encontrado
from app.esquemas.comunes import Mensaje
from app.esquemas.inventario import (
    ArticuloActualizar,
    ArticuloCrear,
    ArticuloSalida,
    BodegaActualizar,
    BodegaCrear,
    BodegaSalida,
    CategoriaCrear,
    CategoriaSalida,
    ExistenciaSalida,
    ProveedorActualizar,
    ProveedorCrear,
    ProveedorSalida,
)
from app.modelos.inventario import Articulo, Bodega, CategoriaArticulo, Existencia, Proveedor
from app.servicios.alcance import cuenta_filtro, cuenta_objetivo, ids_fincas_visibles
from app.servicios.inventario import articulo_de, bodega_de, bodegas_visibles

router = APIRouter(tags=["Inventario"])


def _bodega_salida(bodega: Bodega) -> BodegaSalida:
    datos = BodegaSalida.model_validate(bodega)
    datos.es_central = bodega.finca_id is None
    return datos


def _articulo_salida(articulo: Articulo, existencia_total: float = 0.0) -> ArticuloSalida:
    minimo = float(articulo.stock_minimo or 0)
    return ArticuloSalida(
        id=articulo.id,
        cuenta_id=articulo.cuenta_id,
        categoria_id=articulo.categoria_id,
        categoria_nombre=articulo.categoria.nombre,
        clase=articulo.categoria.clase,
        codigo=articulo.codigo,
        nombre=articulo.nombre,
        unidad=articulo.unidad,
        kg_por_bulto=float(articulo.kg_por_bulto) if articulo.kg_por_bulto is not None else None,
        stock_minimo=minimo,
        observaciones=articulo.observaciones,
        activo=articulo.activo,
        existencia_total=existencia_total,
        bajo_minimo=minimo > 0 and existencia_total < minimo,
    )


# ----------------------------- Bodegas -----------------------------
@router.get("/bodegas", response_model=list[BodegaSalida], summary="Bodegas visibles")
def listar_bodegas(
    todas: bool = Query(False, description="Todas las fincas que puedo ver, no solo la activa"),
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("bodegas", "ver")),
):
    return [_bodega_salida(b) for b in bodegas_visibles(db, ctx, todas, incluir_inactivas)]


@router.post("/bodegas", response_model=BodegaSalida, status_code=201, summary="Crear bodega")
def crear_bodega(
    datos: BodegaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("bodegas", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    finca_id = datos.finca_id
    if finca_id is not None and finca_id not in ids_fincas_visibles(db, ctx):
        raise datos_invalidos("Esa finca no es tuya o no tienes acceso")

    if db.scalars(select(Bodega.id).where(Bodega.cuenta_id == cuenta_id, Bodega.codigo == datos.codigo)).first():
        raise conflicto(f"Ya existe una bodega con el codigo {datos.codigo}")

    bodega = Bodega(
        cuenta_id=cuenta_id,
        finca_id=finca_id,
        codigo=datos.codigo,
        nombre=datos.nombre,
        ubicacion=datos.ubicacion,
    )
    db.add(bodega)
    db.flush()
    registrar(db, ctx, "crear", "bodegas", bodega.id, f"Creo la bodega {bodega.nombre}", datos.model_dump())
    db.commit()
    db.refresh(bodega)
    return _bodega_salida(bodega)


@router.patch("/bodegas/{bodega_id}", response_model=BodegaSalida, summary="Editar bodega")
def editar_bodega(
    bodega_id: int,
    datos: BodegaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("bodegas", "editar")),
):
    bodega = bodega_de(db, ctx, bodega_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "codigo" in cambios and db.scalars(
        select(Bodega.id).where(
            Bodega.cuenta_id == bodega.cuenta_id, Bodega.codigo == cambios["codigo"], Bodega.id != bodega.id
        )
    ).first():
        raise conflicto(f"Ya existe una bodega con el codigo {cambios['codigo']}")

    if "finca_id" in cambios and cambios["finca_id"] is not None:
        if cambios["finca_id"] not in ids_fincas_visibles(db, ctx):
            raise datos_invalidos("Esa finca no es tuya o no tienes acceso")

    for campo, valor in cambios.items():
        setattr(bodega, campo, valor)
    registrar(db, ctx, "editar", "bodegas", bodega.id, f"Edito la bodega {bodega.nombre}", cambios)
    db.commit()
    db.refresh(bodega)
    return _bodega_salida(bodega)


@router.delete("/bodegas/{bodega_id}", response_model=Mensaje, summary="Desactivar bodega")
def desactivar_bodega(
    bodega_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("bodegas", "borrar")),
):
    bodega = bodega_de(db, ctx, bodega_id)
    con_existencias = db.scalar(
        select(func.count()).select_from(Existencia).where(Existencia.bodega_id == bodega.id, Existencia.cantidad > 0)
    )
    if con_existencias:
        raise datos_invalidos("La bodega todavia tiene articulos. Sacalos o trasladalos antes de desactivarla.")

    bodega.activo = False
    registrar(db, ctx, "desactivar", "bodegas", bodega.id, f"Desactivo la bodega {bodega.nombre}")
    db.commit()
    return Mensaje(mensaje="Bodega desactivada")


# --------------------------- Categorias ---------------------------
@router.get("/categorias-articulo", response_model=list[CategoriaSalida], summary="Categorias de articulos")
def listar_categorias(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("articulos", "ver"))):
    consulta = select(CategoriaArticulo).where(
        or_(CategoriaArticulo.cuenta_id.is_(None), CategoriaArticulo.cuenta_id == cuenta_filtro(ctx))
    )
    return db.scalars(consulta.order_by(CategoriaArticulo.nombre)).all()


@router.post("/categorias-articulo", response_model=CategoriaSalida, status_code=201, summary="Crear categoria")
def crear_categoria(
    datos: CategoriaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("articulos", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    existe = db.scalars(
        select(CategoriaArticulo.id).where(
            or_(CategoriaArticulo.cuenta_id.is_(None), CategoriaArticulo.cuenta_id == cuenta_id),
            CategoriaArticulo.nombre == datos.nombre,
        )
    ).first()
    if existe:
        raise conflicto("Ya existe una categoria con ese nombre")

    categoria = CategoriaArticulo(cuenta_id=cuenta_id, nombre=datos.nombre, clase=datos.clase)
    db.add(categoria)
    db.flush()
    registrar(db, ctx, "crear", "categorias_articulo", categoria.id, f"Creo la categoria {categoria.nombre}")
    db.commit()
    db.refresh(categoria)
    return categoria


# ---------------------------- Articulos ----------------------------
def _existencias_por_articulo(db: Session, ctx: Contexto) -> dict[int, float]:
    bodegas = [b.id for b in bodegas_visibles(db, ctx, todas=True, incluir_inactivas=True)]
    if not bodegas:
        return {}
    filas = db.execute(
        select(Existencia.articulo_id, func.sum(Existencia.cantidad))
        .where(Existencia.bodega_id.in_(bodegas))
        .group_by(Existencia.articulo_id)
    ).all()
    return {articulo_id: float(cantidad or 0) for articulo_id, cantidad in filas}


@router.get("/articulos", response_model=list[ArticuloSalida], summary="Articulos de la cuenta")
def listar_articulos(
    buscar: str | None = Query(None, max_length=80),
    categoria_id: int | None = Query(None),
    clase: str | None = Query(None),
    solo_bajo_minimo: bool = Query(False),
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("articulos", "ver")),
):
    consulta = select(Articulo).join(CategoriaArticulo, Articulo.categoria_id == CategoriaArticulo.id)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Articulo.cuenta_id == cuenta)
    if not incluir_inactivos:
        consulta = consulta.where(Articulo.activo.is_(True))
    if categoria_id:
        consulta = consulta.where(Articulo.categoria_id == categoria_id)
    if clase:
        consulta = consulta.where(CategoriaArticulo.clase == clase)
    if buscar:
        patron = f"%{buscar}%"
        consulta = consulta.where(or_(Articulo.nombre.like(patron), Articulo.codigo.like(patron)))

    articulos = db.scalars(consulta.order_by(Articulo.nombre)).unique().all()
    totales = _existencias_por_articulo(db, ctx)
    salida = [_articulo_salida(a, totales.get(a.id, 0.0)) for a in articulos]
    if solo_bajo_minimo:
        salida = [a for a in salida if a.bajo_minimo]
    return salida


@router.post("/articulos", response_model=ArticuloSalida, status_code=201, summary="Crear articulo")
def crear_articulo(
    datos: ArticuloCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("articulos", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    categoria = db.get(CategoriaArticulo, datos.categoria_id)
    if categoria is None or (categoria.cuenta_id is not None and categoria.cuenta_id != cuenta_id):
        raise datos_invalidos("La categoria no existe")

    if db.scalars(select(Articulo.id).where(Articulo.cuenta_id == cuenta_id, Articulo.codigo == datos.codigo)).first():
        raise conflicto(f"Ya existe un articulo con el codigo {datos.codigo}")

    articulo = Articulo(cuenta_id=cuenta_id, **datos.model_dump())
    db.add(articulo)
    db.flush()
    registrar(db, ctx, "crear", "articulos", articulo.id, f"Creo el articulo {articulo.nombre}", datos.model_dump())
    db.commit()
    db.refresh(articulo)
    return _articulo_salida(articulo)


@router.patch("/articulos/{articulo_id}", response_model=ArticuloSalida, summary="Editar articulo")
def editar_articulo(
    articulo_id: int,
    datos: ArticuloActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("articulos", "editar")),
):
    articulo = articulo_de(db, ctx, articulo_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "codigo" in cambios and db.scalars(
        select(Articulo.id).where(
            Articulo.cuenta_id == articulo.cuenta_id, Articulo.codigo == cambios["codigo"], Articulo.id != articulo.id
        )
    ).first():
        raise conflicto(f"Ya existe un articulo con el codigo {cambios['codigo']}")

    if "categoria_id" in cambios and cambios["categoria_id"]:
        categoria = db.get(CategoriaArticulo, cambios["categoria_id"])
        if categoria is None or (categoria.cuenta_id is not None and categoria.cuenta_id != articulo.cuenta_id):
            raise datos_invalidos("La categoria no existe")

    for campo, valor in cambios.items():
        setattr(articulo, campo, valor)
    registrar(db, ctx, "editar", "articulos", articulo.id, f"Edito el articulo {articulo.nombre}", cambios)
    db.commit()
    db.refresh(articulo)
    totales = _existencias_por_articulo(db, ctx)
    return _articulo_salida(articulo, totales.get(articulo.id, 0.0))


@router.delete("/articulos/{articulo_id}", response_model=Mensaje, summary="Desactivar articulo")
def desactivar_articulo(
    articulo_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("articulos", "borrar")),
):
    articulo = articulo_de(db, ctx, articulo_id)
    hay = db.scalar(
        select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(Existencia.articulo_id == articulo.id)
    )
    if hay and float(hay) > 0:
        raise datos_invalidos("Todavia hay existencias de ese articulo en alguna bodega")

    articulo.activo = False
    registrar(db, ctx, "desactivar", "articulos", articulo.id, f"Desactivo el articulo {articulo.nombre}")
    db.commit()
    return Mensaje(mensaje="Articulo desactivado")


# --------------------------- Existencias ---------------------------
@router.get("/existencias", response_model=list[ExistenciaSalida], summary="Que hay en cada bodega")
def listar_existencias(
    bodega_id: int | None = Query(None),
    solo_bajo_minimo: bool = Query(False),
    ocultar_en_cero: bool = Query(True),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("bodegas", "ver")),
):
    visibles = [b.id for b in bodegas_visibles(db, ctx, todas=True, incluir_inactivas=True)]
    if bodega_id is not None:
        bodega_de(db, ctx, bodega_id)
        visibles = [bodega_id]
    if not visibles:
        return []

    filas = db.execute(
        select(Existencia, Articulo, Bodega)
        .join(Articulo, Existencia.articulo_id == Articulo.id)
        .join(Bodega, Existencia.bodega_id == Bodega.id)
        .where(Existencia.bodega_id.in_(visibles))
        .order_by(Bodega.nombre, Articulo.nombre)
    ).all()

    salida = []
    for existencia, articulo, bodega in filas:
        cantidad = float(existencia.cantidad or 0)
        minimo = float(articulo.stock_minimo or 0)
        if ocultar_en_cero and cantidad == 0:
            continue
        bajo = minimo > 0 and cantidad < minimo
        if solo_bajo_minimo and not bajo:
            continue
        salida.append(
            ExistenciaSalida(
                bodega_id=bodega.id,
                bodega_nombre=bodega.nombre,
                articulo_id=articulo.id,
                articulo_codigo=articulo.codigo,
                articulo_nombre=articulo.nombre,
                unidad=articulo.unidad,
                cantidad=cantidad,
                costo_promedio=float(existencia.costo_promedio or 0),
                stock_minimo=minimo,
                bajo_minimo=bajo,
            )
        )
    return salida


# --------------------------- Proveedores ---------------------------
@router.get("/proveedores", response_model=list[ProveedorSalida], summary="Proveedores")
def listar_proveedores(
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("proveedores", "ver")),
):
    consulta = select(Proveedor)
    cuenta = cuenta_filtro(ctx)
    if cuenta is not None:
        consulta = consulta.where(Proveedor.cuenta_id == cuenta)
    if not incluir_inactivos:
        consulta = consulta.where(Proveedor.activo.is_(True))
    return db.scalars(consulta.order_by(Proveedor.nombre)).all()


@router.post("/proveedores", response_model=ProveedorSalida, status_code=201, summary="Crear proveedor")
def crear_proveedor(
    datos: ProveedorCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("proveedores", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, None)
    if db.scalars(
        select(Proveedor.id).where(Proveedor.cuenta_id == cuenta_id, Proveedor.nombre == datos.nombre)
    ).first():
        raise conflicto("Ya existe un proveedor con ese nombre")

    proveedor = Proveedor(cuenta_id=cuenta_id, **datos.model_dump())
    db.add(proveedor)
    db.flush()
    registrar(db, ctx, "crear", "proveedores", proveedor.id, f"Creo el proveedor {proveedor.nombre}")
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorSalida, summary="Editar proveedor")
def editar_proveedor(
    proveedor_id: int,
    datos: ProveedorActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("proveedores", "editar")),
):
    proveedor = db.get(Proveedor, proveedor_id)
    if proveedor is None or (not ctx.es_plataforma and proveedor.cuenta_id != ctx.cuenta_id):
        raise no_encontrado("El proveedor no existe")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(proveedor, campo, valor)
    registrar(db, ctx, "editar", "proveedores", proveedor.id, f"Edito el proveedor {proveedor.nombre}", cambios)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.delete("/proveedores/{proveedor_id}", response_model=Mensaje, summary="Desactivar proveedor")
def desactivar_proveedor(
    proveedor_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("proveedores", "borrar")),
):
    proveedor = db.get(Proveedor, proveedor_id)
    if proveedor is None or (not ctx.es_plataforma and proveedor.cuenta_id != ctx.cuenta_id):
        raise no_encontrado("El proveedor no existe")
    proveedor.activo = False
    registrar(db, ctx, "desactivar", "proveedores", proveedor.id, f"Desactivo el proveedor {proveedor.nombre}")
    db.commit()
    return Mensaje(mensaje="Proveedor desactivado")
