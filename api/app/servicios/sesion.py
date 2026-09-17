"""Creacion y cierre de sesiones."""

from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import config
from app.core.contexto import fincas_del_usuario, permisos_de_rol
from app.core.seguridad import crear_token_acceso, huella, nuevo_refresco
from app.esquemas.auth import FincaResumen, SesionSalida, UsuarioSesion
from app.modelos.acceso import Sesion, Usuario

RUTA_COOKIE = "/api/v1/auth"


def sin_zona(momento: datetime) -> datetime:
    return momento.replace(tzinfo=None)


def ahora_simple() -> datetime:
    return sin_zona(datetime.now(timezone.utc))


def cargar_usuario(db: Session, usuario_id: int) -> Usuario | None:
    return db.scalars(
        select(Usuario)
        .options(joinedload(Usuario.rol), joinedload(Usuario.cuenta))
        .where(Usuario.id == usuario_id)
    ).first()


def abrir_sesion(db: Session, usuario: Usuario, finca_id: int | None, ip: str | None, agente: str | None):
    """Crea la sesion y devuelve (sesion, token de refresco en claro)."""
    token, marca = nuevo_refresco()
    sesion = Sesion(
        usuario_id=usuario.id,
        huella=marca,
        finca_id=finca_id,
        ip=ip,
        agente=(agente or "")[:255] or None,
        expira_en=ahora_simple() + timedelta(days=config.dias_refresco),
        creado_en=ahora_simple(),
    )
    db.add(sesion)
    db.flush()
    return sesion, token


def buscar_sesion(db: Session, token: str) -> Sesion | None:
    sesion = db.scalars(select(Sesion).where(Sesion.huella == huella(token))).first()
    if sesion is None or sesion.revocada_en is not None or sesion.expira_en < ahora_simple():
        return None
    return sesion


def cerrar_sesion(db: Session, sesion: Sesion) -> None:
    sesion.revocada_en = ahora_simple()


def guardar_cookie(respuesta: Response, token: str) -> None:
    respuesta.set_cookie(
        key=config.cookie_refresco,
        value=token,
        httponly=True,
        secure=config.cookie_segura,
        samesite="lax",
        path=RUTA_COOKIE,
        max_age=config.dias_refresco * 86400,
    )


def borrar_cookie(respuesta: Response) -> None:
    respuesta.delete_cookie(key=config.cookie_refresco, path=RUTA_COOKIE)


def armar_respuesta(db: Session, usuario: Usuario, sesion: Sesion) -> SesionSalida:
    fincas = fincas_del_usuario(db, usuario)
    activa = next((f for f, _ in fincas if f.id == sesion.finca_id), None)
    solo_lectura = next((lectura for f, lectura in fincas if f.id == sesion.finca_id), False)

    return SesionSalida(
        token=crear_token_acceso(
            usuario_id=usuario.id,
            rol=usuario.rol.clave,
            cuenta_id=usuario.cuenta_id,
            finca_id=sesion.finca_id,
            sesion_id=sesion.id,
        ),
        expira_en_minutos=config.minutos_acceso,
        usuario=UsuarioSesion(
            id=usuario.id,
            nombres=usuario.nombres,
            apellidos=usuario.apellidos,
            email=usuario.email,
            rol=usuario.rol.clave,
            rol_nombre=usuario.rol.nombre,
            cuenta_id=usuario.cuenta_id,
            cuenta_nombre=usuario.cuenta.nombre if usuario.cuenta else None,
            debe_cambiar_clave=usuario.debe_cambiar_clave,
        ),
        finca_activa=(
            FincaResumen(
                id=activa.id,
                codigo=activa.codigo,
                nombre=activa.nombre,
                municipio=activa.municipio,
                solo_lectura=solo_lectura,
            )
            if activa
            else None
        ),
        fincas=[
            FincaResumen(
                id=f.id, codigo=f.codigo, nombre=f.nombre, municipio=f.municipio, solo_lectura=lectura
            )
            for f, lectura in fincas
        ],
        permisos=permisos_de_rol(db, usuario.rol_id),
    )
