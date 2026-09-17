"""
Pruebas de extremo a extremo contra una base de datos MySQL REAL.

Requisitos:
  - Base creada con database/01_schema.sql y database/02_seed.sql
  - Superadmin creado con: python -m scripts.crear_superadmin
  - Variables de entorno de la conexión + ADMIN_EMAIL / ADMIN_PASSWORD

Ejecutar desde BACKEND/:   pip install -r requirements-dev.txt && python -m pytest -q tests
(Crea datos de prueba con nombres únicos; úsalo en una base de desarrollo.)
"""
import os
import uuid
from datetime import date, datetime, timedelta

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()  # permite usar BACKEND/.env

from main import app  # noqa: E402

HOY = date.today().isoformat()
AHORA = datetime.now().replace(microsecond=0).isoformat()
SUFIJO = uuid.uuid4().hex[:6]


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/access/token", data={
        "username": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ok(r, code=200):
    assert r.status_code == code, f"{r.request.method} {r.request.url} -> {r.status_code}: {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def base(client, auth):
    """Crea finca, galpón y tipo de gallina para el resto de pruebas."""
    ok(client.post("/lands/crear", headers=auth, json={
        "nombre": f"Finca {SUFIJO}", "longitud": -74.08, "latitud": 4.6, "estado": True}), 201)
    finca = next(f for f in ok(client.get("/lands/all", headers=auth)) if f["nombre"] == f"Finca {SUFIJO}")

    ok(client.post("/sheds/crear-galpon", headers=auth, json={
        "id_finca": finca["id_finca"], "nombre": f"Galpon {SUFIJO}",
        "capacidad": 100, "cant_actual": 0, "estado": True}), 201)
    galpon = next(g for g in ok(client.get("/sheds/all", headers=auth)) if g["nombre"] == f"Galpon {SUFIJO}")

    ok(client.post("/type_chicken/crear", headers=auth, json={
        "raza": f"Raza {SUFIJO}", "descripcion": "Prueba automatizada"}), 201)
    tipo = next(t for t in ok(client.get("/type_chicken/all-type-chickens", headers=auth))
                if t["raza"] == f"Raza {SUFIJO}")
    return {"finca": finca, "galpon": galpon, "tipo": tipo}


def test_health(client):
    assert ok(client.get("/health"))["database"] == "ok"


def test_login_incorrecto(client):
    r = client.post("/access/token", data={"username": "nadie@x.com", "password": "malamala"})
    assert r.status_code == 401


def test_sin_token(client):
    assert client.get("/lands/all").status_code == 401


def test_ocupacion_galpon_por_trigger(client, auth, base):
    gid = base["galpon"]["id_galpon"]
    ok(client.post("/chickens/crear", headers=auth, json={
        "id_galpon": gid, "fecha": HOY, "id_tipo_gallina": base["tipo"]["id_tipo_gallinas"],
        "cantidad_gallinas": 40}), 201)
    assert ok(client.get(f"/sheds/by-id/{gid}", headers=auth))["cant_actual"] == 40

    # Supera la capacidad (100)
    r = client.post("/chickens/crear", headers=auth, json={
        "id_galpon": gid, "fecha": HOY, "id_tipo_gallina": base["tipo"]["id_tipo_gallinas"],
        "cantidad_gallinas": 70})
    assert r.status_code == 400

    registros = ok(client.get(f"/chickens/by-galpon?id_galpon={gid}", headers=auth))["record_chickens"]
    ingreso = registros[0]["id_ingreso"]
    # Editar 40 -> 90 en el mismo galpón es válido (90 <= 100)
    ok(client.put(f"/chickens/by-id/{ingreso}", headers=auth, json={"cantidad_gallinas": 90}))
    assert ok(client.get(f"/sheds/by-id/{gid}", headers=auth))["cant_actual"] == 90

    ok(client.delete(f"/chickens/eliminar/{ingreso}", headers=auth))
    assert ok(client.get(f"/sheds/by-id/{gid}", headers=auth))["cant_actual"] == 0


