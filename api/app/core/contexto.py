"""Quien hace la peticion, desde que cuenta y en que finca."""

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.db import obtener_db
from app.core.errores import datos_invalidos, sin_permiso, sin_sesion
from app.core.seguridad import leer_token_acceso
from app.modelos.acceso import Modulo, Permiso, Sesion, Usuario, UsuarioFinca
from app.modelos.organizacion import Finca

ROLES_TODA_LA_CUENTA = ("plataforma", "propietario", "administrador")
METODOS_DE_LECTURA = ("GET", "HEAD", "OPTIONS")


@dataclass
class Contexto:
    usuario: Usuario
    rol: str
    cuenta_id: int | None
    finca_id: int | None
    solo_lectura: bool
    ip: str | None
    sesion_id: int | None = None
    # Cuenta sobre la que se esta trabajando (la del usuario o, para el rol de
    # plataforma, la duena de la finca elegida)
    cuenta_activa_id: int | None = None
    # La peticion cambia datos (no es GET): las fincas de solo lectura no cuentan
    escribe: bool = True

    @property
    def es_plataforma(self) -> bool:
        return self.rol == "plataforma"

    @property
    def ve_toda_la_cuenta(self) -> bool:
        return self.rol in ROLES_TODA_LA_CUENTA


def ip_de(peticion: Request) -> str | None:
    """IP de quien hace la peticion.

    No se lee X-Forwarded-For aqui: su primer valor lo escribe el cliente y se puede
    falsificar. Uvicorn ya lo resuelve con --proxy-headers, confiando solo en los
    proxies de FORWARDED_ALLOW_IPS (Caddy y la web, en la red interna de Docker).
    """
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
        select(Usuario)
        .options(joinedload(Usuario.rol), joinedload(Usuario.cuenta))
        .where(Usuario.id == int(datos.get("sub", 0)))
    ).first()
    if usuario is None or not usuario.activo:
        raise sin_sesion("El usuario no existe o esta inactivo")
    if usuario.cuenta is not None and not usuario.cuenta.activo:
        raise sin_sesion("La cuenta esta inactiva. Habla con el administrador.")

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
    cuenta_activa_id = usuario.cuenta_id
    if finca_id is not None:
        permitidas = {f.id: (lectura, f.cuenta_id) for f, lectura in fincas_del_usuario(db, usuario)}
        if finca_id not in permitidas:
            raise sin_permiso("No tienes acceso a esa finca")
        solo_lectura, cuenta_activa_id = permitidas[finca_id]

    return Contexto(
        usuario=usuario,
        rol=usuario.rol.clave,
        cuenta_id=usuario.cuenta_id,
        finca_id=finca_id,
        solo_lectura=solo_lectura,
        ip=ip_de(peticion),
        sesion_id=int(sesion_id) if sesion_id else None,
        cuenta_activa_id=cuenta_activa_id,
        escribe=peticion.method not in METODOS_DE_LECTURA,
    )


def _alcance(cuenta_id: int | None):
    """Permisos de fabrica mas los propios de la cuenta (si la hay)."""
    if cuenta_id is None:
        return Permiso.cuenta_id.is_(None)
    return or_(Permiso.cuenta_id.is_(None), Permiso.cuenta_id == cuenta_id)


def permisos_de_rol(db: Session, rol_id: int, cuenta_id: int | None = None) -> dict[str, dict[str, bool]]:
    """Matriz de un rol para una cuenta: lo de la cuenta manda sobre lo de fabrica."""
    filas = db.execute(
        select(Modulo.clave, Permiso.ver, Permiso.crear, Permiso.editar, Permiso.borrar)
        .join(Permiso, Permiso.modulo_id == Modulo.id)
        .where(Permiso.rol_id == rol_id, _alcance(cuenta_id))
        # Primero los de fabrica y despues los de la cuenta, que los reemplazan
        .order_by(Permiso.cuenta_id.is_not(None), Modulo.orden)
    ).all()
    matriz: dict[str, dict[str, bool]] = {}
    for clave, ver, crear, editar, borrar in filas:
        matriz[clave] = {"ver": bool(ver), "crear": bool(crear), "editar": bool(editar), "borrar": bool(borrar)}
    return {clave: acciones for clave, acciones in matriz.items() if any(acciones.values())}


def tiene_permiso(db: Session, rol_id: int, modulo: str, accion: str, cuenta_id: int | None = None) -> bool:
    columna = {"ver": Permiso.ver, "crear": Permiso.crear, "editar": Permiso.editar, "borrar": Permiso.borrar}[accion]
    valor = db.execute(
        select(columna)
        .join(Modulo, Permiso.modulo_id == Modulo.id)
        .where(Permiso.rol_id == rol_id, Modulo.clave == modulo, _alcance(cuenta_id))
        .order_by(Permiso.cuenta_id.is_(None))
        .limit(1)
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
        if not tiene_permiso(db, ctx.usuario.rol_id, modulo, accion, ctx.cuenta_id):
            raise sin_permiso(f"Tu rol no puede {accion} en {modulo}")
        if con_finca and ctx.finca_id is None:
            raise datos_invalidos("Primero elige la finca en la que vas a trabajar")
        return ctx

    return dependencia


def solo_plataforma(ctx: Contexto = Depends(contexto_actual)) -> Contexto:
    """Dependencia para lo que administra todo el sistema (cuentas, empresas).

    No depende de la matriz de permisos: ninguna empresa puede darse este acceso.
    """
    if not ctx.es_plataforma:
        raise sin_permiso("Solo el administrador de la plataforma puede hacer esto")
    return ctx
