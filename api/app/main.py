"""Aplicacion FastAPI de Avícola."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import limites
from app.core.cache import cliente as cliente_redis
from app.core.config import config
from app.core.contexto import ip_de
from app.core.db import motor
from app.core.errores import ErrorApi
from app.core.seguridad import leer_token_acceso
from app.rutas import (
    alertas,
    auth,
    aves,
    cuentas,
    fincas,
    galpones,
    importacion,
    inventario,
    movimientos,
    panel,
    produccion,
    registro,
    reportes,
    roles,
    sanidad,
    sensores,
    trabajo,
    usuarios,
    ventas,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("avicola")

PREFIJO = "/api/v1"

@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    # En produccion los limites de intentos deben ser compartidos entre workers:
    # sin Redis cada worker llevaria su propia cuenta
    if config.es_produccion and cliente_redis() is None:
        raise RuntimeError("En produccion hace falta Redis (REDIS_URL) para los limites de intentos")
    yield


app = FastAPI(
    lifespan=ciclo_de_vida,
    title="Avícola",
    description="API de gestion de granjas avicolas (multi finca y multi cuenta).",
    version="2.0.0",
    # En produccion no se publica la documentacion ni el esquema de la API
    docs_url=None if config.es_produccion else "/docs",
    openapi_url=None if config.es_produccion else "/openapi.json",
    redoc_url=None,
)


# Orden de los middlewares: el primero que se registra queda mas adentro. El limitador
# va primero para que sus respuestas 429 tambien pasen por las cabeceras de seguridad
# y por la captura de errores; CORS (add_middleware, al final) envuelve todo.
@app.middleware("http")
async def limitar_peticiones(peticion: Request, siguiente):
    """Tope general de cambios, subidas y descargas por usuario o por conexion."""
    aplican = limites.limites_de_peticion(peticion.method, peticion.url.path)
    if aplican:
        quien = _quien_pide(peticion)
        try:
            for limite in aplican:
                limite.registrar(quien)
        except ErrorApi as error:
            espera = (error.detail.get("detalles") or {}).get("reintentar_en_segundos")
            cabeceras = {"Retry-After": str(espera)} if espera else None
            return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=cabeceras)
    return await siguiente(peticion)


def _quien_pide(peticion: Request) -> str:
    """El usuario del token (sin ir a la base) o, si no hay sesion valida, la conexion."""
    cabecera = peticion.headers.get("authorization", "")
    if cabecera.lower().startswith("bearer "):
        try:
            return f"usuario:{leer_token_acceso(cabecera[7:].strip()).get('sub')}"
        except ErrorApi:
            pass
    return f"ip:{ip_de(peticion)}"


@app.middleware("http")
async def capturar_errores(peticion: Request, siguiente):
    """Ningun error interno sale con detalles de SQL ni rompe el CORS."""
    try:
        return await siguiente(peticion)
    except Exception:  # noqa: BLE001
        log.exception("Error no controlado en %s %s", peticion.method, peticion.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"codigo": "error_interno", "mensaje": "Ocurrio un error inesperado", "detalles": {}},
        )


@app.middleware("http")
async def cabeceras_de_seguridad(peticion: Request, siguiente):
    """La API responde JSON: que el navegador no lo interprete como otra cosa ni lo enmarque."""
    respuesta = await siguiente(peticion)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
    respuesta.headers.setdefault("Cache-Control", "no-store")
    return respuesta


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.lista_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validacion(peticion: Request, error: RequestValidationError):
    campos = {}
    for detalle in error.errors():
        ruta = ".".join(str(p) for p in detalle["loc"][1:]) or "cuerpo"
        campos[ruta] = detalle.get("msg", "valor invalido")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"codigo": "datos_invalidos", "mensaje": "Revisa los datos enviados", "detalles": campos},
    )


@app.exception_handler(IntegrityError)
async def conflicto_en_la_base(peticion: Request, error: IntegrityError):
    """Un indice unico freno un dato repetido (por ejemplo, dos clics a la vez)."""
    log.warning("Conflicto de integridad en %s %s: %s", peticion.method, peticion.url.path, error.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": {"codigo": "conflicto", "mensaje": "Ese cambio choca con otro que se hizo al mismo tiempo. Recarga e intenta de nuevo.", "detalles": {}}},
    )


@app.exception_handler(Exception)
async def error_general(peticion: Request, error: Exception):
    log.exception("Error no controlado en %s %s", peticion.method, peticion.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"codigo": "error_interno", "mensaje": "Ocurrio un error inesperado", "detalles": {}},
    )


for modulo in (
    auth, panel, cuentas, fincas, galpones, usuarios, roles,
    inventario, movimientos, aves, produccion, sanidad, ventas, importacion,
    trabajo, sensores, alertas, reportes, registro,
):
    app.include_router(modulo.router, prefix=PREFIJO)


@app.get("/", include_in_schema=False)
def inicio():
    return {"nombre": "Avícola"}


@app.get(f"{PREFIJO}/salud", tags=["Estado"], summary="Estado de la API y de la base de datos")
def salud():
    try:
        with motor.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        base = "ok"
    except Exception:  # noqa: BLE001
        log.exception("La base de datos no responde")
        base = "sin conexion"
    return {"api": "ok", "base_datos": base}
