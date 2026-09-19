"use client";

import Link from "next/link";
import { useSesion } from "@/lib/sesion";
import { useDatos } from "@/lib/hooks";
import type { ResumenPanel } from "@/lib/tipos";
import { Barras } from "@/componentes/grafica";
import { Icono } from "@/componentes/iconos";
import { Aviso, Cargando, Dato, Insignia, Tarjeta } from "@/componentes/ui";

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;
const numero = (valor: number) => valor.toLocaleString("es-CO");

const ACCESOS = [
  { modulo: "produccion", texto: "Recoger huevos", ruta: "/produccion", icono: "huevo" },
  { modulo: "ventas", texto: "Abrir la caja", ruta: "/caja", icono: "caja" },
  { modulo: "movimientos_aves", texto: "Registrar aves", ruta: "/lotes", icono: "lote" },
  { modulo: "novedades", texto: "Reportar novedad", ruta: "/novedades", icono: "novedad" },
  { modulo: "movimientos_inventario", texto: "Entrada de bodega", ruta: "/movimientos", icono: "movimiento" },
  { modulo: "sensores", texto: "Ver sensores", ruta: "/sensores", icono: "sensor" },
];

function saludo() {
  const hora = new Date().getHours();
  if (hora < 12) return "Buenos dias";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

export default function Panel() {
  const { sesion, puede } = useSesion();
  const { datos, cargando, error } = useDatos<ResumenPanel>("/panel/resumen", sesion?.finca_activa?.id ?? 0);

  const fechaLarga = new Date().toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
  const hoy = fechaLarga.charAt(0).toUpperCase() + fechaLarga.slice(1);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            {saludo()}, {sesion?.usuario.nombres}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">{hoy}</p>
        </div>
        {sesion?.finca_activa?.solo_lectura ? <Insignia tono="azul">Estas viendo esta finca en solo consulta</Insignia> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {datos ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Dato
              titulo="Aves en la finca"
              valor={numero(datos.aves_en_finca)}
              detalle={`${Math.round(datos.ocupacion)}% de la capacidad · ${datos.lotes_activos} lote(s)`}
              icono="lote"
              tono="verde"
            />
            <Dato
              titulo="Huevos disponibles"
              valor={numero(datos.huevos_disponibles)}
              detalle={`${Math.round(datos.huevos_disponibles / 30)} panales listos para vender`}
              icono="huevo"
              tono="ambar"
            />
            <Dato
              titulo={`Vendido (${datos.dias} dias)`}
              valor={moneda(datos.ventas_periodo)}
              detalle={`Promedio ${numero(Math.round(datos.huevos_promedio))} huevos por dia`}
              icono="dinero"
              tono="azul"
            />
            <Dato
              titulo="Avisos"
              valor={datos.alertas}
              detalle={
                datos.alertas
                  ? "Revisa la campana de arriba"
                  : "Todo en orden por ahora"
              }
              icono="campana"
              tono={datos.alertas ? "rojo" : "gris"}
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
            <Tarjeta
              titulo="Huevos recolectados por dia"
              descripcion={`Ultimos ${datos.dias} dias · ${numero(datos.huevos_periodo)} en total`}
              icono="huevo"
            >
              <Barras datos={datos.produccion} etiqueta="huevos" />
            </Tarjeta>

            <Tarjeta
              titulo="Ventas por dia"
              descripcion={`Ultimos ${datos.dias} dias · ${moneda(datos.ventas_periodo)} en total`}
              icono="dinero"
            >
              <Barras datos={datos.ventas} formato={(valor) => moneda(valor)} />
            </Tarjeta>
          </div>

          <div className="grid gap-5 lg:grid-cols-3 [&>*]:min-w-0">
            <Tarjeta titulo="Para hoy" icono="tarea">
              <ul className="space-y-3 text-sm">
                <li className="flex items-center justify-between gap-3">
                  <span className="text-slate-600">Tareas de hoy</span>
                  <Insignia tono={datos.tareas_hoy ? "azul" : "verde"}>{datos.tareas_hoy}</Insignia>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span className="text-slate-600">Tareas atrasadas</span>
                  <Insignia tono={datos.tareas_atrasadas ? "rojo" : "verde"}>{datos.tareas_atrasadas}</Insignia>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span className="text-slate-600">Novedades sin cerrar</span>
                  <Insignia tono={datos.novedades_abiertas ? "ambar" : "verde"}>{datos.novedades_abiertas}</Insignia>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span className="text-slate-600">Gallinas de descarte</span>
                  <Insignia>{numero(datos.aves_descarte)}</Insignia>
                </li>
              </ul>
              <Link href="/tareas" className="mt-4 inline-flex items-center gap-1.5 text-sm text-emerald-700 hover:underline">
                Ver las tareas
                <Icono nombre="derecha" className="h-4 w-4" />
              </Link>
            </Tarjeta>

            <Tarjeta titulo="Sensores" icono="sensor">
              {datos.sensores === 0 ? (
                <div className="text-sm text-slate-500">
                  Todavia no hay sensores registrados en esta finca.
                  <Link href="/sensores" className="mt-2 block text-emerald-700 hover:underline">
                    Registrar el primero
                  </Link>
                </div>
              ) : (
                <>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-semibold text-slate-900">{datos.sensores}</span>
                    <span className="text-sm text-slate-500">midiendo la finca</span>
                  </div>
                  <p className="mt-2 text-sm">
                    {datos.sensores_alerta ? (
                      <span className="text-rose-700">
                        {datos.sensores_alerta} fuera del rango normal
                      </span>
                    ) : (
                      <span className="text-emerald-700">Todos dentro del rango normal</span>
                    )}
                  </p>
                  <Link href="/sensores" className="mt-4 inline-flex items-center gap-1.5 text-sm text-emerald-700 hover:underline">
                    Ver los sensores
                    <Icono nombre="derecha" className="h-4 w-4" />
                  </Link>
                </>
              )}
            </Tarjeta>

            <Tarjeta titulo="Accesos rapidos" icono="mas">
              <div className="grid grid-cols-2 gap-2">
                {ACCESOS.filter((acceso) => puede(acceso.modulo, "ver")).map((acceso) => (
                  <Link
                    key={acceso.ruta + acceso.texto}
                    href={acceso.ruta}
                    className="flex flex-col gap-1.5 rounded-xl px-3 py-3 text-sm text-slate-700 ring-1 ring-slate-200 transition hover:bg-emerald-50 hover:text-emerald-800 hover:ring-emerald-600"
                  >
                    <Icono nombre={acceso.icono} className="h-5 w-5 text-emerald-700" />
                    {acceso.texto}
                  </Link>
                ))}
              </div>
            </Tarjeta>
          </div>
        </>
      ) : null}
    </>
  );
}
