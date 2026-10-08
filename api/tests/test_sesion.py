"""Pruebas de inicio de sesion, permisos y contrasenas."""

import pytest

from tests.conftest import API, cabeceras, unico

from app.core.config import config


def test_salud(cliente):
    datos = cliente.get(f"{API}/salud").json()
    assert datos["api"] == "ok"
    assert datos["base_datos"] == "ok"


def test_login_con_clave_mala(cliente):
    respuesta = cliente.post(
        f"{API}/auth/login", json={"email": config.admin_email, "clave": "noEsLaClave123"}
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "credenciales"


def test_login_correo_desconocido(cliente):
    respuesta = cliente.post(
        f"{API}/auth/login", json={"email": f"{unico('nadie')}@avicola.com", "clave": "loQueSea123"}
    )
    assert respuesta.status_code == 401


def test_sin_token_no_entra(cliente):
    assert cliente.get(f"{API}/fincas").status_code == 401


def test_token_invalido(cliente):
    assert cliente.get(f"{API}/fincas", headers=cabeceras("esto.no.es.un.token")).status_code == 401


def test_datos_de_la_sesion(cliente, token_plataforma):
    datos = cliente.get(f"{API}/auth/yo", headers=cabeceras(token_plataforma)).json()
    assert datos["usuario"]["rol"] == "plataforma"
    assert datos["permisos"]["fincas"]["crear"] is True


def test_refrescar_y_salir(cliente, token_plataforma):
    assert cliente.post(f"{API}/auth/login", json={"email": config.admin_email, "clave": config.admin_password}).status_code == 200
    assert cliente.post(f"{API}/auth/refrescar").status_code == 200
    assert cliente.post(f"{API}/auth/salir").status_code == 200
    assert cliente.post(f"{API}/auth/refrescar").status_code == 401


@pytest.fixture(scope="module")
def victima(cliente, token_plataforma):
    from tests.test_multicuenta import crear_cuenta_completa

    return crear_cuenta_completa(cliente, token_plataforma, "Victima")


def test_los_ingresos_correctos_no_cuentan_para_el_limite(cliente, victima):
    from tests.test_multicuenta import CLAVE

    for _ in range(35):
        respuesta = cliente.post(f"{API}/auth/login", json={"email": victima["email"], "clave": CLAVE})
        assert respuesta.status_code == 200, respuesta.text


def test_un_atacante_no_deja_sin_entrar_a_los_demas(cliente, victima, monkeypatch):
    from app.rutas import auth
    from tests.test_multicuenta import CLAVE

    monkeypatch.setattr(auth, "ip_de", lambda peticion: "10.0.0.66")
    codigos = [
        cliente.post(f"{API}/auth/login", json={"email": victima["email"], "clave": "mala"}).status_code
        for _ in range(9)
    ]
    assert codigos[:8] == [401] * 8
    assert codigos[8] == 429
    # Desde su conexion queda bloqueado aunque ahora acierte
    bien = {"email": victima["email"], "clave": CLAVE}
    assert cliente.post(f"{API}/auth/login", json=bien).status_code == 429

    # Desde otra conexion, el dueno de la cuenta entra sin problema
    monkeypatch.setattr(auth, "ip_de", lambda peticion: "10.0.0.7")
    assert cliente.post(f"{API}/auth/login", json=bien).status_code == 200


def test_los_correos_inventados_no_llenan_el_registro(cliente, monkeypatch):
    from sqlalchemy import func, select

    from app.core.db import SesionLocal
    from app.modelos.registro import Auditoria
    from app.rutas import auth

    monkeypatch.setattr(auth, "ip_de", lambda peticion: "10.0.0.99")
    with SesionLocal() as db:
        antes = db.scalar(select(func.count(Auditoria.id)))
    for n in range(5):
        cliente.post(f"{API}/auth/login", json={"email": f"nadie{n}@inventado.com", "clave": "x"})
    with SesionLocal() as db:
        assert db.scalar(select(func.count(Auditoria.id))) == antes
