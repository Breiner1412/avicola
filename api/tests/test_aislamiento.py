"""Ninguna empresa puede ver ni cambiar lo de otra, ni darse permisos de plataforma."""

import pytest

from tests.conftest import API, cabeceras
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
