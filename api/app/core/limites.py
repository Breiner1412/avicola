"""Limite de intentos (inicio de sesion y recuperacion de contrasena)."""

from app.core.cache import contar, reiniciar
from app.core.errores import demasiados_intentos


class Limite:
    def __init__(self, nombre: str, maximo: int, ventana_segundos: int, mensaje: str):
        self.nombre = nombre
        self.maximo = maximo
        self.ventana = ventana_segundos
        self.mensaje = mensaje

    def _clave(self, identificador: str) -> str:
        return f"limite:{self.nombre}:{identificador.lower()}"

    def registrar(self, identificador: str) -> None:
        """Cuenta un intento y corta si se paso del maximo."""
        total, faltan = contar(self._clave(identificador), self.ventana)
        if total > self.maximo:
            raise demasiados_intentos(self.mensaje, faltan)

    def limpiar(self, identificador: str) -> None:
        reiniciar(self._clave(identificador))


login_email = Limite("login_email", 8, 900, "Demasiados intentos con este correo. Espera unos minutos.")
login_ip = Limite("login_ip", 30, 900, "Demasiados intentos desde esta conexion. Espera unos minutos.")
recuperar_email = Limite("recuperar_email", 5, 3600, "Ya pediste varios codigos. Intenta mas tarde.")
recuperar_ip = Limite("recuperar_ip", 15, 3600, "Demasiadas solicitudes desde esta conexion.")
restablecer = Limite("restablecer", 10, 900, "Demasiados intentos con el codigo. Espera unos minutos.")
