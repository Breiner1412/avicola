"""Cliente de Redis con respaldo en memoria si no esta disponible."""

import threading
import time

from app.core.config import config

try:  # redis es opcional: sin el, se usa memoria
    import redis as _redis
except ImportError:  # pragma: no cover
    _redis = None


class _Memoria:
    """Contador en memoria para desarrollo o si Redis no responde."""

    def __init__(self) -> None:
        self._datos: dict[str, tuple[int, float]] = {}
        self._candado = threading.Lock()

    def incr(self, clave: str, ventana: int) -> tuple[int, int]:
        ahora = time.time()
        with self._candado:
            valor, vence = self._datos.get(clave, (0, 0.0))
            if vence <= ahora:
                valor, vence = 0, ahora + ventana
            valor += 1
            self._datos[clave] = (valor, vence)
            return valor, int(vence - ahora)

    def borrar(self, clave: str) -> None:
        with self._candado:
            self._datos.pop(clave, None)


_memoria = _Memoria()
_cliente = None


def cliente():
    """Devuelve el cliente de Redis, o None si no hay."""
    global _cliente
    if _cliente is not None:
        return _cliente
    if not config.redis_url or _redis is None:
        return None
    try:
        _cliente = _redis.from_url(config.redis_url, decode_responses=True, socket_timeout=2)
        _cliente.ping()
    except Exception:  # noqa: BLE001 - si falla, seguimos en memoria
        _cliente = None
    return _cliente


def contar(clave: str, ventana: int) -> tuple[int, int]:
    """Suma uno a la clave y devuelve (total, segundos que faltan para reiniciar)."""
    red = cliente()
    if red is None:
        return _memoria.incr(clave, ventana)
    try:
        tubo = red.pipeline()
        tubo.incr(clave)
        tubo.ttl(clave)
        total, ttl = tubo.execute()
        if ttl is None or ttl < 0:
            red.expire(clave, ventana)
            ttl = ventana
        return int(total), int(ttl)
    except Exception:  # noqa: BLE001
        return _memoria.incr(clave, ventana)


def reiniciar(clave: str) -> None:
    red = cliente()
    if red is None:
        _memoria.borrar(clave)
        return
    try:
        red.delete(clave)
    except Exception:  # noqa: BLE001
        _memoria.borrar(clave)
