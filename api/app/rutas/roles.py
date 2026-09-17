"""Roles, modulos y permisos."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, permisos_de_rol, requiere
from app.core.db import obtener_db
from app.core.errores import no_encontrado, sin_permiso
from app.esquemas.usuarios import ModuloSalida, PermisoEntrada, PermisoSalida, RolSalida
from app.modelos.acceso import Modulo, Permiso, Rol

router = APIRouter(tags=["Roles y permisos"])


@router.get("/roles", response_model=list[RolSalida], summary="Roles disponibles")
def listar_roles(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("roles", "ver"))):
    consulta = select(Rol).order_by(Rol.nivel)
    if not ctx.es_plataforma:
        consulta = consulta.where(Rol.de_plataforma.is_(False), Rol.nivel >= ctx.usuario.rol.nivel)
    return db.scalars(consulta).all()


@router.get("/modulos", response_model=list[ModuloSalida], summary="Modulos del sistema")
def listar_modulos(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("roles", "ver"))):
    return db.scalars(select(Modulo).order_by(Modulo.orden)).all()


@router.get("/permisos", response_model=dict[str, dict[str, dict[str, bool]]], summary="Matriz de permisos")
def matriz(db: Session = Depends(obtener_db), ctx: Contexto = Depends(requiere("roles", "ver"))):
    roles = db.scalars(select(Rol).order_by(Rol.nivel)).all()
    if not ctx.es_plataforma:
        roles = [r for r in roles if not r.de_plataforma]
    return {rol.clave: permisos_de_rol(db, rol.id) for rol in roles}


@router.put("/permisos/{rol_clave}/{modulo_clave}", response_model=PermisoSalida, summary="Cambiar un permiso")
def cambiar(
    rol_clave: str,
    modulo_clave: str,
    datos: PermisoEntrada,
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("roles", "editar")),
):
    rol = db.scalars(select(Rol).where(Rol.clave == rol_clave)).first()
    modulo = db.scalars(select(Modulo).where(Modulo.clave == modulo_clave)).first()
    if rol is None or modulo is None:
        raise no_encontrado("El rol o el modulo no existe")
    if rol.de_plataforma and not ctx.es_plataforma:
        raise sin_permiso("No puedes cambiar los permisos de ese rol")
    if not ctx.es_plataforma and rol.nivel < ctx.usuario.rol.nivel:
        raise sin_permiso("No puedes cambiar los permisos de un rol superior al tuyo")

    permiso = db.get(Permiso, {"rol_id": rol.id, "modulo_id": modulo.id})
    if permiso is None:
        permiso = Permiso(rol_id=rol.id, modulo_id=modulo.id)
        db.add(permiso)

    permiso.ver = datos.ver or datos.crear or datos.editar or datos.borrar
    permiso.crear = datos.crear
    permiso.editar = datos.editar
    permiso.borrar = datos.borrar

    registrar(
        db, ctx, "editar", "permisos", None,
        f"Permisos de {rol.clave} en {modulo.clave}",
        datos.model_dump(),
    )
    db.commit()
    return PermisoSalida(
        rol=rol.clave, modulo=modulo.clave,
        ver=permiso.ver, crear=permiso.crear, editar=permiso.editar, borrar=permiso.borrar,
    )
