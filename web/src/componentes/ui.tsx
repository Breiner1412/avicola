"use client";

import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

type Tono = "principal" | "suave" | "peligro";

const TONOS: Record<Tono, string> = {
  principal: "bg-emerald-700 text-white hover:bg-emerald-800 disabled:bg-emerald-300",
  suave: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 disabled:text-slate-400",
  peligro: "bg-white text-red-700 border border-red-300 hover:bg-red-50 disabled:text-red-300",
};

export function Boton({
  tono = "principal",
  className = "",
  children,
  ...resto
}: ButtonHTMLAttributes<HTMLButtonElement> & { tono?: Tono }) {
  return (
    <button
      {...resto}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${TONOS[tono]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Campo({
  etiqueta,
  error,
  className = "",
  ...resto
}: InputHTMLAttributes<HTMLInputElement> & { etiqueta: string; error?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{etiqueta}</span>
      <input
        {...resto}
        className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-800 outline-none focus:border-emerald-600 ${className}`}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

export function Lista({
  etiqueta,
  children,
  className = "",
  ...resto
}: SelectHTMLAttributes<HTMLSelectElement> & { etiqueta: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{etiqueta}</span>
      <select
        {...resto}
        className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 outline-none focus:border-emerald-600 ${className}`}
      >
        {children}
      </select>
    </label>
  );
}

export function Aviso({ tipo = "error", children }: { tipo?: "error" | "bien" | "info"; children: ReactNode }) {
  const estilos = {
    error: "bg-red-50 text-red-800 border-red-200",
    bien: "bg-emerald-50 text-emerald-800 border-emerald-200",
    info: "bg-sky-50 text-sky-800 border-sky-200",
  }[tipo];
  return <div className={`rounded-lg border px-4 py-3 text-sm ${estilos}`}>{children}</div>;
}

export function Tarjeta({ titulo, children, acciones }: { titulo?: string; children: ReactNode; acciones?: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {(titulo || acciones) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-800">{titulo}</h2>
          {acciones}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Tabla({ columnas, children }: { columnas: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            {columnas.map((columna) => (
              <th key={columna} className="whitespace-nowrap px-3 py-2 font-semibold">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}

export function Vacio({ children }: { children: ReactNode }) {
  return <p className="px-3 py-6 text-center text-sm text-slate-500">{children}</p>;
}

export function Insignia({ children, tono = "gris" }: { children: ReactNode; tono?: "gris" | "verde" | "rojo" | "azul" }) {
  const estilos = {
    gris: "bg-slate-100 text-slate-600",
    verde: "bg-emerald-100 text-emerald-700",
    rojo: "bg-red-100 text-red-700",
    azul: "bg-sky-100 text-sky-700",
  }[tono];
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${estilos}`}>{children}</span>;
}

export function Modal({
  titulo,
  abierto,
  onCerrar,
  children,
}: {
  titulo: string;
  abierto: boolean;
  onCerrar: () => void;
  children: ReactNode;
}) {
  if (!abierto) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4">
      <div className="mt-10 w-full max-w-lg rounded-xl bg-white shadow-lg">
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-slate-800">{titulo}</h3>
          <button onClick={onCerrar} className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Cerrar">
            ✕
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function Cargando({ texto = "Cargando..." }: { texto?: string }) {
  return (
    <div className="flex items-center gap-3 px-3 py-6 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-600" />
      {texto}
    </div>
  );
}
