"""Caja, ventas de huevos y de aves, descuentos y anulaciones."""

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa


@pytest.fixture(scope="module")
def tienda(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaVentas")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    galpon = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "Galpon 1", "capacidad": 2000}
    ).json()

    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={
            "codigo": "L1",
            "galpon_id": galpon["id"],
            "proposito": "postura",
            "fecha_ingreso": "2026-01-05",
            "aves_iniciales": 600,
            "costo_ave": 18000,
        },
    ).json()
    engorde = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={
            "codigo": "E1",
            "galpon_id": galpon["id"],
            "proposito": "engorde",
            "fecha_ingreso": "2026-05-01",
            "aves_iniciales": 300,
            "costo_ave": 3000,
        },
    ).json()

    # 100 gallinas pasan a descarte
    cliente.post(
        f"{API}/movimientos-aves",
        headers=cab,
        json={"lote_id": lote["id"], "fecha": "2026-06-01", "tipo": "descarte", "cantidad": 100},
    )

    tipos = cliente.get(f"{API}/tipos-huevo", headers=cab).json()
    aaa = next(t for t in tipos if t["nombre"] == "AAA")
    cliente.post(
        f"{API}/produccion",
        headers=cab,
        json={"lote_id": lote["id"], "fecha": "2026-06-02", "detalles": [{"tipo_huevo_id": aaa["id"], "cantidad": 900}]},
    )

    punto = cliente.post(
        f"{API}/puntos-venta",
        headers=cab,
        json={"codigo": "PV1", "nombre": "Punto de la finca", "finca_id": datos["finca_id"]},
    )
    assert punto.status_code == 201, punto.text
    punto = punto.json()

    panal = cliente.post(
        f"{API}/productos-venta",
        headers=cab,
        json={
            "nombre": "Panal de huevo AAA",
            "clase": "huevo",
            "presentacion": "panal",
            "tipo_huevo_id": aaa["id"],
            "precio": 18000,
        },
    ).json()
    unidad = cliente.post(
        f"{API}/productos-venta",
        headers=cab,
        json={"nombre": "Huevo AAA por unidad", "clase": "huevo", "presentacion": "unidad", "tipo_huevo_id": aaa["id"], "precio": 700},
    ).json()
    gallina = cliente.post(
        f"{API}/productos-venta",
        headers=cab,
        json={"nombre": "Gallina de descarte", "clase": "ave_descarte", "presentacion": "unidad", "precio": 12000},
    ).json()
    pollo = cliente.post(
        f"{API}/productos-venta",
        headers=cab,
        json={"nombre": "Pollo en pie", "clase": "ave_engorde", "presentacion": "kg", "precio": 9000},
    ).json()

    # Cajero del punto
    email = f"{unico('cajero')}@avisena.com"
    cliente.post(
        f"{API}/usuarios",
        headers=cab,
        json={
            "nombres": "Cajero",
            "email": email,
            "rol": "cajero",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "fincas": [{"finca_id": datos["finca_id"], "solo_lectura": False}],
        },
    )
    sesion_cajero = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()

    datos.update(
        {
            "cab": cab,
            "cab_cajero": cabeceras(sesion_cajero["token"], finca_id=datos["finca_id"]),
            "galpon": galpon,
            "lote": lote,
            "engorde": engorde,
            "punto": punto,
            "aaa": aaa,
            "panal": panal,
            "unidad": unidad,
            "gallina": gallina,
            "pollo": pollo,
        }
    )
    return datos


def stock_aaa(cliente, tienda) -> int:
    filas = cliente.get(f"{API}/stock-huevos", headers=tienda["cab"]).json()
    fila = next((f for f in filas if f["tipo"] == "AAA"), None)
    return fila["cantidad"] if fila else 0


def lote(cliente, tienda, clave="lote") -> dict:
    return cliente.get(f"{API}/lotes/{tienda[clave]['id']}", headers=tienda["cab"]).json()


def test_sin_caja_abierta_no_se_vende(cliente, tienda):
    respuesta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}]},
    )
    assert respuesta.status_code == 400
    assert "abre la caja" in respuesta.json()["detail"]["mensaje"]


