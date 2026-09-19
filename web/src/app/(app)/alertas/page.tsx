"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import type { ResumenAlertas } from "@/lib/tipos";
import { Icono } from "@/componentes/iconos";
import { Aviso, Boton, Cargando, Dato, Insignia, Lista, Paginador, Tarjeta, Vacio, usePaginas } from "@/componentes/ui";
import { avisar } from "@/componentes/dialogos";

const NIVEL: Record<string, { texto: string; tono: "rojo" | "ambar" | "azul" }> = {
  critico: { texto: "Urgente", tono: "rojo" },
  aviso: { texto: "Para revisar", tono: "ambar" },
  info: { texto: "Informacion", tono: "azul" },
};

const TIPO: Record<string, string> = {
  stock: "articulo",
  sensor: "sensor",
  sanidad: "vacuna",
  tarea: "tarea",
  novedad: "novedad",
  caja: "caja",
  lote: "lote",
};

export default function Alertas() {
  const [recargas, setRecargas] = useState(0);
  const [nivel, setNivel] = useState("");
  const { datos, cargando, error, recargar } = useDatos<ResumenAlertas>("/alertas", recargas);

  async function marcarTodas() {
    try {
      await api("/alertas/leidas", { metodo: "POST" });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  const lista = (datos?.alertas ?? []).filter((alerta) => !nivel || alerta.nivel === nivel);
  const pagAvisos = usePaginas(lista, 15, nivel);

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Avisos</h1>
          <p className="text-sm text-slate-500">
            Lo que el sistema encontro revisando el inventario, los sensores, las vacunas y el trabajo
          </p>
        </div>
        {datos && datos.sin_leer > 0 ? (
          <Boton tono="suave" onClick={marcarTodas}>
            Marcar todos como vistos
          </Boton>
        ) : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {datos ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Dato titulo="Avisos activos" valor={datos.total} icono="campana" tono={datos.total ? "ambar" : "gris"} />
            <Dato titulo="Urgentes" valor={datos.criticas} icono="alerta" tono={datos.criticas ? "rojo" : "gris"} />
            <Dato titulo="Sin ver" valor={datos.sin_leer} icono="reloj" tono={datos.sin_leer ? "azul" : "gris"} />
          </div>

          <Tarjeta
            titulo="Lista de avisos"
            acciones={
              <div className="w-44">
                <Lista etiqueta="" value={nivel} onChange={(e) => setNivel(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="critico">Urgentes</option>
                  <option value="aviso">Para revisar</option>
                  <option value="info">Informacion</option>
                </Lista>
              </div>
            }
          >
            {lista.length === 0 ? (
              <Vacio icono="bien">Nada pendiente por ahora.</Vacio>
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {pagAvisos.visibles.map((alerta) => (
                    <li key={alerta.id}>
                      <Link
                        href={alerta.ruta ?? "/panel"}
                        className="flex items-start gap-3 py-3 transition hover:bg-slate-50"
                      >
                        <span
                          className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${
                            alerta.nivel === "critico"
                              ? "bg-rose-50 text-rose-700"
                              : alerta.nivel === "aviso"
                                ? "bg-amber-50 text-amber-700"
                                : "bg-sky-50 text-sky-700"
                          }`}
                        >
                          <Icono nombre={TIPO[alerta.tipo] ?? "alerta"} className="h-5 w-5" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-slate-800">{alerta.titulo}</span>
                            <Insignia tono={NIVEL[alerta.nivel].tono}>{NIVEL[alerta.nivel].texto}</Insignia>
                            {!alerta.leida ? <Insignia tono="verde">Nuevo</Insignia> : null}
                          </span>
                          {alerta.detalle ? (
                            <span className="mt-0.5 block text-sm text-slate-500">{alerta.detalle}</span>
                          ) : null}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <Paginador {...pagAvisos} nombre="avisos" />
              </>
            )}
          </Tarjeta>
        </>
      ) : null}
    </>
  );
}
