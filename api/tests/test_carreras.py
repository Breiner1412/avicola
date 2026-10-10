"""Dos clics (o dos personas) a la vez no duplican turnos, anulaciones ni importaciones.

Cada prueba lanza la misma peticion varias veces en paralelo y revisa que solo una
tenga efecto. Sin los bloqueos (SELECT ... FOR UPDATE) estas pruebas fallan de forma
intermitente.
"""

import io
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from openpyxl import Workbook

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import CLAVE, crear_cuenta_completa

EN_PARALELO = 6


def a_la_vez(funcion, veces: int = EN_PARALELO) -> list:
    """Corre la funcion en varios hilos que arrancan juntos y devuelve los codigos."""
    salida = threading.Barrier(veces)

    def correr(_):
        salida.wait()
        return funcion()

    with ThreadPoolExecutor(max_workers=veces) as hilos:
        return [r.status_code for r in hilos.map(correr, range(veces))]


@pytest.fixture(scope="module")
def granja(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "Carreras")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    galpon = cliente.post(f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "G1", "capacidad": 5000}).json()
    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={"codigo": "L1", "galpon_id": galpon["id"], "fecha_ingreso": "2026-01-05", "aves_iniciales": 1000},
    ).json()
    aaa = next(t for t in cliente.get(f"{API}/tipos-huevo", headers=cab).json() if t["nombre"] == "AAA")
    cliente.post(
        f"{API}/produccion",
        headers=cab,
        json={"lote_id": lote["id"], "fecha": "2026-06-02", "detalles": [{"tipo_huevo_id": aaa["id"], "cantidad": 3000}]},
    )
    punto = cliente.post(
        f"{API}/puntos-venta", headers=cab, json={"codigo": "PV", "nombre": "Punto", "finca_id": datos["finca_id"]}
    ).json()
    panal = cliente.post(
        f"{API}/productos-venta",
        headers=cab,
        json={"nombre": "Panal AAA", "clase": "huevo", "presentacion": "panal", "tipo_huevo_id": aaa["id"], "precio": 18000},
    ).json()

    email = f"{unico('cajero')}@avicola.com"
    cliente.post(
        f"{API}/usuarios",
        headers=cab,
        json={"nombres": "Cajero", "email": email, "rol": "cajero", "clave": CLAVE, "debe_cambiar_clave": False,
              "fincas": [{"finca_id": datos["finca_id"], "solo_lectura": False}]},
    )
    token_cajero = cliente.post(f"{API}/auth/login", json={"email": email, "clave": CLAVE}).json()["token"]

    bodega = cliente.post(f"{API}/bodegas", headers=cab, json={"codigo": "B1", "nombre": "Bodega"}).json()
    categoria = cliente.get(f"{API}/categorias-articulo", headers=cab).json()[0]
    articulo = cliente.post(
        f"{API}/articulos",
        headers=cab,
        json={"codigo": "ART1", "nombre": "Concentrado", "categoria_id": categoria["id"], "unidad": "kg"},
    ).json()

    datos.update({
        "cab": cab,
        "cab_cajero": cabeceras(token_cajero, finca_id=datos["finca_id"]),
        "lote": lote,
        "aaa": aaa,
        "punto": punto,
        "panal": panal,
        "bodega": bodega,
        "articulo": articulo,
    })
    return datos


def stock_aaa(cliente, granja) -> int:
    filas = cliente.get(f"{API}/stock-huevos", headers=granja["cab"]).json()
    return next(f["cantidad"] for f in filas if f["tipo"] == "AAA")


def existencia(cliente, granja) -> float:
    filas = cliente.get(f"{API}/existencias", headers=granja["cab"], params={"bodega_id": granja["bodega"]["id"]}).json()
    return next((f["cantidad"] for f in filas if f["articulo_id"] == granja["articulo"]["id"]), 0)


def test_dos_aperturas_a_la_vez_dejan_una_sola_caja(cliente, granja):
    codigos = a_la_vez(
        lambda: cliente.post(
            f"{API}/caja/abrir",
            headers=granja["cab_cajero"],
            json={"punto_venta_id": granja["punto"]["id"], "base_inicial": 10000},
        )
    )
    assert codigos.count(201) == 1, codigos
    turnos = cliente.get(f"{API}/caja/turnos", headers=granja["cab"]).json()
    assert sum(1 for t in turnos if t["estado"] == "abierto") == 1


def test_anular_la_misma_venta_a_la_vez_devuelve_el_huevo_una_vez(cliente, granja):
    venta = cliente.post(
        f"{API}/ventas", headers=granja["cab_cajero"], json={"items": [{"producto_id": granja["panal"]["id"], "cantidad": 2}]}
    )
    assert venta.status_code == 201, venta.text
    antes = stock_aaa(cliente, granja)

    codigos = a_la_vez(
        lambda: cliente.post(
            f"{API}/ventas/{venta.json()['id']}/anular",
            headers=granja["cab_cajero"],
            json={"motivo": "doble clic en anular"},
        )
    )
    assert codigos.count(200) == 1, codigos
    assert stock_aaa(cliente, granja) == antes + 60


