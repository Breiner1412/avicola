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


@pytest.fixture(scope="module")
def supervisor_con_finca_ajena(cliente, token_plataforma):
    """Supervisor de la finca 1 que solo puede consultar la finca 2."""
    cuenta = crear_cuenta_completa(cliente, token_plataforma, "Superv")
    admin = cabeceras(cuenta["token"])
    finca2 = cliente.post(f"{API}/fincas", headers=admin, json={"codigo": "P2", "nombre": unico("Finca2")}).json()
    galpon2 = cliente.post(
        f"{API}/galpones",
        headers=cabeceras(cuenta["token"], finca2["id"]),
        json={"codigo": "G2", "nombre": "Galpon ajeno", "capacidad": 100},
    ).json()
    email = f"{unico('superv')}@avicola.com"
    creado = cliente.post(
        f"{API}/usuarios",
        headers=admin,
        json={
            "nombres": "Super",
            "email": email,
            "rol": "supervisor",
            "clave": "ClaveDePrueba123",
            "debe_cambiar_clave": False,
            "fincas": [
                {"finca_id": cuenta["finca_id"], "solo_lectura": False},
                {"finca_id": finca2["id"], "solo_lectura": True},
            ],
        },
    )
    assert creado.status_code == 201, creado.text
    sesion = cliente.post(f"{API}/auth/login", json={"email": email, "clave": "ClaveDePrueba123"}).json()
    return {"token": sesion["token"], "finca1": cuenta["finca_id"], "finca2": finca2["id"], "galpon2": galpon2}


def test_no_escribe_en_finca_de_solo_lectura_sin_finca_activa(cliente, supervisor_con_finca_ajena):
    datos = supervisor_con_finca_ajena
    galpon = datos["galpon2"]["id"]
    respuesta = cliente.patch(f"{API}/galpones/{galpon}", headers=cabeceras(datos["token"]), json={"nombre": "Cambiado"})
    assert respuesta.status_code == 403
    # Consultar si puede
    assert cliente.get(f"{API}/galpones/{galpon}", headers=cabeceras(datos["token"])).status_code == 200


def test_no_escribe_en_finca_de_solo_lectura_desde_otra_finca(cliente, supervisor_con_finca_ajena):
    datos = supervisor_con_finca_ajena
    respuesta = cliente.patch(
        f"{API}/galpones/{datos['galpon2']['id']}",
        headers=cabeceras(datos["token"], datos["finca1"]),
        json={"nombre": "Cambiado"},
    )
    assert respuesta.status_code in (403, 404)


def test_ids_de_otra_empresa_en_el_cuerpo_se_rechazan(cliente, propietario_a, propietario_b):
    cab_a = cabeceras(propietario_a["token"], propietario_a["finca_id"])
    cab_b = cabeceras(propietario_b["token"], propietario_b["finca_id"])

    # Raza propia de B usada en un lote de A
    raza_b = cliente.post(f"{API}/razas", headers=cab_b, json={"nombre": unico("RazaB")}).json()
    galpon_a = cliente.post(
        f"{API}/galpones", headers=cab_a, json={"codigo": unico("G")[:20], "nombre": "Galpon A", "capacidad": 500}
    ).json()
    lote = cliente.post(
        f"{API}/lotes",
        headers=cab_a,
        json={"codigo": "LX", "galpon_id": galpon_a["id"], "raza_id": raza_b["id"],
              "fecha_ingreso": "2026-01-05", "aves_iniciales": 10},
    )
    assert lote.status_code == 400, lote.text

    # Proveedor de B en una entrada de inventario de A
    proveedor_b = cliente.post(f"{API}/proveedores", headers=cab_b, json={"nombre": unico("ProvB")}).json()
    bodega_a = cliente.post(
        f"{API}/bodegas", headers=cab_a, json={"codigo": unico("BX")[:20], "nombre": "Bodega A"}
    ).json()
    categoria = cliente.get(f"{API}/categorias-articulo", headers=cab_a).json()[0]
    articulo_a = cliente.post(
        f"{API}/articulos",
        headers=cab_a,
        json={"codigo": unico("AX")[:30], "nombre": "Articulo A", "categoria_id": categoria["id"], "unidad": "kg"},
    ).json()
    entrada = cliente.post(
        f"{API}/movimientos",
        headers=cab_a,
        json={"tipo": "entrada", "fecha": "2026-02-01", "bodega_id": bodega_a["id"], "proveedor_id": proveedor_b["id"],
              "items": [{"articulo_id": articulo_a["id"], "cantidad": 1, "costo_unitario": 100}]},
    )
    assert entrada.status_code == 400, entrada.text

    # Galpon de B en una tarea de A
    galpon_b = cliente.post(
        f"{API}/galpones", headers=cab_b, json={"codigo": unico("G")[:20], "nombre": "Galpon B", "capacidad": 500}
    ).json()
    tarea = cliente.post(
        f"{API}/tareas",
        headers=cab_a,
        json={"titulo": "Revisar galpon", "fecha": "2026-02-01", "galpon_id": galpon_b["id"]},
    )
    assert tarea.status_code == 400, tarea.text


