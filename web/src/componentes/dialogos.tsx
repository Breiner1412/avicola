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
        toastOptions={{ className: "!rounded-lg !font-sans !text-base", duration: 4000 }}
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
    "mt-1.5 block min-h-12 w-full rounded-lg border-[1.5px] border-linea bg-superficie px-3 py-2 text-base font-normal text-tinta placeholder:text-tinta-3 focus:border-galpon focus:ring-3 focus:ring-galpon/15 focus:outline-none";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-galpon-honda/55 p-3 sm:items-center sm:p-4"
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
        className="w-full max-w-md rounded-xl bg-superficie p-5 shadow-[0_20px_50px_-12px_rgb(22_58_44/0.45)]"
      >
        <div className="flex gap-3">
          <span
            className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${
              opciones.peligro ? "bg-alerta-suave text-alerta" : "bg-galpon-suave text-galpon"
            }`}
          >
            <Icono nombre={opciones.peligro ? "alerta" : abierto.tipo === "texto" ? "novedad" : "bien"} className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="dialogo-titulo" className="font-cifra text-xl font-bold text-tinta [font-stretch:108%]">
              {opciones.titulo}
            </h2>
            {opciones.mensaje ? <div className="mt-1 text-base text-tinta-2">{opciones.mensaje}</div> : null}

            {abierto.tipo === "texto" ? (
              <label className="mt-4 block text-sm font-semibold text-tinta">
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
            className="min-h-11 rounded-lg px-4 text-base font-semibold text-tinta ring-[1.5px] ring-inset ring-linea transition hover:bg-cal"
          >
            {opciones.cancelar ?? "Cancelar"}
          </button>
          <button
            ref={aceptarBoton}
            type="submit"
            disabled={Boolean(requerido && !texto.trim())}
            className={`min-h-11 rounded-lg px-4 text-base font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
              opciones.peligro
                ? "bg-alerta text-white hover:bg-alerta/90"
                : "bg-yema text-tinta shadow-[inset_0_-2px_0_var(--color-yema-honda)] hover:bg-yema-clara"
            }`}
          >
            {opciones.aceptar ?? "Aceptar"}
          </button>
        </div>
      </form>
    </div>
  );
}
