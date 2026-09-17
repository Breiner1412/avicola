"""
Limitador de intentos sencillo en memoria.

Sirve para frenar ataques de fuerza bruta en login y recuperación de contraseña.
Nota: al ser en memoria, cada worker de gunicorn lleva su propio conteo.
Si en el futuro se usan varios servidores, conviene moverlo a Redis.
"""
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def _clean(self, key: str, now: float) -> deque:
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._clean(key, time.monotonic())) >= self.max_attempts

    def hit(self, key: str) -> int:
        """Registra un intento y devuelve cuántos lleva en la ventana."""
        with self._lock:
            now = time.monotonic()
            q = self._clean(key, now)
            q.append(now)
            return len(q)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


# 10 intentos fallidos de login cada 15 minutos por email+IP
login_limiter = RateLimiter(max_attempts=10, window_seconds=15 * 60)
# 30 intentos fallidos por email (desde cualquier IP) cada 15 minutos
login_email_limiter = RateLimiter(max_attempts=30, window_seconds=15 * 60)
# 3 solicitudes de código cada 15 minutos por email y 10 por IP
forgot_email_limiter = RateLimiter(max_attempts=3, window_seconds=15 * 60)
forgot_ip_limiter = RateLimiter(max_attempts=10, window_seconds=15 * 60)
# 5 códigos erróneos por email: al llegar al límite se invalida el código
reset_limiter = RateLimiter(max_attempts=5, window_seconds=60 * 60)
reset_ip_limiter = RateLimiter(max_attempts=20, window_seconds=60 * 60)
