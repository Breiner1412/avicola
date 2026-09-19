"use client";

import { useEffect, useRef, useState } from "react";

export type Punto = { fecha: string; valor: number };

function dia(fecha: string) {
  const [, mes, numero] = fecha.split("-");
  return `${numero}/${mes}`;
}

/** Barras por dia, una sola serie. Al pasar el mouse muestra el valor. */
export function Barras({
  datos,
  formato = (valor: number) => valor.toLocaleString("es-CO"),
  etiqueta = "",
  alto = "h-36",
}: {
  datos: Punto[];
  formato?: (valor: number) => string;
  etiqueta?: string;
  alto?: string;
}) {
  const [encima, setEncima] = useState<number | null>(null);
  const maximo = Math.max(1, ...datos.map((d) => d.valor));
  const hayDatos = datos.some((d) => d.valor > 0);

  if (!hayDatos) {
    return (
      <div className={`flex ${alto} items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400`}>
        Sin datos en este periodo
      </div>
    );
  }

  return (
    <div>
      <div className={`relative flex ${alto} items-end gap-[3px]`}>
        {datos.map((punto, indice) => {
          const altura = Math.max(punto.valor > 0 ? 4 : 2, Math.round((punto.valor / maximo) * 100));
          const activo = encima === indice;
          return (
            <div
              key={punto.fecha}
              className="group relative flex h-full flex-1 items-end"
              onMouseEnter={() => setEncima(indice)}
              onMouseLeave={() => setEncima(null)}
            >
              <div
                className={`w-full rounded-t transition-colors ${
                  punto.valor === 0 ? "bg-slate-200" : activo ? "bg-emerald-700" : "bg-emerald-600"
                }`}
                style={{ height: `${altura}%` }}
                role="img"
                aria-label={`${dia(punto.fecha)}: ${formato(punto.valor)} ${etiqueta}`}
                title={`${dia(punto.fecha)}: ${formato(punto.valor)} ${etiqueta}`}
              />
              {activo ? (
                <div className="pointer-events-none absolute -top-1 left-1/2 z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-lg bg-slate-900 px-2 py-1 text-xs text-white shadow-lg">
                  <span className="font-medium">{formato(punto.valor)}</span>
                  <span className="ml-1 text-slate-300">{dia(punto.fecha)}</span>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-slate-400">
        <span>{dia(datos[0].fecha)}</span>
        <span>{dia(datos[datos.length - 1].fecha)}</span>
      </div>
    </div>
  );
}

/** Linea pequena para meter dentro de una tarjeta. */
export function Linea({ valores, className = "h-10 w-full" }: { valores: number[]; className?: string }) {
  if (valores.length < 2) return null;

  const maximo = Math.max(...valores);
  const minimo = Math.min(...valores);
  const rango = maximo - minimo || 1;
  const puntos = valores
    .map((valor, indice) => {
      const x = (indice / (valores.length - 1)) * 100;
      const y = 30 - ((valor - minimo) / rango) * 26 - 2;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 100 32" preserveAspectRatio="none" className={className} aria-hidden="true">
      <polyline
        points={puntos}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export type Medida = { momento: number; valor: number };

/**
 * Linea en el tiempo con la franja del rango normal. Una sola serie, sin leyenda
 * (el titulo de la tarjeta la nombra). Al pasar el mouse muestra el valor y la hora.
 */
export function LineaTiempo({
  datos,
  minimo,
  maximo,
  unidad = "",
  alto = 240,
}: {
  datos: Medida[];
  minimo?: number | null;
  maximo?: number | null;
  unidad?: string;
  alto?: number;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const [ancho, setAncho] = useState(640);
  const [encima, setEncima] = useState<number | null>(null);

  useEffect(() => {
    if (!caja.current) return;
    const observador = new ResizeObserver(([entrada]) => setAncho(Math.max(280, entrada.contentRect.width)));
    observador.observe(caja.current);
    return () => observador.disconnect();
  }, []);

  if (datos.length < 2) {
    return (
      <div ref={caja} className="flex items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400" style={{ height: alto }}>
        No hay suficientes mediciones en este periodo
      </div>
    );
  }

  const orden = [...datos].sort((a, b) => a.momento - b.momento);
  const margen = { arriba: 12, derecha: 12, abajo: 26, izquierda: 44 };
  const w = ancho - margen.izquierda - margen.derecha;
  const h = alto - margen.arriba - margen.abajo;

  const valores = orden.map((d) => d.valor);
  let bajo = Math.min(...valores, ...(minimo != null ? [minimo] : []));
  let alto_ = Math.max(...valores, ...(maximo != null ? [maximo] : []));
  const holgura = (alto_ - bajo || 1) * 0.08;
  bajo -= holgura;
  alto_ += holgura;
  const t0 = orden[0].momento;
  const t1 = orden[orden.length - 1].momento;

  const x = (t: number) => margen.izquierda + ((t - t0) / (t1 - t0 || 1)) * w;
  const y = (v: number) => margen.arriba + (1 - (v - bajo) / (alto_ - bajo)) * h;

  const trazo = orden.map((d, i) => `${i ? "L" : "M"}${x(d.momento).toFixed(1)},${y(d.valor).toFixed(1)}`).join(" ");

  // Marcas del eje Y: 4 valores redondos
  const paso = pasoBonito((alto_ - bajo) / 4);
  const marcasY: number[] = [];
  for (let v = Math.ceil(bajo / paso) * paso; v <= alto_; v += paso) marcasY.push(Number(v.toFixed(6)));

  // Marcas del eje X: hasta 6 fechas u horas
  const duracion = t1 - t0;
  const variosDias = duracion > 36 * 3600 * 1000;
  const cuantas = ancho < 480 ? 3 : ancho < 800 ? 4 : 6;
  const marcasX = Array.from({ length: cuantas }, (_, i) => t0 + (duracion * i) / (cuantas - 1));
  const etiquetaX = (t: number) =>
    new Date(t).toLocaleString("es-CO", variosDias ? { day: "numeric", month: "short" } : { hour: "numeric", minute: "2-digit" });

  const franjaArriba = maximo != null ? y(Math.min(maximo, alto_)) : margen.arriba;
  const franjaAbajo = minimo != null ? y(Math.max(minimo, bajo)) : margen.arriba + h;

  function mover(evento: React.MouseEvent<SVGRectElement>) {
    const caja_ = evento.currentTarget.getBoundingClientRect();
    const t = t0 + ((evento.clientX - caja_.left) / caja_.width) * (t1 - t0);
    let cerca = 0;
    for (let i = 1; i < orden.length; i++) if (Math.abs(orden[i].momento - t) < Math.abs(orden[cerca].momento - t)) cerca = i;
    setEncima(cerca);
  }

  const punto = encima !== null ? orden[encima] : null;
  const fuera = (v: number) => (maximo != null && v > maximo) || (minimo != null && v < minimo);

  return (
    <div ref={caja} className="relative">
      <svg width={ancho} height={alto} className="block max-w-full" role="img" aria-label="Grafica de mediciones">
        {minimo != null || maximo != null ? (
          <rect
            x={margen.izquierda}
            y={franjaArriba}
            width={w}
            height={Math.max(0, franjaAbajo - franjaArriba)}
            className="fill-emerald-50"
          />
        ) : null}
        {marcasY.map((v) => (
          <g key={v}>
            <line x1={margen.izquierda} x2={margen.izquierda + w} y1={y(v)} y2={y(v)} className="stroke-slate-100" />
            <text x={margen.izquierda - 8} y={y(v)} dy="0.32em" textAnchor="end" className="fill-slate-400 text-[11px]">
              {v.toLocaleString("es-CO")}
            </text>
          </g>
        ))}
        {marcasX.map((t, i) => (
          <text
            key={t}
            x={x(t)}
            y={alto - 6}
            textAnchor={i === 0 ? "start" : i === cuantas - 1 ? "end" : "middle"}
            className="fill-slate-400 text-[11px]"
          >
            {etiquetaX(t)}
          </text>
        ))}
        {maximo != null ? (
          <line x1={margen.izquierda} x2={margen.izquierda + w} y1={y(maximo)} y2={y(maximo)} className="stroke-emerald-300" strokeDasharray="4 4" />
        ) : null}
        {minimo != null ? (
          <line x1={margen.izquierda} x2={margen.izquierda + w} y1={y(minimo)} y2={y(minimo)} className="stroke-emerald-300" strokeDasharray="4 4" />
        ) : null}
        <path d={trazo} fill="none" className="stroke-emerald-700" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {orden.map((d) =>
          fuera(d.valor) ? <circle key={d.momento} cx={x(d.momento)} cy={y(d.valor)} r={2.5} className="fill-rose-600" /> : null,
        )}
        {punto ? (
          <g>
            <line x1={x(punto.momento)} x2={x(punto.momento)} y1={margen.arriba} y2={margen.arriba + h} className="stroke-slate-300" />
            <circle cx={x(punto.momento)} cy={y(punto.valor)} r={4.5} className="fill-white stroke-emerald-700" strokeWidth={2} />
          </g>
        ) : null}
        <rect
          x={margen.izquierda}
          y={margen.arriba}
          width={w}
          height={h}
          fill="transparent"
          onMouseMove={mover}
          onMouseLeave={() => setEncima(null)}
        />
      </svg>
      {punto ? (
        <div
          className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs text-white shadow-lg"
          style={{ left: Math.min(Math.max(x(punto.momento), 70), ancho - 70) }}
        >
          <span className="font-semibold">
            {punto.valor.toLocaleString("es-CO")} {unidad}
          </span>
          <span className="ml-1.5 text-slate-300">
            {new Date(punto.momento).toLocaleString("es-CO", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}
          </span>
        </div>
      ) : null}
    </div>
  );
}

function pasoBonito(bruto: number) {
  const potencia = Math.pow(10, Math.floor(Math.log10(bruto || 1)));
  const n = bruto / potencia;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * potencia;
}
