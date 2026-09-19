"""Datos de ejemplo: una granja que lleva seis meses usando AVISENA.

Crea la cuenta "Granja Avicola La Esperanza" con dos fincas, sus usuarios, galpones,
bodegas, articulos, lotes, puntos de venta y sensores, y despues simula dia por dia
el trabajo de los ultimos meses: recoleccion de huevos, alimento, mortalidad, pesajes,
vacunas, compras, traslados, ventas con su caja, descarte, pollo de engorde, tareas,
rutinas, novedades y mediciones de los sensores.

Todo se registra con las mismas reglas del sistema (las funciones de la API), asi que
el inventario, las aves y la caja cuadran como si lo hubiera hecho la gente.

Uso:
    python -m app.demo                 # 180 dias hasta hoy
    python -m app.demo --dias 90       # otro periodo

Con Docker:
    docker compose -f docker-compose.v2.yml exec api python -m app.demo

Solo se puede cargar una vez por base de datos. Para empezar de cero hay que borrar la
base (docker compose -f docker-compose.v2.yml down -v) y volver a levantar todo.
"""

from __future__ import annotations

import argparse
import logging
import math
import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException
from freezegun import freeze_time
from sqlalchemy import select

from app.core.contexto import Contexto
from app.core.db import SesionLocal
from app.core.seguridad import cifrar_clave
from app.esquemas.aves import (
    CerrarLote,
    ConsumoCrear,
    DetalleProduccion,
    LoteCrear,
    MovimientoAvesCrear,
    PesajeCrear,
    ProduccionCrear,
    SanidadCrear,
)
from app.esquemas.inventario import ItemEntrada, MovimientoCrear
from app.esquemas.trabajo import (
    CerrarNovedad,
    GenerarTareas,
    NovedadCrear,
    RutinaCrear,
    TareaActualizar,
    TareaCrear,
)
from app.esquemas.ventas import (
    AbrirTurno,
    AnularVenta,
    CerrarTurno,
    ItemVenta,
    PagoVenta,
    PrecioCrear,
    ProductoCrear,
    PuntoVentaCrear,
    VentaCrear,
)
from app.modelos.acceso import Rol, Usuario, UsuarioFinca
from app.modelos.aves import Lote, Raza, TipoHuevo
from app.modelos.inventario import Articulo, Bodega, CategoriaArticulo, Existencia, Proveedor
from app.modelos.organizacion import Cuenta, Finca, Galpon
from app.modelos.sensores import LecturaSensor, Sensor, TipoSensor
from app.modelos.trabajo import Tarea
from app.modelos.ventas import MetodoPago, TurnoCaja
from app.rutas import aves as r_aves
from app.rutas import movimientos as r_mov
from app.rutas import produccion as r_prod
from app.rutas import sanidad as r_san
from app.rutas import trabajo as r_tra
from app.rutas import ventas as r_ven
from app.rutas.sensores import estado_de

log = logging.getLogger("avisena.demo")

NOMBRE_CUENTA = "Granja Avicola La Esperanza"
CLAVE_DEMO = "Granja2026"
DOMINIO = "demo-avisena.com"
# Colombia no cambia de hora: la hora local es UTC - 5
DESFASE = timedelta(hours=5)

COMERCIALES = ["Super", "AAA", "AA", "A", "B"]
CLIENTES_MAYORISTAS = [
    "Distribuidora Huevos del Otun",
    "Supermercado La Canasta",
    "Tienda Don Pacho",
    "Panaderia El Trigal",
    "Restaurante Sazon Paisa",
    "Minimercado La 14 de Santa Rosa",
]
COMPRADORES_POLLO = ["Asadero El Pollo Dorado", "Carnes Frias Risaralda", "Plaza de mercado Dosquebradas"]


# ---------------------------------------------------------------- utilidades
def poisson(media: float) -> int:
    if media <= 0:
        return 0
    limite, k, p = math.exp(-media), 0, 1.0
    while True:
        p *= random.random()
        if p <= limite:
            return k
        k += 1


def redondear(valor: float, paso: int) -> int:
    return int(math.ceil(valor / paso) * paso)


