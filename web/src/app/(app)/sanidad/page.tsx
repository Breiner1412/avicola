"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Articulo, Bodega, Galpon, Lote, Sanidad } from "@/lib/tipos";
import {
  Aviso,
  Boton,
  Campo,
  Cargando,
  Insignia,
  Lista,
  Modal,
  Paginador,
  Tabla,
  Tarjeta,
  Vacio,
  usePaginas,
} from "@/componentes/ui";
import { fecha, hoy } from "@/lib/formato";

const TIPOS = [
  { valor: "vacuna", texto: "Vacuna" },
  { valor: "medicamento", texto: "Medicamento" },
  { valor: "vitamina", texto: "Vitaminas" },
  { valor: "desinfeccion", texto: "Desinfeccion" },
  { valor: "otro", texto: "Otro" },
];

const VIAS = ["agua", "ocular", "aspersion", "inyectado", "alimento", "otro"];

const VACIO = {
  fecha: hoy(),
  tipo: "vacuna",
  producto: "",
  lote_id: "",
  galpon_id: "",
  articulo_id: "",
  bodega_id: "",
  cantidad_usada: "",
  lote_producto: "",
  dosis: "",
  via: "agua",
  aves_tratadas: "",
  responsable: "",
  proximo_refuerzo: "",
  observaciones: "",
};

