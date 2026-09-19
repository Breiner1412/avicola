"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { LecturaSensor, Sensor } from "@/lib/tipos";
import { LineaTiempo } from "@/componentes/grafica";
import { Icono } from "@/componentes/iconos";
import { Aviso, Cargando, Chips, Dato, Insignia, Paginador, Tabla, Tarjeta, Vacio, usePaginas } from "@/componentes/ui";
import { aFecha, fechaHora, haceCuanto, hoy, unidad } from "@/lib/formato";

type Periodo = "24h" | "hoy" | "7d" | "30d" | "dia";

const PERIODOS: { clave: Periodo; texto: string }[] = [
  { clave: "24h", texto: "Ultimas 24 h" },
  { clave: "hoy", texto: "Hoy" },
  { clave: "7d", texto: "7 dias" },
  { clave: "30d", texto: "30 dias" },
  { clave: "dia", texto: "Un dia" },
];

const ESTADO: Record<string, { texto: string; tono: "verde" | "rojo" | "ambar" | "gris" }> = {
  ok: { texto: "Normal", tono: "verde" },
  alto: { texto: "Muy alto", tono: "rojo" },
  bajo: { texto: "Muy bajo", tono: "ambar" },
  sin_datos: { texto: "Sin datos", tono: "gris" },
};

/** Inicio y fin del periodo en UTC, calculados con la hora del dispositivo. */
function limites(periodo: Periodo, dia: string): { desde: string; hasta: string; texto: string } {
  const ahora = new Date();
  const medianoche = (fecha: Date) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  let desde: Date;
  let hasta = new Date(ahora.getTime() + 60_000);
  let texto: string;
  switch (periodo) {
    case "hoy":
      desde = medianoche(ahora);
      texto = "hoy";
      break;
    case "7d":
      desde = new Date(ahora.getTime() - 7 * 86_400_000);
      texto = "los ultimos 7 dias";
      break;
    case "30d":
      desde = new Date(ahora.getTime() - 30 * 86_400_000);
      texto = "los ultimos 30 dias";
      break;
    case "dia": {
      desde = aFecha(dia);
      hasta = new Date(desde.getTime() + 86_400_000);
      texto = desde.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
      break;
    }
    default:
      desde = new Date(ahora.getTime() - 86_400_000);
      texto = "las ultimas 24 horas";
  }
  return { desde: desde.toISOString(), hasta: hasta.toISOString(), texto };
}

