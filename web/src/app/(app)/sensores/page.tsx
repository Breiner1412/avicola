"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Galpon, Sensor, TipoSensor } from "@/lib/tipos";
import { Linea } from "@/componentes/grafica";
import { Icono } from "@/componentes/iconos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tarjeta, Vacio } from "@/componentes/ui";
import { haceCuanto, unidad } from "@/lib/formato";
import Link from "next/link";

const ESTADO: Record<string, { texto: string; tono: "verde" | "rojo" | "ambar" | "gris"; icono: string }> = {
  ok: { texto: "Normal", tono: "verde", icono: "bien" },
  alto: { texto: "Muy alto", tono: "rojo", icono: "alerta" },
  bajo: { texto: "Muy bajo", tono: "ambar", icono: "alerta" },
  sin_datos: { texto: "Sin datos", tono: "gris", icono: "reloj" },
};

const VACIO = { codigo: "", nombre: "", tipo_id: "", galpon_id: "", ubicacion: "", min_ok: "", max_ok: "" };

function rango(minimo: number | null, maximo: number | null, unidad: string) {
  if (minimo !== null && maximo !== null) return `normal entre ${minimo} y ${maximo} ${unidad}`;
  if (maximo !== null) return `normal hasta ${maximo} ${unidad}`;
  if (minimo !== null) return `normal desde ${minimo} ${unidad}`;
  return "sin rango definido";
}


export default function Sensores() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);

  const { datos, cargando, error, recargar } = useDatos<Sensor[]>("/sensores", `${finca}-${recargas}`);
  const { datos: tipos } = useDatos<TipoSensor[]>("/tipos-sensor");
  const { datos: galpones } = useDatos<Galpon[]>("/galpones", finca);

  // Las mediciones llegan solas: se vuelve a consultar cada minuto
  useEffect(() => {
    const reloj = setInterval(() => setRecargas((n) => n + 1), 60_000);
    return () => clearInterval(reloj);
  }, []);

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);


  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/sensores", {
        metodo: "POST",
        cuerpo: {
          codigo: formulario.codigo,
          nombre: formulario.nombre,
          tipo_id: Number(formulario.tipo_id),
          galpon_id: formulario.galpon_id ? Number(formulario.galpon_id) : null,
          ubicacion: formulario.ubicacion || null,
          min_ok: formulario.min_ok === "" ? null : Number(formulario.min_ok),
          max_ok: formulario.max_ok === "" ? null : Number(formulario.max_ok),
        },
      });
      setAbierto(false);
      setFormulario(VACIO);
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Sensores</h1>
          <p className="text-sm text-slate-500">
            Lo que miden los equipos en los galpones. Se actualiza solo.
          </p>
        </div>
        {puede("sensores", "crear") ? (
          <Boton icono="mas" onClick={() => setAbierto(true)}>
            Nuevo sensor
          </Boton>
        ) : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando && !datos ? <Cargando /> : null}

      {!cargando && (!datos || datos.length === 0) ? (
        <Tarjeta>
          <Vacio icono="sensor">
            Todavia no hay sensores en esta finca. Registra cada equipo con su codigo: sus mediciones llegan solas y el
            sistema avisa cuando algo se sale del rango normal.
          </Vacio>
        </Tarjeta>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {(datos ?? []).map((sensor) => {
          const estado = ESTADO[sensor.estado];
          return (
            <div key={sensor.id} className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200/80">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-800">{sensor.nombre}</p>
                  <p className="truncate text-xs text-slate-500">
                    {sensor.tipo}
                    {sensor.galpon_nombre ? ` · ${sensor.galpon_nombre}` : ""}
                  </p>
                </div>
                <Insignia tono={estado.tono} punto>
                  {estado.texto}
                </Insignia>
              </div>

              <div className="mt-3 flex items-end justify-between gap-3">
                <p className="text-3xl font-semibold tracking-tight text-slate-900">
                  {sensor.ultimo_valor !== null ? sensor.ultimo_valor : "—"}
                  <span className="ml-1 text-base font-normal text-slate-500">{unidad(sensor.unidad)}</span>
                </p>
                <span
                  className={`${
                    sensor.estado === "ok" ? "text-emerald-600" : sensor.estado === "sin_datos" ? "text-slate-300" : "text-rose-600"
                  } w-24`}
                >
                  <Linea valores={sensor.historial} />
                </span>
              </div>

              <p className="mt-1 text-xs text-slate-500">
                {haceCuanto(sensor.ultima_medicion)} · {rango(sensor.min_ok, sensor.max_ok, unidad(sensor.unidad))}
              </p>

              <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
                <span className="text-xs text-slate-400">{sensor.codigo}</span>
                <Link
                  href={`/sensores/${sensor.id}`}
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
                >
                  Ver historial
                  <Icono nombre="derecha" className="h-4 w-4" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <Modal titulo="Nuevo sensor" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Codigo"
              required
              placeholder="S1"
              value={formulario.codigo}
              onChange={(e) => setFormulario({ ...formulario, codigo: e.target.value })}
            />
            <Campo
              etiqueta="Nombre"
              required
              placeholder="Temperatura galpon 1"
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
            />
            <Lista
              etiqueta="Que mide"
              required
              value={formulario.tipo_id}
              onChange={(e) => {
                const tipo = tipos?.find((t) => String(t.id) === e.target.value);
                setFormulario({
                  ...formulario,
                  tipo_id: e.target.value,
                  min_ok: tipo?.min_ok !== null && tipo?.min_ok !== undefined ? String(tipo.min_ok) : "",
                  max_ok: tipo?.max_ok !== null && tipo?.max_ok !== undefined ? String(tipo.max_ok) : "",
                });
              }}
            >
              <option value="">Elige el tipo</option>
              {(tipos ?? []).map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nombre} ({unidad(tipo.unidad)})
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Galpon"
              value={formulario.galpon_id}
              onChange={(e) => setFormulario({ ...formulario, galpon_id: e.target.value })}
            >
              <option value="">Toda la finca</option>
              {(galpones ?? []).map((galpon) => (
                <option key={galpon.id} value={galpon.id}>
                  {galpon.nombre}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Minimo normal"
              type="number"
              step="0.1"
              value={formulario.min_ok}
              onChange={(e) => setFormulario({ ...formulario, min_ok: e.target.value })}
            />
            <Campo
              etiqueta="Maximo normal"
              type="number"
              step="0.1"
              value={formulario.max_ok}
              onChange={(e) => setFormulario({ ...formulario, max_ok: e.target.value })}
            />
          </div>

          <Campo
            etiqueta="Donde esta"
            placeholder="Pared norte, a la altura de las aves"
            value={formulario.ubicacion}
            onChange={(e) => setFormulario({ ...formulario, ubicacion: e.target.value })}
          />

          <Aviso tipo="info">
            Cuando una medicion se salga de ese rango, el sensor se marca en rojo y sale un aviso en la campana.
          </Aviso>

          {fallo ? <Aviso>{fallo}</Aviso> : null}

          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setAbierto(false)}>
              Cancelar
            </Boton>
            <Boton type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Boton>
          </div>
        </form>
      </Modal>

    </>
  );
}
