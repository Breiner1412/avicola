"""Crea la cuenta, las fincas, los usuarios y lo que hay en ellas."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.esquemas.aves import LoteCrear
from app.esquemas.ventas import ProductoCrear, PuntoVentaCrear
from app.modelos.acceso import Rol, Usuario, UsuarioFinca
from app.modelos.aves import Raza, TipoHuevo
from app.modelos.inventario import Articulo, Bodega, CategoriaArticulo, Proveedor
from app.modelos.organizacion import Cuenta, Finca, Galpon
from app.modelos.sensores import Sensor, TipoSensor
from app.modelos.ventas import MetodoPago
from app.rutas import aves as r_aves
from app.rutas import ventas as r_ven
from app.demo.datos import log, NOMBRE_CUENTA, CLAVE_DEMO, DOMINIO, DESFASE, COMERCIALES


class EstructuraMixin:
    """Crea la cuenta, las fincas, los usuarios y lo que hay en ellas."""

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
