"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Toaster, toast } from "sonner";
import { Icono } from "@/componentes/iconos";

// Ventanas para confirmar o pedir un dato, con el mismo estilo del sistema, en lugar
// de los confirm() y prompt() del navegador. Las notificaciones usan sonner.

type Confirmacion = {
  titulo: string;
  mensaje?: ReactNode;
  aceptar?: string;
  cancelar?: string;
  peligro?: boolean;
};

type PedidoTexto = Confirmacion & {
  etiqueta?: string;
  valor?: string;
  placeholder?: string;
  requerido?: boolean;
  largo?: boolean;
};

type Abierto =
  | { tipo: "confirmar"; opciones: Confirmacion; responder: (valor: boolean) => void }
  | { tipo: "texto"; opciones: PedidoTexto; responder: (valor: string | null) => void };

type Dialogos = {
  confirmar: (opciones: Confirmacion) => Promise<boolean>;
  pedirTexto: (opciones: PedidoTexto) => Promise<string | null>;
};

const Contexto = createContext<Dialogos | null>(null);

export function useDialogos(): Dialogos {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useDialogos va dentro de ProveedorDialogos");
  return valor;
}

/** Notificaciones cortas en la esquina de la pantalla. */
export const avisar = {
  bien: (mensaje: string) => toast.success(mensaje),
  error: (mensaje: string) => toast.error(mensaje),
  info: (mensaje: string) => toast(mensaje),
};

export function ProveedorDialogos({ children }: { children: ReactNode }) {
  const [abierto, setAbierto] = useState<Abierto | null>(null);

  const confirmar = useCallback(
    (opciones: Confirmacion) =>
      new Promise<boolean>((resolver) => setAbierto({ tipo: "confirmar", opciones, responder: resolver })),
    [],
  );
  const pedirTexto = useCallback(
    (opciones: PedidoTexto) =>
      new Promise<string | null>((resolver) => setAbierto({ tipo: "texto", opciones, responder: resolver })),
    [],
  );

  return (
    <Contexto.Provider value={{ confirmar, pedirTexto }}>
      {children}
      {abierto ? <Ventana abierto={abierto} cerrar={() => setAbierto(null)} /> : null}
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{ className: "!rounded-xl !text-sm", duration: 4000 }}
      />
    </Contexto.Provider>
  );
}

function Ventana({ abierto, cerrar }: { abierto: Abierto; cerrar: () => void }) {
  const { opciones } = abierto;
  const [texto, setTexto] = useState(abierto.tipo === "texto" ? (abierto.opciones.valor ?? "") : "");
  const campo = useRef<HTMLTextAreaElement & HTMLInputElement>(null);
  const aceptarBoton = useRef<HTMLButtonElement>(null);
  const requerido = abierto.tipo === "texto" && abierto.opciones.requerido;

  function responder(aceptado: boolean) {
    if (abierto.tipo === "confirmar") abierto.responder(aceptado);
    else abierto.responder(aceptado ? texto.trim() : null);
    cerrar();
  }

  useEffect(() => {
    (abierto.tipo === "texto" ? campo.current : aceptarBoton.current)?.focus();
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") responder(false);
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clasesCampo =
    "mt-1.5 block w-full rounded-xl border-0 bg-white px-3 py-2 text-sm text-slate-800 ring-1 ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-emerald-600";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-slate-900/50 p-4 backdrop-blur-sm sm:items-center"
      onMouseDown={(e) => e.target === e.currentTarget && responder(false)}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialogo-titulo"
        onSubmit={(e) => {
          e.preventDefault();
          if (requerido && !texto.trim()) return;
          responder(true);
        }}
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl ring-1 ring-slate-200"
      >
        <div className="flex gap-3">
          <span
            className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${
              opciones.peligro ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-700"
            }`}
          >
            <Icono nombre={opciones.peligro ? "alerta" : abierto.tipo === "texto" ? "novedad" : "bien"} className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="dialogo-titulo" className="text-base font-semibold text-slate-800">
              {opciones.titulo}
            </h2>
            {opciones.mensaje ? <div className="mt-1 text-sm text-slate-600">{opciones.mensaje}</div> : null}

            {abierto.tipo === "texto" ? (
              <label className="mt-4 block text-sm font-medium text-slate-700">
                {abierto.opciones.etiqueta ?? "Escribe aqui"}
                {abierto.opciones.largo ? (
                  <textarea
                    ref={campo}
                    rows={3}
                    value={texto}
                    placeholder={abierto.opciones.placeholder}
                    onChange={(e) => setTexto(e.target.value)}
                    className={clasesCampo}
                  />
                ) : (
                  <input
                    ref={campo}
                    value={texto}
                    placeholder={abierto.opciones.placeholder}
                    onChange={(e) => setTexto(e.target.value)}
                    className={clasesCampo}
                  />
                )}
              </label>
            ) : null}
          </div>
        </div>

        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => responder(false)}
            className="rounded-xl px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 transition hover:bg-slate-50"
          >
            {opciones.cancelar ?? "Cancelar"}
          </button>
          <button
            ref={aceptarBoton}
            type="submit"
            disabled={Boolean(requerido && !texto.trim())}
            className={`rounded-xl px-4 py-2 text-sm font-medium text-white shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
              opciones.peligro ? "bg-rose-600 hover:bg-rose-700" : "bg-emerald-700 hover:bg-emerald-800"
            }`}
          >
            {opciones.aceptar ?? "Aceptar"}
          </button>
        </div>
      </form>
    </div>
  );
}
