"""Envio de correo.

Si no hay SMTP configurado, en desarrollo deja el mensaje en el log para poder
probar; en produccion solo avisa que no se envio: el cuerpo puede llevar un codigo
de recuperacion y no debe quedar en los logs.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import config

log = logging.getLogger("avicola.correo")


def enviar(destino: str, asunto: str, cuerpo: str) -> bool:
    if not config.smtp_host or not config.smtp_user:
        if config.es_produccion:
            log.error("Sin SMTP configurado: no se envio el correo '%s' a %s", asunto, destino)
        else:
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
