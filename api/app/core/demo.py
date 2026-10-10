"""Limites de la demo publica (DEMO=true).

Los usuarios de la demo comparten la misma clave publicada, asi que nada de lo que
haga uno puede dejar a los demas sin entrar ni cambiar como funciona la demo.
Lo demas (lotes, ventas, inventario...) se puede usar libremente y se reinicia
cada noche.
"""

from app.core.config import config
from app.core.errores import ErrorApi


def no_en_demo(que: str) -> None:
    """Corta la peticion si se esta en la demo."""
    if config.demo:
        raise ErrorApi(403, "demo", f"En la demo no se puede {que}. Los datos se reinician cada noche.")


def bloqueado_en_demo(que: str):
    """Dependencia para rutas que la demo no permite."""

    def dependencia() -> None:
        no_en_demo(que)

    return dependencia
