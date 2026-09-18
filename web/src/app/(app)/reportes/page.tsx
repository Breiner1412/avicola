"use client";

import { useState } from "react";
import { useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { ResumenReporte } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;
const numero = (valor: number) => valor.toLocaleString("es-CO");

const DESCARGAS = [
  { tipo: "produccion", texto: "Produccion de huevos" },
  { tipo: "ventas", texto: "Ventas" },
  { tipo: "aves", texto: "Movimientos de aves" },
  { tipo: "alimento", texto: "Alimento entregado" },
  { tipo: "existencias", texto: "Existencias de bodega" },
  { tipo: "novedades", texto: "Novedades" },
  { tipo: "tareas", texto: "Tareas" },
];

const NOMBRE_CLASE: Record<string, string> = {
  huevo: "Huevos",
  ave_descarte: "Gallinas de descarte",
  ave_engorde: "Aves de engorde",
  otro: "Otros",
};

function haceDias(dias: number) {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - dias);
  return fecha.toISOString().slice(0, 10);
}

function Dato({ titulo, valor, detalle }: { titulo: string; valor: string | number; detalle?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className="mt-1 text-xl font-semibold text-slate-800">{valor}</p>
      {detalle ? <p className="mt-0.5 text-xs text-slate-500">{detalle}</p> : null}
    </div>
  );
}