def test_abrir_caja(cliente, tienda):
    respuesta = cliente.post(
        f"{API}/caja/abrir",
        headers=tienda["cab_cajero"],
        json={"punto_venta_id": tienda["punto"]["id"], "base_inicial": 50000},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["estado"] == "abierto"
    assert respuesta.json()["base_inicial"] == 50000
    # no se puede abrir dos veces
    assert (
        cliente.post(
            f"{API}/caja/abrir",
            headers=tienda["cab_cajero"],
            json={"punto_venta_id": tienda["punto"]["id"], "base_inicial": 0},
        ).status_code
        == 400
    )


def test_vender_panales_descuenta_huevos(cliente, tienda):
    antes = stock_aaa(cliente, tienda)
    respuesta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 2}]},
    )
    assert respuesta.status_code == 201, respuesta.text
    venta = respuesta.json()

    assert venta["numero"] == "PV1-000001"
    assert venta["total"] == 36000
    assert venta["detalles"][0]["unidades"] == 60
    assert venta["pagos"][0]["metodo_nombre"] == "Efectivo"
    assert stock_aaa(cliente, tienda) == antes - 60
    tienda["venta_huevos"] = venta


def test_vender_por_unidad(cliente, tienda):
    antes = stock_aaa(cliente, tienda)
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["unidad"]["id"], "cantidad": 3}]},
    ).json()
    assert venta["total"] == 2100
    assert stock_aaa(cliente, tienda) == antes - 3


def test_no_se_venden_huevos_que_no_hay(cliente, tienda):
    respuesta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 100}]},
    )
    assert respuesta.status_code == 400
    assert "huevos" in respuesta.json()["detail"]["mensaje"]


def test_vender_gallinas_de_descarte(cliente, tienda):
    antes = lote(cliente, tienda)
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["gallina"]["id"], "cantidad": 10, "lote_id": tienda["lote"]["id"]}]},
    )
    assert venta.status_code == 201, venta.text
    assert venta.json()["total"] == 120000

    despues = lote(cliente, tienda)
    assert despues["aves_descarte"] == antes["aves_descarte"] - 10
    assert despues["aves_actuales"] == antes["aves_actuales"]
    tienda["venta_gallinas"] = venta.json()


def test_no_se_venden_mas_gallinas_de_descarte_de_las_que_hay(cliente, tienda):
    respuesta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["gallina"]["id"], "cantidad": 500, "lote_id": tienda["lote"]["id"]}]},
    )
    assert respuesta.status_code == 400
    assert "descarte" in respuesta.json()["detail"]["mensaje"]


def test_vender_engorde_por_kilo(cliente, tienda):
    antes = lote(cliente, tienda, "engorde")
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={
            "items": [
                {"producto_id": tienda["pollo"]["id"], "cantidad": 48.5, "aves": 20, "lote_id": tienda["engorde"]["id"]}
            ]
        },
    )
    assert venta.status_code == 201, venta.text
    # 48.5 kg x 9000
    assert venta.json()["total"] == 436500
    assert venta.json()["detalles"][0]["peso_kg"] == 48.5

    despues = lote(cliente, tienda, "engorde")
    assert despues["aves_actuales"] == antes["aves_actuales"] - 20


def test_el_cajero_no_puede_pasarse_del_tope_de_descuento(cliente, tienda):
    respuesta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}], "descuento": 9000},
    )
    assert respuesta.status_code == 400
    assert "descuento maximo" in respuesta.json()["detail"]["mensaje"]

    # dentro del tope si pasa (10% de 18000 = 1800)
    permitido = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}], "descuento": 1500},
    )
    assert permitido.status_code == 201, permitido.text
    assert permitido.json()["total"] == 16500


def test_descuento_en_porcentaje(cliente, tienda):
    # 5% de un panal de 18000 = 900
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}], "descuento_porcentaje": 5},
    )
    assert venta.status_code == 201, venta.text
    assert venta.json()["descuento"] == 900
    assert venta.json()["total"] == 17100

    # el cajero no puede pasar del tope de la cuenta (10%)
    mucho = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}], "descuento_porcentaje": 15},
    )
    assert mucho.status_code == 400
    assert "10%" in mucho.json()["detail"]["mensaje"]


def test_el_tope_de_descuento_se_configura(cliente, tienda):
    ajustes = cliente.get(f"{API}/ventas/ajustes", headers=tienda["cab_cajero"])
    assert ajustes.status_code == 200, ajustes.text
    assert ajustes.json() == {"descuento_maximo": 10, "tengo_tope": True}

    # el cajero no lo puede cambiar
    assert cliente.patch(f"{API}/ventas/ajustes", headers=tienda["cab_cajero"], json={"descuento_maximo": 50}).status_code == 403

    # el propietario si; y desde ahi el cajero puede dar hasta 15%
    cambio = cliente.patch(f"{API}/ventas/ajustes", headers=tienda["cab"], json={"descuento_maximo": 15})
    assert cambio.status_code == 200, cambio.text
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={"items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}], "descuento_porcentaje": 15},
    )
    assert venta.status_code == 201, venta.text
    cliente.patch(f"{API}/ventas/ajustes", headers=tienda["cab"], json={"descuento_maximo": 10})


