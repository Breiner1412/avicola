"""Ninguna empresa puede ver ni cambiar lo de otra, ni darse permisos de plataforma."""

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import crear_cuenta_completa


@pytest.fixture(scope="module")
def propietario_a(cliente, token_plataforma):
    return crear_cuenta_completa(cliente, token_plataforma, "PropA", rol="propietario")


@pytest.fixture(scope="module")
def propietario_b(cliente, token_plataforma):
    return crear_cuenta_completa(cliente, token_plataforma, "PropB", rol="propietario")


def test_propietario_no_puede_darse_el_modulo_de_cuentas(cliente, propietario_a, propietario_b):
    token = propietario_a["token"]
    cliente.put(
        f"{API}/permisos/propietario/cuentas",
        headers=cabeceras(token),
        json={"ver": True, "crear": True, "editar": True, "borrar": True},
    )
    assert cliente.get(f"{API}/cuentas", headers=cabeceras(token)).status_code == 403
    cuenta_b = propietario_b["cuenta_id"]
    assert cliente.get(f"{API}/cuentas/{cuenta_b}", headers=cabeceras(token)).status_code == 403
    assert (
        cliente.patch(f"{API}/cuentas/{cuenta_b}", headers=cabeceras(token), json={"nombre": "Robada"}).status_code
        == 403
    )
    assert cliente.delete(f"{API}/cuentas/{cuenta_b}", headers=cabeceras(token)).status_code == 403


def test_plataforma_si_administra_cuentas(cliente, token_plataforma, propietario_b):
    respuesta = cliente.get(f"{API}/cuentas/{propietario_b['cuenta_id']}", headers=cabeceras(token_plataforma))
    assert respuesta.status_code == 200


def test_los_permisos_de_una_empresa_no_cambian_los_de_otra(cliente, propietario_a, propietario_b):
    quitar = {"ver": False, "crear": False, "editar": False, "borrar": False}
    respuesta = cliente.put(f"{API}/permisos/cajero/ventas", headers=cabeceras(propietario_a["token"]), json=quitar)
    assert respuesta.status_code == 200, respuesta.text

    propia = cliente.get(f"{API}/permisos", headers=cabeceras(propietario_a["token"])).json()
    ajena = cliente.get(f"{API}/permisos", headers=cabeceras(propietario_b["token"])).json()
    assert "ventas" not in propia["cajero"]
    assert ajena["cajero"]["ventas"]["crear"] is True


def test_una_empresa_no_ve_la_matriz_de_otra(cliente, propietario_a, propietario_b):
    respuesta = cliente.get(
        f"{API}/permisos",
        headers=cabeceras(propietario_a["token"]),
        params={"cuenta_id": propietario_b["cuenta_id"]},
    )
    assert respuesta.status_code == 403


def test_nadie_cambia_los_permisos_de_su_propio_rol(cliente, propietario_a):
    respuesta = cliente.put(
        f"{API}/permisos/propietario/roles",
        headers=cabeceras(propietario_a["token"]),
        json={"ver": False, "crear": False, "editar": False, "borrar": False},
    )
    assert respuesta.status_code == 403
    matriz = cliente.get(f"{API}/permisos", headers=cabeceras(propietario_a["token"]))
    assert matriz.status_code == 200


def _crear_articulo_bajo_minimo(cliente, cuenta, nombre):
    cab = cabeceras(cuenta["token"], cuenta["finca_id"])
    categoria = cliente.get(f"{API}/categorias-articulo", headers=cab).json()[0]
    articulo = cliente.post(
        f"{API}/articulos",
        headers=cab,
        json={"codigo": unico("B")[:30], "nombre": nombre, "categoria_id": categoria["id"], "unidad": "kg", "stock_minimo": 50},
    )
    assert articulo.status_code == 201, articulo.text


def test_el_reporte_no_muestra_inventario_de_otra_empresa(cliente, propietario_a, propietario_b):
    secreto = unico("SecretoDeB")
    _crear_articulo_bajo_minimo(cliente, propietario_b, secreto)
    _crear_articulo_bajo_minimo(cliente, propietario_a, "Propio de A")
    cab = cabeceras(propietario_a["token"], propietario_a["finca_id"])
    bodega = cliente.post(f"{API}/bodegas", headers=cab, json={"codigo": unico("BC")[:20], "nombre": "Central A"})
    assert bodega.status_code == 201, bodega.text

    resumen = cliente.get(f"{API}/reportes/resumen", headers=cab)
    assert resumen.status_code == 200, resumen.text
    nombres = {b["articulo"] for b in resumen.json()["inventario"]["bajo_minimo"]}
    assert secreto not in nombres
    assert "Propio de A" in nombres
