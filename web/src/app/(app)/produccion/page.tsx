"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Lote, ProduccionDia, StockHuevos, TipoHuevo } from "@/lib/tipos";
import {
  Aviso,
  Boton,
  Campo,
  Cargando,
  Insignia,
  Lista,
  Paginador,
  Tabla,
  Tarjeta,
  Vacio,
  usePaginas,
} from "@/componentes/ui";
import { fecha as verFecha, hoy } from "@/lib/formato";

type Resumen = {
  huevos_recolectados: number;
  dias_con_registro: number;
  promedio_diario: number;
  huevos_disponibles: number;
  panales_disponibles: number;
};

export default function Produccion() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;

  const { datos: lotes } = useDatos<Lote[]>("/lotes?solo_activos=true", finca);
  const { datos: tipos } = useDatos<TipoHuevo[]>("/tipos-huevo", finca);
  const [recargas, setRecargas] = useState(0);
  const { datos: dias, cargando } = useDatos<ProduccionDia[]>("/produccion", `${finca}-${recargas}`);
  const { datos: stock } = useDatos<StockHuevos[]>("/stock-huevos", `${finca}-${recargas}`);
  const { datos: resumen } = useDatos<Resumen>("/produccion/resumen", `${finca}-${recargas}`);
  const pagDias = usePaginas(dias, 20, "");

  const [loteId, setLoteId] = useState("");
  const [fecha, setFecha] = useState(hoy());
  const [cantidades, setCantidades] = useState<Record<number, string>>({});
  const [fallo, setFallo] = useState("");
  const [aviso, setAviso] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!loteId && lotes && lotes.length > 0) {
      const postura = lotes.find((l) => l.proposito === "postura") ?? lotes[0];
      setLoteId(String(postura.id));
    }
  }, [lotes, loteId]);

  const lote = lotes?.find((l) => String(l.id) === loteId);
  const total = Object.values(cantidades).reduce((suma, valor) => suma + Number(valor || 0), 0);
  const porcentaje = lote && lote.aves_actuales ? Math.round((total * 1000) / lote.aves_actuales) / 10 : 0;

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setFallo("");
    setAviso("");

    const detalles = Object.entries(cantidades)
      .filter(([, valor]) => valor !== "")
      .map(([tipo, valor]) => ({ tipo_huevo_id: Number(tipo), cantidad: Number(valor) }));

    if (!loteId || detalles.length === 0) {
      setFallo("Elige el lote y escribe cuantos huevos se recogieron");
      return;
    }

    setGuardando(true);
    try {
      const guardado = await api<ProduccionDia>("/produccion", {
        metodo: "POST",
        cuerpo: { lote_id: Number(loteId), fecha, detalles },
      });
      setAviso(`Se guardaron ${guardado.total} huevos del ${verFecha(guardado.fecha)} (postura ${guardado.porcentaje_postura}%)`);
      setCantidades({});
      setRecargas((n) => n + 1);
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <div>
        <h1 className="titulo-pantalla">Produccion de huevos</h1>
        <p className="bajada">
          Registra la recoleccion del dia. Si te equivocas, vuelve a registrar el mismo dia y se corrige.
        </p>
      </div>

      {resumen ? (
        <div className="grid grid-cols-2 gap-2.5 sm:gap-4 xl:grid-cols-4">
          <div className="rounded-xl border border-linea bg-superficie p-4">
            <p className="text-sm text-tinta-2">Recolectados</p>
            <p className="cifra mt-1 text-[1.75rem] leading-tight font-bold text-tinta">
              {resumen.huevos_recolectados.toLocaleString("es-CO")}
            </p>
          </div>
          <div className="rounded-xl border border-linea bg-superficie p-4">
            <p className="text-sm text-tinta-2">Promedio diario</p>
            <p className="cifra mt-1 text-[1.75rem] leading-tight font-bold text-tinta">{Math.round(resumen.promedio_diario).toLocaleString("es-CO")}</p>
            <p className="text-sm text-tinta-2">{resumen.dias_con_registro} dias con registro</p>
          </div>
          <div className="rounded-xl border border-linea bg-superficie p-4">
            <p className="text-sm text-tinta-2">Disponibles</p>
            <p className="cifra mt-1 text-[1.75rem] leading-tight font-bold text-tinta">
              {resumen.huevos_disponibles.toLocaleString("es-CO")}
            </p>
            <p className="text-sm text-tinta-2">{resumen.panales_disponibles.toLocaleString("es-CO", { maximumFractionDigits: 1 })} panales</p>
          </div>
          <div className="rounded-xl border border-linea bg-superficie p-4">
            <p className="text-sm text-tinta-2">Lotes en postura</p>
            <p className="cifra mt-1 text-[1.75rem] leading-tight font-bold text-tinta">
              {(lotes ?? []).filter((l) => l.proposito === "postura").length}
            </p>
          </div>
        </div>
      ) : null}

      {puede("produccion", "crear") ? (
        <Tarjeta titulo="Recoleccion del dia">
          <form onSubmit={guardar} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <Lista etiqueta="Lote" value={loteId} onChange={(e) => setLoteId(e.target.value)}>
                <option value="">Elige un lote</option>
                {(lotes ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.codigo} · {l.galpon_nombre} ({l.aves_actuales} aves)
                  </option>
                ))}
              </Lista>
              <Campo etiqueta="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
              <div className="flex items-end gap-4 rounded-lg bg-cal px-4 py-2 sm:bg-transparent sm:px-0" aria-live="polite">
                <span className="text-base text-tinta-2">
                  Total <span className="cifra ml-1 text-2xl font-bold text-tinta">{total.toLocaleString("es-CO")}</span>
                </span>
                {lote ? <span className="pb-0.5 text-base text-tinta-2">postura {porcentaje} %</span> : null}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {(tipos ?? []).map((tipo) => (
                <Campo
                  key={tipo.id}
                  etiqueta={tipo.comercial ? tipo.nombre : `${tipo.nombre} (no se vende)`}
                  type="number"
                  min={0}
                  inputMode="numeric"
                  className="cifra text-lg"
                  value={cantidades[tipo.id] ?? ""}
                  onChange={(e) => setCantidades({ ...cantidades, [tipo.id]: e.target.value })}
                />
              ))}
            </div>

            {fallo ? <Aviso>{fallo}</Aviso> : null}
            {aviso ? <Aviso tipo="bien">{aviso}</Aviso> : null}

            <Boton type="submit" tamano="grande" disabled={guardando} className="w-full sm:w-auto">
              {guardando ? "Guardando..." : "Guardar recoleccion"}
            </Boton>
          </form>
        </Tarjeta>
      ) : null}

      <Tarjeta titulo="Huevos disponibles">
        {!stock || stock.length === 0 ? (
          <Vacio>No hay huevos en existencia.</Vacio>
        ) : (
          <Tabla columnas={["Tipo", "Huevos", "Panales"]} numericas={[1, 2]}>
            {stock.map((fila) => (
              <tr key={fila.tipo_huevo_id} className="hover:bg-cal">
                <td className="px-3 py-2 font-medium text-tinta">
                  {fila.tipo}
                  {!fila.comercial ? (
                    <span className="ml-2">
                      <Insignia>No se vende</Insignia>
                    </span>
                  ) : null}
                </td>
                <td className="px-3 py-2 cifra text-right">{fila.cantidad.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2 cifra text-right">{fila.panales.toLocaleString("es-CO", { maximumFractionDigits: 1 })}</td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Tarjeta titulo="Ultimos dias">
        {cargando ? (
          <Cargando />
        ) : !dias || dias.length === 0 ? (
          <Vacio>Todavia no hay recolecciones registradas.</Vacio>
        ) : (
          <>
            <Tabla columnas={["Fecha", "Lote", "Total", "Se venden", "Postura", "Detalle"]} numericas={[2, 3]}>
              {pagDias.visibles.map((dia) => (
                <tr key={`${dia.lote_id}-${dia.fecha}`} className="hover:bg-cal">
                  <td className="whitespace-nowrap px-3 py-2">{verFecha(dia.fecha)}</td>
                  <td className="px-3 py-2">{dia.lote_codigo}</td>
                  <td className="px-3 py-2 font-medium text-tinta cifra text-right">{dia.total.toLocaleString("es-CO")}</td>
                  <td className="px-3 py-2 cifra text-right">{dia.comercial.toLocaleString("es-CO")}</td>
                  <td className="px-3 py-2">{dia.porcentaje_postura}%</td>
                  <td className="px-3 py-2 text-sm text-tinta-2">
                    {Object.entries(dia.detalles)
                      .map(([tipo, cantidad]) => `${tipo}: ${cantidad}`)
                      .join(" · ")}
                  </td>
                </tr>
              ))}
            </Tabla>
            <Paginador {...pagDias} nombre="registros" />
          </>
        )}
      </Tarjeta>
    </>
  );
}
