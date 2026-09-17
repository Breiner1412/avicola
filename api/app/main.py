"""Aplicacion FastAPI de AVISENA."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import config
from app.core.db import motor
from app.rutas import auth, cuentas, fincas, galpones, panel, registro, roles, usuarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("avisena")

PREFIJO = "/api/v1"

app = FastAPI(
    title="AVISENA",
    description="API de gestion de granjas avicolas (multi finca y multi cuenta).",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)


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


@app.exception_handler(Exception)
async def error_general(peticion: Request, error: Exception):
    log.exception("Error no controlado en %s %s", peticion.method, peticion.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"codigo": "error_interno", "mensaje": "Ocurrio un error inesperado", "detalles": {}},
    )


for modulo in (auth, panel, cuentas, fincas, galpones, usuarios, roles, registro):
    app.include_router(modulo.router, prefix=PREFIJO)


@app.get("/", include_in_schema=False)
def inicio():
    return {"nombre": "AVISENA", "version": app.version, "documentacion": "/docs"}


@app.get(f"{PREFIJO}/salud", tags=["Estado"], summary="Estado de la API y de la base de datos")
def salud():
    try:
        with motor.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        base = "ok"
    except Exception:  # noqa: BLE001
        log.exception("La base de datos no responde")
        base = "sin conexion"
    return {"api": "ok", "base_datos": base, "entorno": config.entorno}
