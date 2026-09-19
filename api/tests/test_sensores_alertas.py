"""Sensores, lecturas y los avisos de la campana."""

from datetime import date, timedelta

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import crear_cuenta_completa


@pytest.fixture(scope="module")
def finca(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaSensores")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    galpon = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "Galpon 1", "capacidad": 800}
    ).json()

    tipos = cliente.get(f"{API}/tipos-sensor", headers=cab).json()
    temperatura = next(t for t in tipos if t["nombre"] == "Temperatura")

    sensor = cliente.post(
        f"{API}/sensores",
        headers=cab,
        json={
            "codigo": "S1",
            "nombre": "Temperatura galpon 1",
            "tipo_id": temperatura["id"],
            "galpon_id": galpon["id"],
            "min_ok": 18,
            "max_ok": 28,
        },
    )
    assert sensor.status_code == 201, sensor.text

    datos.update({"cab": cab, "galpon": galpon, "tipo": temperatura, "sensor": sensor.json()})
    return datos


def test_los_tipos_de_sensor_vienen_cargados(cliente, finca):
    tipos = cliente.get(f"{API}/tipos-sensor", headers=finca["cab"]).json()
    nombres = {t["nombre"] for t in tipos}
    assert {"Temperatura", "Humedad", "Amoniaco"} <= nombres


def test_un_sensor_nuevo_no_tiene_datos(cliente, finca):
    sensores = cliente.get(f"{API}/sensores", headers=finca["cab"]).json()
    sensor = next(s for s in sensores if s["id"] == finca["sensor"]["id"])
    assert sensor["estado"] == "sin_datos"
    assert sensor["unidad"] == "C"
    assert sensor["galpon_nombre"] == "Galpon 1"


