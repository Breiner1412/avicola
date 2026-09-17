"""Lotes de aves, produccion de huevos, alimentacion, pesajes y sanidad."""

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import crear_cuenta_completa


@pytest.fixture(scope="module")
def granja(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaAves")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    galpon = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "Galpon 1", "capacidad": 1000}
    )
    assert galpon.status_code == 201, galpon.text

    bodega = cliente.post(f"{API}/bodegas", headers=cab, json={"codigo": "B1", "nombre": "Bodega"}).json()
    categorias = cliente.get(f"{API}/categorias-articulo", headers=cab).json()
    alimento_cat = next(c for c in categorias if c["clase"] == "alimento")
    vacuna_cat = next(c for c in categorias if c["clase"] == "vacuna")

    alimento = cliente.post(
        f"{API}/articulos",
        headers=cab,
        json={"codigo": unico("AL")[:30], "nombre": "Concentrado", "categoria_id": alimento_cat["id"], "unidad": "kg"},
    ).json()
    vacuna = cliente.post(
        f"{API}/articulos",
        headers=cab,
        json={"codigo": unico("VA")[:30], "nombre": "Newcastle", "categoria_id": vacuna_cat["id"], "unidad": "dosis"},
    ).json()

    cliente.post(
        f"{API}/movimientos",
        headers=cab,
        json={
            "tipo": "entrada",
            "fecha": "2026-01-02",
            "bodega_id": bodega["id"],
            "items": [
                {"articulo_id": alimento["id"], "cantidad": 2000, "costo_unitario": 2500},
                {"articulo_id": vacuna["id"], "cantidad": 1000, "costo_unitario": 100},
            ],
        },
    )

    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={
            "codigo": "L1",
            "galpon_id": galpon.json()["id"],
            "proposito": "postura",
            "fecha_ingreso": "2026-01-05",
            "edad_dias_ingreso": 112,
            "aves_iniciales": 500,
            "costo_ave": 18000,
        },
    )
    assert lote.status_code == 201, lote.text

    datos.update(
        {
            "cab": cab,
            "galpon": galpon.json(),
            "bodega": bodega,
            "alimento": alimento,
            "vacuna": vacuna,
            "lote": lote.json(),
        }
    )
    return datos


def galpon_actual(cliente, granja) -> int:
    galpones = cliente.get(f"{API}/galpones", headers=granja["cab"]).json()
    return next(g for g in galpones if g["id"] == granja["galpon"]["id"])["aves_actuales"]


def lote_actual(cliente, granja) -> dict:
    return cliente.get(f"{API}/lotes/{granja['lote']['id']}", headers=granja["cab"]).json()


def test_el_lote_ocupa_el_galpon(cliente, granja):
    assert granja["lote"]["aves_actuales"] == 500
    assert granja["lote"]["edad_semanas"] >= 16
    assert galpon_actual(cliente, granja) == 500


def test_no_cabe_mas_de_la_capacidad(cliente, granja):
    respuesta = cliente.post(
        f"{API}/lotes",
        headers=granja["cab"],
        json={
            "codigo": "L2",
            "galpon_id": granja["galpon"]["id"],
            "fecha_ingreso": "2026-01-06",
            "aves_iniciales": 900,
        },
    )
    assert respuesta.status_code == 400
    assert "capacidad" in respuesta.json()["detail"]["mensaje"]


