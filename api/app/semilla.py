"""Carga inicial: modulos, roles, permisos, usuario de plataforma y cuenta de ejemplo.

Se puede correr varias veces sin danar nada:
    python -m app.semilla
    python -m app.semilla --reiniciar-admin   (vuelve a poner la contrasena del admin)
"""

import argparse
import logging
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.catalogo import CATEGORIAS_ARTICULO, MODULOS, PERMISOS, ROLES
from app.core.config import config
from app.core.db import SesionLocal
from app.core.seguridad import cifrar_clave
from app.modelos.acceso import Modulo, Permiso, Rol, Usuario
from app.modelos.inventario import Bodega, CategoriaArticulo
from app.modelos.organizacion import Cuenta, Finca

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("semilla")


def sembrar_modulos(db: Session) -> dict[str, Modulo]:
    existentes = {m.clave: m for m in db.scalars(select(Modulo)).all()}
    for clave, nombre, grupo, orden in MODULOS:
        modulo = existentes.get(clave)
        if modulo is None:
            modulo = Modulo(clave=clave, nombre=nombre, grupo=grupo, orden=orden)
            db.add(modulo)
            existentes[clave] = modulo
        else:
            modulo.nombre, modulo.grupo, modulo.orden = nombre, grupo, orden
    db.flush()
    return existentes


def sembrar_roles(db: Session) -> dict[str, Rol]:
    existentes = {r.clave: r for r in db.scalars(select(Rol)).all()}
    for clave, nombre, descripcion, nivel, plataforma in ROLES:
        rol = existentes.get(clave)
        if rol is None:
            rol = Rol(clave=clave, nombre=nombre, descripcion=descripcion, nivel=nivel, de_plataforma=plataforma)
            db.add(rol)
            existentes[clave] = rol
        else:
            rol.nombre, rol.descripcion, rol.nivel, rol.de_plataforma = nombre, descripcion, nivel, plataforma
    db.flush()
    return existentes


def sembrar_permisos(db: Session, roles: dict[str, Rol], modulos: dict[str, Modulo], forzar: bool) -> None:
    """Crea los permisos que falten. Con --forzar-permisos vuelve a dejar los de fabrica."""
    actuales = {(p.rol_id, p.modulo_id): p for p in db.scalars(select(Permiso)).all()}

    for rol_clave, asignaciones in PERMISOS.items():
        rol = roles.get(rol_clave)
        if rol is None:
            continue
        for modulo_clave, letras in asignaciones.items():
            modulo = modulos.get(modulo_clave)
            if modulo is None:
                continue
            permiso = actuales.get((rol.id, modulo.id))
            if permiso is None:
                permiso = Permiso(rol_id=rol.id, modulo_id=modulo.id)
                db.add(permiso)
            elif not forzar:
                continue
            permiso.ver = "v" in letras
            permiso.crear = "c" in letras
            permiso.editar = "e" in letras
            permiso.borrar = "b" in letras
    db.flush()


def sembrar_categorias(db: Session) -> None:
    """Categorias de articulos del sistema, compartidas por todas las cuentas."""
    existentes = {
        c.nombre for c in db.scalars(select(CategoriaArticulo).where(CategoriaArticulo.cuenta_id.is_(None))).all()
    }
    for nombre, clase in CATEGORIAS_ARTICULO:
        if nombre not in existentes:
            db.add(CategoriaArticulo(cuenta_id=None, nombre=nombre, clase=clase))
    db.flush()


def sembrar_admin(db: Session, roles: dict[str, Rol], reiniciar: bool) -> Usuario:
    email = config.admin_email.lower()
    usuario = db.scalars(select(Usuario).where(Usuario.email == email)).first()

    if usuario is None:
        partes = config.admin_nombre.split(" ", 1)
        usuario = Usuario(
            cuenta_id=None,
            rol_id=roles["plataforma"].id,
            nombres=partes[0],
            apellidos=partes[1] if len(partes) > 1 else "",
            email=email,
            clave_hash=cifrar_clave(config.admin_password),
            activo=True,
            debe_cambiar_clave=True,
        )
        db.add(usuario)
        db.flush()
        log.info("Usuario de plataforma creado: %s", email)
    elif reiniciar:
        usuario.clave_hash = cifrar_clave(config.admin_password)
        usuario.activo = True
        usuario.debe_cambiar_clave = True
        log.info("Contrasena del usuario %s reiniciada", email)
    return usuario


def sembrar_cuenta_demo(db: Session, roles: dict[str, Rol]) -> None:
    """La primera vez crea una cuenta y una finca para poder empezar a trabajar."""
    if db.scalars(select(Cuenta.id)).first() is not None:
        return

    cuenta = Cuenta(tipo="empresa", nombre=config.cuenta_demo, activo=True)
    db.add(cuenta)
    db.flush()

    finca = Finca(cuenta_id=cuenta.id, codigo="F1", nombre=config.finca_demo, activo=True)
    db.add(finca)
    db.flush()

    db.add(Bodega(cuenta_id=cuenta.id, finca_id=None, codigo="BC", nombre="Bodega central"))
    db.add(Bodega(cuenta_id=cuenta.id, finca_id=finca.id, codigo="B1", nombre=f"Bodega {finca.nombre}"))
    db.flush()
    log.info("Cuenta '%s', finca '%s' y sus bodegas creadas", cuenta.nombre, finca.nombre)


def principal(reiniciar_admin: bool = False, forzar_permisos: bool = False) -> None:
    with SesionLocal() as db:
        modulos = sembrar_modulos(db)
        roles = sembrar_roles(db)
        sembrar_permisos(db, roles, modulos, forzar_permisos)
        sembrar_categorias(db)
        sembrar_admin(db, roles, reiniciar_admin)
        sembrar_cuenta_demo(db, roles)
        db.commit()
    log.info("Datos iniciales listos")


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description="Carga los datos iniciales de AVISENA")
    analizador.add_argument("--reiniciar-admin", action="store_true", help="vuelve a poner la contrasena del admin")
    analizador.add_argument("--forzar-permisos", action="store_true", help="restaura los permisos de fabrica")
    args = analizador.parse_args()
    try:
        principal(args.reiniciar_admin, args.forzar_permisos)
    except Exception as error:  # noqa: BLE001
        log.error("No se pudieron cargar los datos iniciales: %s", error)
        sys.exit(1)