def interpolar(tabla: list[tuple[float, float]], x: float) -> float:
    if x <= tabla[0][0]:
        return tabla[0][1]
    for (x0, y0), (x1, y1) in zip(tabla, tabla[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tabla[-1][1]


# Peso de pollo de engorde (dias, kg) y de pollita de levante (semanas, kg)
PESO_POLLO = [(0, 0.042), (7, 0.19), (14, 0.48), (21, 0.95), (28, 1.5), (35, 2.1), (42, 2.75), (49, 3.2)]
PESO_POLLITA = [(0, 0.04), (2, 0.12), (4, 0.29), (6, 0.45), (8, 0.65), (10, 0.84), (12, 1.03), (14, 1.2),
                (16, 1.37), (18, 1.5), (22, 1.75), (30, 1.9), (80, 2.0)]
# Alimento de pollita en gramos por ave y dia, por semana de edad
GRAMOS_POLLITA = [10, 14, 19, 24, 29, 34, 39, 44, 48, 52, 56, 59, 62, 65, 68, 71, 74, 78, 84, 92, 100, 106, 110]


def postura(edad_dias: int) -> float:
    semanas = edad_dias / 7
    if semanas < 18.5:
        return 0.0
    if semanas < 25:
        return 0.95 * (1 - math.exp(-(semanas - 18.5) / 1.8))
    if semanas < 32:
        return 0.95
    return max(0.55, 0.95 - 0.004 * (semanas - 32))


def tamanos(edad_dias: int) -> list[float]:
    semanas = edad_dias / 7
    if semanas < 24:
        return [0.0, 0.02, 0.18, 0.45, 0.35]
    if semanas < 30:
        return [0.01, 0.10, 0.40, 0.35, 0.14]
    if semanas < 45:
        return [0.04, 0.25, 0.45, 0.20, 0.06]
    if semanas < 60:
        return [0.08, 0.35, 0.40, 0.13, 0.04]
    return [0.12, 0.40, 0.33, 0.11, 0.04]


class Demo:
    def __init__(self, dias: int):
        self.db = SesionLocal()
        ahora_real = datetime.utcnow() - DESFASE
        self.ahora_local = ahora_real.replace(second=0, microsecond=0)
        self.hoy = self.ahora_local.date()
        self.inicio = self.hoy - timedelta(days=dias)
        self.errores: Counter[str] = Counter()
        self.cuentas: Counter[str] = Counter()
        self.reloj = None

    # ------------------------------------------------------------ reloj
    def a_las(self, dia: date, hora: int, minuto: int = 0) -> bool:
        """Mueve el reloj del sistema a esa hora local. Devuelve False si todavia no ha llegado."""
        momento = datetime.combine(dia, time(hora, minuto))
        if momento > self.ahora_local:
            return False
        self.reloj.move_to(momento + DESFASE)
        return True

    # ------------------------------------------------------------ llamadas
    def ctx(self, usuario: Usuario, finca: Finca | None) -> Contexto:
        return Contexto(
            usuario=usuario,
            rol=usuario.rol.clave,
            cuenta_id=self.cuenta.id,
            finca_id=finca.id if finca else None,
            solo_lectura=False,
            ip="192.168.1.20",
            sesion_id=None,
            cuenta_activa_id=self.cuenta.id,
        )

    def hacer(self, que: str, funcion, *args, **kwargs):
        try:
            resultado = funcion(*args, db=self.db, **kwargs)
            self.cuentas[que] += 1
            return resultado
        except HTTPException as error:
            self.db.rollback()
            self.errores[que] += 1
            if self.errores[que] <= 3:
                log.warning("%s: %s", que, error.detail)
            return None

    def existencia(self, bodega: Bodega, articulo: Articulo) -> float:
        fila = self.db.get(Existencia, (bodega.id, articulo.id))
        return float(fila.cantidad) if fila else 0.0

    # ------------------------------------------------------------ estructura
    def crear_estructura(self) -> None:
        db = self.db
        roles = {r.clave: r for r in db.scalars(select(Rol)).all()}

        self.cuenta = Cuenta(
            tipo="empresa", nombre=NOMBRE_CUENTA, documento="900.487.215-3",
            email_contacto=f"contacto@{DOMINIO}", telefono="606 364 1122", descuento_maximo=10,
        )
        db.add(self.cuenta)
        db.flush()

        self.esperanza = Finca(
            cuenta_id=self.cuenta.id, codigo="ESP", nombre="La Esperanza", municipio="Santa Rosa de Cabal",
            departamento="Risaralda", direccion="Vereda El Lembo, km 4 via a Termales", telefono="313 555 0142",
        )
        self.recreo = Finca(
            cuenta_id=self.cuenta.id, codigo="REC", nombre="El Recreo", municipio="Dosquebradas",
            departamento="Risaralda", direccion="Vereda La Badea, lote 12", telefono="314 555 0187",
        )
        db.add_all([self.esperanza, self.recreo])
        db.flush()

        def galpon(finca, codigo, nombre, tipo, capacidad, obs=None):
            g = Galpon(finca_id=finca.id, codigo=codigo, nombre=nombre, tipo=tipo, capacidad=capacidad, observaciones=obs)
            db.add(g)
            return g

        self.g1 = galpon(self.esperanza, "G1", "Galpon 1", "postura", 3200, "Piso con cama de viruta, nidos de madera")
        self.g2 = galpon(self.esperanza, "G2", "Galpon 2", "postura", 3000)
        self.g3 = galpon(self.esperanza, "G3", "Galpon 3", "postura", 2800)
        self.g4 = galpon(self.esperanza, "G4", "Galpon de levante", "levante", 2600, "Criadoras a gas")
        self.e1 = galpon(self.recreo, "E1", "Engorde 1", "engorde", 1700)
        self.e2 = galpon(self.recreo, "E2", "Engorde 2", "engorde", 1700)
        db.flush()

        # Usuarios
        clave = cifrar_clave(CLAVE_DEMO)

        def usuario(nombres, apellidos, correo, rol, fincas=(), documento=None, telefono=None):
            u = Usuario(
                cuenta_id=self.cuenta.id, rol_id=roles[rol].id, nombres=nombres, apellidos=apellidos,
                email=f"{correo}@{DOMINIO}", clave_hash=clave, debe_cambiar_clave=False,
                documento=documento, telefono=telefono,
            )
            db.add(u)
            db.flush()
            for finca in fincas:
                db.add(UsuarioFinca(usuario_id=u.id, finca_id=finca.id, solo_lectura=False))
            return u

        self.carlos = usuario("Carlos", "Ramirez Osorio", "dueno", "propietario", documento="10.123.456", telefono="310 555 0101")
        self.diana = usuario("Diana", "Lopez Castano", "admin", "administrador", documento="42.087.331", telefono="311 555 0102")
        self.jorge = usuario("Jorge", "Cardenas Rios", "supervisor", "supervisor", [self.esperanza, self.recreo], "9.876.543", "312 555 0103")
        self.luis = usuario("Luis", "Mejia Arango", "operario1", "operario", [self.esperanza], "1.088.234.567", "315 555 0104")
        self.andres = usuario("Andres", "Valencia Gil", "operario2", "operario", [self.esperanza], "1.088.345.678", "316 555 0105")
        self.yuliana = usuario("Yuliana", "Rios Marin", "operario3", "operario", [self.recreo], "1.093.456.789", "317 555 0106")
        self.paola = usuario("Paola", "Gomez Duque", "caja", "cajero", [self.esperanza], "1.088.567.890", "318 555 0107")

        # Bodegas
        self.central = Bodega(cuenta_id=self.cuenta.id, finca_id=None, codigo="BC", nombre="Bodega central", ubicacion="Santa Rosa de Cabal, Cra 14 # 12-30")
        self.b_esp = Bodega(cuenta_id=self.cuenta.id, finca_id=self.esperanza.id, codigo="B-ESP", nombre="Bodega La Esperanza", ubicacion="Junto al galpon 1")
        self.b_rec = Bodega(cuenta_id=self.cuenta.id, finca_id=self.recreo.id, codigo="B-REC", nombre="Bodega El Recreo", ubicacion="Entrada de la finca")
        db.add_all([self.central, self.b_esp, self.b_rec])
        db.flush()

        # Proveedores
        def proveedor(nombre, nit, tel, correo, direccion):
            p = Proveedor(cuenta_id=self.cuenta.id, nombre=nombre, documento=nit, telefono=tel, email=correo, direccion=direccion)
            db.add(p)
            return p

        self.italcol = proveedor("Italcol de Occidente", "890.900.123-1", "606 335 2000", f"ventas.italcol@{DOMINIO}", "Pereira, Zona Industrial La Popa")
        self.solla = proveedor("Solla S.A.", "890.901.456-2", "604 444 1000", f"pedidos.solla@{DOMINIO}", "Dosquebradas, Via La Romelia")
        self.agrovet = proveedor("Agroveterinaria El Campo", "901.234.567-8", "606 364 5566", f"agrovet@{DOMINIO}", "Santa Rosa de Cabal, Calle 13 # 15-20")
        self.empaques = proveedor("Empaques del Cafe", "900.765.432-1", "606 321 7788", f"empaques@{DOMINIO}", "Pereira, Av. 30 de Agosto")
        self.ferreteria = proveedor("Ferreteria La Rosa", "71.456.789-0", "606 364 9911", None, "Santa Rosa de Cabal, Carrera 15 # 13-44")
        db.flush()

        # Articulos
        categorias = {c.nombre: c.id for c in db.scalars(select(CategoriaArticulo).where(CategoriaArticulo.cuenta_id.is_(None))).all()}

        def articulo(codigo, nombre, categoria, unidad, minimo, bulto=None, obs=None):
            a = Articulo(
                cuenta_id=self.cuenta.id, categoria_id=categorias[categoria], codigo=codigo, nombre=nombre,
                unidad=unidad, kg_por_bulto=bulto, stock_minimo=minimo, observaciones=obs,
            )
            db.add(a)
            return a

        self.a_postura = articulo("ALI-POS", "Alimento postura fase 1", "Alimento", "kg", 1500, 40)
        self.a_levante = articulo("ALI-LEV", "Alimento levante pollitas", "Alimento", "kg", 500, 40)
        self.a_inicio = articulo("ALI-INI", "Alimento iniciacion pollo", "Alimento", "kg", 400, 40)
        self.a_engorde = articulo("ALI-ENG", "Alimento engorde finalizador", "Alimento", "kg", 800, 40)
        self.a_newcastle = articulo("VAC-NEW", "Vacuna Newcastle La Sota", "Vacunas", "dosis", 2000, obs="Frasco x 1.000 dosis, cadena de frio")
        self.a_gumboro = articulo("VAC-GUM", "Vacuna Gumboro intermedia", "Vacunas", "dosis", 1000, obs="Frasco x 1.000 dosis")
        self.a_bronquitis = articulo("VAC-BRO", "Vacuna Bronquitis Mass", "Vacunas", "dosis", 1000, obs="Frasco x 1.000 dosis")
        self.a_viruela = articulo("VAC-VIR", "Vacuna viruela aviar", "Vacunas", "dosis", 0, obs="Frasco x 1.000 dosis")
        self.a_vitaminas = articulo("MED-VIT", "Vitaminas y electrolitos", "Medicamentos", "litro", 4)
        self.a_antibiotico = articulo("MED-ENR", "Enrofloxacina 10%", "Medicamentos", "litro", 1)
        self.a_desinfectante = articulo("ASE-DES", "Desinfectante yodado", "Insumos de aseo", "litro", 20)
        self.a_cal = articulo("ASE-CAL", "Cal viva", "Insumos de aseo", "kg", 50)
        self.a_viruta = articulo("MAT-VIR", "Viruta de madera", "Materiales", "bulto", 30)
        self.a_cubetas = articulo("MAT-CUB", "Cubetas de carton x 30", "Materiales", "unidad", 800)
        self.a_bombillo = articulo("REP-BOM", "Bombillo LED 12 W", "Repuestos", "unidad", 6)
        self.a_bebedero = articulo("HER-BEB", "Bebedero de campana", "Herramientas", "unidad", 2)
        db.flush()

        self.costos = {
            self.a_postura.id: 2375, self.a_levante.id: 2450, self.a_inicio.id: 2620, self.a_engorde.id: 2510,
            self.a_newcastle.id: 26, self.a_gumboro.id: 42, self.a_bronquitis.id: 31, self.a_viruela.id: 58,
            self.a_vitaminas.id: 38000, self.a_antibiotico.id: 96000, self.a_desinfectante.id: 21500,
            self.a_cal.id: 900, self.a_viruta.id: 9500, self.a_cubetas.id: 420, self.a_bombillo.id: 12500,
            self.a_bebedero.id: 38000,
        }

        # Sensores
        tipos = {t.nombre: t for t in db.scalars(select(TipoSensor).where(TipoSensor.cuenta_id.is_(None))).all()}
        creado = datetime.combine(self.inicio, time(8)) + DESFASE

        def sensor(finca, galpon_, codigo, nombre, tipo, ubicacion, minimo=None, maximo=None):
            s = Sensor(
                cuenta_id=self.cuenta.id, finca_id=finca.id, galpon_id=galpon_.id if galpon_ else None,
                tipo_id=tipos[tipo].id, codigo=codigo, nombre=nombre, ubicacion=ubicacion,
                min_ok=minimo, max_ok=maximo, activo=True, creado_en=creado,
            )
            db.add(s)
            return s

        self.sensores = {
            "t1": sensor(self.esperanza, self.g1, "TEMP-G1", "Temperatura galpon 1", "Temperatura", "Centro del galpon, a 1,5 m"),
            "h1": sensor(self.esperanza, self.g1, "HUM-G1", "Humedad galpon 1", "Humedad", "Centro del galpon"),
            "a1": sensor(self.esperanza, self.g1, "NH3-G1", "Amoniaco galpon 1", "Amoniaco", "A la altura de las aves"),
            "t2": sensor(self.esperanza, self.g2, "TEMP-G2", "Temperatura galpon 2", "Temperatura", "Lado de la cortina oriental"),
            "h2": sensor(self.esperanza, self.g2, "HUM-G2", "Humedad galpon 2", "Humedad", "Centro del galpon"),
            "t3": sensor(self.esperanza, self.g3, "TEMP-G3", "Temperatura galpon 3", "Temperatura", "Centro del galpon"),
            "silo": sensor(self.esperanza, self.g1, "SILO-1", "Silo de alimento", "Peso del silo", "Silo exterior, 4 toneladas", 400, None),
            "te1": sensor(self.recreo, self.e1, "TEMP-E1", "Temperatura engorde 1", "Temperatura", "Zona de criadoras", 20, 34),
            "he1": sensor(self.recreo, self.e1, "HUM-E1", "Humedad engorde 1", "Humedad", "Centro del galpon"),
        }
        db.flush()

        # Catalogos del sistema
        self.razas = {r.nombre: r.id for r in db.scalars(select(Raza).where(Raza.cuenta_id.is_(None))).all()}
        self.tipos = {t.nombre: t.id for t in db.scalars(select(TipoHuevo).where(TipoHuevo.cuenta_id.is_(None))).all()}
        self.pagos = {m.nombre: m.id for m in db.scalars(select(MetodoPago).where(MetodoPago.cuenta_id.is_(None))).all()}
        db.commit()
        log.info("Estructura creada: 2 fincas, 6 galpones, 7 usuarios, 3 bodegas, 16 articulos, 9 sensores")

    # ------------------------------------------------------------ inicio
    def arrancar(self) -> None:
        dia = self.inicio
        self.a_las(dia, 7)
        ctx_admin_esp = self.ctx(self.diana, self.esperanza)
        ctx_admin_rec = self.ctx(self.diana, self.recreo)

        # Puntos de venta y productos
        self.pv1 = self.hacer("punto", r_ven.crear_punto, PuntoVentaCrear(
            codigo="PV1", nombre="Tienda La Esperanza", direccion="Entrada de la finca La Esperanza",
            prefijo="PV1", finca_id=self.esperanza.id), ctx=ctx_admin_esp)
        self.pv2 = self.hacer("punto", r_ven.crear_punto, PuntoVentaCrear(
            codigo="PV2", nombre="Venta El Recreo", direccion="Finca El Recreo", prefijo="PV2",
            finca_id=self.recreo.id), ctx=ctx_admin_rec)

        self.productos: dict[str, dict] = {}

        def producto(clave, nombre, clase, presentacion, precio, tipo=None, cobro="unidad", orden=0, factor=1):
            salida = self.hacer("producto", r_ven.crear_producto, ProductoCrear(
                nombre=nombre, clase=clase, presentacion=presentacion,
                tipo_huevo_id=self.tipos[tipo] if tipo else None, cobro_por=cobro, precio=precio, orden=orden,
            ), ctx=ctx_admin_esp)
            self.productos[clave] = {"id": salida.id, "precio": precio, "tipo": tipo, "factor": factor}

        precios_panal = {"Super": 21000, "AAA": 18500, "AA": 16500, "A": 14500, "B": 12000}
        for orden, tipo in enumerate(COMERCIALES):
            producto(f"panal_{tipo}", f"Panal huevo {tipo} x 30", "huevo", "panal", precios_panal[tipo], tipo, orden=orden * 10, factor=30)
        producto("medio_AAA", "Medio panal huevo AAA x 15", "huevo", "medio_panal", 9500, "AAA", orden=60, factor=15)
        producto("medio_AA", "Medio panal huevo AA x 15", "huevo", "medio_panal", 8500, "AA", orden=61, factor=15)
        producto("docena_AA", "Docena huevo AA", "huevo", "docena", 7000, "AA", orden=70, factor=12)
        producto("docena_A", "Docena huevo A", "huevo", "docena", 6200, "A", orden=71, factor=12)
        producto("unidad_AA", "Huevo AA por unidad", "huevo", "unidad", 600, "AA", orden=80)
        producto("unidad_A", "Huevo A por unidad", "huevo", "unidad", 520, "A", orden=81)
        producto("descarte", "Gallina de descarte (kg)", "ave_descarte", "kg", 7500, cobro="kg", orden=90)
        producto("pollo", "Pollo en pie (kg)", "ave_engorde", "kg", 6900, cobro="kg", orden=91)
        producto("gallinaza", "Gallinaza bulto 40 kg", "otro", "unidad", 8000, orden=95)

        # Lotes que ya estaban en la finca cuando empezaron a usar el sistema
        ctx_jorge = self.ctx(self.jorge, self.esperanza)

        def lote(ctx, galpon_, codigo, raza, proposito, aves, edad, costo, obs=None, fecha=None):
            salida = self.hacer("lote", r_aves.nuevo_lote, LoteCrear(
                codigo=codigo, galpon_id=galpon_.id, raza_id=self.razas[raza], proposito=proposito,
                fecha_ingreso=fecha or dia, edad_dias_ingreso=edad, aves_iniciales=aves, costo_ave=costo,
                observaciones=obs,
            ), ctx=ctx)
            return salida.id

        self.po1 = lote(ctx_jorge, self.g1, "PO-01", "Hy-Line Brown", "postura", 3050, 182, 24500, "Lote en pico de postura")
        self.po2 = lote(ctx_jorge, self.g2, "PO-02", "Lohmann Brown", "postura", 2820, 330, 23800)
        self.po3 = lote(ctx_jorge, self.g3, "PO-03", "Isa Brown", "postura", 2380, 490, 22000, "Lote viejo, se descarta este semestre")
        self.po4 = lote(ctx_jorge, self.g4, "PO-04", "Hy-Line Brown", "postura", 2500, 1, 4300, "Pollitas de un dia, vacunadas contra Marek en la incubadora")
        self.ponedoras = [self.po1, self.po2, self.po3, self.po4]
        self.engordes: list[dict] = []

        # Inventario inicial
        self.compra(dia, self.b_esp, self.italcol, [(self.a_postura, 6000), (self.a_levante, 800)])
        self.compra(dia, self.central, self.agrovet, [
            (self.a_newcastle, 10000), (self.a_gumboro, 6000), (self.a_bronquitis, 6000), (self.a_viruela, 3000),
            (self.a_vitaminas, 20), (self.a_antibiotico, 4), (self.a_desinfectante, 60), (self.a_cal, 250),
        ], hora=10)
        self.compra(dia, self.b_esp, self.empaques, [(self.a_cubetas, 3000)], hora=11)
        self.compra(dia, self.central, self.ferreteria, [(self.a_bombillo, 20), (self.a_bebedero, 6)], hora=11)
        self.compra(dia, self.b_rec, self.solla, [(self.a_viruta, 120)], hora=12)
        self.traslado(dia, self.central, self.b_esp, [(self.a_desinfectante, 30), (self.a_cal, 150), (self.a_vitaminas, 10)])
        self.traslado(dia, self.central, self.b_rec, [(self.a_desinfectante, 15), (self.a_cal, 80), (self.a_vitaminas, 5)])

        # Rutinas
        self.rutinas(dia)

    # ------------------------------------------------------------ inventario
    def precio(self, articulo: Articulo, dia: date) -> float:
        base = self.costos[articulo.id]
        subidas = (dia - self.inicio).days // 60
        return round(base * (1.015 ** subidas) * random.uniform(0.99, 1.01), 0 if base > 100 else 1)

    def compra(self, dia, bodega, proveedor, lineas, hora=9) -> None:
        if not self.a_las(dia, hora, random.randint(0, 50)):
            return
        items = []
        for articulo, cantidad in lineas:
            venc = dia + timedelta(days=random.randint(90, 360)) if articulo.categoria_id and articulo.unidad in ("dosis", "litro") else None
            items.append(ItemEntrada(
                articulo_id=articulo.id, cantidad=cantidad, costo_unitario=self.precio(articulo, dia),
                lote=f"L{random.randint(2400, 9800)}" if venc else None, vencimiento=venc,
            ))
        self.hacer("compra", r_mov.crear, MovimientoCrear(
            tipo="entrada", fecha=dia, bodega_id=bodega.id, proveedor_id=proveedor.id,
            documento=f"FV-{random.randint(10000, 99999)}", items=items,
        ), ctx=self.ctx(self.diana, None))

    def traslado(self, dia, origen, destino, lineas, hora=13) -> None:
        if not self.a_las(dia, hora, random.randint(0, 50)):
            return
        self.hacer("traslado", r_mov.crear, MovimientoCrear(
            tipo="traslado", fecha=dia, bodega_id=origen.id, bodega_destino_id=destino.id,
            observaciones="Envio a finca", items=[ItemEntrada(articulo_id=a.id, cantidad=c) for a, c in lineas],
        ), ctx=self.ctx(self.diana, None))

    def asegurar(self, dia, bodega, articulo, cantidad) -> None:
        """Si en la bodega de la finca no alcanza, se trae de la central (y si alli tampoco, se compra)."""
        falta = cantidad - self.existencia(bodega, articulo)
        if falta <= 0:
            return
        paso = 1000 if articulo.unidad == "dosis" else 5
        pedir = redondear(max(falta, cantidad * 3), paso)
        if self.existencia(self.central, articulo) < pedir:
            proveedor = {self.a_viruta.id: self.solla, self.a_bombillo.id: self.ferreteria,
                         self.a_bebedero.id: self.ferreteria, self.a_cubetas.id: self.empaques}.get(articulo.id, self.agrovet)
            self.compra(dia, self.central, proveedor, [(articulo, redondear(pedir * 3, paso))], hora=6)
        self.traslado(dia, self.central, bodega, [(articulo, pedir)], hora=7)

    def alimento_semanal(self, dia) -> None:
        """Cada lunes se pide el alimento de las proximas dos semanas."""
        necesidades: dict[tuple[int, int], float] = defaultdict(float)
        for lote_id in self.lotes_activos():
            lote = self.db.get(Lote, lote_id)
            articulo, kg = self.racion(lote, dia)
            bodega = self.b_esp if lote.finca_id == self.esperanza.id else self.b_rec
            necesidades[(bodega.id, articulo.id)] += kg * 15
        for (bodega_id, articulo_id), kg in necesidades.items():
            bodega = self.db.get(Bodega, bodega_id)
            articulo = self.db.get(Articulo, articulo_id)
            falta = kg - self.existencia(bodega, articulo)
            if falta > 200:
                proveedor = self.italcol if bodega.id == self.b_esp.id else self.solla
                self.compra(dia, bodega, proveedor, [(articulo, redondear(falta, 40))], hora=9)

    # ------------------------------------------------------------ aves
    def lotes_activos(self) -> list[int]:
        return list(self.db.scalars(select(Lote.id).where(Lote.cuenta_id == self.cuenta.id, Lote.estado == "activo")).all())

    def edad(self, lote: Lote, dia: date) -> int:
        return lote.edad_dias_ingreso + (dia - lote.fecha_ingreso).days

    def racion(self, lote: Lote, dia: date) -> tuple[Articulo, float]:
        edad = self.edad(lote, dia)
        aves = lote.aves_actuales + lote.aves_descarte
        if lote.proposito == "engorde":
            gramos = 22 + 4.1 * edad
            return (self.a_inicio if edad <= 21 else self.a_engorde), aves * gramos / 1000
        semana = edad // 7
        if semana < len(GRAMOS_POLLITA) and semana < 19:
            return self.a_levante, aves * GRAMOS_POLLITA[semana] / 1000
        return self.a_postura, aves * random.uniform(0.108, 0.116)

    def alimentar(self, dia, lote_id, usuario, finca) -> None:
        lote = self.db.get(Lote, lote_id)
        if lote.aves_actuales + lote.aves_descarte == 0:
            return
        articulo, kg = self.racion(lote, dia)
        kg = max(1, round(kg))
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        if self.existencia(bodega, articulo) < kg:
            proveedor = self.italcol if bodega.id == self.b_esp.id else self.solla
            self.compra(dia, bodega, proveedor, [(articulo, redondear(kg * 10, 40))], hora=6)
        if self.a_las(dia, 6, random.randint(0, 40)):
            self.hacer("alimento", r_aves.nuevo_consumo, ConsumoCrear(
                lote_id=lote_id, fecha=dia, articulo_id=articulo.id, bodega_id=bodega.id, cantidad=kg,
            ), ctx=self.ctx(usuario, finca))

    def mortalidad(self, dia, lote_id, usuario, finca) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        if lote.proposito == "engorde":
            tasa = 0.0016 if edad <= 7 else (0.0005 if edad <= 28 else 0.0009)
            motivos = ["Muerte natural", "Ascitis", "Muerte subita", "Aplastamiento", "Problema de patas"]
        elif edad < 126:
            tasa = 0.0012 if edad <= 10 else 0.00018
            motivos = ["Muerte natural", "Pollita debil", "Picaje", "Aplastamiento"]
        else:
            tasa = 0.00011 + 0.0000003 * edad
            motivos = ["Muerte natural", "Prolapso", "Picaje", "Peritonitis", "Muerte natural"]
        muertas = min(poisson(lote.aves_actuales * tasa), lote.aves_actuales)
        if muertas and self.a_las(dia, 7, random.randint(0, 50)):
            self.hacer("mortalidad", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                lote_id=lote_id, fecha=dia, tipo="muerte", cantidad=muertas, motivo=random.choice(motivos),
            ), ctx=self.ctx(usuario, finca))

    def recoleccion(self, dia, lote_id) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        porcentaje = postura(edad) * random.uniform(0.975, 1.02)
        if lote.galpon_id == self.g2.id and self.calor(dia):
            porcentaje *= 0.94  # el galpon 2 se calienta y baja la postura
        huevos = int(lote.aves_actuales * porcentaje)
        if huevos <= 0:
            return
        sucios = int(huevos * random.uniform(0.01, 0.02))
        rotos = int(huevos * random.uniform(0.005, 0.009 + edad / 70000))
        buenos = huevos - sucios - rotos
        detalles = []
        repartido = 0
        for tipo, peso in zip(COMERCIALES, tamanos(edad)):
            cantidad = int(buenos * peso * random.uniform(0.93, 1.07))
            repartido += cantidad
            detalles.append((tipo, cantidad))
        detalles[2] = ("AA", detalles[2][1] + buenos - repartido)
        detalles += [("Sucio", sucios), ("Roto", rotos)]
        usuario = random.choice([self.luis, self.andres])
        if self.a_las(dia, 15, random.randint(10, 55)):
            self.hacer("produccion", r_prod.registrar_produccion, ProduccionCrear(
                lote_id=lote_id, fecha=dia,
                detalles=[DetalleProduccion(tipo_huevo_id=self.tipos[t], cantidad=max(0, c)) for t, c in detalles],
            ), ctx=self.ctx(usuario, self.esperanza))

    def pesaje(self, dia, lote_id, usuario, finca, muestra) -> None:
        lote = self.db.get(Lote, lote_id)
        edad = self.edad(lote, dia)
        if lote.proposito == "engorde":
            promedio = interpolar(PESO_POLLO, edad)
        else:
            promedio = interpolar(PESO_POLLITA, edad / 7)
        total = round(muestra * promedio * random.uniform(0.96, 1.04), 2)
        if self.a_las(dia, 10, random.randint(0, 50)):
            self.hacer("pesaje", r_aves.nuevo_pesaje, PesajeCrear(
                lote_id=lote_id, fecha=dia, aves_muestra=muestra, peso_total_kg=total,
                observaciones=random.choice([None, None, "Lote parejo", "Algunas aves pequenas en la esquina", "Buena uniformidad"]),
            ), ctx=self.ctx(usuario, finca))

    def vacuna(self, dia, lote_id, finca, articulo, producto, via, refuerzo_dias=None, tipo="vacuna", dosis="1 dosis por ave", cantidad=None) -> None:
        lote = self.db.get(Lote, lote_id)
        aves = lote.aves_actuales + lote.aves_descarte
        if aves == 0:
            return
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        usada = cantidad if cantidad is not None else redondear(aves, 100)
        if articulo is not None:
            self.asegurar(dia, bodega, articulo, usada)
        if self.a_las(dia, 8, random.randint(0, 50)):
            self.hacer("sanidad", r_san.crear, SanidadCrear(
                fecha=dia, tipo=tipo, producto=producto, lote_id=lote_id, galpon_id=lote.galpon_id,
                articulo_id=articulo.id if articulo else None, bodega_id=bodega.id if articulo else None,
                cantidad_usada=usada if articulo else None, lote_producto=f"S{random.randint(1000, 9999)}",
                dosis=dosis, via=via, aves_tratadas=aves, responsable="Jorge Cardenas",
                proximo_refuerzo=dia + timedelta(days=refuerzo_dias) if refuerzo_dias else None,
            ), ctx=self.ctx(self.jorge, finca))

    def desinfeccion(self, dia, galpon_, finca, litros=8, refuerzo=30) -> None:
        bodega = self.b_esp if finca.id == self.esperanza.id else self.b_rec
        self.asegurar(dia, bodega, self.a_desinfectante, litros)
        if self.a_las(dia, 9, random.randint(0, 50)):
            self.hacer("sanidad", r_san.crear, SanidadCrear(
                fecha=dia, tipo="desinfeccion", producto="Desinfectante yodado", galpon_id=galpon_.id,
                articulo_id=self.a_desinfectante.id, bodega_id=bodega.id, cantidad_usada=litros,
                dosis="10 ml por litro de agua", via="aspersion", responsable="Jorge Cardenas",
                proximo_refuerzo=dia + timedelta(days=refuerzo) if refuerzo else None,
            ), ctx=self.ctx(self.jorge, finca))

    # ------------------------------------------------------------ clima
    def calor(self, dia: date) -> bool:
        # Temporadas secas del Eje Cafetero: diciembre-febrero y julio-agosto
        return dia.month in (1, 2, 7, 8) and (dia.toordinal() * 7919) % 5 < 2

    # ------------------------------------------------------------ ventas
    def stock_huevos(self) -> dict[str, int]:
        from app.modelos.aves import StockHuevos

        filas = self.db.scalars(select(StockHuevos).where(StockHuevos.finca_id == self.esperanza.id)).all()
        por_id = {f.tipo_huevo_id: f.cantidad for f in filas}
        return {t: por_id.get(self.tipos[t], 0) for t in COMERCIALES}

    def vender(self, ctx, items, pagos=None, descuento=0.0, obs=None):
        return self.hacer("venta", r_ven.vender, VentaCrear(items=items, pagos=pagos or [], descuento=descuento, observaciones=obs), ctx=ctx)

    def jornada_tienda(self, dia) -> None:
        if dia.weekday() == 6:  # domingo cerrado
            return
        ctx = self.ctx(self.paola, self.esperanza)
        if not self.a_las(dia, 7, random.randint(25, 40)):
            return
        if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv1.id, base_inicial=100000), ctx=ctx) is None:
            return

        # Mayoristas en la manana: se llevan lo de ayer y dejan algo para el mostrador
        stock = self.stock_huevos()
        clientes = random.sample(CLIENTES_MAYORISTAS, k=random.randint(2, 4) + (1 if dia.weekday() == 0 else 0))
        for n, cliente in enumerate(clientes):
            if not self.a_las(dia, 8 + n, random.randint(0, 50)):
                break
            items = []
            for tipo in COMERCIALES:
                reserva = 240 if tipo in ("AA", "A") else 60
                panales = max(0, (stock[tipo] - reserva) // 30 // (len(clientes) - n))
                if panales:
                    producto = self.productos[f"panal_{tipo}"]
                    precio = round(producto["precio"] * self.factor_precio(dia) * 0.88, -2)
                    items.append(ItemVenta(producto_id=producto["id"], cantidad=panales, precio_unitario=precio))
                    stock[tipo] -= panales * 30
            if not items:
                continue
            total = sum(i.cantidad * i.precio_unitario for i in items)
            metodo = "Credito" if random.random() < 0.35 else "Transferencia"
            self.vender(ctx, items, [PagoVenta(metodo_pago_id=self.pagos[metodo], monto=total,
                                               referencia=f"Factura {random.randint(1000, 9999)}" if metodo == "Credito" else f"Bancolombia {random.randint(100000, 999999)}")],
                        obs=cliente)

        # Mostrador
        catalogo = [("panal_AA", 30), ("panal_A", 15), ("medio_AA", 14), ("docena_AA", 14), ("unidad_AA", 8),
                    ("panal_AAA", 9), ("medio_AAA", 5), ("docena_A", 6), ("unidad_A", 4), ("panal_B", 5), ("panal_Super", 3)]
        claves, pesos = zip(*catalogo)
        clientes_dia = random.randint(14, 24) + (10 if dia.weekday() == 5 else 0)
        stock = self.stock_huevos()
        for n in range(clientes_dia):
            minuto = 8 * 60 + int(n * (9 * 60) / clientes_dia) + random.randint(0, 15)
            if not self.a_las(dia, minuto // 60, minuto % 60):
                break
            items, total = [], 0
            for clave in set(random.choices(claves, weights=pesos, k=random.choice([1, 1, 1, 2]))):
                producto = self.productos[clave]
                if clave.startswith("unidad"):
                    cantidad = random.choice([5, 6, 10, 10, 15, 20])
                elif clave.startswith("panal"):
                    cantidad = random.choice([1, 1, 1, 2, 2, 3])
                else:
                    cantidad = random.choice([1, 1, 2])
                if stock[producto["tipo"]] < cantidad * producto["factor"]:
                    continue
                stock[producto["tipo"]] -= cantidad * producto["factor"]
                items.append(ItemVenta(producto_id=producto["id"], cantidad=cantidad))
                total += cantidad * producto["precio"] * self.factor_precio(dia)
            if not items:
                continue
            descuento = 1000 if total > 40000 and random.random() < 0.08 else 0
            venta = self.vender(ctx, items, None, descuento)
            if venta is not None and random.random() < 0.015:
                self.hacer("anulacion", r_ven.anular, venta.id, AnularVenta(
                    motivo=random.choice(["Se registro la cantidad equivocada", "El cliente cambio de producto", "Venta repetida por error"])),
                    ctx=ctx)

        # Pagos por transferencia del mostrador (Nequi / Daviplata)
        for _ in range(random.randint(2, 6)):
            clave = random.choice(["panal_AA", "panal_AAA", "medio_AA", "panal_A"])
            producto = self.productos[clave]
            cantidad = random.choice([1, 2])
            if stock[producto["tipo"]] < cantidad * producto["factor"]:
                continue
            if not self.a_las(dia, random.randint(9, 16), random.randint(0, 59)):
                continue
            stock[producto["tipo"]] -= cantidad * producto["factor"]
            precio = float(self.precio_vigente(producto["id"]))
            self.vender(ctx, [ItemVenta(producto_id=producto["id"], cantidad=cantidad)],
                        [PagoVenta(metodo_pago_id=self.pagos["Transferencia"], monto=precio * cantidad,
                                   referencia=f"{random.choice(['Nequi', 'Daviplata'])} {random.randint(100000, 999999)}")])

        # Cierre de caja
        if dia == self.hoy:
            return  # la caja de hoy sigue abierta
        if not self.a_las(dia, 17, random.randint(20, 50)):
            return
        turno = self.db.scalars(select(TurnoCaja).where(TurnoCaja.usuario_id == self.paola.id, TurnoCaja.estado == "abierto")).first()
        if turno is None:
            return
        from app.servicios.ventas import totales_turno

        esperado = totales_turno(self.db, turno)["esperado_en_caja"]
        azar = random.random()
        diferencia = 0 if azar < 0.8 else (-random.choice([500, 1000, 2000, 5000]) if azar < 0.92 else random.choice([200, 500, 1000]))
        self.hacer("caja", r_ven.cerrar, CerrarTurno(
            efectivo_contado=esperado + diferencia,
            observaciones=None if diferencia == 0 else ("Faltante, se revisa con la cajera" if diferencia < 0 else "Sobrante, un cliente no recibio vueltas"),
        ), ctx=ctx)

    def cerrar_caja(self, dia, usuario, ctx, hora, minuto) -> None:
        from app.servicios.ventas import totales_turno

        if not self.a_las(dia, hora, minuto):
            return
        turno = self.db.scalars(select(TurnoCaja).where(TurnoCaja.usuario_id == usuario.id, TurnoCaja.estado == "abierto")).first()
        if turno:
            self.hacer("caja", r_ven.cerrar, CerrarTurno(efectivo_contado=totales_turno(self.db, turno)["esperado_en_caja"]), ctx=ctx)

    def precio_vigente(self, producto_id: int) -> Decimal:
        from app.servicios.ventas import precio_vigente

        return precio_vigente(self.db, producto_id, self.pv1.id)

    def factor_precio(self, dia: date) -> float:
        return 1.06 if self.subida_precio and dia >= self.subida_precio else 1.0

    def subir_precios(self, dia) -> None:
        """A mitad del periodo sube el huevo un 6%."""
        if not self.a_las(dia, 6, 30):
            return
        ctx = self.ctx(self.diana, self.esperanza)
        for producto in self.productos.values():
            if producto["tipo"] is None:
                continue
            nuevo = round(producto["precio"] * 1.06, -2)
            self.hacer("precio", r_ven.poner_precio, PrecioCrear(producto_id=producto["id"], precio=nuevo, desde=dia), ctx=ctx)
        self.subida_precio = dia

    def venta_aves(self, dia, ctx, producto, lote_id, aves, kilos, cliente, hora) -> None:
        if aves <= 0 or not self.a_las(dia, hora, random.randint(0, 50)):
            return
        precio = float(self.precio_vigente(self.productos[producto]["id"]))
        total = round(kilos, 1) * precio
        self.vender(ctx, [ItemVenta(producto_id=self.productos[producto]["id"], cantidad=round(kilos, 1), lote_id=lote_id, aves=aves)],
                    [PagoVenta(metodo_pago_id=self.pagos["Transferencia"], monto=round(total, 2), referencia=f"Bancolombia {random.randint(100000, 999999)}")],
                    obs=cliente)

    # ------------------------------------------------------------ descarte (galpon 3)
    def descarte(self, dia) -> None:
        dias = (dia - self.inicio).days
        plan = {68: 450, 84: 650, 99: 700, 108: None}
        lote = self.db.get(Lote, self.po3)
        if dias in plan and lote.estado == "activo" and self.a_las(dia, 10, 30):
            cantidad = plan[dias] or lote.aves_actuales
            cantidad = min(cantidad, lote.aves_actuales)
            if cantidad:
                self.hacer("descarte", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                    lote_id=self.po3, fecha=dia, tipo="descarte", cantidad=cantidad,
                    motivo="Baja postura, fin de ciclo" if plan[dias] else "Descarte final del lote",
                ), ctx=self.ctx(self.jorge, self.esperanza))
        if dias - 1 in plan or dias - 2 in plan:
            lote = self.db.get(Lote, self.po3)
            aves = lote.aves_descarte if dias - 2 in plan else lote.aves_descarte // 2
            if aves and self.a_las(dia, 10, 50):
                ctx = self.ctx(self.jorge, self.esperanza)
                if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv1.id, base_inicial=0,
                                                               observaciones="Venta de gallina de descarte"), ctx=ctx):
                    self.venta_aves(dia, ctx, "descarte", self.po3, aves, aves * random.uniform(1.85, 2.0),
                                    "Comercializadora Avicola del Cafe", 11)
                    self.cerrar_caja(dia, self.jorge, ctx, 11, 45)
        if dias == 111:
            lote = self.db.get(Lote, self.po3)
            if lote.estado == "activo" and lote.aves_actuales + lote.aves_descarte == 0 and self.a_las(dia, 16):
                self.hacer("cierre", r_aves.cerrar, self.po3, CerrarLote(
                    fecha=dia, observaciones="Lote descartado y vendido completo"), ctx=self.ctx(self.diana, self.esperanza))
        if dias == 113:
            self.desinfeccion(dia, self.g3, self.esperanza, litros=16)
            self.asegurar(dia, self.b_esp, self.a_cal, 60)
        if dias == 122:
            self.desinfeccion(dia, self.g4, self.esperanza, litros=12, refuerzo=None)
        if dias == 120 and self.a_las(dia, 9, 15):
            lote4 = self.db.get(Lote, self.po4)
            self.hacer("traslado", r_aves.nuevo_movimiento, MovimientoAvesCrear(
                lote_id=self.po4, fecha=dia, tipo="traslado", cantidad=lote4.aves_actuales + lote4.aves_descarte,
                galpon_destino_id=self.g3.id, motivo="Pasan a postura",
                observaciones="Pollitas de 17 semanas, peso dentro de la tabla",
            ), ctx=self.ctx(self.jorge, self.esperanza))

    # ------------------------------------------------------------ pollo de engorde
    def engorde(self, dia) -> None:
        dias = (dia - self.inicio).days
        ctx_diana = self.ctx(self.diana, self.recreo)
        # Ingresos: el galpon E1 cada 56 dias desde el dia 0; el E2 desde el dia 21
        for galpon_, desde in ((self.e1, 0), (self.e2, 21)):
            if dias >= desde and (dias - desde) % 56 == 0 and self.a_las(dia, 8, 10):
                numero = len(self.engordes) + 1
                raza = "Ross 308" if numero % 2 else "Cobb 500"
                self.compra(dia, self.b_rec, self.solla, [(self.a_viruta, 60)], hora=7)
                if self.a_las(dia, 7, 30):
                    usar = min(60, int(self.existencia(self.b_rec, self.a_viruta)))
                    self.hacer("salida", r_mov.crear, MovimientoCrear(
                        tipo="salida", fecha=dia, bodega_id=self.b_rec.id, motivo="Consumo en galpones",
                        observaciones=f"Cama para el {galpon_.nombre}", items=[ItemEntrada(articulo_id=self.a_viruta.id, cantidad=usar)],
                    ), ctx=self.ctx(self.yuliana, self.recreo))
                salida = self.hacer("lote", r_aves.nuevo_lote, LoteCrear(
                    codigo=f"PE-{numero:02d}", galpon_id=galpon_.id, raza_id=self.razas[raza], proposito="engorde",
                    fecha_ingreso=dia, edad_dias_ingreso=1, aves_iniciales=random.choice([1500, 1550, 1600]),
                    costo_ave=random.choice([2900, 3000, 3100]), observaciones="Pollito de un dia de la incubadora del Valle",
                ), ctx=ctx_diana)
                if salida:
                    self.engordes.append({"id": salida.id, "inicio": dia, "galpon": galpon_})

        for datos in self.engordes:
            lote = self.db.get(Lote, datos["id"])
            if lote.estado != "activo":
                continue
            edad = (dia - datos["inicio"]).days + 1
            if edad in (7, 14, 21, 28, 35) and self.a_las(dia, 10):
                self.pesaje(dia, lote.id, self.yuliana, self.recreo, 50)
            if edad == 7:
                self.vacuna(dia, lote.id, self.recreo, self.a_newcastle, "Newcastle + Bronquitis", "ocular", 14)
                self.vacuna(dia, lote.id, self.recreo, self.a_bronquitis, "Bronquitis Mass", "ocular")
            if edad == 14:
                self.vacuna(dia, lote.id, self.recreo, self.a_gumboro, "Gumboro intermedia", "agua")
            if edad == 21:
                self.vacuna(dia, lote.id, self.recreo, self.a_newcastle, "Newcastle refuerzo", "agua")
            if edad == 24:
                self.vacuna(dia, lote.id, self.recreo, self.a_vitaminas, "Vitaminas antiestres", "agua", tipo="vitamina",
                            dosis="1 ml por litro", cantidad=2)
            # Venta en tres dias (41, 42 y 43)
            if edad in (41, 42, 43):
                if not self.a_las(dia, 7, 45):
                    continue
                if self.hacer("caja", r_ven.abrir, AbrirTurno(punto_venta_id=self.pv2.id, base_inicial=50000), ctx=ctx_diana) is None:
                    continue
                lote = self.db.get(Lote, lote.id)
                aves = lote.aves_actuales if edad == 43 else lote.aves_actuales // (44 - edad)
                peso = interpolar(PESO_POLLO, edad) * random.uniform(0.97, 1.03)
                self.venta_aves(dia, ctx_diana, "pollo", lote.id, aves, aves * peso, COMPRADORES_POLLO[edad - 41], 8)
                if edad == 43 and self.a_las(dia, 11):
                    bultos = random.randint(55, 80)
                    precio = float(self.precio_vigente(self.productos["gallinaza"]["id"]))
                    self.vender(ctx_diana, [ItemVenta(producto_id=self.productos["gallinaza"]["id"], cantidad=bultos)],
                                [PagoVenta(metodo_pago_id=self.pagos["Efectivo"], monto=bultos * precio)],
                                obs="Gallinaza para cultivo de cafe")
                self.cerrar_caja(dia, self.diana, ctx_diana, 12, 30)
            if edad == 45:
                lote = self.db.get(Lote, lote.id)
                if lote.aves_actuales + lote.aves_descarte == 0 and self.a_las(dia, 15):
                    self.hacer("cierre", r_aves.cerrar, lote.id, CerrarLote(fecha=dia, observaciones="Lote vendido completo"), ctx=ctx_diana)
                    self.desinfeccion(dia + timedelta(days=0), datos["galpon"], self.recreo, litros=10)

    # ------------------------------------------------------------ tareas y rutinas
    def rutinas(self, dia) -> None:
        ctx_esp = self.ctx(self.jorge, self.esperanza)
        ctx_rec = self.ctx(self.jorge, self.recreo)
        lista = [
            (ctx_esp, "Suministrar alimento a los galpones", "diaria", [], None, "06:00", "alta", self.luis, None),
            (ctx_esp, "Recoger huevos (manana)", "diaria", [], None, "09:00", "alta", self.luis, None),
            (ctx_esp, "Recoger huevos (tarde)", "diaria", [], None, "14:30", "alta", self.andres, None),
            (ctx_esp, "Clasificar y empacar huevo", "diaria", [], None, "15:30", "media", self.andres, None),
            (ctx_esp, "Revisar temperatura y manejo de cortinas", "diaria", [], None, "12:00", "media", self.jorge, None),
            (ctx_esp, "Lavar bebederos", "semanal", [0, 3], None, "10:00", "media", self.andres, None),
            (ctx_esp, "Remover cama y agregar cal", "semanal", [4], None, "11:00", "baja", self.luis, None),
            (ctx_esp, "Desinfeccion general de galpones", "mensual", [], 1, "09:00", "media", self.jorge, None),
            (ctx_esp, "Conteo fisico de bodega", "mensual", [], 28, "16:00", "media", self.jorge, None),
            (ctx_rec, "Alimentar y revisar pollos", "diaria", [], None, "06:30", "alta", self.yuliana, None),
            (ctx_rec, "Revisar bebederos y camas de engorde", "diaria", [], None, "13:00", "media", self.yuliana, None),
        ]
        for ctx, titulo, frecuencia, dias_semana, dia_mes, hora, prioridad, usuario, galpon_ in lista:
            self.hacer("rutina", r_tra.crear_rutina, RutinaCrear(
                titulo=titulo, frecuencia=frecuencia, dias_semana=dias_semana, dia_mes=dia_mes, hora=hora,
                prioridad=prioridad, asignado_a=usuario.id, galpon_id=galpon_.id if galpon_ else None,
            ), ctx=ctx)

    def tareas_del_dia(self, dia) -> None:
        for finca in (self.esperanza, self.recreo):
            if self.a_las(dia, 5, 55):
                self.hacer("generar", r_tra.generar, GenerarTareas(fecha=dia), ctx=self.ctx(self.jorge, finca))

    def cerrar_tareas(self, dia) -> None:
        """Al final del dia cada quien marca lo que hizo."""
        tareas = self.db.scalars(
            select(Tarea).where(Tarea.cuenta_id == self.cuenta.id, Tarea.fecha == dia, Tarea.estado.in_(("pendiente", "en_proceso")))
        ).all()
        faltan = (self.hoy - dia).days
        normales = [t for t in tareas if t.prioridad != "alta"]
        sin_hacer = {t.id for t in random.sample(normales, k=min(2, len(normales)))} if faltan == 1 else set()
        for tarea in tareas:
            hora, minuto = (int(x) for x in (tarea.hora or "10:00").split(":"))
            hora_fin = min(18, hora + random.choice([0, 1, 1, 2]))
            azar = random.random()
            if tarea.id in sin_hacer:
                continue  # ayer quedaron un par sin hacer: aparecen como atrasadas
            if faltan == 0:
                if not self.a_las(dia, hora_fin, random.randint(0, 59)):
                    continue
            elif not self.a_las(dia, hora_fin, random.randint(0, 59)):
                continue
            usuario = self.db.get(Usuario, tarea.asignado_a) if tarea.asignado_a else self.jorge
            finca = self.esperanza if tarea.finca_id == self.esperanza.id else self.recreo
            if azar < 0.03:
                self.hacer("tarea", r_tra.editar_tarea, tarea.id, TareaActualizar(
                    estado="cancelada", notas=random.choice(["Llovio todo el dia", "Se paso para manana", "No habia insumo"])),
                    ctx=self.ctx(self.jorge, finca))
            else:
                nota = random.choice([None] * 8 + ["Sin novedad", "Todo en orden", "Se reviso tambien el tanque"])
                self.hacer("tarea", r_tra.editar_tarea, tarea.id, TareaActualizar(estado="hecha", notas=nota), ctx=self.ctx(usuario, finca))

    TAREAS_SUELTAS = [
        ("Reparar malla lateral del galpon 2", "alta", "g2", "andres"),
        ("Cambiar bombillos fundidos del galpon 1", "media", "g1", "luis"),
        ("Revisar fuga en el tanque de agua", "alta", None, "luis"),
        ("Pintar comederos del galpon de levante", "baja", "g4", "andres"),
        ("Cambiar viruta humeda cerca a los bebederos", "media", "g1", "luis"),
        ("Arreglar puerta de la bodega", "baja", None, "andres"),
        ("Limpiar canales del techo", "media", None, "luis"),
        ("Revisar criadoras a gas", "alta", "g4", "andres"),
        ("Fumigar contra moscas alrededor de los galpones", "media", None, "luis"),
        ("Organizar cubetas en la bodega", "baja", None, "andres"),
        ("Rozar el pasto alrededor de los galpones", "baja", None, "luis"),
        ("Ajustar altura de comederos", "media", "g3", "andres"),
    ]

    def tarea_suelta(self, dia) -> None:
        if random.random() > 0.3 or not self.a_las(dia, 7, random.randint(0, 50)):
            return
        titulo, prioridad, galpon_, quien = random.choice(self.TAREAS_SUELTAS)
        usuario = self.luis if quien == "luis" else self.andres
        galpon_obj = getattr(self, galpon_) if galpon_ else None
        para = dia + timedelta(days=random.choice([0, 1, 1, 2, 3]))
        tarea = self.hacer("tarea", r_tra.crear_tarea, TareaCrear(
            titulo=titulo, fecha=para, hora=random.choice(["08:00", "10:00", "14:00", None]), prioridad=prioridad,
            asignado_a=usuario.id, galpon_id=galpon_obj.id if galpon_obj else None,
            descripcion=random.choice([None, "Llevar la herramienta de la bodega", "Avisar cuando quede listo"]),
        ), ctx=self.ctx(self.jorge, self.esperanza))
        self.cuentas["tareas_sueltas"] += 1 if tarea else 0

    # ------------------------------------------------------------ novedades
    def novedades(self) -> dict[int, list[dict]]:
        n = {}

        def agregar(dia, **datos):
            n.setdefault(dia, []).append(datos)

        agregar(9, categoria="servicios", subtipo="Corte de energia", titulo="Corte de luz de 5 horas en la vereda",
                gravedad="media", galpon="g1", costo=0, acciones="Se prendio la planta electrica para las bombas de agua", cerrar=0)
        agregar(17, categoria="animales", subtipo="Zarigueya", titulo="Zarigueya entro al galpon 3 de noche",
                gravedad="alta", galpon="g3", lote="po3", aves=9, costo=0, acciones="Se reforzo la malla y se puso trampa", cerrar=2)
        agregar(26, categoria="infraestructura", subtipo="Bebederos", titulo="Bebedero de campana roto en el galpon 2",
                gravedad="baja", galpon="g2", costo=38000, acciones="Se cambio por uno nuevo de la bodega", cerrar=1)
        agregar(33, categoria="clima", subtipo="Lluvia fuerte", titulo="Aguacero con granizo, se mojo la cama del galpon 1",
                gravedad="media", galpon="g1", costo=120000, acciones="Se cambio la viruta mojada y se reviso el techo", cerrar=3)
        agregar(41, categoria="salud", subtipo="Respiratorio", titulo="Aves con estornudos en el galpon 2",
                gravedad="alta", galpon="g2", lote="po2", costo=250000,
                acciones="Visita del veterinario, tratamiento con enrofloxacina 5 dias", cerrar=6, tratamiento="po2")
        agregar(55, categoria="seguridad", subtipo="Robo", titulo="Faltaron 4 panales de huevo de la bodega",
                gravedad="media", costo=66000, acciones="Se puso candado nuevo y se revisan las llaves", cerrar=4)
        agregar(63, categoria="servicios", subtipo="Agua", titulo="Falla de la bomba de agua",
                gravedad="alta", costo=380000, acciones="Se reparo el motor de la bomba", cerrar=1)
        agregar(78, categoria="animales", subtipo="Ratas", titulo="Presencia de ratas en la bodega de alimento",
                gravedad="media", costo=45000, acciones="Se pusieron cebos y se sellaron huecos", cerrar=7)
        agregar(90, categoria="clima", subtipo="Calor", titulo="Dia muy caluroso, jadeo en el galpon 2",
                gravedad="media", galpon="g2", lote="po2", aves=6, costo=0, acciones="Se abrieron cortinas y se dieron electrolitos", cerrar=1)
        agregar(97, categoria="infraestructura", subtipo="Techo", titulo="Teja rota en el galpon de levante",
                gravedad="media", galpon="g4", costo=85000, acciones="Se cambiaron dos tejas", cerrar=2)
        agregar(118, categoria="salud", subtipo="Picaje", titulo="Picaje en pollitas del galpon de levante",
                gravedad="media", galpon="g4", lote="po4", aves=4, costo=0, acciones="Se bajo la intensidad de luz", cerrar=5)
        agregar(131, categoria="servicios", subtipo="Corte de energia", titulo="Se quemo el transformador de la finca",
                gravedad="alta", costo=950000, acciones="La empresa de energia cambio el transformador", cerrar=3)
        agregar(146, categoria="infraestructura", subtipo="Cortinas", titulo="Cortina del galpon 3 rasgada por el viento",
                gravedad="baja", galpon="g3", costo=160000, acciones="Se cosio y se cambio el tramo roto", cerrar=4)
        agregar(158, categoria="animales", subtipo="Perros", titulo="Perros de la vereda rondando los galpones",
                gravedad="baja", costo=0, acciones="Se hablo con los vecinos", cerrar=2)
        agregar(167, categoria="infraestructura", subtipo="Techo", titulo="Goteras en el techo del galpon 2",
                gravedad="alta", galpon="g2", costo=300000, acciones=None, cerrar=None)
        agregar(174, categoria="clima", subtipo="Lluvia fuerte", titulo="Barro en la entrada, el camion de alimento no pudo subir",
                gravedad="media", costo=0, acciones=None, cerrar=None)
        agregar(178, categoria="salud", subtipo="Diarrea", titulo="Heces liquidas en algunas aves del galpon 1",
                gravedad="media", galpon="g1", lote="po1", costo=0, acciones=None, cerrar=None)
        return n

    def registrar_novedades(self, dia, pendientes: list) -> None:
        dias = (dia - self.inicio).days
        for datos in self.plan_novedades.get(dias, []):
            if not self.a_las(dia, random.randint(7, 11), random.randint(0, 59)):
                continue
            galpon_ = getattr(self, datos["galpon"]) if datos.get("galpon") else None
            lote_id = getattr(self, datos["lote"]) if datos.get("lote") else None
            if lote_id:
                lote = self.db.get(Lote, lote_id)
                if lote.estado != "activo":
                    lote_id = None
            quien = random.choice([self.jorge, self.luis, self.andres])
            novedad = self.hacer("novedad", r_tra.crear_novedad, NovedadCrear(
                fecha=dia, categoria=datos["categoria"], subtipo=datos["subtipo"], titulo=datos["titulo"],
                gravedad=datos["gravedad"], galpon_id=galpon_.id if galpon_ else None, lote_id=lote_id,
                aves_afectadas=datos.get("aves", 0) if lote_id else 0, descontar_aves=bool(datos.get("aves")) and bool(lote_id),
                costo_estimado=datos["costo"], descripcion="Reportado por " + quien.nombres,
            ), ctx=self.ctx(quien, self.esperanza))
            if novedad and datos.get("cerrar") is not None:
                pendientes.append((dia + timedelta(days=datos["cerrar"]), novedad.id, datos["acciones"]))
            if novedad and datos.get("tratamiento"):
                self.vacuna(dia, getattr(self, datos["tratamiento"]), self.esperanza, self.a_antibiotico,
                            "Enrofloxacina 10%", "agua", tipo="medicamento", dosis="1 ml por litro, 5 dias", cantidad=3)
        for pendiente in [p for p in pendientes if p[0] == dia]:
            if self.a_las(dia, 16, random.randint(0, 59)):
                self.hacer("novedad", r_tra.cerrar_novedad, pendiente[1], CerrarNovedad(acciones=pendiente[2]),
                           ctx=self.ctx(self.jorge, self.esperanza))
            pendientes.remove(pendiente)

    # ------------------------------------------------------------ inventario de rutina
    def inventario_rutina(self, dia) -> None:
        dias = (dia - self.inicio).days
        # Cada sabado se sacan las cubetas usadas
        if dia.weekday() == 5 and self.a_las(dia, 17, 55):
            usadas = random.randint(900, 1300)
            usadas = min(usadas, int(self.existencia(self.b_esp, self.a_cubetas)))
            if usadas > 0:
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Empaque de huevo",
                    items=[ItemEntrada(articulo_id=self.a_cubetas.id, cantidad=usadas)],
                ), ctx=self.ctx(self.jorge, self.esperanza))
        if dia.weekday() == 0 and self.existencia(self.b_esp, self.a_cubetas) < 1600:
            self.compra(dia, self.b_esp, self.empaques, [(self.a_cubetas, 3000)], hora=10)
        # Cal y viruta de los jueves
        if dia.weekday() == 4:
            self.asegurar(dia, self.b_esp, self.a_cal, 25)
            if self.a_las(dia, 11, 30):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Consumo en galpones",
                    observaciones="Cal para la cama", items=[ItemEntrada(articulo_id=self.a_cal.id, cantidad=25)],
                ), ctx=self.ctx(self.luis, self.esperanza))
        # Conteo de fin de mes (dia 28): pequenas diferencias
        if dia.day == 28 and self.a_las(dia, 16, 40):
            items = []
            for articulo in (self.a_cubetas, self.a_cal, self.a_postura):
                actual = self.existencia(self.b_esp, articulo)
                contado = max(0, round(actual + random.choice([-1, -1, 0, 1]) * random.uniform(0, 0.004) * actual))
                items.append(ItemEntrada(articulo_id=articulo.id, cantidad=contado))
            self.hacer("ajuste", r_mov.crear, MovimientoCrear(
                tipo="ajuste", fecha=dia, bodega_id=self.b_esp.id, motivo="Conteo fisico de fin de mes", items=items,
            ), ctx=self.ctx(self.jorge, self.esperanza))
        # Viruta nueva para las ponedoras cada mes
        if dia.day == 3:
            self.asegurar(dia, self.b_esp, self.a_viruta, 18)
            if self.a_las(dia, 11, 10):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Consumo en galpones",
                    observaciones="Cambio de cama en nidos y zonas humedas", items=[ItemEntrada(articulo_id=self.a_viruta.id, cantidad=18)],
                ), ctx=self.ctx(self.luis, self.esperanza))
        # Bombillos que se funden
        if dias % 23 == 11:
            self.asegurar(dia, self.b_esp, self.a_bombillo, 2)
            if self.a_las(dia, 14, 20):
                self.hacer("salida", r_mov.crear, MovimientoCrear(
                    tipo="salida", fecha=dia, bodega_id=self.b_esp.id, motivo="Reposicion",
                    observaciones="Cambio de bombillos fundidos", items=[ItemEntrada(articulo_id=self.a_bombillo.id, cantidad=2)],
                ), ctx=self.ctx(self.luis, self.esperanza))

    # ------------------------------------------------------------ plan de sanidad de ponedoras
    def sanidad_ponedoras(self, dia) -> None:
        dias = (dia - self.inicio).days
        # Revacunacion de Newcastle cada 90 dias, escalonada por lote
        for lote_id, desfase in ((self.po1, 20), (self.po2, 45), (self.po3, 5)):
            if dias >= desfase and (dias - desfase) % 90 == 0:
                self.vacuna(dia, lote_id, self.esperanza, self.a_newcastle, "Newcastle revacunacion", "agua", 90)
        # Vitaminas el primer lunes de cada mes
        if dia.weekday() == 0 and dia.day <= 7:
            for lote_id in (self.po1, self.po2, self.po3, self.po4):
                lote = self.db.get(Lote, lote_id)
                if lote.estado == "activo":
                    litros = max(1, round((lote.aves_actuales + lote.aves_descarte) / 1000))
                    self.vacuna(dia, lote_id, self.esperanza, self.a_vitaminas, "Vitaminas y electrolitos", "agua",
                                tipo="vitamina", dosis="1 ml por litro, 3 dias", cantidad=litros)
        # Desinfeccion mensual
        if dia.day == 1:
            for galpon_ in (self.g1, self.g2, self.g4 if dias < 120 else self.g3):
                self.desinfeccion(dia, galpon_, self.esperanza)
        # Plan de la pollita (PO-04)
        edad = 1 + dias
        plan = {
            7: (self.a_newcastle, "Newcastle + Bronquitis", "ocular", 14),
            8: (self.a_bronquitis, "Bronquitis Mass", "ocular", None),
            14: (self.a_gumboro, "Gumboro intermedia", "agua", 14),
            21: (self.a_newcastle, "Newcastle refuerzo", "agua", 35),
            28: (self.a_gumboro, "Gumboro refuerzo", "agua", None),
            56: (self.a_viruela, "Viruela aviar", "inyectado", None),
            84: (self.a_newcastle, "Newcastle refuerzo", "agua", 28),
            112: (self.a_newcastle, "Newcastle + Bronquitis pre postura", "aspersion", 90),
            113: (self.a_bronquitis, "Bronquitis pre postura", "aspersion", None),
        }
        if edad in plan:
            articulo, producto, via, refuerzo = plan[edad]
            self.vacuna(dia, self.po4, self.esperanza, articulo, producto, via, refuerzo)
        # Pesajes: pollitas cada 14 dias, ponedoras cada mes
        if edad % 14 == 0 and edad <= 140:
            self.pesaje(dia, self.po4, self.jorge, self.esperanza, 50)
        if dia.day == 15:
            for lote_id in (self.po1, self.po2, self.po3):
                lote = self.db.get(Lote, lote_id)
                if lote.estado == "activo" and lote.aves_actuales:
                    self.pesaje_ponedora(dia, lote_id)

    def pesaje_ponedora(self, dia, lote_id) -> None:
        total = round(30 * random.uniform(1.92, 2.05), 2)
        if self.a_las(dia, 10, random.randint(0, 50)):
            self.hacer("pesaje", r_aves.nuevo_pesaje, PesajeCrear(
                lote_id=lote_id, fecha=dia, aves_muestra=30, peso_total_kg=total), ctx=self.ctx(self.jorge, self.esperanza))

    # ------------------------------------------------------------ sensores
    def lecturas(self) -> int:
        """Una medicion cada 30 minutos de los ultimos 20 dias y cada 3 horas de antes."""
        filas = []
        creado = datetime.utcnow()
        limite_detalle = self.hoy - timedelta(days=20)
        silo = 3200.0
        momento = datetime.combine(self.inicio, time(0))
        while momento <= self.ahora_local:
            paso = timedelta(minutes=30) if momento.date() >= limite_detalle else timedelta(hours=3)
            hora = momento.hour + momento.minute / 60
            dia = momento.date()
            # Clima de montana: minima al amanecer, maxima a las 2 de la tarde
            onda = math.sin((hora - 8) / 24 * 2 * math.pi)
            calor = 2.6 if self.calor(dia) else 0
            estacion = 1.2 * math.sin((dia.toordinal() % 365) / 365 * 2 * math.pi)
            ruido = random.gauss(0, 0.5)
            t_base = 21.5 + 4.2 * onda + estacion + ruido
            valores = {
                "t1": t_base + calor * max(onda, 0),
                "t2": t_base + 0.9 + (calor + 0.8) * max(onda, 0),
                "t3": t_base - 0.3 + calor * max(onda, 0),
                "h1": 68 - 12 * onda + random.gauss(0, 2.5),
                "h2": 66 - 12 * onda + random.gauss(0, 2.5),
                "a1": 9 + 4 * math.sin(dia.toordinal() / 5) + (7 if (dia.toordinal() % 29) in (0, 1) else 0) + random.gauss(0, 1.2),
                "te1": 27 + 3.5 * onda + ruido,
                "he1": 64 - 10 * onda + random.gauss(0, 2.5),
            }
            # Silo: baja con el consumo y se llena los lunes
            if momento.weekday() == 0 and momento.hour == 9 and momento.minute == 0:
                silo = 3900.0
            silo = max(150.0, silo - (340 / 24) * paso.total_seconds() / 3600 * random.uniform(0.8, 1.2))
            valores["silo"] = silo
            # Ultima lectura del galpon 2: se esta calentando ahora
            if momento + paso > self.ahora_local:
                valores["t2"] = max(valores["t2"], 29.4)
            for clave, valor in valores.items():
                sensor = self.sensores[clave]
                if clave == "te1" and not self.hay_pollo(dia):
                    continue
                valor = round(valor, 1 if clave != "silo" else 0)
                minimo = float(sensor.min_ok) if sensor.min_ok is not None else sensor_tipo_min(self, sensor)
                maximo = float(sensor.max_ok) if sensor.max_ok is not None else sensor_tipo_max(self, sensor)
                filas.append(LecturaSensor(
                    sensor_id=sensor.id, valor=valor, medido_en=momento + DESFASE,
                    fuera_rango=estado_de(valor, minimo, maximo) != "ok", origen="dispositivo", creado_en=creado,
                ))
            if len(filas) > 5000:
                self.db.add_all(filas)
                self.db.commit()
                self.cuentas["lecturas"] += len(filas)
                filas = []
            momento += paso
        self.db.add_all(filas)
        self.db.commit()
        self.cuentas["lecturas"] += len(filas)
        return self.cuentas["lecturas"]

    def hay_pollo(self, dia: date) -> bool:
        dias = (dia - self.inicio).days
        return dias >= 0 and dias % 56 < 46

    # ------------------------------------------------------------ todo junto
    def correr(self) -> None:
        random.seed(2026)
        self.subida_precio = None
        existente = self.db.scalars(select(Cuenta.id).where(Cuenta.nombre == NOMBRE_CUENTA)).first()
        if existente:
            raise SystemExit(
                f"Ya existe la cuenta '{NOMBRE_CUENTA}'. Los datos de ejemplo se cargan una sola vez; "
                "para empezar de cero borra la base de datos."
            )
        self.crear_estructura()
        self.plan_novedades = self.novedades()
        pendientes: list = []

        congelador = freeze_time(datetime.combine(self.inicio, time(6)) + DESFASE, tick=False)
        self.reloj = congelador.start()
        try:
            self.arrancar()
            dia = self.inicio
            while dia <= self.hoy:
                numero = (dia - self.inicio).days
                if numero and numero % 15 == 0:
                    log.info("Dia %s de %s (%s)", numero, (self.hoy - self.inicio).days, dia.isoformat())
                if numero == (self.hoy - self.inicio).days // 2:
                    self.subir_precios(dia)
                self.tareas_del_dia(dia)
                if dia.weekday() == 0:
                    self.alimento_semanal(dia)
                for lote_id in self.lotes_activos():
                    lote = self.db.get(Lote, lote_id)
                    finca = self.esperanza if lote.finca_id == self.esperanza.id else self.recreo
                    usuario = self.luis if finca.id == self.esperanza.id else self.yuliana
                    self.alimentar(dia, lote_id, usuario, finca)
                    self.mortalidad(dia, lote_id, usuario, finca)
                self.sanidad_ponedoras(dia)
                self.engorde(dia)
                self.descarte(dia)
                self.tarea_suelta(dia)
                self.registrar_novedades(dia, pendientes)
                self.jornada_tienda(dia)
                for lote_id in (self.po1, self.po2, self.po3, self.po4):
                    lote = self.db.get(Lote, lote_id)
                    if lote.estado == "activo":
                        self.recoleccion(dia, lote_id)
                self.inventario_rutina(dia)
                self.cerrar_tareas(dia)
                dia += timedelta(days=1)
        finally:
            congelador.stop()

        # Tareas de dias pasados creadas a mano que nadie cerro: se marcan hechas
        viejas = self.db.scalars(
            select(Tarea).where(Tarea.cuenta_id == self.cuenta.id, Tarea.fecha < self.hoy - timedelta(days=1),
                                Tarea.estado.in_(("pendiente", "en_proceso")))
        ).all()
        for tarea in viejas:
            tarea.estado = "hecha"
            tarea.terminada_por = tarea.asignado_nombre
            tarea.terminada_en = datetime.combine(tarea.fecha, time(17)) + DESFASE
        # Ultimo ingreso de cada usuario
        for usuario in (self.carlos, self.diana, self.jorge, self.luis, self.andres, self.yuliana, self.paola):
            usuario.ultimo_ingreso = datetime.utcnow() - timedelta(hours=random.randint(1, 30))
        self.db.commit()

        log.info("Guardando mediciones de los sensores...")
        self.lecturas()


