"""Roles, modulos y permisos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.contexto import Contexto, permisos_de_rol, requiere
from app.core.db import obtener_db
from app.core.demo import bloqueado_en_demo
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


MODULOS_DE_PLATAFORMA = ("cuentas",)


def _cuenta_de_la_matriz(ctx: Contexto, cuenta_id: int | None) -> int | None:
    """Cuenta cuyos permisos se ven o cambian (None = los de fabrica).

    Una empresa siempre trabaja sobre los suyos; la plataforma elige la cuenta
    o, si no indica ninguna, los de fabrica.
    """
    if ctx.es_plataforma:
        return cuenta_id
    if cuenta_id is not None and cuenta_id != ctx.cuenta_id:
        raise sin_permiso("No puedes ver ni cambiar los permisos de otra cuenta")
    return ctx.cuenta_id


@router.get("/permisos", response_model=dict[str, dict[str, dict[str, bool]]], summary="Matriz de permisos")
def matriz(
    cuenta_id: int | None = Query(None, description="Solo para el rol de plataforma"),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("roles", "ver")),
):
    cuenta = _cuenta_de_la_matriz(ctx, cuenta_id)
    roles = db.scalars(select(Rol).order_by(Rol.nivel)).all()
    if not ctx.es_plataforma:
        roles = [r for r in roles if not r.de_plataforma]
    return {rol.clave: permisos_de_rol(db, rol.id, cuenta) for rol in roles}


@router.put(
    "/permisos/{rol_clave}/{modulo_clave}",
    response_model=PermisoSalida,
    summary="Cambiar un permiso",
    dependencies=[Depends(bloqueado_en_demo("cambiar permisos"))],
)
def cambiar(
    rol_clave: str,
    modulo_clave: str,
    datos: PermisoEntrada,
    cuenta_id: int | None = Query(None, description="Solo para el rol de plataforma"),
    db: Session = Depends(obtener_db),
    ctx: Contexto = Depends(requiere("roles", "editar")),
):
    rol = db.scalars(select(Rol).where(Rol.clave == rol_clave)).first()
    modulo = db.scalars(select(Modulo).where(Modulo.clave == modulo_clave)).first()
    if rol is None or modulo is None:
        raise no_encontrado("El rol o el modulo no existe")
    if not ctx.es_plataforma:
        if rol.de_plataforma or modulo.clave in MODULOS_DE_PLATAFORMA:
            raise sin_permiso("Ese permiso solo lo administra la plataforma")
        # Ni el propio rol ni uno superior: evita darse mas permisos o bloquearse
        if rol.nivel <= ctx.usuario.rol.nivel:
            raise sin_permiso("Solo puedes cambiar los permisos de los roles por debajo del tuyo")
    cuenta = _cuenta_de_la_matriz(ctx, cuenta_id)

    permiso = db.scalars(
        select(Permiso).where(
            Permiso.rol_id == rol.id,
            Permiso.modulo_id == modulo.id,
            Permiso.cuenta_id.is_(None) if cuenta is None else Permiso.cuenta_id == cuenta,
        )
    ).first()
    if permiso is None:
        permiso = Permiso(cuenta_id=cuenta, rol_id=rol.id, modulo_id=modulo.id)
        db.add(permiso)

    permiso.ver = datos.ver or datos.crear or datos.editar or datos.borrar
    permiso.crear = datos.crear
    permiso.editar = datos.editar
    permiso.borrar = datos.borrar

    registrar(
        db, ctx, "editar", "permisos", None,
        f"Permisos de {rol.clave} en {modulo.clave}" + (" (de fabrica)" if cuenta is None else ""),
        {**datos.model_dump(), "cuenta_id": cuenta},
    )
    db.commit()
    return PermisoSalida(
        rol=rol.clave, modulo=modulo.clave,
        ver=permiso.ver, crear=permiso.crear, editar=permiso.editar, borrar=permiso.borrar,
    )
