"""Filtros que garantizan que cada quien solo vea lo de su cuenta y su finca."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, fincas_del_usuario
from app.core.errores import no_encontrado, sin_permiso
from app.modelos.organizacion import Finca, Galpon


def cuenta_filtro(ctx: Contexto) -> int | None:
    """Cuenta por la que se deben filtrar las consultas (None = sin filtro)."""
    if not ctx.es_plataforma:
        return ctx.cuenta_id
    return ctx.cuenta_activa_id


def ids_fincas_visibles(db: Session, ctx: Contexto) -> list[int]:
    return [f.id for f, _ in fincas_del_usuario(db, ctx.usuario)]


def fincas_visibles(db: Session, ctx: Contexto) -> list[Finca]:
    return [f for f, _ in fincas_del_usuario(db, ctx.usuario)]


def finca_de(db: Session, ctx: Contexto, finca_id: int) -> Finca:
    """Devuelve la finca si el usuario puede verla; si no, 404."""
    finca = db.get(Finca, finca_id)
    if finca is None:
        raise no_encontrado("La finca no existe")
    if ctx.es_plataforma:
        return finca
    if finca.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("La finca no existe")
    if finca_id not in ids_fincas_visibles(db, ctx):
        raise sin_permiso("No tienes acceso a esa finca")
    return finca


def galpon_de(db: Session, ctx: Contexto, galpon_id: int) -> Galpon:
    galpon = db.get(Galpon, galpon_id)
    if galpon is None:
        raise no_encontrado("El galpon no existe")
    finca_de(db, ctx, galpon.finca_id)
    if ctx.finca_id is not None and galpon.finca_id != ctx.finca_id:
        raise no_encontrado("El galpon no existe en la finca activa")
    return galpon


def cuenta_objetivo(ctx: Contexto, cuenta_id: int | None) -> int:
    """La cuenta sobre la que se trabaja.

    Para un usuario normal es la suya. El rol de plataforma puede indicarla, o
    se toma la de la finca que tenga elegida.
    """
    if ctx.es_plataforma:
        if cuenta_id is not None:
            return cuenta_id
        if ctx.cuenta_activa_id is not None:
            return ctx.cuenta_activa_id
        raise sin_permiso("Elige primero la finca o la cuenta sobre la que quieres trabajar")
    if cuenta_id is not None and cuenta_id != ctx.cuenta_id:
        raise sin_permiso("No puedes trabajar sobre otra cuenta")
    if ctx.cuenta_id is None:
        raise sin_permiso("Tu usuario no pertenece a ninguna cuenta")
    return ctx.cuenta_id


def existe_codigo_finca(db: Session, cuenta_id: int, codigo: str, excluir: int | None = None) -> bool:
    consulta = select(Finca.id).where(Finca.cuenta_id == cuenta_id, Finca.codigo == codigo)
    if excluir:
        consulta = consulta.where(Finca.id != excluir)
    return db.scalars(consulta).first() is not None
