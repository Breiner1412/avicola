"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ResumenAlertas } from "@/lib/tipos";
import { Icono } from "./iconos";
import { rutaInterna } from "@/lib/menu";

const TONO: Record<string, string> = {
  critico: "bg-alerta-suave text-alerta",
  aviso: "bg-aten-suave text-aten",
  info: "bg-info-suave text-info",
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
        className="relative grid h-11 w-11 place-items-center rounded-lg text-tinta transition hover:bg-cal-honda"
        aria-label={`Avisos${sinLeer ? `: ${sinLeer} sin leer` : ""}`}
      >
        <Icono nombre="campana" className="h-6 w-6" />
        {sinLeer > 0 ? (
          <span
            className={`absolute top-0.5 right-0.5 grid h-5 min-w-5 place-items-center rounded-full px-1 font-cifra text-xs font-bold ring-2 ring-superficie ${
              criticas ? "bg-alerta text-white" : "bg-yema text-tinta"
            }`}
          >
            {sinLeer > 9 ? "9+" : sinLeer}
          </span>
        ) : null}
      </button>

      {abierta ? (
        <div className="fixed inset-x-3 top-16 z-50 mt-1 overflow-hidden rounded-xl border border-linea bg-superficie shadow-[0_16px_40px_-12px_rgb(22_58_44/0.35)] sm:absolute sm:inset-x-auto sm:top-auto sm:right-0 sm:mt-2 sm:w-96">
          <div className="flex items-center justify-between border-b border-linea-suave px-4 py-3">
            <p className="font-cifra text-lg font-bold text-tinta">Avisos</p>
            {sinLeer > 0 ? (
              <button onClick={marcarTodas} className="min-h-10 px-2 text-sm font-semibold text-galpon hover:underline">
                Marcar como vistos
              </button>
            ) : null}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {!datos || datos.alertas.length === 0 ? (
              <p className="px-4 py-8 text-center text-base text-tinta-2">Todo en orden por ahora.</p>
            ) : (
              <ul className="divide-y divide-linea-suave">
                {datos.alertas.slice(0, 12).map((alerta) => (
                  <li key={alerta.id}>
                    <Link
                      href={rutaInterna(alerta.ruta)}
                      onClick={() => setAbierta(false)}
                      className={`flex gap-3 px-4 py-3 transition hover:bg-cal ${alerta.leida ? "opacity-70" : ""}`}
                    >
                      <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${TONO[alerta.nivel]}`}>
                        <Icono nombre={alerta.nivel === "critico" ? "alerta" : "campana"} className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-base font-semibold text-tinta">{alerta.titulo}</span>
                        {alerta.detalle ? (
                          <span className="block text-sm text-tinta-2">{alerta.detalle}</span>
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
            className="flex min-h-12 items-center justify-center border-t border-linea-suave px-4 text-base font-semibold text-galpon hover:bg-cal"
          >
            Ver todos los avisos
          </Link>
        </div>
      ) : null}
    </div>
  );
}
