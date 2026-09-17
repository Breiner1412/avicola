"""Bodegas, articulos y movimientos de inventario."""

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa


@pytest.fixture(scope="module")
def cuenta(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaInv")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    central = cliente.post(
        f"{API}/bodegas", headers=cab, json={"codigo": "BC", "nombre": "Bodega central"}
    )
    assert central.status_code == 201, central.text
    finca = cliente.post(
        f"{API}/bodegas",
        headers=cab,
        json={"codigo": "B1", "nombre": "Bodega de la finca", "finca_id": datos["finca_id"]},
    )
    assert finca.status_code == 201, finca.text

    categorias = cliente.get(f"{API}/categorias-articulo", headers=cab).json()
    alimento = next(c for c in categorias if c["clase"] == "alimento")

    articulo = cliente.post(
        f"{API}/articulos",
        headers=cab,
        json={
            "codigo": unico("A")[:30],
            "nombre": "Concentrado ponedora",
            "categoria_id": alimento["id"],
            "unidad": "kg",
            "kg_por_bulto": 40,
            "stock_minimo": 100,
        },
    )
    assert articulo.status_code == 201, articulo.text

    datos.update(
        {
            "cab": cab,
            "central": central.json(),
            "bodega_finca": finca.json(),
            "articulo": articulo.json(),
        }
    )
    return datos


def existencia(cliente, cuenta, bodega_id: int) -> float:
    filas = cliente.get(f"{API}/existencias?bodega_id={bodega_id}", headers=cuenta["cab"]).json()
    fila = next((f for f in filas if f["articulo_id"] == cuenta["articulo"]["id"]), None)
    return fila["cantidad"] if fila else 0.0


def test_la_bodega_central_y_la_de_la_finca_se_ven(cliente, cuenta):
    bodegas = cliente.get(f"{API}/bodegas", headers=cuenta["cab"]).json()
    codigos = {b["codigo"] for b in bodegas}
    assert {"BC", "B1"} <= codigos
    central = next(b for b in bodegas if b["codigo"] == "BC")
    assert central["es_central"] is True


def test_entrada_suma_y_calcula_costo(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "entrada",
            "fecha": "2026-09-01",
            "bodega_id": cuenta["central"]["id"],
            "documento": "FAC-001",
            "items": [
                {"articulo_id": cuenta["articulo"]["id"], "cantidad": 400, "costo_unitario": 2500}
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["total"] == 1000000
    assert existencia(cliente, cuenta, cuenta["central"]["id"]) == 400


def test_no_se_puede_sacar_mas_de_lo_que_hay(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "salida",
            "fecha": "2026-09-02",
            "bodega_id": cuenta["central"]["id"],
            "motivo": "consumo",
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 10000}],
        },
    )
    assert respuesta.status_code == 400
    assert "No hay suficiente" in respuesta.json()["detail"]["mensaje"]
    assert existencia(cliente, cuenta, cuenta["central"]["id"]) == 400


def test_traslado_entre_bodegas(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "traslado",
            "fecha": "2026-09-03",
            "bodega_id": cuenta["central"]["id"],
            "bodega_destino_id": cuenta["bodega_finca"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 150}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert existencia(cliente, cuenta, cuenta["central"]["id"]) == 250
    assert existencia(cliente, cuenta, cuenta["bodega_finca"]["id"]) == 150


def test_salida_descuenta(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "salida",
            "fecha": "2026-09-04",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "motivo": "consumo",
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 50}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert existencia(cliente, cuenta, cuenta["bodega_finca"]["id"]) == 100


def test_ajuste_deja_la_cantidad_contada(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "ajuste",
            "fecha": "2026-09-05",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "motivo": "conteo fisico",
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 92}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["items"][0]["cantidad_aplicada"] == -8
    assert existencia(cliente, cuenta, cuenta["bodega_finca"]["id"]) == 92


def test_el_ajuste_exige_motivo(cliente, cuenta):
    respuesta = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "ajuste",
            "fecha": "2026-09-05",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 10}],
        },
    )
    assert respuesta.status_code == 400


def test_anular_devuelve_las_existencias(cliente, cuenta):
    antes = existencia(cliente, cuenta, cuenta["central"]["id"])
    creado = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "entrada",
            "fecha": "2026-09-06",
            "bodega_id": cuenta["central"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 60, "costo_unitario": 2600}],
        },
    ).json()
    assert existencia(cliente, cuenta, cuenta["central"]["id"]) == antes + 60

    anulado = cliente.post(
        f"{API}/movimientos/{creado['id']}/anular",
        headers=cuenta["cab"],
        json={"motivo": "Se registro dos veces"},
    )
    assert anulado.status_code == 200, anulado.text
    assert anulado.json()["anulado"] is True
    assert anulado.json()["motivo_anulacion"] == "Se registro dos veces"
    assert existencia(cliente, cuenta, cuenta["central"]["id"]) == antes

    # No se puede anular dos veces y el movimiento sigue en la lista
    assert (
        cliente.post(
            f"{API}/movimientos/{creado['id']}/anular", headers=cuenta["cab"], json={"motivo": "otra vez"}
        ).status_code
        == 400
    )
    lista = cliente.get(f"{API}/movimientos", headers=cuenta["cab"]).json()
    assert creado["id"] in [m["id"] for m in lista["datos"]]


