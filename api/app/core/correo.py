"""Envio de correo. Si no hay SMTP configurado, solo deja el mensaje en el log."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import config

log = logging.getLogger("avisena.correo")


def enviar(destino: str, asunto: str, cuerpo: str) -> bool:
    if not config.smtp_host or not config.smtp_user:
        log.warning("Sin SMTP configurado. Correo para %s: %s | %s", destino, asunto, cuerpo)
        return False

    mensaje = EmailMessage()
    mensaje["From"] = config.smtp_desde or config.smtp_user
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as servidor:
            servidor.starttls()
            servidor.login(config.smtp_user, config.smtp_password)
            servidor.send_message(mensaje)
        return True
    except Exception:  # noqa: BLE001 - el flujo no debe romperse por el correo
        log.exception("No se pudo enviar el correo a %s", destino)
        return False
