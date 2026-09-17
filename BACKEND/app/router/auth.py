from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.router.dependencies import authenticate_user
from app.schemas.auth import ResponseLoggin
from core.security import create_access_token
from core.database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.crud import users as crud_users
from core.email import send_password_reset_email
from core.rate_limit import (
    login_limiter,
    login_email_limiter,
    forgot_email_limiter,
    forgot_ip_limiter,
    reset_limiter,
    reset_ip_limiter,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

MIN_PASSWORD_LENGTH = 8


def _client_ip(request: Request) -> str:
    # No se lee X-Forwarded-For directamente (el cliente lo puede falsificar).
    # Si hay un proxy delante, arrancar uvicorn/gunicorn con --forwarded-allow-ips
    # para que request.client.host ya traiga la IP real.
    return request.client.host if request.client else "desconocida"


@router.post("/token", response_model=ResponseLoggin)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    email_key = form_data.username.lower()
    limiter_key = f"{email_key}|{_client_ip(request)}"
    if login_limiter.is_blocked(limiter_key) or login_email_limiter.is_blocked(email_key):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.",
        )

    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        login_limiter.hit(limiter_key)
        login_email_limiter.hit(email_key)
        raise HTTPException(
            status_code=401,
            detail="Datos incorrectos en email o password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.estado:
        raise HTTPException(status_code=403, detail="Usuario inactivo, no autorizado")

    # consultar estado del rol (activo o inactivo)
    sentencia = text("""
                    SELECT estado
                    FROM roles
                    WHERE id_rol = :rol 
                    """)
    res = db.execute(sentencia, {"rol": user.id_rol}).mappings().first()

    if not res:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    # Si el estado del rol es inactivo
    if res['estado'] == 0:
        raise HTTPException(status_code=403, detail="Rol inactivo")

    login_limiter.reset(limiter_key)

    data = {"sub": str(user.id_usuario), "rol": user.id_rol}
    access_token = create_access_token(data)

    return ResponseLoggin(
        user=user,
        access_token=access_token
    )


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = payload.email.lower()
    ip = _client_ip(request)
    mensaje = {
        "message": "Si el correo existe, recibirás un código de 6 dígitos para recuperar tu contraseña"
    }

    if forgot_ip_limiter.is_blocked(ip):
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Espera unos minutos e inténtalo de nuevo.",
        )
    forgot_ip_limiter.hit(ip)

    # Si ya se pidieron varios códigos para este correo, se responde igual
    # (sin revelar nada) pero no se envían más correos.
    if forgot_email_limiter.is_blocked(email):
        return mensaje
    forgot_email_limiter.hit(email)

    try:
        user = crud_users.get_user_by_email(db, payload.email)

        if user:
            reset_token = crud_users.save_reset_token(db, payload.email)

            if reset_token:
                reset_limiter.reset(email)
                email_sent = send_password_reset_email(payload.email, reset_token)

                if email_sent:
                    logger.info(f"Código de recuperación enviado a: {payload.email}")
                else:
                    logger.warning(f"No se pudo enviar email a: {payload.email}")
        return mensaje
    except Exception as e:
        logger.error(f"Error en forgot_password: {e}")
        raise HTTPException(status_code=500, detail="Error al procesar la solicitud")


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = payload.email.lower()
    ip = _client_ip(request)

    if reset_ip_limiter.is_blocked(ip) or reset_limiter.is_blocked(email):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Solicita un nuevo código más tarde.",
        )

    if not payload.token.isdigit() or len(payload.token) != 6:
        raise HTTPException(
            status_code=400,
            detail="El código debe tener exactamente 6 dígitos"
        )

    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
        )

    try:
        success = crud_users.update_password_with_token(
            db,
            payload.email,
            payload.token,
            payload.new_password
        )
    except Exception as e:
        logger.error(f"Error en reset_password: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al restablecer la contraseña"
        )

    if not success:
        reset_ip_limiter.hit(ip)
        intentos = reset_limiter.hit(email)
        if intentos >= reset_limiter.max_attempts:
            # Demasiados códigos erróneos: se invalida el código actual
            try:
                crud_users.clear_reset_token(db, payload.email)
            except Exception as e:
                logger.error(f"No se pudo invalidar el código de {payload.email}: {e}")
            raise HTTPException(
                status_code=400,
                detail="Demasiados intentos fallidos. Solicita un nuevo código."
            )
        raise HTTPException(
            status_code=400,
            detail="Código inválido o expirado"
        )

    reset_limiter.reset(email)
    return {
        "message": "Contraseña actualizada exitosamente"
    }
