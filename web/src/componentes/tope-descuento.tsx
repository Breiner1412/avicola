"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { avisar } from "@/componentes/dialogos";
import { Boton, Tarjeta } from "@/componentes/ui";

export type AjustesVentas = { descuento_maximo: number; tengo_tope: boolean };

/** Tope de descuento que pueden dar el cajero, el operario y el supervisor. */
export function TopeDescuento({ editable }: { editable: boolean }) {
  const { datos, recargar } = useDatos<AjustesVentas>("/ventas/ajustes");
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (datos) setValor(String(datos.descuento_maximo));
  }, [datos]);

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    try {
      await api("/ventas/ajustes", { metodo: "PATCH", cuerpo: { descuento_maximo: Number(valor) } });
      await recargar();
      avisar.bien(`Tope de descuento: ${valor}%`);
    } catch (error) {
      avisar.error(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Tarjeta
      titulo="Descuentos"
      descripcion="Porcentaje maximo que pueden dar el cajero, el operario y el supervisor. El administrador y el propietario no tienen tope."
      icono="dinero"
    >
      {editable ? (
        <form onSubmit={guardar} className="flex flex-wrap items-end gap-3">
          <label className="block text-sm font-medium text-slate-700">
            Tope de descuento
            <span className="mt-1.5 flex w-32 items-center gap-1 rounded-xl bg-white px-3 ring-1 ring-slate-300 focus-within:ring-2 focus-within:ring-emerald-600">
              <input
                type="number"
                min={0}
                max={100}
                required
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                className="w-full border-0 bg-transparent py-2 text-right text-sm focus:ring-0"
              />
              <span className="text-sm text-slate-500">%</span>
            </span>
          </label>
          <Boton type="submit" disabled={guardando || valor === String(datos?.descuento_maximo ?? "")}>
            {guardando ? "Guardando..." : "Guardar"}
          </Boton>
        </form>
      ) : (
        <p className="text-sm text-slate-600">
          Tope actual: <span className="font-semibold">{datos?.descuento_maximo ?? "—"}%</span>
        </p>
      )}
    </Tarjeta>
  );
}
