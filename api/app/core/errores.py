"""Errores de la API con codigo y mensaje en espanol."""

from fastapi import HTTPException, status


class ErrorApi(HTTPException):
    def __init__(self, codigo_http: int, codigo: str, mensaje: str, detalles: dict | None = None):
        super().__init__(status_code=codigo_http, detail={"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}})


def no_encontrado(mensaje: str = "No se encontro el registro") -> ErrorApi:
    return ErrorApi(status.HTTP_404_NOT_FOUND, "no_encontrado", mensaje)


def datos_invalidos(mensaje: str, detalles: dict | None = None) -> ErrorApi:
    return ErrorApi(status.HTTP_400_BAD_REQUEST, "datos_invalidos", mensaje, detalles)


def conflicto(mensaje: str) -> ErrorApi:
    return ErrorApi(status.HTTP_409_CONFLICT, "conflicto", mensaje)


def sin_sesion(mensaje: str = "La sesion no es valida o expiro") -> ErrorApi:
    return ErrorApi(status.HTTP_401_UNAUTHORIZED, "sin_sesion", mensaje)


def sin_permiso(mensaje: str = "No tienes permiso para esta accion") -> ErrorApi:
    return ErrorApi(status.HTTP_403_FORBIDDEN, "sin_permiso", mensaje)


def demasiados_intentos(mensaje: str, segundos: int) -> ErrorApi:
    return ErrorApi(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "demasiados_intentos",
        mensaje,
        {"reintentar_en_segundos": segundos},
    )