def sensor_tipo_min(demo: Demo, sensor: Sensor) -> float | None:
    tipo = demo.db.get(TipoSensor, sensor.tipo_id)
    return float(tipo.min_ok) if tipo.min_ok is not None else None


def sensor_tipo_max(demo: Demo, sensor: Sensor) -> float | None:
    tipo = demo.db.get(TipoSensor, sensor.tipo_id)
    return float(tipo.max_ok) if tipo.max_ok is not None else None


def principal() -> None:
    analizador = argparse.ArgumentParser(description="Carga datos de ejemplo de una granja con varios meses de trabajo")
    analizador.add_argument("--dias", type=int, default=180, help="cuantos dias hacia atras (por defecto 180)")
    argumentos = analizador.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("avisena").setLevel(logging.INFO)

    demo = Demo(max(30, min(argumentos.dias, 400)))
    demo.correr()

    print()
    print("Listo. Esto quedo registrado:")
    for que, cuantos in sorted(demo.cuentas.items()):
        print(f"  {que:<16} {cuantos:>7}")
    if demo.errores:
        print("Operaciones que el sistema rechazo (normal si son pocas):")
        for que, cuantos in sorted(demo.errores.items()):
            print(f"  {que:<16} {cuantos:>7}")
    print()
    print(f"Entra con cualquiera de estos usuarios (contrasena: {CLAVE_DEMO}):")
    for correo, rol in (("dueno", "propietario"), ("admin", "administrador"), ("supervisor", "supervisor"),
                        ("operario1", "operario"), ("caja", "cajero")):
        print(f"  {correo + '@' + DOMINIO:<32} {rol}")


if __name__ == "__main__":
    principal()
