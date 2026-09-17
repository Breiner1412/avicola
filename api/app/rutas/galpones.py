"""Galpones de la finca activa."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, datos_invalidos
from app.esquemas.comunes import Mensaje
from app.esquemas.organizacion import GalponActualizar, GalponCrear, GalponSalida
from app.modelos.organizacion import Galpon
from app.servicios.alcance import galpon_de

router = APIRouter(prefix="/galpones", tags=["Galpones"])


def _codigo_repetido(db: Session, finca_id: int, codigo: str, excluir: int | None = None) -> bool:
    consulta = select(Galpon.id).where(Galpon.finca_id == finca_id, Galpon.codigo == codigo)
    if excluir:
        consulta = consulta.where(Galpon.id != excluir)
    return db.scalars(consulta).first() is not None


@router.get("", response_model=list[GalponSalida], summary="Galpones de la finca activa")
def listar(
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("galpones", "ver", con_finca=True)),
):
    consulta = select(Galpon).where(Galpon.finca_id == ctx.finca_id)
    if not incluir_inactivos:
        consulta = consulta.where(Galpon.activo.is_(True))
    return db.scalars(consulta.order_by(Galpon.codigo)).all()


@router.post("", response_model=GalponSalida, status_code=201, summary="Crear galpon")
def crear(
    datos: GalponCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("galpones", "crear", con_finca=True)),
):
    if _codigo_repetido(db, ctx.finca_id, datos.codigo):
        raise conflicto(f"Ya existe un galpon con el codigo {datos.codigo} en esta finca")

    galpon = Galpon(finca_id=ctx.finca_id, **datos.model_dump())
    db.add(galpon)
    db.flush()
    registrar(db, ctx, "crear", "galpones", galpon.id, f"Creo el galpon {galpon.nombre}", datos.model_dump())
    db.commit()
    db.refresh(galpon)
    return galpon


@router.get("/{galpon_id}", response_model=GalponSalida, summary="Ver un galpon")
def ver(galpon_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("galpones", "ver"))):
    return galpon_de(db, ctx, galpon_id)


@router.patch("/{galpon_id}", response_model=GalponSalida, summary="Editar galpon")
def editar(
    galpon_id: int,
    datos: GalponActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("galpones", "editar")),
):
    galpon = galpon_de(db, ctx, galpon_id)
    cambios = datos.model_dump(exclude_unset=True)

    if "codigo" in cambios and _codigo_repetido(db, galpon.finca_id, cambios["codigo"], excluir=galpon.id):
        raise conflicto(f"Ya existe un galpon con el codigo {cambios['codigo']} en esta finca")
    if "capacidad" in cambios and cambios["capacidad"] < galpon.aves_actuales:
        raise datos_invalidos(
            f"La capacidad no puede ser menor que las {galpon.aves_actuales} aves que hay en el galpon"
        )

    for campo, valor in cambios.items():
        setattr(galpon, campo, valor)
    registrar(db, ctx, "editar", "galpones", galpon.id, f"Edito el galpon {galpon.nombre}", cambios)
    db.commit()
    db.refresh(galpon)
    return galpon


@router.delete("/{galpon_id}", response_model=Mensaje, summary="Desactivar galpon")
def desactivar(
    galpon_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("galpones", "borrar")),
):
    galpon = galpon_de(db, ctx, galpon_id)
    if galpon.aves_actuales > 0:
        raise datos_invalidos("No puedes desactivar un galpon que todavia tiene aves")
    galpon.activo = False
    registrar(db, ctx, "desactivar", "galpones", galpon.id, f"Desactivo el galpon {galpon.nombre}")
    db.commit()
    return Mensaje(mensaje="Galpon desactivado")
