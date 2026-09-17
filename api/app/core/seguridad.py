"""Contrasenas, tokens de acceso y tokens de refresco."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import config
from app.core.errores import sin_sesion

_LIMITE_BCRYPT = 72


def _a_bytes(clave: str) -> bytes:
    return clave.encode("utf-8")[:_LIMITE_BCRYPT]


def cifrar_clave(clave: str) -> str:
    return bcrypt.hashpw(_a_bytes(clave), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_clave(clave: str, cifrada: str) -> bool:
    if not cifrada:
        return False
    try:
        return bcrypt.checkpw(_a_bytes(clave), cifrada.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def crear_token_acceso(
    usuario_id: int,
    rol: str,
    cuenta_id: int | None,
    finca_id: int | None,
    sesion_id: int,
) -> str:
    expira = ahora() + timedelta(minutes=config.minutos_acceso)
    carga: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol,
        "cuenta": cuenta_id,
        "finca": finca_id,
        "ses": sesion_id,
        "exp": expira,
        "iat": ahora(),
    }
    return jwt.encode(carga, config.jwt_secret, algorithm=config.jwt_algoritmo)


def leer_token_acceso(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algoritmo])
    except JWTError as exc:  # token vencido, firma invalida, etc.
        raise sin_sesion() from exc


def nuevo_refresco() -> tuple[str, str]:
    """Devuelve (token en claro para la cookie, huella que se guarda en la base)."""
    token = secrets.token_urlsafe(48)
    return token, huella(token)


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def codigo_numerico(digitos: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(digitos))