def test_no_se_anula_si_ya_se_gasto(cliente, cuenta):
    entrada = cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "entrada",
            "fecha": "2026-09-07",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 20, "costo_unitario": 2500}],
        },
    ).json()
    cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "salida",
            "fecha": "2026-09-07",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "motivo": "consumo",
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 112}],
        },
    )
    respuesta = cliente.post(
        f"{API}/movimientos/{entrada['id']}/anular", headers=cuenta["cab"], json={"motivo": "error"}
    )
    assert respuesta.status_code == 400


def test_no_se_desactiva_una_bodega_con_articulos(cliente, cuenta):
    respuesta = cliente.delete(f"{API}/bodegas/{cuenta['central']['id']}", headers=cuenta["cab"])
    assert respuesta.status_code == 400


def test_alerta_de_stock_minimo(cliente, cuenta):
    categorias = cliente.get(f"{API}/categorias-articulo", headers=cuenta["cab"]).json()
    vacunas = next(c for c in categorias if c["clase"] == "vacuna")
    nuevo = cliente.post(
        f"{API}/articulos",
        headers=cuenta["cab"],
        json={
            "codigo": unico("V")[:30],
            "nombre": "Vacuna Newcastle",
            "categoria_id": vacunas["id"],
            "unidad": "dosis",
            "stock_minimo": 500,
        },
    ).json()

    # Sin existencias y con minimo de 500 dosis, debe salir en la alerta
    bajos = cliente.get(f"{API}/articulos?solo_bajo_minimo=true", headers=cuenta["cab"]).json()
    assert nuevo["id"] in [a["id"] for a in bajos]

    # Con una entrada por encima del minimo deja de aparecer
    cliente.post(
        f"{API}/movimientos",
        headers=cuenta["cab"],
        json={
            "tipo": "entrada",
            "fecha": "2026-09-10",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "items": [{"articulo_id": nuevo["id"], "cantidad": 600, "costo_unitario": 900}],
        },
    )
    bajos = cliente.get(f"{API}/articulos?solo_bajo_minimo=true", headers=cuenta["cab"]).json()
    assert nuevo["id"] not in [a["id"] for a in bajos]


def test_otra_cuenta_no_ve_ni_mueve_nada(cliente, cuenta, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaInvB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/bodegas", headers=cab).json() == []
    assert cliente.get(f"{API}/articulos", headers=cab).json() == []
    assert cliente.get(f"{API}/existencias", headers=cab).json() == []

    intento = cliente.post(
        f"{API}/movimientos",
        headers=cab,
        json={
            "tipo": "entrada",
            "fecha": "2026-09-08",
            "bodega_id": cuenta["central"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 5}],
        },
    )
    assert intento.status_code == 404


def test_el_operario_registra_pero_no_anula(cliente, cuenta):
    email = f"{unico('bodeguero')}@avisena.com"
    creado = cliente.post(
        f"{API}/usuarios",
        headers=cuenta["cab"],
        json={
            "nombres": "Bodeguero",
            "email": email,
            "rol": "operario",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "fincas": [{"finca_id": cuenta["finca_id"], "solo_lectura": False}],
        },
    )
    assert creado.status_code == 201, creado.text
    token = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()["token"]
    cab = cabeceras(token, finca_id=cuenta["finca_id"])

    movimiento = cliente.post(
        f"{API}/movimientos",
        headers=cab,
        json={
            "tipo": "entrada",
            "fecha": "2026-09-09",
            "bodega_id": cuenta["bodega_finca"]["id"],
            "items": [{"articulo_id": cuenta["articulo"]["id"], "cantidad": 10, "costo_unitario": 2500}],
        },
    )
    assert movimiento.status_code == 201, movimiento.text

    anular = cliente.post(
        f"{API}/movimientos/{movimiento.json()['id']}/anular", headers=cab, json={"motivo": "no deberia"}
    )
    assert anular.status_code == 403
    # Tampoco crea bodegas ni articulos
    assert cliente.post(f"{API}/bodegas", headers=cab, json={"codigo": "X1", "nombre": "No"}).status_code == 403
