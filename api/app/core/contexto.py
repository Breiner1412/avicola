"""Quien hace la peticion, desde que cuenta y en que finca."""

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.db import obtener_db
from app.core.errores import datos_invalidos, sin_permiso, sin_sesion
from app.core.seguridad import leer_token_acceso
from app.modelos.acceso import Modulo, Permiso, Sesion, Usuario, UsuarioFinca
from app.modelos.organizacion import Finca

ROLES_TODA_LA_CUENTA = ("plataforma", "propietario", "administrador")


@dataclass
class Contexto:
    usuario: Usuario
    rol: str
    cuenta_id: int | None
    finca_id: int | None
    solo_lectura: bool
    ip: str | None
    sesion_id: int | None = None

    @property
    def es_plataforma(self) -> bool:
        return self.rol == "plataforma"

    @property
    def ve_toda_la_cuenta(self) -> bool:
        return self.rol in ROLES_TODA_LA_CUENTA


def ip_de(peticion: Request) -> str | None:
    reenviada = peticion.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return peticion.client.host if peticion.client else None


def _token_de(peticion: Request) -> str:
    cabecera = peticion.headers.get("authorization", "")
    if not cabecera.lower().startswith("bearer "):
        raise sin_sesion("Falta el token de acceso")
    return cabecera[7:].strip()


def fincas_del_usuario(db: Session, usuario: Usuario) -> list[tuple[Finca, bool]]:
    """Fincas a las que entra el usuario, con la marca de solo lectura."""
    if usuario.rol.clave == "plataforma":
        fincas = db.scalars(select(Finca).where(Finca.activo.is_(True)).order_by(Finca.nombre)).all()
        return [(f, False) for f in fincas]

    if usuario.rol.clave in ROLES_TODA_LA_CUENTA:
        fincas = db.scalars(
            select(Finca)
            .where(Finca.cuenta_id == usuario.cuenta_id, Finca.activo.is_(True))
            .order_by(Finca.nombre)
        ).all()
        return [(f, False) for f in fincas]

    filas = db.execute(
        select(Finca, UsuarioFinca.solo_lectura)
        .join(UsuarioFinca, UsuarioFinca.finca_id == Finca.id)
        .where(UsuarioFinca.usuario_id == usuario.id, Finca.activo.is_(True))
        .order_by(UsuarioFinca.solo_lectura, Finca.nombre)
    ).all()
    return [(finca, bool(solo_lectura)) for finca, solo_lectura in filas]


def contexto_actual(
    peticion: Request,
    db: Session = Depends(obtener_db),
    x_finca_id: str | None = Header(default=None, alias="X-Finca-Id"),
) -> Contexto:
    datos = leer_token_acceso(_token_de(peticion))

    usuario = db.scalars(
        select(Usuario).options(joinedload(Usuario.rol)).where(Usuario.id == int(datos.get("sub", 0)))
    ).first()
    if usuario is None or not usuario.activo:
        raise sin_sesion("El usuario no existe o esta inactivo")

    sesion_id = datos.get("ses")
    if sesion_id:
        sesion = db.get(Sesion, int(sesion_id))
        if sesion is None or sesion.revocada_en is not None or sesion.expira_en < datetime.now(timezone.utc).replace(tzinfo=None):
            raise sin_sesion("La sesion se cerro. Vuelve a entrar.")

    finca_id = datos.get("finca")
    if x_finca_id:
        try:
            finca_id = int(x_finca_id)
        except ValueError as exc:
            raise datos_invalidos("La finca indicada no es valida") from exc

    solo_lectura = False
    if finca_id is not None:
        permitidas = {f.id: lectura for f, lectura in fincas_del_usuario(db, usuario)}
        if finca_id not in permitidas:
            raise sin_permiso("No tienes acceso a esa finca")
        solo_lectura = permitidas[finca_id]

    return Contexto(
        usuario=usuario,
        rol=usuario.rol.clave,
        cuenta_id=usuario.cuenta_id,
        finca_id=finca_id,
        solo_lectura=solo_lectura,
        ip=ip_de(peticion),
        sesion_id=int(sesion_id) if sesion_id else None,
    )


def permisos_de_rol(db: Session, rol_id: int) -> dict[str, dict[str, bool]]:
    filas = db.execute(
        select(Modulo.clave, Permiso.ver, Permiso.crear, Permiso.editar, Permiso.borrar)
        .join(Permiso, Permiso.modulo_id == Modulo.id)
        .where(Permiso.rol_id == rol_id)
        .order_by(Modulo.orden)
    ).all()
    return {
        clave: {"ver": bool(ver), "crear": bool(crear), "editar": bool(editar), "borrar": bool(borrar)}
        for clave, ver, crear, editar, borrar in filas
        if ver or crear or editar or borrar
    }


def tiene_permiso(db: Session, rol_id: int, modulo: str, accion: str) -> bool:
    columna = {"ver": Permiso.ver, "crear": Permiso.crear, "editar": Permiso.editar, "borrar": Permiso.borrar}[accion]
    valor = db.execute(
        select(columna).join(Modulo, Permiso.modulo_id == Modulo.id).where(Permiso.rol_id == rol_id, Modulo.clave == modulo)
    ).scalar_one_or_none()
    return bool(valor)


def requiere(modulo: str, accion: str = "ver", con_finca: bool = False):
    """Dependencia que exige un permiso y, si se pide, tener una finca elegida."""

    def dependencia(
        ctx: Contexto = Depends(contexto_actual),
        db: Session = Depends(obtener_db),
    ) -> Contexto:
        if accion != "ver" and ctx.solo_lectura:
            raise sin_permiso("Solo puedes consultar esta finca")
        if not tiene_permiso(db, ctx.usuario.rol_id, modulo, accion):
            raise sin_permiso(f"Tu rol no puede {accion} en {modulo}")
        if con_finca and ctx.finca_id is None:
            raise datos_invalidos("Primero elige la finca en la que vas a trabajar")
        return ctx

    return dependencia
