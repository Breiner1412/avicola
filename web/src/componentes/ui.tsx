"use client";

import { useEffect, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { Icono } from "./iconos";

type Tono = "principal" | "suave" | "peligro" | "fantasma";

const TONOS: Record<Tono, string> = {
  principal:
    "bg-emerald-700 text-white shadow-sm hover:bg-emerald-800 active:bg-emerald-900 disabled:bg-emerald-300 disabled:shadow-none",
  suave:
    "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 hover:ring-slate-400 disabled:text-slate-400 disabled:ring-slate-200",
  peligro: "bg-white text-rose-700 ring-1 ring-rose-200 hover:bg-rose-50 hover:ring-rose-300 disabled:text-rose-300",
  fantasma: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
};

export function Boton({
  tono = "principal",
  icono,
  className = "",
  children,
  ...resto
}: ButtonHTMLAttributes<HTMLButtonElement> & { tono?: Tono; icono?: string }) {
  return (
    <button
      {...resto}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition
        focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600
        disabled:cursor-not-allowed ${TONOS[tono]} ${className}`}
    >
      {icono ? <Icono nombre={icono} className="h-4 w-4" /> : null}
      {children}
    </button>
  );
}

const CAMPO =
  "w-full rounded-xl border-0 bg-white px-3 py-2 text-slate-800 ring-1 ring-slate-300 transition placeholder:text-slate-400 focus:ring-2 focus:ring-emerald-600 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400";

export function Campo({
  etiqueta,
  error,
  ayuda,
  className = "",
  ...resto
}: InputHTMLAttributes<HTMLInputElement> & { etiqueta: string; error?: string; ayuda?: string }) {
  return (
    <label className="block text-sm">
      {etiqueta ? <span className="mb-1.5 block font-medium text-slate-700">{etiqueta}</span> : null}
      <input {...resto} className={`${CAMPO} ${error ? "ring-rose-400" : ""} ${className}`} />
      {ayuda && !error ? <span className="mt-1 block text-xs text-slate-500">{ayuda}</span> : null}
      {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
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
      {etiqueta ? <span className="mb-1.5 block font-medium text-slate-700">{etiqueta}</span> : null}
      <select {...resto} className={`${CAMPO} appearance-none pr-8 ${className}`}>
        {children}
      </select>
      {ayuda ? <span className="mt-1 block text-xs text-slate-500">{ayuda}</span> : null}
    </label>
  );
}

const AVISOS = {
  error: { caja: "bg-rose-50 text-rose-800 ring-rose-200", icono: "alerta" },
  bien: { caja: "bg-emerald-50 text-emerald-800 ring-emerald-200", icono: "bien" },
  info: { caja: "bg-sky-50 text-sky-900 ring-sky-200", icono: "alerta" },
};

export function Aviso({ tipo = "error", children }: { tipo?: "error" | "bien" | "info"; children: ReactNode }) {
  const estilo = AVISOS[tipo];
  return (
    <div className={`flex items-start gap-2.5 rounded-xl px-4 py-3 text-sm ring-1 ${estilo.caja}`}>
      <Icono nombre={estilo.icono} className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0">{children}</div>
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
    <section className={`rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/80 ${className}`}>
      {(titulo || acciones) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            {icono ? (
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                <Icono nombre={icono} className="h-4 w-4" />
              </span>
            ) : null}
            <div>
              <h2 className="text-sm font-semibold text-slate-800">{titulo}</h2>
              {descripcion ? <p className="text-xs text-slate-500">{descripcion}</p> : null}
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
  verde: "bg-emerald-50 text-emerald-700",
  ambar: "bg-amber-50 text-amber-700",
  rojo: "bg-rose-50 text-rose-700",
  azul: "bg-sky-50 text-sky-700",
  gris: "bg-slate-100 text-slate-600",
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
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200/80">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
          <p className="mt-1 truncate text-2xl font-semibold tracking-tight text-slate-900">{valor}</p>
          {detalle ? <p className="mt-0.5 text-xs text-slate-500">{detalle}</p> : null}
        </div>
        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${TONOS_DATO[tono]}`}>
          <Icono nombre={icono} className="h-5 w-5" />
        </span>
      </div>
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}

export function Tabla({ columnas, children }: { columnas: string[]; children: ReactNode }) {
  return (
    <div className="-mx-5 overflow-x-auto px-5">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs font-medium uppercase tracking-wide text-slate-500">
            {columnas.map((columna, i) => (
              <th key={`${columna}-${i}`} className="whitespace-nowrap px-3 py-2.5">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-slate-700">{children}</tbody>
      </table>
    </div>
  );
}

export function Vacio({ children, icono = "alerta" }: { children: ReactNode; icono?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-3 py-10 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-400">
        <Icono nombre={icono} className="h-5 w-5" />
      </span>
      <p className="text-sm text-slate-500">{children}</p>
    </div>
  );
}

const TONOS_INSIGNIA: Record<string, string> = {
  gris: "bg-slate-100 text-slate-600 ring-slate-200",
  verde: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  rojo: "bg-rose-50 text-rose-700 ring-rose-200",
  azul: "bg-sky-50 text-sky-700 ring-sky-200",
  ambar: "bg-amber-50 text-amber-800 ring-amber-200",
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
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONOS_INSIGNIA[tono]}`}
    >
      {punto ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}
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
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <div role="dialog" aria-modal="true" className={`mt-8 w-full ${ancho} rounded-2xl bg-white shadow-xl ring-1 ring-slate-200`}>
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
          <h3 className="text-base font-semibold text-slate-800">{titulo}</h3>
          <button
            onClick={onCerrar}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Cerrar"
          >
            <Icono nombre="cerrar" className="h-4 w-4" />
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function Cargando({ texto = "Cargando..." }: { texto?: string }) {
  return (
    <div className="flex items-center gap-3 px-3 py-8 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-emerald-600" />
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
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
      {opciones.map((opcion) => (
        <button
          key={opcion.clave}
          onClick={() => onCambiar(opcion.clave)}
          className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-sm transition ${
            activa === opcion.clave
              ? "border-emerald-600 font-medium text-emerald-800"
              : "border-transparent text-slate-500 hover:text-slate-800"
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

  const base = "grid h-8 min-w-8 place-items-center rounded-lg px-2 text-sm transition";
  return (
    <nav aria-label="Paginas" className="mt-4 flex flex-col items-center justify-between gap-3 border-t border-slate-100 pt-4 sm:flex-row">
      <p className="text-xs text-slate-500">
        {desde.toLocaleString("es-CO")}–{hasta.toLocaleString("es-CO")} de {total.toLocaleString("es-CO")} {nombre}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => setPagina(pagina - 1)}
          disabled={pagina <= 1}
          aria-label="Pagina anterior"
          className={`${base} text-slate-600 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <Icono nombre="izquierda" className="h-4 w-4" />
        </button>
        {numeros.map((n, i) =>
          n === "..." ? (
            <span key={`p${i}`} className="px-1 text-sm text-slate-400">
              …
            </span>
          ) : (
            <button
              key={n}
              onClick={() => setPagina(n)}
              aria-current={n === pagina ? "page" : undefined}
              className={`${base} ${n === pagina ? "bg-emerald-700 font-medium text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {n}
            </button>
          ),
        )}
        <button
          onClick={() => setPagina(pagina + 1)}
          disabled={pagina >= paginas}
          aria-label="Pagina siguiente"
          className={`${base} text-slate-600 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <Icono nombre="derecha" className="h-4 w-4" />
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
    <div className="inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
      {opciones.map((opcion) => (
        <button
          key={opcion.clave}
          type="button"
          onClick={() => onCambiar(opcion.clave)}
          className={`rounded-lg px-3 py-1.5 text-sm transition ${
            valor === opcion.clave ? "bg-white font-medium text-emerald-800 shadow-sm" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          {opcion.texto}
        </button>
      ))}
    </div>
  );
}
