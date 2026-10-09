"""Constantes y curvas de la simulacion (postura, pesos, clientes...)."""

from __future__ import annotations

import logging
import math
import random
from datetime import timedelta


log = logging.getLogger("avicola.demo")

NOMBRE_CUENTA = "Granja Avicola La Esperanza"
CLAVE_DEMO = "Granja2026"
DOMINIO = "demo-avicola.com"
# Colombia no cambia de hora: la hora local es UTC - 5
DESFASE = timedelta(hours=5)

COMERCIALES = ["Super", "AAA", "AA", "A", "B"]
CLIENTES_MAYORISTAS = [
    "Distribuidora Huevos del Otun",
    "Supermercado La Canasta",
    "Tienda Don Pacho",
    "Panaderia El Trigal",
    "Restaurante Sazon Paisa",
    "Minimercado La 14 de Santa Rosa",
]
COMPRADORES_POLLO = ["Asadero El Pollo Dorado", "Carnes Frias Risaralda", "Plaza de mercado Dosquebradas"]


# ---------------------------------------------------------------- utilidades
def poisson(media: float) -> int:
    if media <= 0:
        return 0
    limite, k, p = math.exp(-media), 0, 1.0
    while True:
        p *= random.random()
        if p <= limite:
            return k
        k += 1


def redondear(valor: float, paso: int) -> int:
    return int(math.ceil(valor / paso) * paso)


def interpolar(tabla: list[tuple[float, float]], x: float) -> float:
    if x <= tabla[0][0]:
        return tabla[0][1]
    for (x0, y0), (x1, y1) in zip(tabla, tabla[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tabla[-1][1]


# Peso de pollo de engorde (dias, kg) y de pollita de levante (semanas, kg)
PESO_POLLO = [(0, 0.042), (7, 0.19), (14, 0.48), (21, 0.95), (28, 1.5), (35, 2.1), (42, 2.75), (49, 3.2)]
PESO_POLLITA = [(0, 0.04), (2, 0.12), (4, 0.29), (6, 0.45), (8, 0.65), (10, 0.84), (12, 1.03), (14, 1.2),
                (16, 1.37), (18, 1.5), (22, 1.75), (30, 1.9), (80, 2.0)]
# Alimento de pollita en gramos por ave y dia, por semana de edad
GRAMOS_POLLITA = [10, 14, 19, 24, 29, 34, 39, 44, 48, 52, 56, 59, 62, 65, 68, 71, 74, 78, 84, 92, 100, 106, 110]


def postura(edad_dias: int) -> float:
    semanas = edad_dias / 7
    if semanas < 18.5:
        return 0.0
    if semanas < 25:
        return 0.95 * (1 - math.exp(-(semanas - 18.5) / 1.8))
    if semanas < 32:
        return 0.95
    return max(0.55, 0.95 - 0.004 * (semanas - 32))


def tamanos(edad_dias: int) -> list[float]:
    semanas = edad_dias / 7
    if semanas < 24:
        return [0.0, 0.02, 0.18, 0.45, 0.35]
    if semanas < 30:
        return [0.01, 0.10, 0.40, 0.35, 0.14]
    if semanas < 45:
        return [0.04, 0.25, 0.45, 0.20, 0.06]
    if semanas < 60:
        return [0.08, 0.35, 0.40, 0.13, 0.04]
    return [0.12, 0.40, 0.33, 0.11, 0.04]
