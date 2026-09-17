"""Pruebas de inicio de sesion, permisos y contrasenas."""

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
        f"{API}/auth/login", json={"email": f"{unico('nadie')}@avisena.com", "clave": "loQueSea123"}
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
