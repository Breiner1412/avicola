"""Cada cuenta ve solo lo suyo, y cada empleado solo sus fincas."""

import pytest

from tests.conftest import API, cabeceras, unico

CLAVE = "ClaveDePrueba123"


def crear_cuenta_completa(cliente, token, nombre: str):
    """Crea cuenta + finca + administrador y devuelve sus datos."""
    cuenta = cliente.post(
        f"{API}/cuentas", headers=cabeceras(token), json={"tipo": "empresa", "nombre": unico(nombre)}
    )
    assert cuenta.status_code == 201, cuenta.text
    cuenta_id = cuenta.json()["id"]

    finca = cliente.post(
        f"{API}/fincas",
        headers=cabeceras(token),
        json={"codigo": "P1", "nombre": unico("Finca"), "cuenta_id": cuenta_id, "municipio": "Sabana"},
    )
    assert finca.status_code == 201, finca.text
    finca_id = finca.json()["id"]

    email = f"{unico('admin')}@avicola.com"
    usuario = cliente.post(
        f"{API}/usuarios",
        headers=cabeceras(token),
        json={
            "nombres": "Admin",
            "apellidos": "Prueba",
            "email": email,
            "rol": "administrador",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "cuenta_id": cuenta_id,
        },
    )
    assert usuario.status_code == 201, usuario.text

    sesion = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE})
    assert sesion.status_code == 200, sesion.text
    return {
        "cuenta_id": cuenta_id,
        "finca_id": finca_id,
        "email": email,
        "token": sesion.json()["token"],
        "sesion": sesion.json(),
    }


@pytest.fixture(scope="module")
def cuenta_a(cliente, token_plataforma):
    return crear_cuenta_completa(cliente, token_plataforma, "CuentaA")


@pytest.fixture(scope="module")
def cuenta_b(cliente, token_plataforma):
    return crear_cuenta_completa(cliente, token_plataforma, "CuentaB")


def test_el_administrador_ve_su_finca(cliente, cuenta_a):
    fincas = cliente.get(f"{API}/fincas", headers=cabeceras(cuenta_a["token"])).json()
    assert [f["id"] for f in fincas] == [cuenta_a["finca_id"]]


def test_no_ve_la_finca_de_otra_cuenta(cliente, cuenta_a, cuenta_b):
    respuesta = cliente.get(f"{API}/fincas/{cuenta_b['finca_id']}", headers=cabeceras(cuenta_a["token"]))
    assert respuesta.status_code == 404


def test_no_puede_trabajar_en_otra_finca(cliente, cuenta_a, cuenta_b):
    respuesta = cliente.get(
        f"{API}/galpones", headers=cabeceras(cuenta_a["token"], finca_id=cuenta_b["finca_id"])
    )
    assert respuesta.status_code == 403


def test_no_ve_usuarios_de_otra_cuenta(cliente, cuenta_a, cuenta_b):
    usuarios = cliente.get(f"{API}/usuarios", headers=cabeceras(cuenta_a["token"])).json()
    correos = {u["email"] for u in usuarios}
    assert cuenta_a["email"] in correos
    assert cuenta_b["email"] not in correos


def test_no_puede_crear_cuentas(cliente, cuenta_a):
    respuesta = cliente.post(
        f"{API}/cuentas", headers=cabeceras(cuenta_a["token"]), json={"nombre": unico("Intruso")}
    )
    assert respuesta.status_code == 403


def test_no_puede_crear_usuarios_de_plataforma(cliente, cuenta_a):
    respuesta = cliente.post(
        f"{API}/usuarios",
        headers=cabeceras(cuenta_a["token"]),
        json={
            "nombres": "Falso",
            "email": f"{unico('falso')}@avicola.com",
            "rol": "plataforma",
            "clave": CLAVE,
        },
    )
    assert respuesta.status_code == 403


def test_operario_solo_entra_a_su_finca(cliente, cuenta_a, token_plataforma):
    otra = cliente.post(
        f"{API}/fincas",
        headers=cabeceras(token_plataforma),
        json={"codigo": "P2", "nombre": unico("Finca2"), "cuenta_id": cuenta_a["cuenta_id"]},
    ).json()

    email = f"{unico('operario')}@avicola.com"
    creado = cliente.post(
        f"{API}/usuarios",
        headers=cabeceras(cuenta_a["token"]),
        json={
            "nombres": "Operario",
            "email": email,
            "rol": "operario",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "fincas": [{"finca_id": cuenta_a["finca_id"], "solo_lectura": False}],
        },
    )
    assert creado.status_code == 201, creado.text

    sesion = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()
    assert [f["id"] for f in sesion["fincas"]] == [cuenta_a["finca_id"]]
    assert sesion["finca_activa"]["id"] == cuenta_a["finca_id"]

    token = sesion["token"]
    assert cliente.get(f"{API}/galpones", headers=cabeceras(token)).status_code == 200
    assert cliente.get(f"{API}/galpones", headers=cabeceras(token, finca_id=otra["id"])).status_code == 403
    # El operario no administra usuarios
    assert cliente.get(f"{API}/usuarios", headers=cabeceras(token)).status_code == 403


def test_supervisor_de_solo_lectura(cliente, cuenta_a, token_plataforma):
    otra = cliente.post(
        f"{API}/fincas",
        headers=cabeceras(token_plataforma),
        json={"codigo": "P3", "nombre": unico("Finca3"), "cuenta_id": cuenta_a["cuenta_id"]},
    ).json()

    email = f"{unico('supervisor')}@avicola.com"
    cliente.post(
        f"{API}/usuarios",
        headers=cabeceras(cuenta_a["token"]),
        json={
            "nombres": "Supervisor",
            "email": email,
            "rol": "supervisor",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "fincas": [
                {"finca_id": cuenta_a["finca_id"], "solo_lectura": False},
                {"finca_id": otra["id"], "solo_lectura": True},
            ],
        },
    )
    token = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()["token"]

    # En la finca a cargo si puede registrar
    creado = cliente.post(
        f"{API}/galpones",
        headers=cabeceras(token, finca_id=cuenta_a["finca_id"]),
        json={"codigo": unico("G")[:20], "nombre": "Galpon supervisado", "capacidad": 100},
    )
    assert creado.status_code == 201, creado.text

    # En la otra finca solo mira
    assert cliente.get(f"{API}/galpones", headers=cabeceras(token, finca_id=otra["id"])).status_code == 200
    bloqueado = cliente.post(
        f"{API}/galpones",
        headers=cabeceras(token, finca_id=otra["id"]),
        json={"codigo": unico("G")[:20], "nombre": "No deberia", "capacidad": 50},
    )
    assert bloqueado.status_code == 403
