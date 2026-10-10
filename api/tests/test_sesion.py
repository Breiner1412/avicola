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


def test_los_ingresos_correctos_tambien_tienen_tope(cliente, victima, monkeypatch):
    from app.core import limites
    from tests.test_multicuenta import CLAVE

    monkeypatch.setattr(limites.ingresos_ip, "maximo", 3)
    codigos = [
        cliente.post(f"{API}/auth/login", json={"email": victima["email"], "clave": CLAVE}).status_code
        for _ in range(4)
    ]
    assert codigos == [200, 200, 200, 429]


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


def _navegador():
    """Un cliente con su propio frasco de cookies, como otro navegador."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _entrar(navegador, email):
    from tests.test_multicuenta import CLAVE

    respuesta = navegador.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["token"]


def test_el_token_de_refresco_cambia_y_el_viejo_no_se_puede_reusar(victima):
    from datetime import datetime, timedelta

    from sqlalchemy import update

    from app.core.config import config as ajustes
    from app.core.db import SesionLocal
    from app.modelos.acceso import Sesion

    navegador = _navegador()
    _entrar(navegador, victima["email"])
    viejo = navegador.cookies.get(ajustes.cookie_refresco)

    assert navegador.post(f"{API}/auth/refrescar").status_code == 200
    nuevo = navegador.cookies.get(ajustes.cookie_refresco)
    assert nuevo and nuevo != viejo

    # Otra pestana que todavia mando el viejo: se acepta unos segundos
    otra = _navegador()
    otra.cookies.set(ajustes.cookie_refresco, viejo, path="/api/v1/auth")
    assert otra.post(f"{API}/auth/refrescar").status_code == 200

    # Pasado ese margen, usar el viejo cierra la sesion (posible robo)
    with SesionLocal() as db:
        db.execute(update(Sesion).where(Sesion.rotada_en.is_not(None)).values(rotada_en=datetime(2020, 1, 1)))
        db.commit()
    assert otra.post(f"{API}/auth/refrescar").status_code == 401
    assert navegador.post(f"{API}/auth/refrescar").status_code == 401


def test_cambiar_la_clave_cierra_las_demas_sesiones(cliente, token_plataforma):
    from tests.test_multicuenta import CLAVE, crear_cuenta_completa

    datos = crear_cuenta_completa(cliente, token_plataforma, "CambiaClave")
    aqui = _entrar(_navegador(), datos["email"])
    alla = _entrar(_navegador(), datos["email"])

    cambio = cliente.post(
        f"{API}/auth/cambiar-clave",
        headers=cabeceras(aqui),
        json={"clave_actual": CLAVE, "clave_nueva": "OtraClaveSegura123"},
    )
    assert cambio.status_code == 200, cambio.text
    assert cliente.get(f"{API}/auth/yo", headers=cabeceras(aqui)).status_code == 200
    assert cliente.get(f"{API}/auth/yo", headers=cabeceras(alla)).status_code == 401


def test_una_cuenta_desactivada_queda_por_fuera_de_inmediato(cliente, token_plataforma):
    from tests.test_multicuenta import crear_cuenta_completa

    datos = crear_cuenta_completa(cliente, token_plataforma, "Desactivada")
    assert cliente.get(f"{API}/auth/yo", headers=cabeceras(datos["token"])).status_code == 200
    respuesta = cliente.delete(f"{API}/cuentas/{datos['cuenta_id']}", headers=cabeceras(token_plataforma))
    assert respuesta.status_code == 200, respuesta.text
    assert cliente.get(f"{API}/auth/yo", headers=cabeceras(datos["token"])).status_code == 401


def test_una_ip_enorme_no_rompe_el_inicio_de_sesion(cliente, victima):
    from tests.test_multicuenta import CLAVE

    cabecera = {"X-Forwarded-For": "1" * 300}
    mala = cliente.post(f"{API}/auth/login", json={"email": victima["email"], "clave": "mala"}, headers=cabecera)
    assert mala.status_code == 401
    buena = cliente.post(f"{API}/auth/login", json={"email": victima["email"], "clave": CLAVE}, headers=cabecera)
    assert buena.status_code == 200, buena.text


def test_sin_smtp_en_produccion_el_codigo_no_queda_en_el_log(monkeypatch, caplog):
    from app.core import correo
    from app.core.config import config as ajustes

    monkeypatch.setattr(ajustes, "entorno", "produccion")
    monkeypatch.setattr(ajustes, "smtp_host", "")
    with caplog.at_level("WARNING", logger="avicola.correo"):
        correo.enviar("alguien@avicola.com", "Codigo", "Tu codigo es 123456")
    assert "123456" not in caplog.text
    assert "no se envio" in caplog.text


def test_un_x_forwarded_for_falso_no_salta_el_limite(cliente, victima):
    codigos = [
        cliente.post(
            f"{API}/auth/login",
            json={"email": victima["email"], "clave": "mala"},
            headers={"X-Forwarded-For": f"203.0.113.{n}"},
        ).status_code
        for n in range(9)
    ]
    assert codigos[8] == 429


def test_la_api_responde_con_cabeceras_de_seguridad(cliente):
    respuesta = cliente.get(f"{API}/salud")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["Cache-Control"] == "no-store"


def test_un_correo_que_no_existe_tarda_como_uno_que_si(cliente, victima):
    import time

    def tiempo(email):
        inicio = time.perf_counter()
        cliente.post(f"{API}/auth/login", json={"email": email, "clave": "mala"})
        return time.perf_counter() - inicio

    existente = min(tiempo(victima["email"]) for _ in range(3))
    inexistente = min(tiempo("nadie-nunca@avicola.com") for _ in range(3))
    # Ambos pasan por bcrypt: el inexistente no puede ser mucho mas rapido
    assert inexistente > existente * 0.5
