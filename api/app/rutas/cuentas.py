"""Cuentas del sistema (empresas o personas). Solo para el rol de plataforma."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, requiere
from app.core.db import obtener_db
from app.core.errores import conflicto, no_encontrado
from app.esquemas.comunes import Mensaje
from app.esquemas.organizacion import CuentaActualizar, CuentaCrear, CuentaSalida
from app.modelos.organizacion import Cuenta

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])


@router.get("", response_model=list[CuentaSalida], summary="Listar cuentas")
def listar(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("cuentas", "ver"))):
    return db.scalars(select(Cuenta).order_by(Cuenta.nombre)).all()


@router.post("", response_model=CuentaSalida, status_code=201, summary="Crear cuenta")
def crear(
    datos: CuentaCrear,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("cuentas", "crear")),
):
    if datos.documento and db.scalars(select(Cuenta.id).where(Cuenta.documento == datos.documento)).first():
        raise conflicto("Ya existe una cuenta con ese documento")

    cuenta = Cuenta(**datos.model_dump())
    db.add(cuenta)
    db.flush()
    registrar(db, ctx, "crear", "cuentas", cuenta.id, f"Creo la cuenta {cuenta.nombre}", datos.model_dump())
    db.commit()
    db.refresh(cuenta)
    return cuenta


@router.get("/{cuenta_id}", response_model=CuentaSalida, summary="Ver una cuenta")
def ver(cuenta_id: int, db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("cuentas", "ver"))):
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None:
        raise no_encontrado("La cuenta no existe")
    return cuenta


@router.patch("/{cuenta_id}", response_model=CuentaSalida, summary="Editar cuenta")
def editar(
    cuenta_id: int,
    datos: CuentaActualizar,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("cuentas", "editar")),
):
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None:
        raise no_encontrado("La cuenta no existe")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(cuenta, campo, valor)
    registrar(db, ctx, "editar", "cuentas", cuenta.id, f"Edito la cuenta {cuenta.nombre}", cambios)
    db.commit()
    db.refresh(cuenta)
    return cuenta


@router.delete("/{cuenta_id}", response_model=Mensaje, summary="Desactivar cuenta")
def desactivar(
    cuenta_id: int,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("cuentas", "borrar")),
):
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None:
        raise no_encontrado("La cuenta no existe")
    cuenta.activo = False
    registrar(db, ctx, "desactivar", "cuentas", cuenta.id, f"Desactivo la cuenta {cuenta.nombre}")
    db.commit()
    return Mensaje(mensaje="Cuenta desactivada")