def test_vender_mientras_se_cierra_la_caja_no_descuadra_el_cierre(cliente, granja):
    def vender():
        return cliente.post(
            f"{API}/ventas", headers=granja["cab_cajero"], json={"items": [{"producto_id": granja["panal"]["id"], "cantidad": 1}]}
        )

    def cerrar():
        return cliente.post(f"{API}/caja/cerrar", headers=granja["cab_cajero"], json={"efectivo_contado": 0})

    acciones = [cerrar] + [vender] * (EN_PARALELO - 1)
    barrera = threading.Barrier(len(acciones))

    def correr(accion):
        barrera.wait()
        return accion()

    with ThreadPoolExecutor(max_workers=len(acciones)) as hilos:
        list(hilos.map(correr, acciones))

    turno = next(t for t in cliente.get(f"{API}/caja/turnos", headers=granja["cab"]).json() if t["estado"] == "cerrado")
    # La diferencia guardada al cerrar cuadra con lo que el turno vendio: ninguna venta entro despues
    assert turno["diferencia"] == pytest.approx(0 - turno["esperado_en_caja"])


def test_anular_el_mismo_movimiento_de_inventario_a_la_vez(cliente, granja):
    entrada = cliente.post(
        f"{API}/movimientos",
        headers=granja["cab"],
        json={"tipo": "entrada", "fecha": "2026-06-01", "bodega_id": granja["bodega"]["id"],
              "items": [{"articulo_id": granja["articulo"]["id"], "cantidad": 100, "costo_unitario": 10}]},
    )
    assert entrada.status_code == 201, entrada.text
    antes = existencia(cliente, granja)

    codigos = a_la_vez(
        lambda: cliente.post(
            f"{API}/movimientos/{entrada.json()['id']}/anular", headers=granja["cab"], json={"motivo": "doble clic"}
        )
    )
    assert codigos.count(200) == 1, codigos
    assert existencia(cliente, granja) == antes - 100


def test_aplicar_y_revertir_la_misma_importacion_a_la_vez(cliente, granja):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Codigo", "Nombre", "Unidad"])
    codigos_articulos = [unico("IMP")[:20] for _ in range(3)]
    for codigo in codigos_articulos:
        hoja.append([codigo, f"Articulo {codigo}", "kg"])
    memoria = io.BytesIO()
    libro.save(memoria)

    subida = cliente.post(
        f"{API}/importacion/analizar",
        headers=granja["cab"],
        data={"tipo": "articulos"},
        files={"archivo": ("art.xlsx", memoria.getvalue(), "application/octet-stream")},
    ).json()
    cuerpo = {"mapeo": subida["mapeo_sugerido"]}

    codigos = a_la_vez(
        lambda: cliente.post(f"{API}/importacion/{subida['id']}/aplicar", headers=granja["cab"], json=cuerpo)
    )
    assert codigos.count(200) == 1, codigos
    articulos = cliente.get(f"{API}/articulos", headers=granja["cab"]).json()
    assert sum(1 for a in articulos if a["codigo"] in codigos_articulos) == 3

    codigos = a_la_vez(lambda: cliente.post(f"{API}/importacion/{subida['id']}/revertir", headers=granja["cab"]))
    assert codigos.count(200) == 1, codigos


def test_ver_los_avisos_a_la_vez_no_falla(cliente, granja):
    codigos = a_la_vez(lambda: cliente.get(f"{API}/alertas", headers=granja["cab"]))
    assert codigos == [200] * EN_PARALELO


def test_refrescar_la_sesion_a_la_vez_rota_el_token_una_sola_vez(cliente, granja):
    from fastapi.testclient import TestClient

    from app.core.config import config as ajustes
    from app.main import app

    navegador = TestClient(app)
    navegador.post(f"{API}/auth/login", json={"email": granja["email"], "clave": CLAVE})
    cookie = navegador.cookies.get(ajustes.cookie_refresco)

    def refrescar():
        pestana = TestClient(app)
        pestana.cookies.set(ajustes.cookie_refresco, cookie, path="/api/v1/auth")
        return pestana.post(f"{API}/auth/refrescar")

    salida = threading.Barrier(EN_PARALELO)

    def correr(_):
        salida.wait()
        return refrescar()

    with ThreadPoolExecutor(max_workers=EN_PARALELO) as hilos:
        respuestas = list(hilos.map(correr, range(EN_PARALELO)))
    assert [r.status_code for r in respuestas] == [200] * EN_PARALELO
    # Solo una entrega un token nuevo; las demas usan el margen de gracia
    assert sum(1 for r in respuestas if "set-cookie" in r.headers) == 1