export default function DetalleSensor() {
  const { id } = useParams<{ id: string }>();
  const { sesion } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;

  const [periodo, setPeriodo] = useState<Periodo>("24h");
  const [dia, setDia] = useState(hoy());
  const [soloFuera, setSoloFuera] = useState(false);

  const { datos: sensores, cargando: cargandoSensor } = useDatos<Sensor[]>("/sensores", finca);
  const sensor = sensores?.find((s) => String(s.id) === id) ?? null;

  const rango = useMemo(() => limites(periodo, dia), [periodo, dia]);
  const ruta = `/sensores/${id}/lecturas?desde=${encodeURIComponent(rango.desde)}&hasta=${encodeURIComponent(rango.hasta)}`;
  const { datos: lecturas, cargando, error } = useDatos<LecturaSensor[]>(ruta, ruta);

  const resumen = useMemo(() => {
    if (!lecturas || lecturas.length === 0) return null;
    const valores = lecturas.map((l) => l.valor);
    const suma = valores.reduce((a, b) => a + b, 0);
    const fuera = lecturas.filter((l) => l.fuera_rango).length;
    return {
      minimo: Math.min(...valores),
      maximo: Math.max(...valores),
      promedio: suma / valores.length,
      fuera,
      porcentaje: Math.round((fuera * 100) / lecturas.length),
    };
  }, [lecturas]);

  const filas = useMemo(() => (soloFuera ? (lecturas ?? []).filter((l) => l.fuera_rango) : lecturas ?? []), [lecturas, soloFuera]);
  const paginas = usePaginas(filas, 15, `${ruta}-${soloFuera}`);
  const puntos = useMemo(
    () => (lecturas ?? []).map((l) => ({ momento: aFecha(l.medido_en).getTime(), valor: l.valor })),
    [lecturas],
  );

  if (cargandoSensor && !sensor) return <Cargando />;
  if (!sensor) {
    return (
      <Tarjeta>
        <Vacio icono="sensor">Ese sensor no existe en esta finca.</Vacio>
      </Tarjeta>
    );
  }

  const u = unidad(sensor.unidad);
  const redondo = (valor: number) => Number(valor.toFixed(1)).toLocaleString("es-CO");
  const estado = ESTADO[sensor.estado];

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href="/sensores" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-emerald-700">
            <Icono nombre="izquierda" className="h-4 w-4" />
            Sensores
          </Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-2 text-xl font-semibold text-slate-800">
            {sensor.nombre}
            <Insignia tono={estado.tono} punto>
              {estado.texto}
            </Insignia>
          </h1>
          <p className="text-sm text-slate-500">
            {sensor.tipo}
            {sensor.galpon_nombre ? ` · ${sensor.galpon_nombre}` : ""}
            {sensor.ubicacion ? ` · ${sensor.ubicacion}` : ""} · codigo {sensor.codigo}
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-semibold tracking-tight text-slate-900">
            {sensor.ultimo_valor !== null ? redondo(sensor.ultimo_valor) : "—"}
            <span className="ml-1 text-base font-normal text-slate-500">{u}</span>
          </p>
          <p className="text-xs text-slate-500">ultima medicion {haceCuanto(sensor.ultima_medicion)}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Chips opciones={PERIODOS} valor={periodo} onCambiar={setPeriodo} />
        {periodo === "dia" ? (
          <input
            type="date"
            value={dia}
            max={hoy()}
            onChange={(e) => e.target.value && setDia(e.target.value)}
            className="rounded-xl border-0 bg-white px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-300 focus:ring-2 focus:ring-emerald-600"
            aria-label="Dia a consultar"
          />
        ) : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <Dato titulo="Minimo" valor={resumen ? `${redondo(resumen.minimo)} ${u}` : "—"} icono="abajo" tono="azul" />
        <Dato titulo="Maximo" valor={resumen ? `${redondo(resumen.maximo)} ${u}` : "—"} icono="alerta" tono="ambar" />
        <Dato
          titulo="Promedio"
          valor={resumen ? `${redondo(resumen.promedio)} ${u}` : "—"}
          detalle={resumen ? `${lecturas?.length.toLocaleString("es-CO")} mediciones` : undefined}
          icono="reporte"
        />
        <Dato
          titulo="Fuera de rango"
          valor={resumen ? `${resumen.porcentaje}%` : "—"}
          detalle={resumen ? `${resumen.fuera.toLocaleString("es-CO")} mediciones` : undefined}
          icono="alerta"
          tono={resumen && resumen.fuera > 0 ? "rojo" : "verde"}
        />
      </div>

      <Tarjeta
        titulo={`Mediciones de ${rango.texto}`}
        descripcion={
          sensor.min_ok !== null || sensor.max_ok !== null
            ? `La franja verde es el rango normal${sensor.min_ok !== null ? ` desde ${sensor.min_ok}` : ""}${
                sensor.max_ok !== null ? ` hasta ${sensor.max_ok}` : ""
              } ${u}. Los puntos rojos se salieron.`
            : "Este sensor no tiene rango normal definido."
        }
        icono="sensor"
      >
        {cargando ? <Cargando /> : <LineaTiempo datos={puntos} minimo={sensor.min_ok} maximo={sensor.max_ok} unidad={u} />}
      </Tarjeta>

      <Tarjeta
        titulo="Registro"
        descripcion="De la mas reciente a la mas antigua"
        icono="reloj"
        acciones={
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={soloFuera}
              onChange={(e) => setSoloFuera(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-600"
            />
            Solo fuera de rango
          </label>
        }
      >
        {cargando ? (
          <Cargando />
        ) : filas.length === 0 ? (
          <Vacio icono="reloj">{soloFuera ? "Ninguna medicion se salio del rango en este periodo." : "No hay mediciones en este periodo."}</Vacio>
        ) : (
          <>
            <Tabla columnas={["Fecha y hora", "Valor", "Estado", "Origen"]}>
              {paginas.visibles.map((lectura) => (
                <tr key={lectura.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{fechaHora(lectura.medido_en)}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-800">
                    {lectura.valor.toLocaleString("es-CO")} {u}
                  </td>
                  <td className="px-3 py-2">
                    {lectura.fuera_rango ? (
                      <Insignia tono="rojo" punto>
                        Fuera de rango
                      </Insignia>
                    ) : (
                      <Insignia tono="verde" punto>
                        Normal
                      </Insignia>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {lectura.origen === "dispositivo" ? "Equipo" : (lectura.usuario_nombre ?? "Manual")}
                  </td>
                </tr>
              ))}
            </Tabla>
            <Paginador {...paginas} nombre="mediciones" />
          </>
        )}
      </Tarjeta>
    </>
  );
}
