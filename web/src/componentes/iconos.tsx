"use client";

type Props = { nombre: string; className?: string };

// Dibujos simples, del mismo trazo, para todo el sistema.
const TRAZOS: Record<string, React.ReactNode> = {
  inicio: (
    <>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
      <path d="M9.5 21v-6h5v6" />
    </>
  ),
  finca: (
    <>
      <path d="M3 21h18" />
      <path d="M5 21V9l7-5 7 5v12" />
      <path d="M9.5 21v-5h5v5" />
    </>
  ),
  galpon: (
    <>
      <path d="M3 20h18" />
      <path d="M4 20V9l8-4 8 4v11" />
      <path d="M8 20v-6h8v6" />
      <path d="M8 11h8" />
    </>
  ),
  usuario: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  llave: (
    <>
      <circle cx="8" cy="12" r="3.5" />
      <path d="M11.5 12H21" />
      <path d="M17 12v3.5" />
      <path d="M20 12v2.5" />
    </>
  ),
  lote: (
    <>
      <path d="M12 3c3 2.5 4.5 5.2 4.5 8A4.5 4.5 0 0 1 12 15.5 4.5 4.5 0 0 1 7.5 11c0-2.8 1.5-5.5 4.5-8Z" />
      <path d="M12 15.5V21" />
      <path d="M9 21h6" />
    </>
  ),
  huevo: (
    <>
      <path d="M12 3c3.2 2.8 5 6 5 9a5 5 0 0 1-10 0c0-3 1.8-6.2 5-9Z" />
    </>
  ),
  vacuna: (
    <>
      <path d="m16 3 5 5" />
      <path d="m18.5 5.5-9 9L7 20l-3-3 5.5-2.5 9-9" />
      <path d="m12 8 4 4" />
    </>
  ),
  bodega: (
    <>
      <path d="M3 9.5 12 4l9 5.5V20H3z" />
      <path d="M8 20v-7h8v7" />
    </>
  ),
  articulo: (
    <>
      <path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5z" />
      <path d="M12 12v9" />
      <path d="m3.5 7.5 8.5 4.5 8.5-4.5" />
    </>
  ),
  movimiento: (
    <>
      <path d="M4 8h13" />
      <path d="m14 5 3 3-3 3" />
      <path d="M20 16H7" />
      <path d="m10 13-3 3 3 3" />
    </>
  ),
  proveedor: (
    <>
      <path d="M3 16V8h11v8z" />
      <path d="M14 11h4l3 3v2h-7z" />
      <circle cx="7" cy="17.5" r="1.8" />
      <circle cx="17" cy="17.5" r="1.8" />
    </>
  ),
  caja: (
    <>
      <rect x="3" y="7" width="18" height="12" rx="2" />
      <path d="M3 11h18" />
      <path d="M7 15h3" />
    </>
  ),
  producto: (
    <>
      <path d="M4 7h16l-1.5 13h-13z" />
      <path d="M9 7V5.5a3 3 0 0 1 6 0V7" />
    </>
  ),
  tienda: (
    <>
      <path d="M4 10V20h16V10" />
      <path d="M3 10 5 4h14l2 6z" />
      <path d="M10 20v-5h4v5" />
    </>
  ),
  tarea: (
    <>
      <rect x="4" y="4" width="16" height="17" rx="2" />
      <path d="M9 3.5h6" />
      <path d="m8.5 11 2 2 4-4" />
      <path d="M8.5 16.5h7" />
    </>
  ),
  novedad: (
    <>
      <path d="M12 4 2.5 20h19z" />
      <path d="M12 10v4" />
      <path d="M12 17.2v.2" />
    </>
  ),
  sensor: (
    <>
      <path d="M12 3v4" />
      <circle cx="12" cy="12" r="3" />
      <path d="M5.5 5.5A9 9 0 0 0 5.5 18.5" />
      <path d="M18.5 5.5a9 9 0 0 1 0 13" />
    </>
  ),
  reporte: (
    <>
      <path d="M4 20h16" />
      <rect x="6" y="11" width="3" height="7" rx="1" />
      <rect x="11" y="7" width="3" height="11" rx="1" />
      <rect x="16" y="13" width="3" height="5" rx="1" />
    </>
  ),
  excel: (
    <>
      <path d="M6 3h8l5 5v13H6z" />
      <path d="M14 3v5h5" />
      <path d="m9.5 12 4 5" />
      <path d="m13.5 12-4 5" />
    </>
  ),
  registro: (
    <>
      <path d="M5 4h14v17l-7-3.5L5 21z" />
      <path d="M9 9h6" />
      <path d="M9 13h4" />
    </>
  ),
  cuenta: (
    <>
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6" />
      <path d="M3 12h18" />
    </>
  ),
  campana: (
    <>
      <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" />
      <path d="M10.5 20a2 2 0 0 0 3 0" />
    </>
  ),
  menu: (
    <>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </>
  ),
  cerrar: (
    <>
      <path d="m6 6 12 12" />
      <path d="m18 6-12 12" />
    </>
  ),
  salir: (
    <>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 8 6 12l4 4" />
      <path d="M6 12h9" />
    </>
  ),
  abajo: <path d="m6 9 6 6 6-6" />,
  fijar: (
    <>
      <path d="M9 4h6l-1 5 3 3v2H7v-2l3-3-1-5Z" />
      <path d="M12 14v6" />
    </>
  ),
  derecha: <path d="m9 6 6 6-6 6" />,
  izquierda: <path d="m15 6-6 6 6 6" />,
  mas: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  buscar: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  alerta: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5" />
      <path d="M12 16.2v.2" />
    </>
  ),
  bien: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12.5 2.5 2.5L16 9.5" />
    </>
  ),
  reloj: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.5l3.5 2" />
    </>
  ),
  peso: (
    <>
      <path d="M4 20h16l-2-9H6z" />
      <circle cx="12" cy="6.5" r="2.5" />
    </>
  ),
  dinero: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5v9" />
      <path d="M14.5 10a2.5 2.5 0 0 0-2.5-1.5c-1.4 0-2.5.8-2.5 2s1.1 1.8 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2A2.5 2.5 0 0 1 9.5 14" />
    </>
  ),
};

export function Icono({ nombre, className = "h-5 w-5" }: Props) {
  const trazo = TRAZOS[nombre] ?? TRAZOS.alerta;
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {trazo}
    </svg>
  );
}
