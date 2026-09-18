"""Importar datos desde un archivo de Excel sin formato predefinido."""

import io

import pytest
from openpyxl import Workbook

from tests.conftest import API, cabeceras, unico
from tests.test_multicuenta import crear_cuenta_completa


def excel(encabezados: list[str], filas: list[list]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Inventario de la finca"])  # fila suelta antes del encabezado
    hoja.append(encabezados)
    for fila in filas:
        hoja.append(fila)
    memoria = io.BytesIO()
    libro.save(memoria)
    return memoria.getvalue()


@pytest.fixture(scope="module")
def finca(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "CuentaImport")
    cab = cabeceras(datos["token"], finca_id=datos["finca_id"])

    bodega = cliente.post(f"{API}/bodegas", headers=cab, json={"codigo": "B1", "nombre": "Bodega"}).json()
    galpon = cliente.post(
        f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "Galpon 1", "capacidad": 1000}
    ).json()
    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={"codigo": "L1", "galpon_id": galpon["id"], "fecha_ingreso": "2026-01-05", "aves_iniciales": 500},
    ).json()

    datos.update({"cab": cab, "bodega": bodega, "galpon": galpon, "lote": lote})
    return datos


def subir(cliente, finca, tipo: str, contenido: bytes, nombre="archivo.xlsx"):
    return cliente.post(
        f"{API}/importacion/analizar",
        headers=finca["cab"],
        data={"tipo": tipo},
        files={"archivo": (nombre, contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def test_los_tipos_traen_sus_campos(cliente, finca):
    tipos = cliente.get(f"{API}/importacion/tipos", headers=finca["cab"]).json()
    claves = {t["clave"] for t in tipos}
    assert {"articulos", "entrada_inventario", "proveedores", "sanidad", "produccion"} <= claves
    articulos = next(t for t in tipos if t["clave"] == "articulos")
    assert any(c["clave"] == "codigo" and c["obligatorio"] for c in articulos["campos"])


def test_adivina_las_columnas_aunque_tengan_otro_nombre(cliente, finca):
    contenido = excel(
        ["CÓDIGO", "DESCRIPCIÓN DEL PRODUCTO", "UND", "CANTIDAD", "VR UNITARIO", "PROVEEDOR", "FECHA"],
        [["AL-01", "Concentrado ponedora", "kg", 500, 2500, "Agroinsumos SAS", "2026-02-01"]],
    )
    respuesta = subir(cliente, finca, "entrada_inventario", contenido)
    assert respuesta.status_code == 201, respuesta.text
    analisis = respuesta.json()

    assert analisis["filas_totales"] == 1
    assert "CÓDIGO" in analisis["columnas"]
    sugerido = analisis["mapeo_sugerido"]
    assert sugerido["codigo"] == "CÓDIGO"
    assert sugerido["articulo"] == "DESCRIPCIÓN DEL PRODUCTO"
    assert sugerido["cantidad"] == "CANTIDAD"
    assert sugerido["costo_unitario"] == "VR UNITARIO"
    assert sugerido["proveedor"] == "PROVEEDOR"
    finca["analisis_entrada"] = analisis


def test_validar_muestra_los_errores_sin_guardar_nada(cliente, finca):
    contenido = excel(
        ["Codigo", "Articulo", "Cantidad", "Costo"],
        [
            ["AL-01", "Concentrado ponedora", 500, 2500],
            ["VI-01", "Vacuna Newcastle", "mil", 900],   # cantidad invalida
            ["", "", "", ""],                              # fila vacia se ignora al leer
            ["AL-02", "", 100, 1000],                      # falta el articulo
        ],
    )
    analisis = subir(cliente, finca, "entrada_inventario", contenido).json()
    finca["importacion"] = analisis["id"]

    validacion = cliente.post(
        f"{API}/importacion/{analisis['id']}/validar",
        headers=finca["cab"],
        json={"mapeo": analisis["mapeo_sugerido"], "opciones": {"bodega_id": finca["bodega"]["id"]}},
    )
    assert validacion.status_code == 200, validacion.text
    datos = validacion.json()
    assert datos["filas_ok"] == 1
    assert datos["filas_error"] == 2
    assert any("numero" in error for error in datos["errores"])

    # todavia no hay nada en el inventario
    assert cliente.get(f"{API}/articulos", headers=finca["cab"]).json() == []


def test_falta_indicar_una_columna_obligatoria(cliente, finca):
    respuesta = cliente.post(
        f"{API}/importacion/{finca['importacion']}/validar",
        headers=finca["cab"],
        json={"mapeo": {"cantidad": "Cantidad"}, "opciones": {}},
    )
    assert respuesta.status_code == 400
    assert "Articulo" in respuesta.json()["detail"]["mensaje"]


def test_aplicar_crea_articulos_proveedor_y_entrada(cliente, finca):
    contenido = excel(
        ["Codigo", "Articulo", "Unidad", "Cantidad", "Costo", "Proveedor", "Fecha", "Factura"],
        [
            ["AL-01", "Concentrado ponedora", "kg", 500, 2500, "Agroinsumos SAS", "2026-02-01", "FAC-100"],
            ["VI-01", "Vacuna Newcastle", "dosis", 1000, 900, "Agroinsumos SAS", "2026-02-01", "FAC-100"],
        ],
    )
    analisis = subir(cliente, finca, "entrada_inventario", contenido).json()
    cuerpo = {
        "mapeo": analisis["mapeo_sugerido"],
        "opciones": {"bodega_id": finca["bodega"]["id"], "crear_articulos": True},
    }

    aplicado = cliente.post(f"{API}/importacion/{analisis['id']}/aplicar", headers=finca["cab"], json=cuerpo)
    assert aplicado.status_code == 200, aplicado.text
    datos = aplicado.json()
    assert datos["estado"] == "aplicada"
    assert datos["filas_ok"] == 2
    assert datos["resumen"]["movimientos"] == 1  # misma fecha y factura: un solo movimiento

    articulos = cliente.get(f"{API}/articulos", headers=finca["cab"]).json()
    assert {a["codigo"] for a in articulos} == {"AL-01", "VI-01"}
    assert next(a for a in articulos if a["codigo"] == "AL-01")["existencia_total"] == 500

    proveedores = cliente.get(f"{API}/proveedores", headers=finca["cab"]).json()
    assert any(p["nombre"] == "Agroinsumos SAS" for p in proveedores)

    finca["importacion_aplicada"] = analisis["id"]


def test_no_se_aplica_dos_veces(cliente, finca):
    respuesta = cliente.post(
        f"{API}/importacion/{finca['importacion_aplicada']}/aplicar",
        headers=finca["cab"],
        json={"mapeo": {}, "opciones": {}},
    )
    assert respuesta.status_code == 400


def test_deshacer_devuelve_el_inventario(cliente, finca):
    respuesta = cliente.post(
        f"{API}/importacion/{finca['importacion_aplicada']}/revertir", headers=finca["cab"], json={}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "revertida"

    # los articulos que se crearon con la importacion quedan desactivados
    articulos = cliente.get(f"{API}/articulos", headers=finca["cab"]).json()
    assert articulos == []
    inactivos = cliente.get(f"{API}/articulos?incluir_inactivos=true", headers=finca["cab"]).json()
    assert all(a["existencia_total"] == 0 for a in inactivos)

    movimientos = cliente.get(f"{API}/movimientos", headers=finca["cab"]).json()
    assert all(m["anulado"] for m in movimientos["datos"])


def test_importar_produccion_de_huevos(cliente, finca):
    contenido = excel(
        ["Dia", "Lote", "Tamaño", "Huevos"],
        [
            ["2026-03-01", "L1", "AAA", 320],
            ["2026-03-01", "L1", "AA", 150],
            ["2026-03-02", "L9", "AAA", 100],  # lote que no existe
        ],
    )
    analisis = subir(cliente, finca, "produccion", contenido).json()
    assert analisis["mapeo_sugerido"]["tipo_huevo"] == "Tamaño"

    aplicado = cliente.post(
        f"{API}/importacion/{analisis['id']}/aplicar",
        headers=finca["cab"],
        json={"mapeo": analisis["mapeo_sugerido"], "opciones": {}},
    ).json()
    assert aplicado["filas_ok"] == 2
    assert aplicado["filas_error"] == 1

    stock = {f["tipo"]: f["cantidad"] for f in cliente.get(f"{API}/stock-huevos", headers=finca["cab"]).json()}
    assert stock["AAA"] == 320
    assert stock["AA"] == 150

    # al deshacer, el stock vuelve a cero
    cliente.post(f"{API}/importacion/{analisis['id']}/revertir", headers=finca["cab"], json={})
    stock = {f["tipo"]: f["cantidad"] for f in cliente.get(f"{API}/stock-huevos", headers=finca["cab"]).json()}
    assert stock.get("AAA", 0) == 0


def test_importar_vacunas(cliente, finca):
    contenido = excel(
        ["Fecha", "Vacuna", "Lote", "Via", "Dosis", "Aves", "Aplicado por"],
        [["2026-03-05", "Newcastle La Sota", "L1", "ocular", "1 por ave", 480, "Juan"]],
    )
    analisis = subir(cliente, finca, "sanidad", contenido).json()
    aplicado = cliente.post(
        f"{API}/importacion/{analisis['id']}/aplicar",
        headers=finca["cab"],
        json={"mapeo": analisis["mapeo_sugerido"], "opciones": {}},
    ).json()
    assert aplicado["filas_ok"] == 1

    registros = cliente.get(f"{API}/sanidad", headers=finca["cab"]).json()
    assert any(r["producto"] == "Newcastle La Sota" and r["via"] == "ocular" for r in registros)


def test_leer_un_csv_con_punto_y_coma(cliente, finca):
    csv = "nombre;nit;telefono\nDistribuidora El Campo;900123;3101234567\n".encode("utf-8")
    respuesta = cliente.post(
        f"{API}/importacion/analizar",
        headers=finca["cab"],
        data={"tipo": "proveedores"},
        files={"archivo": ("proveedores.csv", csv, "text/csv")},
    )
    assert respuesta.status_code == 201, respuesta.text
    analisis = respuesta.json()
    assert analisis["columnas"] == ["nombre", "nit", "telefono"]
    assert analisis["mapeo_sugerido"]["documento"] == "nit"

    aplicado = cliente.post(
        f"{API}/importacion/{analisis['id']}/aplicar",
        headers=finca["cab"],
        json={"mapeo": analisis["mapeo_sugerido"], "opciones": {}},
    ).json()
    assert aplicado["filas_ok"] == 1


def test_guardar_y_usar_una_plantilla(cliente, finca):
    plantilla = cliente.post(
        f"{API}/importacion/plantillas",
        headers=finca["cab"],
        json={
            "tipo": "entrada_inventario",
            "nombre": unico("Formato")[:80],
            "mapeo": {"articulo": "Articulo", "cantidad": "Cantidad"},
        },
    )
    assert plantilla.status_code == 201, plantilla.text

    guardadas = cliente.get(f"{API}/importacion/plantillas?tipo=entrada_inventario", headers=finca["cab"]).json()
    assert any(p["id"] == plantilla.json()["id"] for p in guardadas)

    # las plantillas aparecen al subir un archivo del mismo tipo
    analisis = subir(cliente, finca, "entrada_inventario", excel(["Articulo", "Cantidad"], [["X", 1]])).json()
    assert any(p["id"] == plantilla.json()["id"] for p in analisis["plantillas"])


def test_no_se_lee_un_formato_raro(cliente, finca):
    respuesta = cliente.post(
        f"{API}/importacion/analizar",
        headers=finca["cab"],
        data={"tipo": "articulos"},
        files={"archivo": ("datos.pdf", b"%PDF-1.4 algo", "application/pdf")},
    )
    assert respuesta.status_code == 400
    assert "xlsx" in respuesta.json()["detail"]["mensaje"]


def test_otra_cuenta_no_ve_las_importaciones(cliente, finca, token_plataforma):
    otra = crear_cuenta_completa(cliente, token_plataforma, "CuentaImportB")
    cab = cabeceras(otra["token"], finca_id=otra["finca_id"])

    assert cliente.get(f"{API}/importacion", headers=cab).json() == []
    assert cliente.get(f"{API}/importacion/{finca['importacion_aplicada']}", headers=cab).status_code == 404
