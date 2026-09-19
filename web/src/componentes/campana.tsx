"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ResumenAlertas } from "@/lib/tipos";
import { Icono } from "./iconos";

const TONO: Record<string, string> = {
  critico: "bg-rose-100 text-rose-700",
  aviso: "bg-amber-100 text-amber-700",
  info: "bg-sky-100 text-sky-700",
};

export function Campana({ fincaId }: { fincaId: number | null }) {
  const [abierta, setAbierta] = useState(false);
  const [datos, setDatos] = useState<ResumenAlertas | null>(null);
  const caja = useRef<HTMLDivElement>(null);

  async function cargar() {
    try {
      setDatos(await api<ResumenAlertas>("/alertas"));
    } catch {
      // si falla, la campana simplemente no muestra nada
    }
  }

  useEffect(() => {
    void cargar();
    const reloj = setInterval(() => void cargar(), 120000);
    return () => clearInterval(reloj);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fincaId]);

  useEffect(() => {
    function fuera(evento: MouseEvent) {
      if (caja.current && !caja.current.contains(evento.target as Node)) setAbierta(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  const sinLeer = datos?.sin_leer ?? 0;
  const criticas = datos?.criticas ?? 0;

  async function marcarTodas() {
    try {
      await api("/alertas/leidas", { metodo: "POST" });
      await cargar();
    } catch {
      // nada
    }
  }

  return (
    <div className="relative" ref={caja}>
      <button
        onClick={() => setAbierta((v) => !v)}
        className="relative rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
        aria-label={`Avisos${sinLeer ? `: ${sinLeer} sin leer` : ""}`}
      >
        <Icono nombre="campana" className="h-5 w-5" />
        {sinLeer > 0 ? (
          <span
            className={`absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[10px] font-semibold text-white ${
              criticas ? "bg-rose-600" : "bg-amber-500"
            }`}
          >
            {sinLeer > 9 ? "9+" : sinLeer}
          </span>
        ) : null}
      </button>

      {abierta ? (
        <div className="absolute right-0 z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-semibold text-slate-800">Avisos</p>
            {sinLeer > 0 ? (
              <button onClick={marcarTodas} className="text-xs text-emerald-700 hover:underline">
                Marcar como vistos
              </button>
            ) : null}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {!datos || datos.alertas.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-slate-500">Todo en orden por ahora.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {datos.alertas.slice(0, 12).map((alerta) => (
                  <li key={alerta.id}>
                    <Link
                      href={alerta.ruta ?? "/panel"}
                      onClick={() => setAbierta(false)}
                      className={`flex gap-3 px-4 py-3 transition hover:bg-slate-50 ${alerta.leida ? "opacity-70" : ""}`}
                    >
                      <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${TONO[alerta.nivel]}`}>
                        <Icono nombre={alerta.nivel === "critico" ? "alerta" : "campana"} className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-slate-800">{alerta.titulo}</span>
                        {alerta.detalle ? (
                          <span className="block text-xs text-slate-500">{alerta.detalle}</span>
                        ) : null}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Link
            href="/alertas"
            onClick={() => setAbierta(false)}
            className="block border-t border-slate-100 px-4 py-2.5 text-center text-xs font-medium text-emerald-700 hover:bg-slate-50"
          >
            Ver todos los avisos
          </Link>
        </div>
      ) : null}
    </div>
  );
}
