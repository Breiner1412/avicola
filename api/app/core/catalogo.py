"""Modulos, roles y permisos que se cargan al crear la base de datos."""

# (clave, nombre, grupo, orden)
MODULOS: list[tuple[str, str, str, int]] = [
    ("panel", "Panel", "general", 10),
    ("fincas", "Fincas", "organizacion", 20),
    ("galpones", "Galpones", "organizacion", 30),
    ("usuarios", "Usuarios", "organizacion", 40),
    ("roles", "Roles y permisos", "organizacion", 50),
    ("lotes", "Lotes de aves", "aves", 60),
    ("produccion", "Produccion de huevos", "aves", 70),
    ("movimientos_aves", "Movimientos de aves", "aves", 80),
    ("pesajes", "Pesajes", "aves", 90),
    ("alimentacion", "Consumo de alimento", "aves", 100),
    ("sanidad", "Vacunas y tratamientos", "aves", 110),
    ("bodegas", "Bodegas", "inventario", 120),
    ("articulos", "Articulos", "inventario", 130),
    ("movimientos_inventario", "Entradas y salidas", "inventario", 140),
    ("proveedores", "Proveedores", "inventario", 150),
    ("puntos_venta", "Puntos de venta", "ventas", 160),
    ("productos_venta", "Productos", "ventas", 170),
    ("precios", "Precios", "ventas", 180),
    ("ventas", "Ventas", "ventas", 190),
    ("caja", "Turnos de caja", "ventas", 200),
    ("tareas", "Tareas", "operacion", 210),
    ("novedades", "Novedades e incidentes", "operacion", 220),
    ("sensores", "Sensores", "operacion", 230),
    ("gastos", "Gastos", "finanzas", 240),
    ("reportes", "Reportes", "finanzas", 250),
    ("importacion", "Importar desde Excel", "datos", 260),
    ("auditoria", "Registro de cambios", "datos", 270),
    ("cuentas", "Cuentas del sistema", "plataforma", 280),
]

# (clave, nombre, descripcion, nivel, de_plataforma)
ROLES: list[tuple[str, str, str, int, bool]] = [
    ("plataforma", "Plataforma", "Administra el sistema y todas las cuentas", 0, True),
    ("propietario", "Propietario", "Dueno de la cuenta: ve y administra todas sus fincas", 1, False),
    ("administrador", "Administrador", "Administra la operacion de todas las fincas de la cuenta", 2, False),
    ("supervisor", "Supervisor", "Responsable de una o varias fincas", 3, False),
    ("operario", "Operario", "Registra el trabajo diario de la finca", 4, False),
    ("cajero", "Cajero", "Atiende el punto de venta", 4, False),
]

# Letras: v ver, c crear, e editar, b borrar
TODO = "vceb"
OPERAR = "vce"
SOLO_VER = "v"
REGISTRAR = "vc"

PERMISOS: dict[str, dict[str, str]] = {
    "plataforma": {clave: TODO for clave, *_ in MODULOS},
    "propietario": {clave: TODO for clave, *_ in MODULOS if clave != "cuentas"},
    "administrador": {
        **{clave: TODO for clave, *_ in MODULOS if clave not in ("cuentas", "roles", "auditoria")},
        "roles": "ve",
        "auditoria": SOLO_VER,
    },
    "supervisor": {
        "panel": SOLO_VER,
        "fincas": SOLO_VER,
        "galpones": OPERAR,
        "usuarios": SOLO_VER,
        "lotes": OPERAR,
        "produccion": OPERAR,
        "movimientos_aves": OPERAR,
        "pesajes": OPERAR,
        "alimentacion": OPERAR,
        "sanidad": OPERAR,
        "bodegas": SOLO_VER,
        "articulos": OPERAR,
        "movimientos_inventario": OPERAR,
        "proveedores": SOLO_VER,
        "puntos_venta": SOLO_VER,
        "productos_venta": SOLO_VER,
        "precios": SOLO_VER,
        "ventas": OPERAR,
        "caja": SOLO_VER,
        "tareas": TODO,
        "novedades": OPERAR,
        "sensores": OPERAR,
        "gastos": REGISTRAR,
        "reportes": SOLO_VER,
        "importacion": REGISTRAR,
        "auditoria": SOLO_VER,
    },
    "operario": {
        "panel": SOLO_VER,
        "galpones": SOLO_VER,
        "lotes": SOLO_VER,
        "produccion": REGISTRAR,
        "movimientos_aves": REGISTRAR,
        "pesajes": REGISTRAR,
        "alimentacion": REGISTRAR,
        "sanidad": REGISTRAR,
        "bodegas": SOLO_VER,
        "articulos": SOLO_VER,
        "movimientos_inventario": REGISTRAR,
        "tareas": OPERAR,
        "novedades": REGISTRAR,
        "sensores": SOLO_VER,
    },
    "cajero": {
        "panel": SOLO_VER,
        "productos_venta": SOLO_VER,
        "precios": SOLO_VER,
        "ventas": OPERAR,
        "caja": OPERAR,
        "lotes": SOLO_VER,
        "novedades": REGISTRAR,
        "tareas": SOLO_VER,
    },
}

ACCIONES = {"v": "ver", "c": "crear", "e": "editar", "b": "borrar"}


# Categorias de articulos que trae el sistema (las cuentas pueden agregar las suyas)
# (nombre, clase)
CATEGORIAS_ARTICULO: list[tuple[str, str]] = [
    ("Alimento", "alimento"),
    ("Vacunas", "vacuna"),
    ("Medicamentos", "medicamento"),
    ("Herramientas", "herramienta"),
    ("Repuestos", "repuesto"),
    ("Insumos de aseo", "insumo"),
    ("Materiales", "insumo"),
    ("Otros", "otro"),
]


# Razas que trae el sistema (cada cuenta puede agregar las suyas)
# (nombre, proposito)
RAZAS: list[tuple[str, str]] = [
    ("Hy-Line Brown", "postura"),
    ("Lohmann Brown", "postura"),
    ("Isa Brown", "postura"),
    ("Bovans Brown", "postura"),
    ("Criolla", "postura"),
    ("Ross 308", "engorde"),
    ("Cobb 500", "engorde"),
    ("Hubbard", "engorde"),
]

# Tipos de huevo: (nombre, orden, se vende)
TIPOS_HUEVO: list[tuple[str, int, bool]] = [
    ("Super", 10, True),
    ("AAA", 20, True),
    ("AA", 30, True),
    ("A", 40, True),
    ("B", 50, True),
    ("Sucio", 90, False),
    ("Roto", 100, False),
]
