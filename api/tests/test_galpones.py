"""Galpones, panel y registro de cambios."""

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa


@pytest.fixture(scope="module")
def cuenta(cliente, token_plataforma):
    return crear_cuenta_completa(cliente, token_plataforma, "CuentaGalpon")


def test_crear_editar_y_desactivar_galpon(cliente, cuenta):
    cab = cabeceras(cuenta["token"], finca_id=cuenta["finca_id"])
    codigo = unico("G")[:20]

    creado = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": codigo, "nombre": "Galpon 1", "capacidad": 500}
    )
    assert creado.status_code == 201, creado.text
    galpon = creado.json()
    assert galpon["capacidad"] == 500
    assert galpon["aves_actuales"] == 0

    repetido = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": codigo, "nombre": "Otro", "capacidad": 100}
    )
    assert repetido.status_code == 409

    editado = cliente.patch(
        f"{API}/galpones/{galpon['id']}", headers=cab, json={"nombre": "Galpon uno", "capacidad": 600}
    )
    assert editado.status_code == 200
    assert editado.json()["nombre"] == "Galpon uno"

    listado = cliente.get(f"{API}/galpones", headers=cab).json()
    assert galpon["id"] in [g["id"] for g in listado]

    borrado = cliente.delete(f"{API}/galpones/{galpon['id']}", headers=cab)
    assert borrado.status_code == 200
    assert galpon["id"] not in [g["id"] for g in cliente.get(f"{API}/galpones", headers=cab).json()]


def test_capacidad_no_puede_ser_negativa(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/galpones",
        headers=cabeceras(cuenta["token"], finca_id=cuenta["finca_id"]),
        json={"codigo": unico("G")[:20], "nombre": "Negativo", "capacidad": -5},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"


def test_sin_finca_elegida_no_se_registran_galpones(cliente, cuenta):
    """Quien puede entrar a varias fincas debe elegir una antes de registrar."""
    from app.core.config import config

    sesion = cliente.post(
        f"{API}/auth/login", json={"email": config.admin_email, "clave": config.admin_password}
    ).json()
    assert len(sesion["fincas"]) > 1
    assert sesion["finca_activa"] is None

    respuesta = cliente.post(
        f"{API}/galpones",
        headers={"Authorization": f"Bearer {sesion['token']}"},
        json={"codigo": unico("G")[:20], "nombre": "Sin finca", "capacidad": 10},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["codigo"] == "datos_invalidos"


def test_panel(cliente, cuenta):
    datos = cliente.get(
        f"{API}/panel/resumen", headers=cabeceras(cuenta["token"], finca_id=cuenta["finca_id"])
    ).json()
    assert datos["finca_activa"]["id"] == cuenta["finca_id"]
    assert datos["usuarios_activos"] >= 1


def test_el_registro_de_cambios_guarda_lo_hecho(cliente, cuenta):
    cab = cabeceras(cuenta["token"], finca_id=cuenta["finca_id"])
    cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": unico("G")[:20], "nombre": "Auditado", "capacidad": 20}
    )
    pagina = cliente.get(f"{API}/auditoria?entidad=galpones", headers=cab).json()
    assert pagina["total"] >= 1
    acciones = {fila["accion"] for fila in pagina["datos"]}
    assert "crear" in acciones


def test_cambio_de_contrasena(cliente, cuenta):
    nueva = "OtraClaveSegura456"
    cambio = cliente.post(
        f"{API}/auth/cambiar-clave",
        headers=cabeceras(cuenta["token"]),
        json={"clave_actual": CLAVE, "clave_nueva": nueva},
    )
    assert cambio.status_code == 200, cambio.text
    assert cliente.post(f"{API}/auth/login", json={"email": cuenta["email"], "clave": CLAVE}).status_code == 401
    entrada = cliente.post(f"{API}/auth/login", json={"email": cuenta["email"], "clave": nueva})
    assert entrada.status_code == 200
    cuenta["token"] = entrada.json()["token"]


def test_elegir_finca(cliente, cuenta, token_plataforma):
    otra = cliente.post(
        f"{API}/fincas",
        headers=cabeceras(token_plataforma),
        json={"codigo": "P9", "nombre": unico("Finca9"), "cuenta_id": cuenta["cuenta_id"]},
    ).json()

    respuesta = cliente.post(
        f"{API}/auth/finca", headers=cabeceras(cuenta["token"]), json={"finca_id": otra["id"]}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["finca_activa"]["id"] == otra["id"]