def test_produccion_y_venta_de_huevos(client, auth, base):
    gid = base["galpon"]["id_galpon"]

    def stock_tipo1():
        for s in ok(client.get("/stock/stock/all", headers=auth)):
            if s["tipo"] == 1 and s["unidad_medida"] == "unidad":
                return s
        return None

    antes = (stock_tipo1() or {}).get("cantidad_disponible", 0)
    ok(client.post("/produccion-huevos/crear", headers=auth, json={
        "id_galpon": gid, "cantidad": 30, "fecha": HOY, "id_tipo_huevo": 1}), 201)
    producto = stock_tipo1()
    assert producto["cantidad_disponible"] == antes + 30

    venta = ok(client.post("/ventas/crear", headers=auth, json={"fecha_hora": AHORA}), 201)["data_venta"]
    id_venta = venta["id_venta"]

    detalle = {"id_producto": producto["id_producto"], "cantidad": 10, "id_venta": id_venta,
               "valor_descuento": 0, "precio_venta": 500}
    ok(client.post("/detalle_huevos/crear", headers=auth, json=detalle), 201)
    assert stock_tipo1()["cantidad_disponible"] == antes + 20

    # No se puede vender más de lo que hay
    r = client.post("/detalle_huevos/crear", headers=auth,
                    json={**detalle, "cantidad": antes + 1000})
    assert r.status_code == 400

    total = ok(client.get(f"/ventas/by-id?venta_id={id_venta}", headers=auth))["total"]
    assert float(total) == 5000

    detalles = ok(client.get(f"/ventas/all-detalles-by-id?venta_id={id_venta}", headers=auth))
    assert len(detalles) == 1

    # Una venta activa no se puede borrar
    assert client.delete(f"/ventas/by-id/{id_venta}", headers=auth).status_code == 400
    # Anular la venta devuelve el stock y CONSERVA los detalles como historial
    ok(client.put(f"/ventas/cambiar-estado/{id_venta}?nuevo_estado=false", headers=auth))
    assert stock_tipo1()["cantidad_disponible"] == antes + 30
    assert len(ok(client.get(f"/ventas/all-detalles-by-id?venta_id={id_venta}", headers=auth))) == 1
    venta_anulada = ok(client.get(f"/ventas/by-id?venta_id={id_venta}", headers=auth))
    assert venta_anulada["estado"] is False and float(venta_anulada["total"]) == 5000

    # Una venta anulada no admite cambios ni se puede reactivar
    r = client.post("/detalle_huevos/crear", headers=auth, json={**detalle, "cantidad": 1})
    assert r.status_code == 400 and "anulada" in r.json()["detail"]
    id_detalle = detalles[0]["id_detalle"]
    assert client.delete(f"/detalle_huevos/by-id/{id_detalle}", headers=auth).status_code == 400
    assert client.put(f"/ventas/cambiar-estado/{id_venta}?nuevo_estado=true", headers=auth).status_code == 400

    # Eliminarla no vuelve a sumar el stock
    ok(client.delete(f"/ventas/by-id/{id_venta}", headers=auth))
    assert stock_tipo1()["cantidad_disponible"] == antes + 30


def test_salvamento_y_muertes_descuentan_del_galpon(client, auth, base):
    gid = base["galpon"]["id_galpon"]
    tipo = base["tipo"]["id_tipo_gallinas"]
    galpon = lambda: ok(client.get(f"/sheds/by-id/{gid}", headers=auth))["cant_actual"]

    ok(client.post("/chickens/crear", headers=auth, json={
        "id_galpon": gid, "fecha": HOY, "id_tipo_gallina": tipo, "cantidad_gallinas": 50}), 201)
    inicial = galpon()

    # Salvamento: 10 gallinas salen del galpón
    ok(client.post("/rescue/crear", headers=auth, json={
        "id_galpon": gid, "fecha": HOY, "id_tipo_gallina": tipo, "cantidad_gallinas": 10}), 201)
    assert galpon() == inicial - 10
    salv = next(r for r in ok(client.get("/rescue/all", headers=auth)) if r["id_galpon"] == gid)

    # No se pueden retirar más gallinas de las que hay
    r = client.post("/rescue/crear", headers=auth, json={
        "id_galpon": gid, "fecha": HOY, "id_tipo_gallina": tipo, "cantidad_gallinas": 10000})
    assert r.status_code == 400

    # Editar la cantidad ajusta la diferencia
    ok(client.put(f"/rescue/by-id/{salv['id_salvamento']}", headers=auth, json={"cantidad_gallinas": 4}))
    assert galpon() == inicial - 4

    # Muerte descuenta; Enfermedad no
    ok(client.post("/incident/crear", headers=auth, json={
        "galpon_origen": gid, "tipo_incidente": "Muerte", "cantidad": 3,
        "descripcion": "Prueba", "esta_resuelto": False, "fecha_hora": AHORA}), 201)
    assert galpon() == inicial - 7
    ok(client.post("/incident/crear", headers=auth, json={
        "galpon_origen": gid, "tipo_incidente": "Enfermedad", "cantidad": 5,
        "descripcion": "Prueba", "esta_resuelto": False, "fecha_hora": AHORA}), 201)
    assert galpon() == inicial - 7

    # Cambiar el incidente de Muerte a Herida devuelve las gallinas
    muerte = next(i for i in ok(client.get("/incident/all-chicken_incidents", headers=auth))
                  if i["galpon_origen"] == gid and i["tipo_incidente"] == "Muerte")
    ok(client.put(f"/incident/by-id/{muerte['id_inc_gallina']}", headers=auth, json={"tipo_incidente": "Herida"}))
    assert galpon() == inicial - 4

    # Eliminar el salvamento (sin ventas) devuelve lo que quedaba
    ok(client.delete(f"/rescue/by-id/{salv['id_salvamento']}", headers=auth))
    assert galpon() == inicial


