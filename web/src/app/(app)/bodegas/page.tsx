"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Bodega, Existencia } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const VACIO = { codigo: "", nombre: "", ubicacion: "", finca_id: "" };

export default function Bodegas() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa;
  const { datos, cargando, error, recargar } = useDatos<Bodega[]>("/bodegas?incluir_inactivas=true", finca?.id ?? 0);

  const [bodegaVista, setBodegaVista] = useState<number | "">("");
  const rutaExistencias = `/existencias${bodegaVista ? `?bodega_id=${bodegaVista}` : ""}`;
  const { datos: existencias, cargando: cargandoStock } = useDatos<Existencia[]>(
    rutaExistencias,
    `${finca?.id ?? 0}-${bodegaVista}`,
  );

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Bodega | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(bodega?: Bodega) {
    setFallo("");
    setEditando(bodega ?? null);
    setFormulario(
      bodega
        ? {
            codigo: bodega.codigo,
            nombre: bodega.nombre,
            ubicacion: bodega.ubicacion ?? "",
            finca_id: bodega.finca_id ? String(bodega.finca_id) : "",
          }
        : { ...VACIO, finca_id: finca ? String(finca.id) : "" },
    );
    setAbierto(true);
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    const cuerpo = {
      codigo: formulario.codigo,
      nombre: formulario.nombre,
      ubicacion: formulario.ubicacion || null,
      finca_id: formulario.finca_id ? Number(formulario.finca_id) : null,
    };
    try {
      if (editando) await api(`/bodegas/${editando.id}`, { metodo: "PATCH", cuerpo });
      else await api("/bodegas", { metodo: "POST", cuerpo });
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function desactivar(bodega: Bodega) {
    if (!confirm(`Desactivar la bodega ${bodega.nombre}?`)) return;
    try {
      await api(`/bodegas/${bodega.id}`, { metodo: "DELETE" });
      await recargar();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Bodegas</h1>
          <p className="text-sm text-slate-500">
            La bodega central sirve a toda la cuenta; las demas pertenecen a una finca.
          </p>
        </div>
        {puede("bodegas", "crear") ? <Boton onClick={() => abrir()}>Nueva bodega</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta titulo="Bodegas">
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>Todavia no hay bodegas.</Vacio>
        ) : (
          <Tabla columnas={["Codigo", "Nombre", "Donde", "Ubicacion", "Estado", ""]}>
            {datos.map((bodega) => (
              <tr key={bodega.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{bodega.codigo}</td>
                <td className="px-3 py-2">{bodega.nombre}</td>
                <td className="px-3 py-2">
                  {bodega.es_central ? (
                    <Insignia tono="azul">Central</Insignia>
                  ) : (
                    <Insignia>{sesion?.fincas.find((f) => f.id === bodega.finca_id)?.nombre ?? "Finca"}</Insignia>
                  )}
                </td>
                <td className="px-3 py-2 text-slate-500">{bodega.ubicacion ?? "-"}</td>
                <td className="px-3 py-2">
                  {bodega.activo ? <Insignia tono="verde">Activa</Insignia> : <Insignia>Inactiva</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("bodegas", "editar") ? (
                      <Boton tono="suave" onClick={() => abrir(bodega)}>
                        Editar
                      </Boton>
                    ) : null}
                    {puede("bodegas", "borrar") && bodega.activo ? (
                      <Boton tono="peligro" onClick={() => desactivar(bodega)}>
                        Desactivar
                      </Boton>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Tarjeta
        titulo="Que hay en las bodegas"
        acciones={
          <select
            value={bodegaVista}
            onChange={(e) => setBodegaVista(e.target.value === "" ? "" : Number(e.target.value))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
          >
            <option value="">Todas</option>
            {(datos ?? []).map((bodega) => (
              <option key={bodega.id} value={bodega.id}>
                {bodega.nombre}
              </option>
            ))}
          </select>
        }
      >
        {cargandoStock ? (
          <Cargando />
        ) : !existencias || existencias.length === 0 ? (
          <Vacio>No hay existencias registradas.</Vacio>
        ) : (
          <Tabla columnas={["Bodega", "Codigo", "Articulo", "Cantidad", "Costo promedio", ""]}>
            {existencias.map((fila) => (
              <tr key={`${fila.bodega_id}-${fila.articulo_id}`} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-500">{fila.bodega_nombre}</td>
                <td className="px-3 py-2">{fila.articulo_codigo}</td>
                <td className="px-3 py-2 font-medium text-slate-700">{fila.articulo_nombre}</td>
                <td className="px-3 py-2">
                  {fila.cantidad.toLocaleString("es-CO")} {fila.unidad}
                </td>
                <td className="px-3 py-2">${fila.costo_promedio.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2">{fila.bajo_minimo ? <Insignia tono="rojo">Bajo minimo</Insignia> : null}</td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar bodega" : "Nueva bodega"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Codigo"
              required
              maxLength={20}
              value={formulario.codigo}
              onChange={(e) => setFormulario({ ...formulario, codigo: e.target.value })}
            />
            <Campo
              etiqueta="Nombre"
              required
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
            />
          </div>
          <Campo
            etiqueta="Ubicacion"
            value={formulario.ubicacion}
            onChange={(e) => setFormulario({ ...formulario, ubicacion: e.target.value })}
          />
          <Lista
            etiqueta="A quien pertenece"
            value={formulario.finca_id}
            onChange={(e) => setFormulario({ ...formulario, finca_id: e.target.value })}
          >
            <option value="">Central (toda la cuenta)</option>
            {(sesion?.fincas ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {f.nombre}
              </option>
            ))}
          </Lista>

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
