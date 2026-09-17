export type Enlace = { modulo: string; etiqueta: string; ruta: string; icono: string };

export const GRUPOS: { titulo: string; enlaces: Enlace[] }[] = [
  {
    titulo: "General",
    enlaces: [{ modulo: "panel", etiqueta: "Panel", ruta: "/panel", icono: "inicio" }],
  },
  {
    titulo: "Organizacion",
    enlaces: [
      { modulo: "fincas", etiqueta: "Fincas", ruta: "/fincas", icono: "finca" },
      { modulo: "galpones", etiqueta: "Galpones", ruta: "/galpones", icono: "galpon" },
      { modulo: "usuarios", etiqueta: "Usuarios", ruta: "/usuarios", icono: "usuario" },
      { modulo: "roles", etiqueta: "Roles y permisos", ruta: "/roles", icono: "llave" },
    ],
  },
  {
    titulo: "Inventario",
    enlaces: [
      { modulo: "bodegas", etiqueta: "Bodegas", ruta: "/bodegas", icono: "bodega" },
      { modulo: "articulos", etiqueta: "Articulos", ruta: "/articulos", icono: "articulo" },
      { modulo: "movimientos_inventario", etiqueta: "Entradas y salidas", ruta: "/movimientos", icono: "movimiento" },
      { modulo: "proveedores", etiqueta: "Proveedores", ruta: "/proveedores", icono: "proveedor" },
    ],
  },
  {
    titulo: "Sistema",
    enlaces: [
      { modulo: "auditoria", etiqueta: "Registro de cambios", ruta: "/auditoria", icono: "registro" },
      { modulo: "cuentas", etiqueta: "Cuentas", ruta: "/cuentas", icono: "cuenta" },
    ],
  },
];
