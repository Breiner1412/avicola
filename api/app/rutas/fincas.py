"""Fincas de la cuenta."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto
from app.esquemas.comunes import Mensaje
from app.esquemas.organizacion import FincaActualizar, FincaCrear, FincaSalida
from app.modelos.organizacion import Finca
from app.servicios.alcance import cuenta_objetivo, existe_codigo_finca, finca_de, fincas_visibles

router = APIRouter(prefix="/fincas", tags=["Fincas"])


@router.get("", response_model=list[FincaSalida], summary="Fincas que puedo ver")
def listar(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("fincas", "ver"))):
    return fincas_visibles(db, ctx)


@router.post("", response_model=FincaSalida, status_code=201, summary="Crear finca")
def crear(
    datos: FincaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("fincas", "crear")),
):
    cuenta_id = cuenta_objetivo(ctx, datos.cuenta_id)
    if existe_codigo_finca(db, cuenta_id, datos.codigo):
        raise conflicto(f"Ya existe una finca con el codigo {datos.codigo}")

    finca = Finca(
        cuenta_id=cuenta_id,
        **datos.model_dump(exclude={"cuenta_id"}),
    )
    db.add(finca)
    db.flush()
    registrar(db, ctx, "crear", "fincas", finca.id, f"Creo la finca {finca.nombre}", datos.model_dump())
    db.commit()
    db.refresh(finca)
    return finca


@router.get("/{finca_id}", response_model=FincaSalida, summary="Ver una finca")
def ver(finca_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("fincas", "ver"))):
    return finca_de(db, ctx, finca_id)


@router.patch("/{finca_id}", response_model=FincaSalida, summary="Editar finca")
def editar(
    finca_id: int,
    datos: FincaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("fincas", "editar")),
):
    finca = finca_de(db, ctx, finca_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "codigo" in cambios and existe_codigo_finca(db, finca.cuenta_id, cambios["codigo"], excluir=finca.id):
        raise conflicto(f"Ya existe una finca con el codigo {cambios['codigo']}")

    for campo, valor in cambios.items():
        setattr(finca, campo, valor)
    registrar(db, ctx, "editar", "fincas", finca.id, f"Edito la finca {finca.nombre}", cambios)
    db.commit()
    db.refresh(finca)
    return finca


@router.delete("/{finca_id}", response_model=Mensaje, summary="Desactivar finca")
def desactivar(
    finca_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("fincas", "borrar")),
):
    finca = finca_de(db, ctx, finca_id)
    finca.activo = False
    registrar(db, ctx, "desactivar", "fincas", finca.id, f"Desactivo la finca {finca.nombre}")
    db.commit()
    return Mensaje(mensaje="Finca desactivada")
