"""Reportes descargables."""

import pytest

from tests.conftest import API, cabeceras
from tests.test_multicuenta import crear_cuenta_completa


@pytest.fixture(scope="module")
def cuenta(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "Reportes")
    datos["cab"] = cabeceras(datos["token"], datos["finca_id"])
    return datos


def test_el_csv_no_deja_formulas_activas(cliente, cuenta):
    peligrosa = '=HYPERLINK("http://malo.example","clic")'
    creada = cliente.post(
        f"{API}/novedades",
        headers=cuenta["cab"],
        json={"fecha": "2026-06-01", "titulo": peligrosa, "categoria": "otro"},
    )
    assert creada.status_code == 201, creada.text

    respuesta = cliente.get(
        f"{API}/reportes/csv",
        headers=cuenta["cab"],
        params={"tipo": "novedades", "desde": "2026-05-01", "hasta": "2026-06-30"},
    )
    assert respuesta.status_code == 200, respuesta.text
    texto = respuesta.content.decode("utf-8-sig")
    assert "'=HYPERLINK" in texto
    assert ";=HYPERLINK" not in texto and "\n=HYPERLINK" not in texto


@pytest.mark.parametrize("tipo", ["produccion", "ventas", "aves", "alimento", "existencias", "novedades", "tareas"])
def test_cada_csv_se_descarga(cliente, cuenta, tipo):
    respuesta = cliente.get(f"{API}/reportes/csv", headers=cuenta["cab"], params={"tipo": tipo})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("text/csv")


def test_un_csv_que_no_existe(cliente, cuenta):
    assert cliente.get(f"{API}/reportes/csv", headers=cuenta["cab"], params={"tipo": "secreto"}).status_code == 400


def test_el_resumen_trae_todas_las_secciones(cliente, cuenta):
    datos = cliente.get(f"{API}/reportes/resumen", headers=cuenta["cab"]).json()
    assert {"produccion", "aves", "alimento", "ventas", "inventario", "trabajo"} <= set(datos)
    fechas = cliente.get(
        f"{API}/reportes/resumen", headers=cuenta["cab"], params={"desde": "2026-05-01", "hasta": "2026-04-01"}
    )
    assert fechas.status_code == 400
