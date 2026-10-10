"""Limite de intentos (inicio de sesion y recuperacion de contrasena)."""

from app.core.cache import contar, leer, reiniciar
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

    def revisar(self, identificador: str) -> None:
        """Corta si ya se llego al maximo, sin contar este intento."""
        total, faltan = leer(self._clave(identificador))
        if total >= self.maximo:
            raise demasiados_intentos(self.mensaje, faltan)

    def sumar(self, identificador: str) -> None:
        """Cuenta un fallo sin cortar (el corte llega en el siguiente revisar)."""
        contar(self._clave(identificador), self.ventana)

    def limpiar(self, identificador: str) -> None:
        reiniciar(self._clave(identificador))


# Inicio de sesion: solo cuentan los intentos fallidos.
# - correo + conexion: el limite estricto; quien se equivoca no bloquea a otros
# - correo: un tope alto contra ataques repartidos entre muchas conexiones
# - conexion: quien prueba muchos correos desde el mismo lugar
login_email_ip = Limite("login_email_ip", 8, 900, "Demasiados intentos con este correo. Espera unos minutos.")
login_email = Limite("login_email", 100, 900, "Demasiados intentos con este correo. Espera unos minutos.")
login_ip = Limite("login_ip", 30, 900, "Demasiados intentos desde esta conexion. Espera unos minutos.")
# Ingresos correctos por conexion: cada uno cuesta un bcrypt y deja una sesion y una
# linea en el registro (que no se puede depurar), asi que tambien tienen tope
ingresos_ip = Limite("ingresos_ip", 60, 900, "Demasiados ingresos desde esta conexion. Espera unos minutos.")
recuperar_email = Limite("recuperar_email", 5, 3600, "Ya pediste varios codigos. Intenta mas tarde.")
recuperar_ip = Limite("recuperar_ip", 15, 3600, "Demasiadas solicitudes desde esta conexion.")
restablecer = Limite("restablecer", 10, 900, "Demasiados intentos con el codigo. Espera unos minutos.")


# Limites generales por usuario (o por conexion, si no hay sesion), por minuto
escrituras = Limite("escrituras", 120, 60, "Demasiados cambios seguidos. Espera un momento.")
subidas = Limite("subidas", 10, 60, "Demasiados archivos seguidos. Espera un momento.")
descargas = Limite("descargas", 20, 60, "Demasiadas descargas seguidas. Espera un momento.")

METODOS_DE_ESCRITURA = ("POST", "PUT", "PATCH", "DELETE")


def limites_de_peticion(metodo: str, ruta: str) -> list[Limite]:
    """Que limites generales aplican a una peticion."""
    aplican: list[Limite] = []
    if metodo in METODOS_DE_ESCRITURA:
        aplican.append(escrituras)
    if ruta.endswith("/importacion/analizar"):
        aplican.append(subidas)
    if ruta.endswith("/reportes/csv"):
        aplican.append(descargas)
    return aplican
