"use client";

import { useState } from "react";
import { descargar } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { ResumenReporte } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, CifraFranja, Franja, Insignia, Tabla, Tarjeta, Vacio } from "@/componentes/ui";
import { haceDias } from "@/lib/formato";
import { avisar } from "@/componentes/dialogos";

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


export default function Reportes() {
  const { sesion } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [desde, setDesde] = useState(haceDias(29));
  const [hasta, setHasta] = useState(haceDias(0));
  const [bajando, setBajando] = useState("");

  const ruta = `/reportes/resumen?desde=${desde}&hasta=${hasta}`;
  const { datos, cargando, error } = useDatos<ResumenReporte>(ruta, `${finca}-${ruta}`);

  async function bajar(tipo: string) {
    setBajando(tipo);
    try {
      const parametros = new URLSearchParams({ tipo, desde, hasta });
      const contenido = await descargar(`/reportes/csv?${parametros}`);
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(contenido);
      enlace.download = `${tipo}_${desde}_a_${hasta}.csv`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch (error) {
      avisar.error(mensajeDeError(error, "No se pudo descargar el reporte"));
    } finally {
      setBajando("");
    }
  }

  return (
    <>
      <div>
        <h1 className="titulo-pantalla">Reportes</h1>
        <p className="bajada">Como va la finca en el periodo que elijas</p>
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
          <Franja className="grid grid-cols-2 xl:grid-cols-4 [&>*]:border-white/10 max-xl:[&>*:nth-child(-n+2)]:border-b [&>*:nth-child(odd)]:border-r xl:[&>*:not(:last-child)]:border-r">
            <CifraFranja
              compacta
              titulo="Huevos recolectados"
              valor={numero(datos.produccion.huevos)}
              detalle={`${numero(Math.round(datos.produccion.promedio_diario))} por dia`}
            />
            <CifraFranja
              compacta
              titulo="Vendido"
              valor={moneda(datos.ventas.total)}
              detalle={`${datos.ventas.cantidad} venta(s), ${datos.ventas.anuladas} anulada(s)`}
            />
            <CifraFranja
              compacta
              titulo="Aves vivas"
              valor={numero(datos.aves.vivas)}
              detalle={`${numero(datos.aves.descarte)} de descarte`}
            />
            <CifraFranja
              compacta
              titulo="Mortalidad"
              valor={`${datos.aves.mortalidad_porcentaje.toLocaleString("es-CO")}%`}
              detalle={`${numero(datos.aves.muertes)} ave(s) en el periodo`}
            />
          </Franja>

          <div className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
            <Tarjeta titulo="Produccion por tipo">
              {datos.produccion.por_tipo.length === 0 ? (
                <Vacio>Sin recolecciones en el periodo.</Vacio>
              ) : (
                <Tabla columnas={["Tipo", "Huevos", "Panales"]} numericas={[1, 2]}>
                  {datos.produccion.por_tipo.map((fila) => (
                    <tr key={fila.tipo} className="hover:bg-cal">
                      <td className="px-3 py-2 font-medium text-tinta">{fila.tipo}</td>
                      <td className="px-3 py-2 cifra text-right">{numero(fila.cantidad)}</td>
                      <td className="px-3 py-2 text-tinta-2 cifra text-right">{(fila.cantidad / 30).toLocaleString("es-CO", { maximumFractionDigits: 1 })}</td>
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
                  <Tabla columnas={["Que se vendio", "Total"]} numericas={[1]}>
                    {datos.ventas.por_clase.map((fila) => (
                      <tr key={fila.clase} className="hover:bg-cal">
                        <td className="px-3 py-2">{NOMBRE_CLASE[fila.clase] ?? fila.clase}</td>
                        <td className="px-3 py-2 font-medium cifra text-right">{moneda(fila.total)}</td>
                      </tr>
                    ))}
                    {datos.ventas.por_clase.reduce((suma, fila) => suma + fila.total, 0) - datos.ventas.total > 0.5 ? (
                      <tr>
                        <td className="px-3 py-2 text-tinta-2">Descuentos</td>
                        <td className="px-3 py-2 text-tinta-2">
                          -{moneda(datos.ventas.por_clase.reduce((suma, fila) => suma + fila.total, 0) - datos.ventas.total)}
                        </td>
                      </tr>
                    ) : null}
                    <tr className="font-semibold text-tinta">
                      <td className="px-3 py-2 font-bold">Total</td>
                      <td className="cifra px-3 py-2 text-right text-lg font-bold">{moneda(datos.ventas.total)}</td>
                    </tr>
                  </Tabla>
                  <p className="mt-3 text-sm text-tinta-2">
                    Efectivo {moneda(datos.ventas.efectivo)} · otros medios {moneda(datos.ventas.otros_medios)}
                  </p>
                </>
              )}
            </Tarjeta>

            <Tarjeta titulo="Alimento y aves">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-tinta-2">Alimento entregado</dt>
                  <dd>{numero(datos.alimento.kg)} kg</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-tinta-2">Costo del alimento</dt>
                  <dd>{moneda(datos.alimento.costo)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-tinta-2">Kilos por ave</dt>
                  <dd>{datos.alimento.kg_por_ave}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-tinta-2">Aves descartadas</dt>
                  <dd>{numero(datos.aves.descartadas)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-tinta-2">Aves vendidas</dt>
                  <dd>{numero(datos.aves.vendidas)}</dd>
                </div>
              </dl>
            </Tarjeta>

            <Tarjeta titulo="Para revisar">
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-tinta-2">Tareas pendientes</span>
                  <Insignia tono={datos.trabajo.tareas_pendientes ? "azul" : "verde"}>
                    {datos.trabajo.tareas_pendientes}
                  </Insignia>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-tinta-2">Novedades sin cerrar</span>
                  <Insignia tono={datos.trabajo.novedades_abiertas ? "rojo" : "verde"}>
                    {datos.trabajo.novedades_abiertas}
                  </Insignia>
                </div>

                <div>
                  <p className="mb-2 font-semibold text-tinta">Articulos bajo el minimo</p>
                  {datos.inventario.bajo_minimo.length === 0 ? (
                    <p className="text-sm text-tinta-2">Todo esta por encima del minimo.</p>
                  ) : (
                    <ul className="space-y-1.5 text-base text-tinta-2">
                      {datos.inventario.bajo_minimo.map((fila) => (
                        <li key={fila.articulo} className="flex flex-wrap justify-between gap-x-3 border-l-4 border-alerta-borde py-1 pl-3">
                          <span className="text-tinta">{fila.articulo}</span>
                          <span className="cifra">
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
            <p className="mb-3 text-sm text-tinta-2">
              Los archivos salen en CSV con punto y coma, listos para abrir en Excel.
            </p>
            <div className="flex flex-wrap gap-2">
              {DESCARGAS.map((fila) => (
                <Boton key={fila.tipo} tono="suave" onClick={() => bajar(fila.tipo)} disabled={bajando === fila.tipo}>
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
