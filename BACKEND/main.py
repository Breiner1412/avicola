"""AVISENA API - punto de entrada."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.router import (
    alimento, auth, categories, chicken_incident, chickens, consumo_gallinas,
    dashboard, detalle_huevos, detalle_salvamento, incidentes_generales, inventory,
    isolation, lands, metodo_pago, modulos, permisos, produccion_huevos,
    registro_sensores, rescue, roles, sensor_types, sensors, sheds, stock, tareas,
    tipo_huevos, type_chickens, users, ventas,
)
from core.config import settings
from core.database import check_database_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("avisena")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
)


# Captura cualquier error no controlado y lo devuelve como JSON.
# Se registra ANTES del middleware de CORS para que CORS quede por fuera
# y la respuesta 500 también lleve las cabeceras CORS (si no, el navegador
# muestra un "error de CORS" en lugar del mensaje real).
@app.middleware("http")
async def catch_unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor. Intenta de nuevo más tarde."},
        )


# CORS: solo los orígenes configurados (CORS_ORIGINS en .env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# (prefijo, router, etiqueta) — los prefijos son los que usa el frontend
ROUTERS = [
    # Acceso y seguridad
    ("/access", auth.router, "Acceso"),
    ("/users", users.router, "Usuarios"),
    ("/roles", roles.router, "Roles"),
    ("/modulos", modulos.router, "Módulos"),
    ("/permisos", permisos.router, "Permisos"),
    ("/tareas", tareas.router, "Tareas"),
    # Infraestructura
    ("/lands", lands.router, "Fincas"),
    ("/sheds", sheds.router, "Galpones"),
    ("/categories", categories.router, "Categorías de inventario"),
    ("/inventory", inventory.router, "Inventario"),
    ("/incidentes_generales", incidentes_generales.router, "Incidentes generales"),
    # Sensores
    ("/sensor-types", sensor_types.router, "Tipos de sensor"),
    ("/sensors", sensors.router, "Sensores"),
    ("/registro-sensores", registro_sensores.router, "Registros de sensores"),
    # Gallinas
    ("/type_chicken", type_chickens.router, "Tipos de gallina"),
    ("/chickens", chickens.router, "Ingreso de gallinas"),
    ("/incident", chicken_incident.router, "Incidentes de gallinas"),
    ("/isolations", isolation.router, "Aislamientos"),
    ("/rescue", rescue.router, "Salvamento"),
    # Alimentación
    ("/alimento", alimento.router, "Alimento"),
    ("/consumo_gallinas", consumo_gallinas.router, "Consumo de alimento"),
    # Producción y ventas
    ("/tipo-huevos", tipo_huevos.router, "Tipos de huevo"),
    ("/produccion-huevos", produccion_huevos.router, "Producción de huevos"),
    ("/stock", stock.router, "Stock"),
    ("/metodo_pago", metodo_pago.router, "Métodos de pago"),
    ("/ventas", ventas.router, "Ventas"),
    ("/detalle_huevos", detalle_huevos.router, "Detalle de venta (huevos)"),
    ("/detalle_salvamento", detalle_salvamento.router, "Detalle de venta (salvamento)"),
    # Panel
    ("/dashboard", dashboard.router, "Dashboard"),
]

for prefix, router, tag in ROUTERS:
    app.include_router(router, prefix=prefix, tags=[tag])


@app.get("/", tags=["Estado"])
def read_root():
    return {"message": "ok", "autor": "ADSO 2925889"}


@app.get("/health", tags=["Estado"])
def health():
    """Usado por Docker para saber si la API y la base de datos están listas."""
    if not check_database_connection():
        return JSONResponse(status_code=503, content={"status": "error", "database": "sin conexión"})
    return {"status": "ok", "database": "ok"}