def test_lectura_dentro_del_rango(cliente, finca):
    respuesta = cliente.post(
        f"{API}/sensores/{finca['sensor']['id']}/lecturas", headers=finca["cab"], json={"valor": 24.5}
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["fuera_rango"] is False

    sensores = cliente.get(f"{API}/sensores", headers=finca["cab"]).json()
    sensor = next(s for s in sensores if s["id"] == finca["sensor"]["id"])
    assert sensor["estado"] == "ok"
    assert sensor["ultimo_valor"] == 24.5
    assert sensor["historial"] == [24.5]


def test_lectura_alta_marca_fuera_de_rango(cliente, finca):
    respuesta = cliente.post(
        f"{API}/sensores/{finca['sensor']['id']}/lecturas", headers=finca["cab"], json={"valor": 33.2}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["fuera_rango"] is True

    sensores = cliente.get(f"{API}/sensores", headers=finca["cab"]).json()
    sensor = next(s for s in sensores if s["id"] == finca["sensor"]["id"])
    assert sensor["estado"] == "alto"


def test_historial_de_lecturas(cliente, finca):
    lecturas = cliente.get(f"{API}/sensores/{finca['sensor']['id']}/lecturas?horas=48", headers=finca["cab"]).json()
    assert len(lecturas) >= 2
    assert lecturas[0]["valor"] == 33.2


def test_la_campana_avisa_del_sensor(cliente, finca):
    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()
    sensor = [a for a in alertas["alertas"] if a["tipo"] == "sensor"]
    assert sensor, alertas
    assert sensor[0]["nivel"] == "critico"
    assert "fuera de rango" in sensor[0]["titulo"]
    assert sensor[0]["ruta"] == "/sensores"
    assert alertas["sin_leer"] >= 1


def test_el_aviso_se_cierra_solo_cuando_se_arregla(cliente, finca):
    cliente.post(f"{API}/sensores/{finca['sensor']['id']}/lecturas", headers=finca["cab"], json={"valor": 25})
    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()
    assert not [a for a in alertas["alertas"] if a["tipo"] == "sensor"]


def test_avisa_de_tareas_atrasadas_y_stock_bajo(cliente, finca):
    ayer = (date.today() - timedelta(days=3)).isoformat()
    cliente.post(f"{API}/tareas", headers=finca["cab"], json={"titulo": "Revisar el techo", "fecha": ayer})

    bodega = cliente.post(f"{API}/bodegas", headers=finca["cab"], json={"codigo": "B1", "nombre": "Bodega"}).json()
    categorias = cliente.get(f"{API}/categorias-articulo", headers=finca["cab"]).json()
    cliente.post(
        f"{API}/articulos",
        headers=finca["cab"],
        json={
            "codigo": unico("A")[:30],
            "nombre": "Concentrado",
            "categoria_id": categorias[0]["id"],
            "unidad": "kg",
            "stock_minimo": 200,
        },
    )
    assert bodega["id"]

    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()
    tipos = {a["tipo"] for a in alertas["alertas"]}
    assert "tarea" in tipos
    assert "stock" in tipos
    assert alertas["total"] >= 2


def test_marcar_los_avisos_como_vistos(cliente, finca):
    assert cliente.post(f"{API}/alertas/leidas", headers=finca["cab"]).status_code == 200
    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()
    assert alertas["sin_leer"] == 0
    assert alertas["total"] >= 1


def test_otra_cuenta_no_ve_sensores_ni_avisos(cliente, finca, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaSensoresB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/sensores", headers=cab).json() == []
    assert cliente.get(f"{API}/alertas", headers=cab).json()["total"] == 0
    assert (
        cliente.post(f"{API}/sensores/{finca['sensor']['id']}/lecturas", headers=cab, json={"valor": 10}).status_code
        == 404
    )


def test_el_refuerzo_ya_hecho_no_sigue_avisando(cliente, finca):
    hace = lambda dias: (date.today() - timedelta(days=dias)).isoformat()  # noqa: E731
    base = {"tipo": "desinfeccion", "producto": "Yodo agricola", "galpon_id": finca["galpon"]["id"], "via": "aspersion"}

    primera = cliente.post(f"{API}/sanidad", headers=finca["cab"], json={**base, "fecha": hace(40), "proximo_refuerzo": hace(10)})
    assert primera.status_code == 201, primera.text
    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()["alertas"]
    assert any(a["tipo"] == "sanidad" and "Yodo" in a["titulo"] for a in alertas)

    # Se hizo el refuerzo: el aviso viejo se cierra y la lista de proximos queda limpia
    segunda = cliente.post(f"{API}/sanidad", headers=finca["cab"], json={**base, "fecha": hace(8)})
    assert segunda.status_code == 201, segunda.text
    alertas = cliente.get(f"{API}/alertas", headers=finca["cab"]).json()["alertas"]
    assert not any(a["tipo"] == "sanidad" and "Yodo" in a["titulo"] for a in alertas)
    proximas = cliente.get(f"{API}/sanidad/proximas", headers=finca["cab"]).json()
    assert not any(p["producto"] == "Yodo agricola" for p in proximas)


def test_lecturas_por_periodo(cliente, finca):
    from datetime import datetime, timezone

    sensor_id = finca["sensor"]["id"]
    ahora = datetime.now(timezone.utc)
    hace_una_hora = (ahora - timedelta(hours=1)).isoformat()
    en_una_hora = (ahora + timedelta(hours=1)).isoformat()

    dentro = cliente.get(
        f"{API}/sensores/{sensor_id}/lecturas", headers=finca["cab"], params={"desde": hace_una_hora, "hasta": en_una_hora}
    )
    assert dentro.status_code == 200, dentro.text
    assert len(dentro.json()) >= 1

    antes = cliente.get(
        f"{API}/sensores/{sensor_id}/lecturas",
        headers=finca["cab"],
        params={"desde": (ahora - timedelta(days=3)).isoformat(), "hasta": (ahora - timedelta(days=2)).isoformat()},
    )
    assert antes.status_code == 200
    assert antes.json() == []


def test_los_equipos_envian_varias_mediciones_por_codigo(cliente, finca):
    respuesta = cliente.post(
        f"{API}/sensores/lecturas",
        headers=finca["cab"],
        json={
            "lecturas": [
                {"codigo": "S1", "valor": 22.5},
                {"codigo": "S1", "valor": 23.1, "medido_en": "2026-01-10T12:00:00-05:00"},
                {"codigo": "NO-EXISTE", "valor": 1},
            ]
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json() == {"guardadas": 2, "codigos_desconocidos": ["NO-EXISTE"]}

    # la hora con zona se guarda en UTC
    lecturas = cliente.get(
        f"{API}/sensores/{finca['sensor']['id']}/lecturas",
        headers=finca["cab"],
        params={"desde": "2026-01-10T00:00:00Z", "hasta": "2026-01-11T00:00:00Z"},
    ).json()
    assert [l["medido_en"][:16] for l in lecturas] == ["2026-01-10T17:00"]
    assert lecturas[0]["origen"] == "dispositivo"