def test_los_pagos_deben_cuadrar(cliente, tienda):
    metodos = cliente.get(f"{API}/metodos-pago", headers=tienda["cab_cajero"]).json()
    efectivo = next(m for m in metodos if m["es_efectivo"])
    transferencia = next(m for m in metodos if not m["es_efectivo"])

    malo = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={
            "items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}],
            "pagos": [{"metodo_pago_id": efectivo["id"], "monto": 1000}],
        },
    )
    assert malo.status_code == 400

    mixto = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab_cajero"],
        json={
            "items": [{"producto_id": tienda["panal"]["id"], "cantidad": 1}],
            "pagos": [
                {"metodo_pago_id": efectivo["id"], "monto": 8000},
                {"metodo_pago_id": transferencia["id"], "monto": 10000, "referencia": "123"},
            ],
        },
    )
    assert mixto.status_code == 201, mixto.text
    assert len(mixto.json()["pagos"]) == 2


def test_anular_devuelve_los_huevos(cliente, tienda):
    antes = stock_aaa(cliente, tienda)
    venta = tienda["venta_huevos"]

    respuesta = cliente.post(
        f"{API}/ventas/{venta['id']}/anular",
        headers=tienda["cab_cajero"],
        json={"motivo": "El cliente devolvio los panales"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "anulada"
    assert respuesta.json()["anulada_por"]
    assert stock_aaa(cliente, tienda) == antes + 60

    # queda registrada y no se puede anular dos veces
    assert (
        cliente.post(
            f"{API}/ventas/{venta['id']}/anular", headers=tienda["cab_cajero"], json={"motivo": "otra vez"}
        ).status_code
        == 400
    )


def test_anular_devuelve_las_gallinas(cliente, tienda):
    antes = lote(cliente, tienda)
    venta = tienda["venta_gallinas"]

    respuesta = cliente.post(
        f"{API}/ventas/{venta['id']}/anular", headers=tienda["cab_cajero"], json={"motivo": "Se cobro mal"}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert lote(cliente, tienda)["aves_descarte"] == antes["aves_descarte"] + 10


def test_el_cajero_no_anula_ventas_de_otro_turno(cliente, tienda):
    # El administrador vende en su propio turno
    cliente.post(
        f"{API}/caja/abrir", headers=tienda["cab"], json={"punto_venta_id": tienda["punto"]["id"], "base_inicial": 0}
    )
    venta = cliente.post(
        f"{API}/ventas",
        headers=tienda["cab"],
        json={"items": [{"producto_id": tienda["unidad"]["id"], "cantidad": 1}]},
    ).json()

    intento = cliente.post(
        f"{API}/ventas/{venta['id']}/anular", headers=tienda["cab_cajero"], json={"motivo": "no es mia"}
    )
    assert intento.status_code == 403

    # el administrador si puede
    assert (
        cliente.post(
            f"{API}/ventas/{venta['id']}/anular", headers=tienda["cab"], json={"motivo": "prueba"}
        ).status_code
        == 200
    )


def test_cerrar_la_caja_calcula_la_diferencia(cliente, tienda):
    turno = cliente.get(f"{API}/caja/turno", headers=tienda["cab_cajero"]).json()
    esperado = turno["esperado_en_caja"]
    assert turno["ventas"] >= 1

    cerrado = cliente.post(
        f"{API}/caja/cerrar", headers=tienda["cab_cajero"], json={"efectivo_contado": esperado - 5000}
    )
    assert cerrado.status_code == 200, cerrado.text
    assert cerrado.json()["estado"] == "cerrado"
    assert cerrado.json()["diferencia"] == -5000

    # sin turno abierto no se vende
    assert (
        cliente.post(
            f"{API}/ventas",
            headers=tienda["cab_cajero"],
            json={"items": [{"producto_id": tienda["unidad"]["id"], "cantidad": 1}]},
        ).status_code
        == 400
    )


def test_resumen_de_ventas(cliente, tienda):
    resumen = cliente.get(f"{API}/ventas/resumen", headers=tienda["cab"]).json()
    assert resumen["ventas"] >= 1
    assert resumen["total"] > 0
    assert resumen["anuladas"] >= 2
    assert resumen["aves_vendidas"] >= 20


def test_otra_cuenta_no_ve_las_ventas(cliente, tienda, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaVentasB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/puntos-venta", headers=cab).json() == []
    assert cliente.get(f"{API}/productos-venta", headers=cab).json() == []
    assert cliente.get(f"{API}/ventas", headers=cab).json()["total"] == 0
    assert cliente.get(f"{API}/ventas/{tienda['venta_huevos']['id']}", headers=cab).status_code == 404