export default function SanidadPagina() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);

  const { datos, cargando, error } = useDatos<Sanidad[]>("/sanidad", `${finca}-${recargas}`);
  const { datos: proximas } = useDatos<Sanidad[]>("/sanidad/proximas?dias=45", `${finca}-${recargas}`);
  const { datos: lotes } = useDatos<Lote[]>("/lotes?solo_activos=true", finca);
  const { datos: galpones } = useDatos<Galpon[]>("/galpones", finca);
  const { datos: bodegas } = useDatos<Bodega[]>(puede("bodegas", "ver") ? "/bodegas" : null, finca);
  const { datos: articulos } = useDatos<Articulo[]>(puede("articulos", "ver") ? "/articulos" : null, finca);
  const pagAplicaciones = usePaginas(datos, 20, "");

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  const medicamentos = (articulos ?? []).filter((a) => ["vacuna", "medicamento", "insumo", "otro"].includes(a.clase));

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/sanidad", {
        metodo: "POST",
        cuerpo: {
          fecha: formulario.fecha,
          tipo: formulario.tipo,
          producto: formulario.producto,
          lote_id: formulario.lote_id ? Number(formulario.lote_id) : null,
          galpon_id: formulario.galpon_id ? Number(formulario.galpon_id) : null,
          articulo_id: formulario.articulo_id ? Number(formulario.articulo_id) : null,
          bodega_id: formulario.bodega_id ? Number(formulario.bodega_id) : null,
          cantidad_usada: formulario.cantidad_usada ? Number(formulario.cantidad_usada) : null,
          lote_producto: formulario.lote_producto || null,
          dosis: formulario.dosis || null,
          via: formulario.via,
          aves_tratadas: formulario.aves_tratadas ? Number(formulario.aves_tratadas) : null,
          responsable: formulario.responsable || null,
          proximo_refuerzo: formulario.proximo_refuerzo || null,
          observaciones: formulario.observaciones || null,
        },
      });
      setAbierto(false);
      setFormulario(VACIO);
      setRecargas((n) => n + 1);
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
          <h1 className="text-xl font-semibold text-slate-800">Vacunas y tratamientos</h1>
          <p className="text-sm text-slate-500">Que se aplico, a que lote, cuando y con que dosis</p>
        </div>
        {puede("sanidad", "crear") ? <Boton onClick={() => setAbierto(true)}>Registrar aplicacion</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      {proximas && proximas.length > 0 ? (
        <Aviso tipo="info">
          Refuerzos proximos:{" "}
          {proximas
            .slice(0, 4)
            .map((p) => `${p.producto} (${fecha(p.proximo_refuerzo)}${p.lote_codigo ? `, lote ${p.lote_codigo}` : ""})`)
            .join(" · ")}
        </Aviso>
      ) : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>Todavia no hay vacunas ni tratamientos registrados.</Vacio>
        ) : (
          <>
            <Tabla columnas={["Fecha", "Tipo", "Producto", "Lote o galpon", "Via", "Dosis", "Aves", "Refuerzo"]}>
              {pagAplicaciones.visibles.map((fila) => (
                <tr key={fila.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2">{fecha(fila.fecha)}</td>
                  <td className="px-3 py-2 capitalize">{fila.tipo}</td>
                  <td className="px-3 py-2 font-medium text-slate-700">
                    {fila.producto}
                    {fila.lote_producto ? (
                      <span className="block text-xs text-slate-400">lote del producto {fila.lote_producto}</span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2">{fila.lote_codigo ?? fila.galpon_nombre ?? "-"}</td>
                  <td className="px-3 py-2">{fila.via}</td>
                  <td className="px-3 py-2 text-slate-500">{fila.dosis ?? "-"}</td>
                  <td className="px-3 py-2">{fila.aves_tratadas?.toLocaleString("es-CO") ?? "-"}</td>
                  <td className="px-3 py-2">
                    {fila.proximo_refuerzo ? <Insignia tono="azul">{fecha(fila.proximo_refuerzo)}</Insignia> : "-"}
                  </td>
                </tr>
              ))}
            </Tabla>
            <Paginador {...pagAplicaciones} nombre="aplicaciones" />
          </>
        )}
      </Tarjeta>

      <Modal titulo="Registrar vacuna o tratamiento" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Fecha"
              type="date"
              required
              value={formulario.fecha}
              onChange={(e) => setFormulario({ ...formulario, fecha: e.target.value })}
            />
            <Lista
              etiqueta="Tipo"
              value={formulario.tipo}
              onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value })}
            >
              {TIPOS.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.texto}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Producto"
              required
              placeholder="Newcastle La Sota"
              value={formulario.producto}
              onChange={(e) => setFormulario({ ...formulario, producto: e.target.value })}
            />
            <Campo
              etiqueta="Lote del producto"
              value={formulario.lote_producto}
              onChange={(e) => setFormulario({ ...formulario, lote_producto: e.target.value })}
            />
            <Lista
              etiqueta="Lote de aves"
              value={formulario.lote_id}
              onChange={(e) => setFormulario({ ...formulario, lote_id: e.target.value })}
            >
              <option value="">Sin lote (toda la finca)</option>
              {(lotes ?? []).map((l) => (
                <option key={l.id} value={l.id}>
                  {l.codigo} · {l.galpon_nombre}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Galpon"
              value={formulario.galpon_id}
              onChange={(e) => setFormulario({ ...formulario, galpon_id: e.target.value })}
            >
              <option value="">El del lote</option>
              {(galpones ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nombre}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Via"
              value={formulario.via}
              onChange={(e) => setFormulario({ ...formulario, via: e.target.value })}
            >
              {VIAS.map((via) => (
                <option key={via} value={via}>
                  {via}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Dosis"
              placeholder="1 dosis por ave"
              value={formulario.dosis}
              onChange={(e) => setFormulario({ ...formulario, dosis: e.target.value })}
            />
            <Campo
              etiqueta="Aves tratadas"
              type="number"
              min={0}
              value={formulario.aves_tratadas}
              onChange={(e) => setFormulario({ ...formulario, aves_tratadas: e.target.value })}
            />
            <Campo
              etiqueta="Proximo refuerzo"
              type="date"
              value={formulario.proximo_refuerzo}
              onChange={(e) => setFormulario({ ...formulario, proximo_refuerzo: e.target.value })}
            />
          </div>

          <div className="space-y-3 rounded-lg border border-dashed border-slate-300 p-3">
            <p className="text-sm font-medium text-slate-700">Descontar de la bodega (opcional)</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <Lista
                etiqueta="Producto en bodega"
                value={formulario.articulo_id}
                onChange={(e) => setFormulario({ ...formulario, articulo_id: e.target.value })}
              >
                <option value="">No descontar</option>
                {medicamentos.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nombre} ({a.existencia_total} {a.unidad})
                  </option>
                ))}
              </Lista>
              <Lista
                etiqueta="Bodega"
                value={formulario.bodega_id}
                onChange={(e) => setFormulario({ ...formulario, bodega_id: e.target.value })}
              >
                <option value="">Elige la bodega</option>
                {(bodegas ?? []).map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.nombre}
                  </option>
                ))}
              </Lista>
              <Campo
                etiqueta="Cantidad usada"
                type="number"
                min={0}
                step="0.001"
                value={formulario.cantidad_usada}
                onChange={(e) => setFormulario({ ...formulario, cantidad_usada: e.target.value })}
              />
            </div>
          </div>

          <Campo
            etiqueta="Observaciones"
            value={formulario.observaciones}
            onChange={(e) => setFormulario({ ...formulario, observaciones: e.target.value })}
          />

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
