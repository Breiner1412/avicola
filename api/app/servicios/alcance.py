"""Filtros que garantizan que cada quien solo vea lo de su cuenta y su finca."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, fincas_del_usuario
from app.core.errores import datos_invalidos, no_encontrado, sin_permiso
from app.modelos.organizacion import Finca, Galpon


def cuenta_filtro(ctx: Contexto) -> int | None:
    """Cuenta por la que se deben filtrar las consultas (None = sin filtro)."""
    if not ctx.es_plataforma:
        return ctx.cuenta_id
    return ctx.cuenta_activa_id


def _fincas_permitidas(db: Session, ctx: Contexto) -> list[Finca]:
    """Fincas que ve el usuario; si la peticion escribe, sin las de solo lectura."""
    return [f for f, solo_lectura in fincas_del_usuario(db, ctx.usuario) if not (ctx.escribe and solo_lectura)]


def ids_fincas_visibles(db: Session, ctx: Contexto) -> list[int]:
    return [f.id for f in _fincas_permitidas(db, ctx)]


def fincas_visibles(db: Session, ctx: Contexto) -> list[Finca]:
    return _fincas_permitidas(db, ctx)


def finca_de(db: Session, ctx: Contexto, finca_id: int) -> Finca:
    """Devuelve la finca si el usuario puede verla (o cambiarla, si la peticion escribe)."""
    finca = db.get(Finca, finca_id)
    if finca is None:
        raise no_encontrado("La finca no existe")
    if ctx.es_plataforma:
        return finca
    if finca.cuenta_id != ctx.cuenta_id:
        raise no_encontrado("La finca no existe")
    if finca_id not in ids_fincas_visibles(db, ctx):
        if ctx.escribe and finca_id in [f.id for f, _ in fincas_del_usuario(db, ctx.usuario)]:
            raise sin_permiso("Solo puedes consultar esa finca")
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


def de_la_cuenta(db: Session, modelo, registro_id: int | None, cuenta_id: int | None, que: str, compartido: bool = False):
    """Un registro que llega por id en el cuerpo de la peticion, si es de la cuenta.

    Con compartido=True tambien sirven los del sistema (cuenta_id vacio), como
    razas, tipos de huevo o tipos de sensor. Un id de otra cuenta se trata como
    si no existiera, para no revelar nada.
    """
    if registro_id is None:
        return None
    registro = db.get(modelo, registro_id)
    if registro is not None and (registro.cuenta_id == cuenta_id or (compartido and registro.cuenta_id is None)):
        return registro
    raise datos_invalidos(f"{que} no existe")


def de_la_finca(db: Session, modelo, registro_id: int | None, finca_id: int | None, que: str):
    """Un registro de una finca (galpon, lote...) que llega por id en el cuerpo."""
    if registro_id is None:
        return None
    registro = db.get(modelo, registro_id)
    if registro is None or registro.finca_id != finca_id:
        raise datos_invalidos(f"{que} no existe en esta finca")
    return registro
