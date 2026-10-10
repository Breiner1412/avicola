"""En la demo (DEMO=true) nadie puede dejar a los demas sin entrar ni cambiar las reglas."""

import pytest

from app.core.config import config
from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa


@pytest.fixture(scope="module")
def dueno(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "Demo", rol="propietario")
    cab = cabeceras(datos["token"])
    cajero = cliente.post(
        f"{API}/usuarios",
        headers=cab,
        json={"nombres": "Caja", "email": f"{unico('caja')}@avicola.com", "rol": "cajero", "clave": CLAVE,
              "debe_cambiar_clave": False, "fincas": [{"finca_id": datos["finca_id"], "solo_lectura": False}]},
    ).json()
    cab_finca = cabeceras(datos["token"], datos["finca_id"])
    punto = cliente.post(
        f"{API}/puntos-venta", headers=cab_finca, json={"codigo": "PD", "nombre": "Tienda demo", "finca_id": datos["finca_id"]}
    ).json()
    producto = cliente.post(
        f"{API}/productos-venta", headers=cab_finca,
        json={"nombre": "Gallina demo", "clase": "ave_descarte", "presentacion": "unidad", "precio": 12000},
    ).json()
    datos.update({"cab": cab, "cajero": cajero, "punto": punto, "producto": producto})
    return datos


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setattr(config, "demo", True)


def test_la_sesion_avisa_que_es_demo(cliente, dueno, demo):
    sesion = cliente.post(f"{API}/auth/login", json={"email": dueno["email"], "clave": CLAVE}).json()
    assert sesion["demo"] is True


@pytest.mark.parametrize(
    "metodo, ruta, cuerpo",
    [
        ("post", "/auth/cambiar-clave", {"clave_actual": CLAVE, "clave_nueva": "OtraClave12345"}),
        ("post", "/auth/recuperar", {"email": "nadie@avicola.com"}),
        ("post", "/usuarios/{cajero}/clave", {"clave": "OtraClave12345", "debe_cambiar_clave": False}),
        ("patch", "/usuarios/{cajero}", {"email": "robado@avicola.com"}),
        ("patch", "/usuarios/{cajero}", {"rol": "operario"}),
        ("patch", "/usuarios/{cajero}", {"activo": False}),
        ("delete", "/usuarios/{cajero}", None),
        ("put", "/permisos/cajero/ventas", {"ver": False, "crear": False, "editar": False, "borrar": False}),
        ("patch", "/fincas/{finca}", {"activo": False}),
        ("delete", "/fincas/{finca}", None),
        ("patch", "/puntos-venta/{punto}", {"activo": False}),
        ("patch", "/productos-venta/{producto}", {"activo": False}),
        ("post", "/precios", {"producto_id": "{producto}", "precio": 0}),
        ("patch", "/ventas/ajustes", {"descuento_maximo": 100}),
    ],
)
def test_lo_que_la_demo_no_permite(cliente, dueno, demo, metodo, ruta, cuerpo):
    ids = {"cajero": dueno["cajero"]["id"], "finca": dueno["finca_id"], "punto": dueno["punto"]["id"],
           "producto": dueno["producto"]["id"]}
    ruta = ruta.format(**ids)
    argumentos = {"headers": dueno["cab"]}
    if cuerpo is not None:
        argumentos["json"] = {k: (ids["producto"] if v == "{producto}" else v) for k, v in cuerpo.items()}
    respuesta = getattr(cliente, metodo)(f"{API}{ruta}", **argumentos)
    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["detail"]["codigo"] == "demo"


def test_lo_demas_si_se_puede_usar(cliente, dueno, demo):
    telefono = cliente.patch(f"{API}/usuarios/{dueno['cajero']['id']}", headers=dueno["cab"], json={"telefono": "300 000"})
    assert telefono.status_code == 200, telefono.text
    galpon = cliente.post(
        f"{API}/galpones",
        headers=cabeceras(dueno["token"], dueno["finca_id"]),
        json={"codigo": "GD", "nombre": "Galpon demo", "capacidad": 100},
    )
    assert galpon.status_code == 201, galpon.text
    assert cliente.get(f"{API}/ventas/ajustes", headers=cabeceras(dueno["token"], dueno["finca_id"])).status_code == 200


def test_fuera_de_la_demo_si_se_puede(cliente, dueno):
    respuesta = cliente.post(
        f"{API}/usuarios/{dueno['cajero']['id']}/clave",
        headers=dueno["cab"],
        json={"clave": "OtraClave12345", "debe_cambiar_clave": False},
    )
    assert respuesta.status_code == 200, respuesta.text