def test_mortalidad_descuenta_aves_y_galpon(cliente, granja):
    respuesta = cliente.post(
        f"{API}/movimientos-aves",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-01-10",
            "tipo": "muerte",
            "cantidad": 10,
            "motivo": "golpe de calor",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    lote = lote_actual(cliente, granja)
    assert lote["aves_actuales"] == 490
    assert lote["mortalidad"] == 10
    assert galpon_actual(cliente, granja) == 490


def test_no_se_pueden_sacar_mas_aves_de_las_que_hay(cliente, granja):
    respuesta = cliente.post(
        f"{API}/movimientos-aves",
        headers=granja["cab"],
        json={"lote_id": granja["lote"]["id"], "fecha": "2026-01-11", "tipo": "muerte", "cantidad": 5000},
    )
    assert respuesta.status_code == 400


def test_descarte_deja_las_aves_para_salvamento(cliente, granja):
    respuesta = cliente.post(
        f"{API}/movimientos-aves",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-06-01",
            "tipo": "descarte",
            "cantidad": 40,
            "motivo": "dejaron de producir",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    lote = lote_actual(cliente, granja)
    assert lote["aves_actuales"] == 450
    assert lote["aves_descarte"] == 40
    # siguen en el galpon hasta que se vendan
    assert galpon_actual(cliente, granja) == 490


def test_la_venta_sale_del_descarte(cliente, granja):
    respuesta = cliente.post(
        f"{API}/movimientos-aves",
        headers=granja["cab"],
        json={"lote_id": granja["lote"]["id"], "fecha": "2026-06-05", "tipo": "venta", "cantidad": 15},
    )
    assert respuesta.status_code == 201, respuesta.text
    lote = lote_actual(cliente, granja)
    assert lote["aves_descarte"] == 25
    assert lote["aves_actuales"] == 450
    assert galpon_actual(cliente, granja) == 475


def test_anular_devuelve_las_aves(cliente, granja):
    creado = cliente.post(
        f"{API}/movimientos-aves",
        headers=granja["cab"],
        json={"lote_id": granja["lote"]["id"], "fecha": "2026-06-06", "tipo": "muerte", "cantidad": 7},
    ).json()
    assert lote_actual(cliente, granja)["aves_actuales"] == 443

    anulado = cliente.post(
        f"{API}/movimientos-aves/{creado['id']}/anular",
        headers=granja["cab"],
        json={"motivo": "Se conto mal"},
    )
    assert anulado.status_code == 200, anulado.text
    assert lote_actual(cliente, granja)["aves_actuales"] == 450
    assert galpon_actual(cliente, granja) == 475


def test_produccion_suma_al_stock_de_huevos(cliente, granja):
    tipos = cliente.get(f"{API}/tipos-huevo", headers=granja["cab"]).json()
    aaa = next(t for t in tipos if t["nombre"] == "AAA")
    roto = next(t for t in tipos if t["nombre"] == "Roto")

    respuesta = cliente.post(
        f"{API}/produccion",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-06-07",
            "detalles": [
                {"tipo_huevo_id": aaa["id"], "cantidad": 300},
                {"tipo_huevo_id": roto["id"], "cantidad": 12},
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["total"] == 312
    assert respuesta.json()["comercial"] == 300

    stock = cliente.get(f"{API}/stock-huevos", headers=granja["cab"]).json()
    disponible = {fila["tipo"]: fila["cantidad"] for fila in stock}
    assert disponible.get("AAA") == 300
    # los rotos no entran al stock que se vende
    assert "Roto" not in disponible


def test_corregir_la_produccion_no_duplica_el_stock(cliente, granja):
    tipos = cliente.get(f"{API}/tipos-huevo", headers=granja["cab"]).json()
    aaa = next(t for t in tipos if t["nombre"] == "AAA")

    cliente.post(
        f"{API}/produccion",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-06-07",
            "detalles": [{"tipo_huevo_id": aaa["id"], "cantidad": 280}],
        },
    )
    stock = {f["tipo"]: f["cantidad"] for f in cliente.get(f"{API}/stock-huevos", headers=granja["cab"]).json()}
    assert stock["AAA"] == 280


def test_pesaje_calcula_el_promedio(cliente, granja):
    respuesta = cliente.post(
        f"{API}/pesajes",
        headers=granja["cab"],
        json={"lote_id": granja["lote"]["id"], "fecha": "2026-06-08", "aves_muestra": 10, "peso_total_kg": 18.5},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["peso_promedio_kg"] == 1.85
    assert respuesta.json()["edad_dias"] > 100


def test_el_alimento_sale_de_la_bodega(cliente, granja):
    antes = cliente.get(f"{API}/existencias?bodega_id={granja['bodega']['id']}", headers=granja["cab"]).json()
    disponible = next(f for f in antes if f["articulo_id"] == granja["alimento"]["id"])["cantidad"]

    respuesta = cliente.post(
        f"{API}/consumo-alimento",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-06-08",
            "articulo_id": granja["alimento"]["id"],
            "bodega_id": granja["bodega"]["id"],
            "cantidad": 250,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["costo"] == 625000  # 250 kg x 2500

    despues = cliente.get(f"{API}/existencias?bodega_id={granja['bodega']['id']}", headers=granja["cab"]).json()
    ahora = next(f for f in despues if f["articulo_id"] == granja["alimento"]["id"])["cantidad"]
    assert ahora == disponible - 250


def test_no_se_entrega_alimento_que_no_hay(cliente, granja):
    respuesta = cliente.post(
        f"{API}/consumo-alimento",
        headers=granja["cab"],
        json={
            "lote_id": granja["lote"]["id"],
            "fecha": "2026-06-09",
            "articulo_id": granja["alimento"]["id"],
            "bodega_id": granja["bodega"]["id"],
            "cantidad": 99999,
        },
    )
    assert respuesta.status_code == 400


def test_vacuna_con_descuento_de_bodega(cliente, granja):
    respuesta = cliente.post(
        f"{API}/sanidad",
        headers=granja["cab"],
        json={
            "fecha": "2026-06-10",
            "tipo": "vacuna",
            "producto": "Newcastle La Sota",
            "lote_id": granja["lote"]["id"],
            "articulo_id": granja["vacuna"]["id"],
            "bodega_id": granja["bodega"]["id"],
            "cantidad_usada": 450,
            "via": "agua",
            "dosis": "1 dosis por ave",
            "proximo_refuerzo": "2026-07-10",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["aves_tratadas"] == 450

    existencias = cliente.get(f"{API}/existencias?bodega_id={granja['bodega']['id']}", headers=granja["cab"]).json()
    vacuna = next(f for f in existencias if f["articulo_id"] == granja["vacuna"]["id"])
    assert vacuna["cantidad"] == 550

    proximas = cliente.get(f"{API}/sanidad/proximas?dias=365", headers=granja["cab"]).json()
    assert any(p["producto"] == "Newcastle La Sota" for p in proximas)


def test_balance_del_lote(cliente, granja):
    balance = cliente.get(f"{API}/lotes/{granja['lote']['id']}/balance", headers=granja["cab"]).json()
    assert balance["alimento_kg"] == 250
    assert balance["alimento_costo"] == 625000
    assert balance["huevos_total"] == 292  # 280 comerciales + 12 rotos
    assert balance["huevos_comerciales"] == 280
    assert balance["costo_aves"] == 9000000  # 500 aves x 18000
    assert balance["costo_sanidad"] > 0
    assert balance["costo_por_ave"] > 18000


def test_cerrar_el_lote_exige_sacar_las_aves(cliente, granja):
    respuesta = cliente.post(
        f"{API}/lotes/{granja['lote']['id']}/cerrar", headers=granja["cab"], json={"fecha": "2026-06-30"}
    )
    assert respuesta.status_code == 400
    assert "quedan" in respuesta.json()["detail"]["mensaje"]


def test_otra_cuenta_no_ve_los_lotes(cliente, granja, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaAvesB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/lotes", headers=cab).json() == []
    assert cliente.get(f"{API}/lotes/{granja['lote']['id']}", headers=cab).status_code == 404
    intento = cliente.post(
        f"{API}/movimientos-aves",
        headers=cab,
        json={"lote_id": granja["lote"]["id"], "fecha": "2026-06-11", "tipo": "muerte", "cantidad": 1},
    )
    assert intento.status_code == 404