def test_alimento_y_consumo(client, auth, base):
    ok(client.post("/alimento/crear", headers=auth, json={
        "nombre": f"Concentrado {SUFIJO}", "cantidad": 50, "fecha_ingreso": HOY}), 201)
    alimento = next(a for a in ok(client.get("/alimento/all-alimentos", headers=auth))
                    if a["nombre"] == f"Concentrado {SUFIJO}")
    aid, gid = alimento["id_alimento"], base["galpon"]["id_galpon"]

    ok(client.post("/consumo_gallinas/crear", headers=auth, json={
        "id_alimento": aid, "cantidad_alimento": 20, "fecha_registro": HOY, "id_galpon": gid}), 201)
    assert ok(client.get(f"/alimento/by-id?id_alimento={aid}", headers=auth))["cantidad"] == 30

    r = client.post("/consumo_gallinas/crear", headers=auth, json={
        "id_alimento": aid, "cantidad_alimento": 31, "fecha_registro": HOY, "id_galpon": gid})
    assert r.status_code == 400


def test_incidente_y_aislamiento(client, auth, base):
    gid = base["galpon"]["id_galpon"]
    ok(client.post("/incident/crear", headers=auth, json={
        "galpon_origen": gid, "tipo_incidente": "Enfermedad", "cantidad": 2,
        "descripcion": "Prueba", "esta_resuelto": False, "fecha_hora": AHORA}), 201)
    incidente = ok(client.get("/incident/all_incidentes-gallinas-pag?page=1&page_size=1", headers=auth))["incidents"][0]
    ok(client.post("/isolations/crear", headers=auth, json={
        "id_incidente_gallina": incidente["id_inc_gallina"], "id_galpon": gid, "fecha_hora": AHORA}), 201)
    ok(client.put(f"/incident/cambiar-estado/{incidente['id_inc_gallina']}?nuevo_estado=true", headers=auth))


def test_sensores(client, auth, base):
    tipo = ok(client.get("/sensor-types/activos", headers=auth))[0]
    ok(client.post("/sensors/crear", headers=auth, json={
        "nombre": f"Sensor {SUFIJO}", "id_tipo_sensor": tipo["id_tipo"],
        "id_galpon": base["galpon"]["id_galpon"], "descripcion": "Sensor de prueba automatizada",
        "estado": True}), 201)
    sensor = next(s for s in ok(client.get("/sensors/all", headers=auth)) if s["nombre"] == f"Sensor {SUFIJO}")
    ok(client.post("/registro-sensores/crear", headers=auth, json={
        "id_sensor": sensor["id_sensor"], "dato_sensor": 24.5, "fecha_hora": AHORA, "u_medida": "°C"}), 201)


