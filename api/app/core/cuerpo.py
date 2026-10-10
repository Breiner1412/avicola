"""Tope al tamano de lo que se envia a la API.

Caddy ya corta los cuerpos grandes, pero la API tambien se alcanza directo desde la red
de Docker (otros contenedores de la red proxy). Este middleware ASGI rechaza con 413:
- de entrada, si Content-Length pasa del tope;
- mientras se recibe, si el cuerpo (por ejemplo, enviado por partes) lo pasa.
"""

import json

from app.core.errores import ErrorApi

MAX_IMPORTACION = 6 * 1024 * 1024  # el Excel admite 5 MB, mas los separadores del formulario
MAX_GENERAL = 1 * 1024 * 1024
MENSAJE = "Lo que enviaste es demasiado grande"


def tope_para(ruta: str) -> int:
    return MAX_IMPORTACION if ruta.endswith("/importacion/analizar") else MAX_GENERAL


class CuerpoDemasiadoGrande(ErrorApi):
    def __init__(self) -> None:
        super().__init__(413, "demasiado_grande", MENSAJE)


class LimiteDeCuerpo:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        tope = tope_para(scope.get("path", ""))
        declarado = dict(scope.get("headers") or []).get(b"content-length", b"")
        if declarado.isdigit() and int(declarado) > tope:
            return await _responder_413(send)

        recibido = 0

        async def recibir():
            nonlocal recibido
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                recibido += len(mensaje.get("body", b""))
                if recibido > tope:
                    # FastAPI convierte esta excepcion en la respuesta 413
                    raise CuerpoDemasiadoGrande()
            return mensaje

        return await self.app(scope, recibir, send)


async def _responder_413(send) -> None:
    cuerpo = json.dumps({"detail": {"codigo": "demasiado_grande", "mensaje": MENSAJE, "detalles": {}}}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(cuerpo)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": cuerpo})
