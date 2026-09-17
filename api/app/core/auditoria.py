"""Guarda en el registro de cambios lo que hace cada usuario."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.contexto import Contexto
from app.modelos.registro import Auditoria

CAMPOS_OCULTOS = {"clave", "clave_actual", "clave_nueva", "clave_hash", "codigo", "token"}


def limpiar(datos: dict[str, Any] | None) -> dict[str, Any] | None:
    if not datos:
        return None
    return {k: ("***" if k in CAMPOS_OCULTOS else v) for k, v in datos.items()}


def registrar(
    db: Session,
    ctx: Contexto | None,
    accion: str,
    entidad: str,
    entidad_id: int | None = None,
    descripcion: str | None = None,
    datos: dict[str, Any] | None = None,
    cuenta_id: int | None = None,
    finca_id: int | None = None,
    usuario_id: int | None = None,
    usuario_nombre: str | None = None,
    ip: str | None = None,
) -> None:
    """Agrega una linea al registro. Se guarda con el commit de la operacion."""
    db.add(
        Auditoria(
            cuenta_id=cuenta_id if ctx is None else ctx.cuenta_id,
            finca_id=finca_id if ctx is None else (finca_id or ctx.finca_id),
            usuario_id=usuario_id if ctx is None else ctx.usuario.id,
            usuario_nombre=usuario_nombre if ctx is None else ctx.usuario.nombre_completo,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            descripcion=descripcion,
            datos=limpiar(datos),
            ip=ip if ctx is None else ctx.ip,
            creado_en=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