def test_usuarios_y_tareas(client, auth):
    email = f"operario{SUFIJO}@avisena.com"
    ok(client.post("/users/crear", headers=auth, json={
        "nombre": "Operario Prueba", "id_rol": 4, "email": email, "telefono": "3001234567",
        "documento": f"99{SUFIJO}00", "estado": True, "pass_hash": "Operario123"}), 201)
    # Duplicado -> mensaje claro
    r = client.post("/users/crear", headers=auth, json={
        "nombre": "Operario Prueba", "id_rol": 4, "email": email, "telefono": "3001234567",
        "documento": f"98{SUFIJO}00", "estado": True, "pass_hash": "Operario123"})
    assert r.status_code == 400 and "correo" in r.json()["detail"]

    usuario = ok(client.get(f"/users/by-email?email={email}", headers=auth))
    ok(client.post("/tareas/crear", headers=auth, json={
        "id_usuario": usuario["id_usuario"], "descripcion": "Recoger huevos",
        "fecha_hora_init": AHORA, "estado": "Asignada",
        "fecha_hora_fin": (datetime.now() + timedelta(hours=2)).replace(microsecond=0).isoformat()}), 201)

    # El operario inicia sesión y ve solo sus tareas
    tok = ok(client.post("/access/token", data={"username": email, "password": "Operario123"}))["access_token"]
    op = {"Authorization": f"Bearer {tok}"}
    tareas = ok(client.get(f"/tareas/usuario/{usuario['id_usuario']}", headers=op))
    assert len(tareas) == 1
    ok(client.put(f"/tareas/{tareas[0]['id_tarea']}", headers=op, json={"estado": "Completada"}))
    # ...y no puede administrar usuarios
    assert client.get("/users/all-except-admins", headers=op).status_code == 401


def test_inventario_e_incidentes_generales(client, auth, base):
    fid = base["finca"]["id_finca"]
    cat = ok(client.get("/categories/all", headers=auth))[0]
    ok(client.post("/inventory/crear", headers=auth, json={
        "nombre": "Pala", "cantidad": 3, "unidad_medida": "Unidad", "descripcion": "Prueba",
        "id_categoria": cat["id_categoria"], "id_finca": fid}), 201)
    assert ok(client.get(f"/inventory/by-land/{fid}", headers=auth))
    ok(client.post("/incidentes_generales/crear", headers=auth, json={
        "descripcion": "Cerca dañada", "fecha_hora": AHORA, "id_finca": fid, "esta_resuelta": False}), 201)


# Todas las consultas GET deben responder sin error 500
GETS = [
    "/users/all-except-admins", "/users/all-users-except-superadmins", "/users/by-role?role=operario",
    "/roles/all-roles-pag", "/roles/by-id?rol_id=1", "/roles/by-nombre?nombre_rol=superadmin",
    "/modulos/todas", "/modulos/1", "/permisos/todas", "/permisos/1/1",
    "/tareas/pag", "/lands/all", "/sheds/all", "/sheds/activos", "/sheds/fincas/activas",
    "/categories/all", "/inventory/all", "/incidentes_generales/all",
    "/incidentes_generales/by-estado/false", "/incidentes_generales/fincas/activas",
    "/sensor-types/all", "/sensor-types/activos", "/sensors/all", "/registro-sensores/all",
    "/type_chicken/all-type-chickens", "/chickens/all-chickens-pag",
    f"/chickens/by-fechas?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/incident/all-chicken_incidents", "/incident/all_incidentes-gallinas-pag",
    f"/incident/rango-fechas?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/isolations/all-isolation", "/isolations/all_isolations-pag",
    f"/isolations/rango-fechas?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/rescue/all", "/rescue/all-pag", f"/rescue/all-pag-by-date?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/alimento/all-alimentos", "/alimento/all-type-alimentos_pag",
    f"/alimento/rango-fechas?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/consumo_gallinas/all-consumos", "/consumo_gallinas/all-consumos-pag",
    f"/consumo_gallinas/rango-fechas?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/tipo-huevos/all", "/produccion-huevos/all", "/stock/stock/all",
    "/metodo_pago/all-metodosPago", "/ventas/all-ventas-pag",
    f"/ventas/all-rango-fechas-pag?fecha_inicio={HOY}&fecha_fin={HOY}",
    "/ventas/by-id-usuario-pag?usuario_id=1", "/ventas/by-tipo_pago-pag?tipo_id=1",
    "/detalle_huevos/all-products-stock", "/detalle_salvamento/all-products-salvamento",
    "/dashboard/metricas", "/dashboard/produccion-semanal", "/dashboard/produccion-rango",
    "/dashboard/distribucion-tipos", "/dashboard/ocupacion-galpones",
    "/dashboard/incidentes-recientes", "/dashboard/sensores", "/dashboard/actividad-reciente",
    "/dashboard/completo",
]


@pytest.mark.parametrize("url", GETS)
def test_consultas_sin_error(client, auth, base, url):
    r = client.get(url, headers=auth)
    assert r.status_code < 500, f"{url} -> {r.status_code}: {r.text}"
    assert r.status_code != 422, f"{url} -> parámetros incorrectos: {r.text}"