def _crear_usuario(cliente, cab_admin, rol, fincas):
    email = f"{unico(rol)}@avicola.com"
    creado = cliente.post(
        f"{API}/usuarios",
        headers=cab_admin,
        json={"nombres": rol.title(), "email": email, "rol": rol, "clave": "ClaveDePrueba123",
              "debe_cambiar_clave": False, "fincas": [{"finca_id": f, "solo_lectura": False} for f in fincas]},
    )
    assert creado.status_code == 201, creado.text
    sesion = cliente.post(f"{API}/auth/login", json={"email": email, "clave": "ClaveDePrueba123"}).json()
    return {"id": creado.json()["id"], "email": email, "token": sesion["token"]}


@pytest.fixture(scope="module")
def empresa_con_dos_fincas(cliente, token_plataforma):
    cuenta = crear_cuenta_completa(cliente, token_plataforma, "DosFincas")
    admin = cabeceras(cuenta["token"])
    finca2 = cliente.post(f"{API}/fincas", headers=admin, json={"codigo": "P2", "nombre": unico("Lejana")}).json()
    # Algo que quede en el registro de la finca 2
    cliente.post(
        f"{API}/galpones",
        headers=cabeceras(cuenta["token"], finca2["id"]),
        json={"codigo": "GL", "nombre": "Galpon lejano", "capacidad": 300},
    )
    operario2 = _crear_usuario(cliente, admin, "operario", [finca2["id"]])
    supervisor = _crear_usuario(cliente, admin, "supervisor", [cuenta["finca_id"]])
    return {"finca1": cuenta["finca_id"], "finca2": finca2, "operario2": operario2, "supervisor": supervisor}


def test_supervisor_no_ve_usuarios_de_otras_fincas(cliente, empresa_con_dos_fincas):
    datos = empresa_con_dos_fincas
    cab = cabeceras(datos["supervisor"]["token"], datos["finca1"])
    correos = {u["email"] for u in cliente.get(f"{API}/usuarios", headers=cab).json()}
    assert datos["supervisor"]["email"] in correos
    assert datos["operario2"]["email"] not in correos
    assert cliente.get(f"{API}/usuarios/{datos['operario2']['id']}", headers=cab).status_code == 404


def test_supervisor_no_ve_el_registro_de_otras_fincas(cliente, empresa_con_dos_fincas):
    datos = empresa_con_dos_fincas
    cab = cabeceras(datos["supervisor"]["token"], datos["finca1"])
    respuesta = cliente.get(f"{API}/auditoria", headers=cab, params={"tamano": 200})
    assert respuesta.status_code == 200, respuesta.text
    assert all(linea["finca_id"] == datos["finca1"] for linea in respuesta.json()["datos"])


def test_supervisor_ve_un_resumen_de_las_demas_fincas(cliente, empresa_con_dos_fincas):
    datos = empresa_con_dos_fincas
    cab = cabeceras(datos["supervisor"]["token"], datos["finca1"])
    panel = cliente.get(f"{API}/panel/resumen", headers=cab).json()
    otras = {f["id"]: f for f in panel["otras_fincas"]}
    assert datos["finca2"]["id"] in otras
    assert set(otras[datos["finca2"]["id"]]) == {"id", "nombre", "aves", "huevos_periodo", "lotes_activos"}
    # y no puede entrar al detalle de esa finca
    assert cliente.get(f"{API}/galpones", headers=cabeceras(datos["supervisor"]["token"], datos["finca2"]["id"])).status_code == 403
