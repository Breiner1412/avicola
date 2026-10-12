"use client";

import { useEffect, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { Icono } from "./iconos";

type Tono = "principal" | "galpon" | "suave" | "peligro" | "fantasma";
type Tamano = "compacto" | "normal" | "grande" | "cobrar";

// La yema es solo para la accion que termina el trabajo; lo demas va en verde o en blanco
const TONOS: Record<Tono, string> = {
  principal:
    "bg-yema text-tinta shadow-[inset_0_-2px_0_var(--color-yema-honda)] hover:bg-yema-clara active:bg-yema-honda disabled:bg-yema-suave disabled:text-tinta-3 disabled:shadow-none",
  galpon: "bg-galpon text-white hover:bg-galpon-2 active:bg-galpon-honda disabled:bg-galpon-claro",
  suave:
    "bg-superficie text-tinta ring-[1.5px] ring-inset ring-linea hover:bg-cal hover:ring-tinta-3 disabled:text-tinta-3 disabled:ring-linea-suave",
  peligro:
    "bg-superficie text-alerta ring-[1.5px] ring-inset ring-alerta-borde hover:bg-alerta-suave disabled:text-alerta-borde",
  fantasma: "text-tinta-2 hover:bg-cal-honda hover:text-tinta",
};

// Normal: 44 px, el minimo comodo para un dedo. Grande y cobrar: para la caja.
const TAMANOS: Record<Tamano, string> = {
  compacto: "min-h-10 rounded-lg px-3 text-sm",
  normal: "min-h-11 rounded-lg px-4 text-base",
  grande: "min-h-14 rounded-lg px-6 text-lg",
  cobrar: "min-h-16 rounded-xl px-6 font-cifra text-[1.35rem] font-bold [font-stretch:110%]",
};

export function Boton({
  tono = "principal",
  tamano = "normal",
  icono,
  className = "",
  children,
  ...resto
}: ButtonHTMLAttributes<HTMLButtonElement> & { tono?: Tono; tamano?: Tamano; icono?: string }) {
  return (
    <button
      {...resto}
      className={`inline-flex items-center justify-center gap-2 font-semibold transition
        focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-yema-honda
        disabled:cursor-not-allowed ${TAMANOS[tamano]} ${TONOS[tono]} ${className}`}
    >
      {icono ? <Icono nombre={icono} className={tamano === "compacto" ? "h-4 w-4" : "h-5 w-5"} /> : null}
      {children}
    </button>
  );
}

const CAMPO =
  "min-h-12 w-full rounded-lg border-[1.5px] border-linea bg-superficie px-3 py-2 text-base text-tinta transition placeholder:text-tinta-3 focus:border-galpon focus:ring-3 focus:ring-galpon/15 focus:outline-none disabled:bg-cal disabled:text-tinta-3";

export function Campo({
  etiqueta,
  error,
  ayuda,
  className = "",
  ...resto
}: InputHTMLAttributes<HTMLInputElement> & { etiqueta: string; error?: string; ayuda?: string }) {
  return (
    <label className="block text-sm">
      {etiqueta ? <span className="mb-1.5 block font-semibold text-tinta">{etiqueta}</span> : null}
      <input {...resto} className={`${CAMPO} ${error ? "border-alerta" : ""} ${className}`} />
      {ayuda && !error ? <span className="mt-1 block text-sm text-tinta-2">{ayuda}</span> : null}
      {error ? <span className="mt-1 block text-sm font-semibold text-alerta">{error}</span> : null}
    </label>
  );
}

export function Lista({
  etiqueta,
  ayuda,
  children,
  className = "",
  ...resto
}: SelectHTMLAttributes<HTMLSelectElement> & { etiqueta: string; ayuda?: string }) {
  return (
    <label className="block text-sm">
      {etiqueta ? <span className="mb-1.5 block font-semibold text-tinta">{etiqueta}</span> : null}
      <span className="relative block">
        <select {...resto} className={`${CAMPO} appearance-none pr-10 ${className}`}>
          {children}
        </select>
        <Icono
          nombre="abajo"
          className="pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-tinta-2"
        />
      </span>
      {ayuda ? <span className="mt-1 block text-sm text-tinta-2">{ayuda}</span> : null}
    </label>
  );
}

const AVISOS = {
  error: { caja: "bg-alerta-suave border-alerta", icono: "alerta", color: "text-alerta" },
  bien: { caja: "bg-bien-suave border-bien", icono: "bien", color: "text-bien" },
  info: { caja: "bg-info-suave border-info", icono: "alerta", color: "text-info" },
};

export function Aviso({ tipo = "error", children }: { tipo?: "error" | "bien" | "info"; children: ReactNode }) {
  const estilo = AVISOS[tipo];
  return (
    <div className={`flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 text-base text-tinta ${estilo.caja}`}>
      <Icono nombre={estilo.icono} className={`mt-1 h-4 w-4 shrink-0 ${estilo.color}`} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Titulo de la pantalla, con su linea de ayuda y las acciones a la derecha. */
export function Encabezado({
  titulo,
  descripcion,
  acciones,
  antes,
}: {
  titulo: ReactNode;
  descripcion?: ReactNode;
  acciones?: ReactNode;
  antes?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {antes}
        <h1 className="titulo-pantalla">{titulo}</h1>
        {descripcion ? <p className="bajada">{descripcion}</p> : null}
      </div>
      {acciones ? <div className="flex flex-wrap items-center gap-2">{acciones}</div> : null}
    </div>
  );
}

/** Bloque verde para el resumen que mas importa en la pantalla. Uno por pantalla. */
export function Franja({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`overflow-hidden rounded-xl bg-galpon text-galpon-suave ${className}`}>{children}</section>;
}

/** Una cifra dentro de la Franja. */
export function CifraFranja({
  titulo,
  valor,
  detalle,
  children,
}: {
  titulo: string;
  valor: ReactNode;
  detalle?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1 px-5 py-4 sm:px-6 sm:py-5">
      <span className="text-base text-galpon-claro">{titulo}</span>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="cifra text-[2.25rem] leading-none font-bold text-white [font-stretch:118%] sm:text-[2.75rem]">
          {valor}
        </span>
        {children}
      </div>
      {detalle ? <span className="text-base text-galpon-suave">{detalle}</span> : null}
    </div>
  );
}

export function Tarjeta({
  titulo,
  descripcion,
  icono,
  children,
  acciones,
  className = "",
}: {
  titulo?: string;
  descripcion?: string;
  icono?: string;
  children: ReactNode;
  acciones?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-linea bg-superficie ${className}`}>
      {(titulo || acciones) && (
        <header className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4 pb-1">
          <div className="flex min-w-0 items-start gap-2.5">
            {icono ? <Icono nombre={icono} className="mt-1 h-5 w-5 shrink-0 text-galpon-2" /> : null}
            <div className="min-w-0">
              <h2 className="font-cifra text-lg leading-snug font-bold text-tinta [font-stretch:105%]">{titulo}</h2>
              {descripcion ? <p className="text-sm text-tinta-2">{descripcion}</p> : null}
            </div>
          </div>
          {acciones}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

const TONOS_DATO: Record<string, string> = {
  verde: "text-galpon-2",
  ambar: "text-yema-honda",
  rojo: "text-alerta",
  azul: "text-info",
  gris: "text-tinta-3",
};

export function Dato({
  titulo,
  valor,
  detalle,
  icono = "inicio",
  tono = "verde",
  children,
}: {
  titulo: string;
  valor: ReactNode;
  detalle?: string;
  icono?: string;
  tono?: "verde" | "ambar" | "rojo" | "azul" | "gris";
  children?: ReactNode;
}) {
  return (
    <div className={`rounded-xl border border-linea bg-superficie p-4 ${tono === "rojo" ? "border-l-4 border-l-alerta" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-tinta-2">{titulo}</p>
          <p className="cifra mt-1 truncate text-[1.875rem] leading-tight font-bold text-tinta">{valor}</p>
          {detalle ? <p className="mt-0.5 text-sm text-tinta-2">{detalle}</p> : null}
        </div>
        <Icono nombre={icono} className={`h-5 w-5 shrink-0 ${TONOS_DATO[tono]}`} />
      </div>
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}

export function Tabla({
  columnas,
  numericas = [],
  children,
}: {
  columnas: string[];
  /** Posiciones de las columnas con cifras: van alineadas a la derecha */
  numericas?: number[];
  children: ReactNode;
}) {
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="tabla w-full text-left text-base">
        <thead>
          <tr className="border-b-2 border-galpon">
            {columnas.map((columna, i) => (
              <th
                key={`${columna}-${i}`}
                className={`px-3 py-3 text-sm font-semibold whitespace-nowrap text-tinta-2 first:pl-5 last:pr-5 ${
                  numericas.includes(i) ? "text-right" : ""
                }`}
              >
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-linea-suave text-tinta [&_td:first-child]:pl-5 [&_td:last-child]:pr-5">
          {children}
        </tbody>
      </table>
    </div>
  );
}

export function Vacio({ children, icono = "alerta" }: { children: ReactNode; icono?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-3 py-10 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-cal text-tinta-3">
        <Icono nombre={icono} className="h-5 w-5" />
      </span>
      <p className="max-w-prose text-base text-tinta-2">{children}</p>
    </div>
  );
}

const TONOS_INSIGNIA: Record<string, string> = {
  gris: "bg-cal-honda text-tinta-2",
  verde: "bg-bien-suave text-bien",
  rojo: "bg-alerta-suave text-alerta",
  azul: "bg-info-suave text-info",
  ambar: "bg-aten-suave text-aten",
};

export function Insignia({
  children,
  tono = "gris",
  punto = false,
}: {
  children: ReactNode;
  tono?: "gris" | "verde" | "rojo" | "azul" | "ambar";
  punto?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-semibold whitespace-nowrap ${TONOS_INSIGNIA[tono]}`}
    >
      {punto ? <span className="h-2 w-2 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}

export function Modal({
  titulo,
  abierto,
  onCerrar,
  children,
  ancho = "max-w-lg",
}: {
  titulo: string;
  abierto: boolean;
  onCerrar: () => void;
  children: ReactNode;
  ancho?: string;
}) {
  // Se cierra con Esc o dando clic afuera de la ventana
  useEffect(() => {
    if (!abierto) return;
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [abierto, onCerrar]);

  if (!abierto) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-galpon-honda/55 p-3 sm:p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        className={`mt-4 w-full sm:mt-10 ${ancho} rounded-xl bg-superficie shadow-[0_20px_50px_-12px_rgb(22_58_44/0.45)]`}
      >
        <header className="flex items-center justify-between gap-3 border-b border-linea-suave py-2 pr-2 pl-5">
          <h3 className="font-cifra text-xl font-bold text-tinta [font-stretch:108%]">{titulo}</h3>
          <button
            onClick={onCerrar}
            className="grid h-11 w-11 place-items-center rounded-lg text-tinta-2 transition hover:bg-cal hover:text-tinta"
            aria-label="Cerrar"
          >
            <Icono nombre="cerrar" className="h-5 w-5" />
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function Cargando({ texto = "Cargando..." }: { texto?: string }) {
  return (
    <div className="flex items-center gap-3 px-3 py-8 text-base text-tinta-2" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-[2.5px] border-linea border-t-galpon" />
      {texto}
    </div>
  );
}

export function Pestanas({
  opciones,
  activa,
  onCambiar,
}: {
  opciones: { clave: string; texto: string }[];
  activa: string;
  onCambiar: (clave: string) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-linea">
      {opciones.map((opcion) => (
        <button
          key={opcion.clave}
          onClick={() => onCambiar(opcion.clave)}
          aria-pressed={activa === opcion.clave}
          className={`-mb-px min-h-12 border-b-[3px] px-4 text-base whitespace-nowrap transition ${
            activa === opcion.clave
              ? "border-galpon font-bold text-tinta"
              : "border-transparent text-tinta-2 hover:border-linea hover:text-tinta"
          }`}
        >
          {opcion.texto}
        </button>
      ))}
    </div>
  );
}

/** Divide una lista en paginas. Vuelve a la primera cuando cambia `clave` (los filtros). */
export function usePaginas<T>(lista: T[] | null | undefined, porPagina = 20, clave: unknown = "") {
  const [pagina, setPagina] = useState(1);
  const total = lista?.length ?? 0;
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  // Con otros filtros se vuelve a la primera pagina
  useEffect(() => {
    setPagina(1);
  }, [clave]);
  const actual = Math.min(pagina, paginas);
  const visibles = (lista ?? []).slice((actual - 1) * porPagina, actual * porPagina);
  return { visibles, pagina: actual, paginas, total, porPagina, setPagina };
}

export function Paginador({
  pagina,
  paginas,
  total,
  porPagina,
  setPagina,
  nombre = "registros",
}: {
  pagina: number;
  paginas: number;
  total: number;
  porPagina: number;
  setPagina: (pagina: number) => void;
  nombre?: string;
}) {
  if (total <= porPagina) return null;
  const desde = (pagina - 1) * porPagina + 1;
  const hasta = Math.min(total, pagina * porPagina);

  // Numeros a mostrar: primera, ultima y las vecinas de la actual
  const numeros: (number | "...")[] = [];
  for (let n = 1; n <= paginas; n++) {
    if (n === 1 || n === paginas || Math.abs(n - pagina) <= 1) numeros.push(n);
    else if (numeros[numeros.length - 1] !== "...") numeros.push("...");
  }

  const base = "cifra grid h-11 min-w-11 place-items-center rounded-lg px-2 text-base transition";
  return (
    <nav aria-label="Paginas" className="mt-4 flex flex-col items-center justify-between gap-3 border-t border-linea-suave pt-4 sm:flex-row">
      <p className="text-sm text-tinta-2">
        {desde.toLocaleString("es-CO")}–{hasta.toLocaleString("es-CO")} de {total.toLocaleString("es-CO")} {nombre}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => setPagina(pagina - 1)}
          disabled={pagina <= 1}
          aria-label="Pagina anterior"
          className={`${base} text-tinta-2 hover:bg-cal-honda disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <Icono nombre="izquierda" className="h-5 w-5" />
        </button>
        {numeros.map((n, i) =>
          n === "..." ? (
            <span key={`p${i}`} className="px-1 text-sm text-tinta-3">
              …
            </span>
          ) : (
            <button
              key={n}
              onClick={() => setPagina(n)}
              aria-current={n === pagina ? "page" : undefined}
              className={`${base} ${n === pagina ? "bg-galpon font-bold text-white" : "text-tinta-2 hover:bg-cal-honda"}`}
            >
              {n}
            </button>
          ),
        )}
        <button
          onClick={() => setPagina(pagina + 1)}
          disabled={pagina >= paginas}
          aria-label="Pagina siguiente"
          className={`${base} text-tinta-2 hover:bg-cal-honda disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <Icono nombre="derecha" className="h-5 w-5" />
        </button>
      </div>
    </nav>
  );
}

/** Botones para elegir una opcion, como pestanas pequenas. */
export function Chips<T extends string>({
  opciones,
  valor,
  onCambiar,
}: {
  opciones: { clave: T; texto: string }[];
  valor: T;
  onCambiar: (valor: T) => void;
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-lg bg-cal-honda p-1">
      {opciones.map((opcion) => (
        <button
          key={opcion.clave}
          type="button"
          onClick={() => onCambiar(opcion.clave)}
          aria-pressed={valor === opcion.clave}
          className={`min-h-10 rounded-md px-3.5 text-base transition ${
            valor === opcion.clave
              ? "bg-superficie font-bold text-tinta shadow-[0_1px_2px_rgb(28_43_37/0.15)]"
              : "text-tinta-2 hover:text-tinta"
          }`}
        >
          {opcion.texto}
        </button>
      ))}
    </div>
  );
}
