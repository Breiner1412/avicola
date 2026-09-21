"""Tareas, rutinas, novedades y reportes."""

from datetime import date, timedelta

import pytest

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa

HOY = date.today().isoformat()


@pytest.fixture(scope="module")
def finca(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaTrabajo")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    galpon = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "Galpon 1", "capacidad": 1000}
    ).json()
    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={"codigo": "L1", "galpon_id": galpon["id"], "fecha_ingreso": "2026-01-05", "aves_iniciales": 400},
    ).json()

    email = f"{unico('operario')}@avicola.com"
    operario = cliente.post(
        f"{API}/usuarios",
        headers=cab,
        json={
            "nombres": "Operario",
            "email": email,
            "rol": "operario",
            "clave": CLAVE,
            "debe_cambiar_clave": False,
            "fincas": [{"finca_id": datos["finca_id"], "solo_lectura": False}],
        },
    ).json()
    token = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()["token"]

    datos.update(
        {
            "cab": cab,
            "cab_operario": cabeceras(token, finca_id=datos["finca_id"]),
            "galpon": galpon,
            "lote": lote,
            "operario": operario,
        }
    )
    return datos


def test_crear_y_asignar_una_tarea(cliente, finca):
    respuesta = cliente.post(
        f"{API}/tareas",
        headers=finca["cab"],
        json={
            "titulo": "Lavar los bebederos",
            "descripcion": "Galpon 1, antes del mediodia",
            "fecha": HOY,
            "prioridad": "alta",
            "asignado_a": finca["operario"]["id"],
            "galpon_id": finca["galpon"]["id"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    tarea = respuesta.json()
    assert tarea["estado"] == "pendiente"
    assert tarea["asignado_nombre"].startswith("Operario")
    finca["tarea"] = tarea


def test_el_operario_solo_ve_sus_tareas(cliente, finca):
    otra = cliente.post(
        f"{API}/tareas",
        headers=finca["cab"],
        json={"titulo": "Revisar la cerca del lote", "fecha": HOY},
    ).json()

    mias = cliente.get(f"{API}/tareas", headers=finca["cab_operario"]).json()
    ids = [t["id"] for t in mias]
    assert finca["tarea"]["id"] in ids
    assert otra["id"] not in ids
    finca["tarea_ajena"] = otra


def test_el_operario_marca_su_tarea_como_hecha(cliente, finca):
    respuesta = cliente.patch(
        f"{API}/tareas/{finca['tarea']['id']}",
        headers=finca["cab_operario"],
        json={"estado": "hecha", "notas": "Quedaron limpios"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "hecha"
    assert respuesta.json()["terminada_por"].startswith("Operario")


def test_el_operario_no_cambia_el_titulo_ni_tareas_ajenas(cliente, finca):
    solo_estado = cliente.patch(
        f"{API}/tareas/{finca['tarea']['id']}", headers=finca["cab_operario"], json={"titulo": "Otro titulo"}
    )
    assert solo_estado.status_code == 403

    ajena = cliente.patch(
        f"{API}/tareas/{finca['tarea_ajena']['id']}", headers=finca["cab_operario"], json={"estado": "hecha"}
    )
    assert ajena.status_code == 403


def test_rutina_diaria_genera_la_tarea_una_sola_vez(cliente, finca):
    rutina = cliente.post(
        f"{API}/rutinas",
        headers=finca["cab"],
        json={
            "titulo": "Recoger huevos de la tarde",
            "frecuencia": "diaria",
            "hora": "16:00",
            "asignado_a": finca["operario"]["id"],
        },
    )
    assert rutina.status_code == 201, rutina.text

    primera = cliente.post(f"{API}/rutinas/generar", headers=finca["cab"], json={}).json()
    assert primera["creadas"] >= 1

    segunda = cliente.post(f"{API}/rutinas/generar", headers=finca["cab"], json={}).json()
    assert segunda["creadas"] == 0

    tareas = cliente.get(f"{API}/tareas?desde={HOY}&hasta={HOY}", headers=finca["cab"]).json()
    generadas = [t for t in tareas if t["titulo"] == "Recoger huevos de la tarde"]
    assert len(generadas) == 1
    assert generadas[0]["creado_por"] == "Rutina"


def test_rutina_semanal_solo_en_sus_dias(cliente, finca):
    manana = date.today() + timedelta(days=1)
    dia_que_no_toca = (manana.weekday() + 2) % 7

    cliente.post(
        f"{API}/rutinas",
        headers=finca["cab"],
        json={"titulo": "Fumigar el galpon", "frecuencia": "semanal", "dias_semana": [dia_que_no_toca]},
    )
    resultado = cliente.post(f"{API}/rutinas/generar", headers=finca["cab"], json={"fecha": manana.isoformat()}).json()
    tareas = cliente.get(
        f"{API}/tareas?desde={manana.isoformat()}&hasta={manana.isoformat()}", headers=finca["cab"]
    ).json()
    assert not any(t["titulo"] == "Fumigar el galpon" for t in tareas)
    assert resultado["creadas"] >= 0


def test_la_rutina_semanal_exige_dias(cliente, finca):
    respuesta = cliente.post(
        f"{API}/rutinas", headers=finca["cab"], json={"titulo": "Sin dias", "frecuencia": "semanal"}
    )
    assert respuesta.status_code == 400


def test_novedad_de_clima_que_mata_aves(cliente, finca):
    antes = cliente.get(f"{API}/lotes/{finca['lote']['id']}", headers=finca["cab"]).json()

    respuesta = cliente.post(
        f"{API}/novedades",
        headers=finca["cab"],
        json={
            "fecha": HOY,
            "categoria": "clima",
            "subtipo": "vendaval",
            "titulo": "Se volo parte del techo del galpon 1",
            "descripcion": "Entro agua y murieron aves",
            "gravedad": "alta",
            "lote_id": finca["lote"]["id"],
            "aves_afectadas": 25,
            "descontar_aves": True,
            "costo_estimado": 1200000,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    novedad = respuesta.json()
    assert novedad["estado"] == "abierta"
    assert novedad["aves_afectadas"] == 25

    despues = cliente.get(f"{API}/lotes/{finca['lote']['id']}", headers=finca["cab"]).json()
    assert despues["aves_actuales"] == antes["aves_actuales"] - 25

    movimientos = cliente.get(
        f"{API}/movimientos-aves?lote_id={finca['lote']['id']}", headers=finca["cab"]
    ).json()
    assert any(m["tipo"] == "muerte" and m["cantidad"] == 25 for m in movimientos)
    finca["novedad"] = novedad


def test_no_se_descuentan_mas_aves_de_las_que_hay(cliente, finca):
    respuesta = cliente.post(
        f"{API}/novedades",
        headers=finca["cab"],
        json={
            "fecha": HOY,
            "categoria": "animales",
            "titulo": "Ataque de perros",
            "lote_id": finca["lote"]["id"],
            "aves_afectadas": 5000,
            "descontar_aves": True,
        },
    )
    assert respuesta.status_code == 400


def test_cerrar_una_novedad(cliente, finca):
    respuesta = cliente.post(
        f"{API}/novedades/{finca['novedad']['id']}/cerrar",
        headers=finca["cab"],
        json={"acciones": "Se cambiaron las tejas y se reforzo la estructura"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "cerrada"
    assert respuesta.json()["cerrada_por"]

    assert (
        cliente.post(
            f"{API}/novedades/{finca['novedad']['id']}/cerrar", headers=finca["cab"], json={}
        ).status_code
        == 400
    )

    abiertas = cliente.get(f"{API}/novedades?estado=abierta", headers=finca["cab"]).json()
    assert finca["novedad"]["id"] not in [n["id"] for n in abiertas]


def test_el_operario_reporta_novedades(cliente, finca):
    respuesta = cliente.post(
        f"{API}/novedades",
        headers=finca["cab_operario"],
        json={
            "fecha": HOY,
            "categoria": "servicios",
            "titulo": "Se fue la luz toda la manana",
            "gravedad": "media",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["reportado_por"].startswith("Operario")


def test_reporte_resumen(cliente, finca):
    resumen = cliente.get(f"{API}/reportes/resumen", headers=finca["cab"]).json()

    assert resumen["aves"]["vivas"] > 0
    assert resumen["aves"]["muertes"] >= 25
    assert resumen["trabajo"]["tareas_pendientes"] >= 1
    assert resumen["trabajo"]["novedades_abiertas"] >= 1
    assert "por_tipo" in resumen["produccion"]
    assert resumen["dias"] >= 1


def test_descargar_reportes_en_csv(cliente, finca):
    for tipo in ("produccion", "ventas", "aves", "alimento", "existencias", "novedades", "tareas"):
        respuesta = cliente.get(f"{API}/reportes/csv?tipo={tipo}", headers=finca["cab"])
        assert respuesta.status_code == 200, f"{tipo}: {respuesta.text}"
        assert "text/csv" in respuesta.headers["content-type"]
        assert "attachment" in respuesta.headers["content-disposition"]

    aves = cliente.get(f"{API}/reportes/csv?tipo=aves", headers=finca["cab"]).text
    assert "Fecha;Lote;Tipo;Cantidad" in aves
    assert "muerte" in aves


def test_un_reporte_que_no_existe(cliente, finca):
    respuesta = cliente.get(f"{API}/reportes/csv?tipo=inventado", headers=finca["cab"])
    assert respuesta.status_code == 400


def test_otra_cuenta_no_ve_tareas_ni_novedades(cliente, finca, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaTrabajoB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/tareas", headers=cab).json() == []
    assert cliente.get(f"{API}/novedades", headers=cab).json() == []
    assert cliente.patch(f"{API}/tareas/{finca['tarea']['id']}", headers=cab, json={"estado": "hecha"}).status_code == 404