export default function Reportes() {
  const { sesion } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [desde, setDesde] = useState(haceDias(29));
  const [hasta, setHasta] = useState(haceDias(0));
  const [bajando, setBajando] = useState("");

  const ruta = `/reportes/resumen?desde=${desde}&hasta=${hasta}`;
  const { datos, cargando, error } = useDatos<ResumenReporte>(ruta, `${finca}-${ruta}`);

  async function descargar(tipo: string) {
    setBajando(tipo);
    try {
      const respuesta = await fetch(`/api/v1/reportes/csv?tipo=${tipo}&desde=${desde}&hasta=${hasta}`, {
        headers: {
          Authorization: `Bearer ${sesion?.token ?? ""}`,
          ...(finca ? { "X-Finca-Id": String(finca) } : {}),
        },
        credentials: "include",
      });
      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const contenido = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(contenido);
      enlace.download = `${tipo}_${desde}_a_${hasta}.csv`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch {
      alert("No se pudo descargar el reporte");
    } finally {
      setBajando("");
    }
  }

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Reportes</h1>
        <p className="text-sm text-slate-500">Como va la finca en el periodo que elijas</p>
      </div>

      <Tarjeta>
        <div className="flex flex-wrap items-end gap-3">
          <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          <div className="flex flex-wrap gap-2 pb-1">
            <Boton tono="suave" onClick={() => { setDesde(haceDias(6)); setHasta(haceDias(0)); }}>
              Ultima semana
            </Boton>
            <Boton tono="suave" onClick={() => { setDesde(haceDias(29)); setHasta(haceDias(0)); }}>
              Ultimo mes
            </Boton>
          </div>
        </div>
      </Tarjeta>

      {error ? <Aviso>{error}</Aviso> : null}
      {cargando ? <Cargando /> : null}

      {datos ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Dato
              titulo="Huevos recolectados"
              valor={numero(datos.produccion.huevos)}
              detalle={`${datos.produccion.promedio_diario} por dia`}
            />
            <Dato
              titulo="Vendido"
              valor={moneda(datos.ventas.total)}
              detalle={`${datos.ventas.cantidad} venta(s) · ${datos.ventas.anuladas} anulada(s)`}
            />
            <Dato
              titulo="Aves vivas"
              valor={numero(datos.aves.vivas)}
              detalle={`${numero(datos.aves.descarte)} de descarte`}
            />
            <Dato
              titulo="Mortalidad"
              valor={`${datos.aves.mortalidad_porcentaje}%`}
              detalle={`${numero(datos.aves.muertes)} ave(s) en el periodo`}
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
            <Tarjeta titulo="Produccion por tipo">
              {datos.produccion.por_tipo.length === 0 ? (
                <Vacio>Sin recolecciones en el periodo.</Vacio>
              ) : (
                <Tabla columnas={["Tipo", "Huevos", "Panales"]}>
                  {datos.produccion.por_tipo.map((fila) => (
                    <tr key={fila.tipo} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-700">{fila.tipo}</td>
                      <td className="px-3 py-2">{numero(fila.cantidad)}</td>
                      <td className="px-3 py-2 text-slate-500">{(fila.cantidad / 30).toFixed(1)}</td>
                    </tr>
                  ))}
                </Tabla>
              )}
            </Tarjeta>

            <Tarjeta titulo="Ventas por producto">
              {datos.ventas.por_clase.length === 0 ? (
                <Vacio>Sin ventas en el periodo.</Vacio>
              ) : (
                <>
                  <Tabla columnas={["Que se vendio", "Total"]}>
                    {datos.ventas.por_clase.map((fila) => (
                      <tr key={fila.clase} className="hover:bg-slate-50">
                        <td className="px-3 py-2">{NOMBRE_CLASE[fila.clase] ?? fila.clase}</td>
                        <td className="px-3 py-2 font-medium">{moneda(fila.total)}</td>
                      </tr>
                    ))}
                  </Tabla>
                  <p className="mt-3 text-xs text-slate-500">
                    Efectivo {moneda(datos.ventas.efectivo)} · otros medios {moneda(datos.ventas.otros_medios)}
                  </p>
                </>
              )}
            </Tarjeta>

            <Tarjeta titulo="Alimento y aves">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Alimento entregado</dt>
                  <dd>{numero(datos.alimento.kg)} kg</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Costo del alimento</dt>
                  <dd>{moneda(datos.alimento.costo)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Kilos por ave</dt>
                  <dd>{datos.alimento.kg_por_ave}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Aves descartadas</dt>
                  <dd>{numero(datos.aves.descartadas)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Aves vendidas</dt>
                  <dd>{numero(datos.aves.vendidas)}</dd>
                </div>
              </dl>
            </Tarjeta>

            <Tarjeta titulo="Para revisar">
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Tareas pendientes</span>
                  <Insignia tono={datos.trabajo.tareas_pendientes ? "azul" : "verde"}>
                    {datos.trabajo.tareas_pendientes}
                  </Insignia>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Novedades sin cerrar</span>
                  <Insignia tono={datos.trabajo.novedades_abiertas ? "rojo" : "verde"}>
                    {datos.trabajo.novedades_abiertas}
                  </Insignia>
                </div>

                <div>
                  <p className="mb-1 font-medium text-slate-700">Articulos bajo el minimo</p>
                  {datos.inventario.bajo_minimo.length === 0 ? (
                    <p className="text-xs text-slate-500">Todo esta por encima del minimo.</p>
                  ) : (
                    <ul className="space-y-1 text-xs text-slate-600">
                      {datos.inventario.bajo_minimo.map((fila) => (
                        <li key={fila.articulo} className="flex justify-between">
                          <span>{fila.articulo}</span>
                          <span>
                            hay {numero(fila.hay)} {fila.unidad} (minimo {numero(fila.minimo)})
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </Tarjeta>
          </div>

          <Tarjeta titulo="Descargar para Excel">
            <p className="mb-3 text-sm text-slate-500">
              Los archivos salen en CSV con punto y coma, listos para abrir en Excel.
            </p>
            <div className="flex flex-wrap gap-2">
              {DESCARGAS.map((fila) => (
                <Boton key={fila.tipo} tono="suave" onClick={() => descargar(fila.tipo)} disabled={bajando === fila.tipo}>
                  {bajando === fila.tipo ? "Generando..." : fila.texto}
                </Boton>
              ))}
            </div>
          </Tarjeta>
        </>
      ) : null}
    </>
  );
}
