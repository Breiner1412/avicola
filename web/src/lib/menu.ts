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
    titulo: "Sistema",
    enlaces: [
      { modulo: "auditoria", etiqueta: "Registro de cambios", ruta: "/auditoria", icono: "registro" },
      { modulo: "cuentas", etiqueta: "Cuentas", ruta: "/cuentas", icono: "cuenta" },
    ],
  },
];
