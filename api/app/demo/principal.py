"""Punto de entrada: python -m app.demo [--dias N] [--solo-si-falta]."""

from __future__ import annotations

import argparse
import logging

from app.demo.datos import CLAVE_DEMO, DOMINIO
from app.demo.simulacion import Demo, demo_cargada


def principal() -> None:
    analizador = argparse.ArgumentParser(description="Carga datos de ejemplo de una granja con varios meses de trabajo")
    analizador.add_argument("--dias", type=int, default=180, help="cuantos dias hacia atras (por defecto 180)")
    analizador.add_argument(
        "--solo-si-falta",
        action="store_true",
        help="si la demo ya esta cargada, no hace nada y termina bien (para cargarla sola la primera vez)",
    )
    argumentos = analizador.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("avicola").setLevel(logging.INFO)

    if argumentos.solo_si_falta and demo_cargada():
        print("La demo ya estaba cargada: no se hace nada.")
        return

    demo = Demo(max(30, min(argumentos.dias, 400)))
    demo.correr()

    print()
    print("Listo. Esto quedo registrado:")
    for que, cuantos in sorted(demo.cuentas.items()):
        print(f"  {que:<16} {cuantos:>7}")
    if demo.errores:
        print("Operaciones que el sistema rechazo (normal si son pocas):")
        for que, cuantos in sorted(demo.errores.items()):
            print(f"  {que:<16} {cuantos:>7}")
    print()
    print(f"Entra con cualquiera de estos usuarios (contrasena: {CLAVE_DEMO}):")
    for correo, rol in (("dueno", "propietario"), ("admin", "administrador"), ("supervisor", "supervisor"),
                        ("operario1", "operario"), ("caja", "cajero")):
        print(f"  {correo + '@' + DOMINIO:<32} {rol}")
