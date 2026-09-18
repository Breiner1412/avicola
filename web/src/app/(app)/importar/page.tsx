"use client";

import { useState } from "react";
import { api, FalloApi } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type {
  AnalisisImportacion,
  Bodega,
  Importacion,
  TipoImportacion,
  ValidacionImportacion,
} from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

export default function Importar() {
  const { sesion, puede } = useSesion();
  const finca = sesion?.finca_activa?.id ?? 0;
  const [recargas, setRecargas] = useState(0);

  const { datos: tipos } = useDatos<TipoImportacion[]>("/importacion/tipos");
  const { datos: bodegas } = useDatos<Bodega[]>(puede("bodegas", "ver") ? "/bodegas" : null, finca);
  const { datos: historial, recargar } = useDatos<Importacion[]>("/importacion", `${finca}-${recargas}`);

  const [tipo, setTipo] = useState("entrada_inventario");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [analisis, setAnalisis] = useState<AnalisisImportacion | null>(null);
  const [mapeo, setMapeo] = useState<Record<string, string>>({});
  const [bodegaId, setBodegaId] = useState("");
  const [crearArticulos, setCrearArticulos] = useState(true);
  const [validacion, setValidacion] = useState<ValidacionImportacion | null>(null);
  const [resultado, setResultado] = useState<Importacion | null>(null);
  const [nombrePlantilla, setNombrePlantilla] = useState("");
  const [fallo, setFallo] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const definicion = tipos?.find((t) => t.clave === tipo);
  const opciones = { bodega_id: bodegaId ? Number(bodegaId) : null, crear_articulos: crearArticulos };

  function reiniciar() {
    setAnalisis(null);
    setValidacion(null);
    setResultado(null);
    setMapeo({});
    setArchivo(null);
    setFallo("");
  }

  async function subir(evento: React.FormEvent) {
    evento.preventDefault();
    if (!archivo) {
      setFallo("Elige el archivo");
      return;
    }
    setOcupado(true);
    setFallo("");
    try {
      const cuerpo = new FormData();
      cuerpo.append("tipo", tipo);
      cuerpo.append("archivo", archivo);

      const respuesta = await fetch("/api/v1/importacion/analizar", {
        method: "POST",
        body: cuerpo,
        credentials: "include",
        headers: {
          Authorization: `Bearer ${sesion?.token ?? ""}`,
          ...(finca ? { "X-Finca-Id": String(finca) } : {}),
        },
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        throw new FalloApi(respuesta.status, datos?.detail?.codigo ?? "error", datos?.detail?.mensaje ?? "No se pudo leer el archivo");
      }

      setAnalisis(datos as AnalisisImportacion);
      setMapeo((datos as AnalisisImportacion).mapeo_sugerido ?? {});
      setValidacion(null);
      setResultado(null);
    } catch (error) {
      setFallo(mensajeDeError(error, "No se pudo leer el archivo"));
    } finally {
      setOcupado(false);
    }
  }

  async function revisar() {
    if (!analisis) return;
    setOcupado(true);
    setFallo("");
    try {
      setValidacion(await api<ValidacionImportacion>(`/importacion/${analisis.id}/validar`, {
        metodo: "POST",
        cuerpo: { mapeo, opciones },
      }));
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setOcupado(false);
    }
  }

  async function guardar() {
    if (!analisis) return;
    setOcupado(true);
    setFallo("");
    try {
      const hecho = await api<Importacion>(`/importacion/${analisis.id}/aplicar`, {
        metodo: "POST",
        cuerpo: { mapeo, opciones },
      });
      setResultado(hecho);
      setAnalisis(null);
      setValidacion(null);
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setOcupado(false);
    }
  }

  async function guardarPlantilla() {
    if (!analisis || nombrePlantilla.trim().length < 2) return;
    try {
      await api("/importacion/plantillas", {
        metodo: "POST",
        cuerpo: { tipo, nombre: nombrePlantilla.trim(), mapeo },
      });
      setNombrePlantilla("");
      alert("Plantilla guardada. La proxima vez puedes usarla para no volver a emparejar las columnas.");
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  async function deshacer(importacion: Importacion) {
    if (!confirm(`Deshacer la importacion de ${importacion.archivo}? Se quitara lo que se creo con ella.`)) return;
    try {
      await api(`/importacion/${importacion.id}/revertir`, { metodo: "POST" });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Importar desde Excel</h1>
        <p className="text-sm text-slate-500">
          Sube tu archivo tal como lo manejas. El sistema lee sus columnas y tu indicas cual es cual; antes de guardar
          te muestra que quedaria bien y que no.
        </p>
      </div>

      {resultado ? (
        <Aviso tipo="bien">
          Listo: se guardaron {resultado.filas_ok} registro(s) de {resultado.archivo}
          {resultado.filas_error ? `, ${resultado.filas_error} fila(s) quedaron por fuera` : ""}. Si algo salio mal,
          puedes deshacerlo desde el historial.
        </Aviso>
      ) : null}

      {!analisis ? (
        <Tarjeta titulo="1. Elige que vas a subir">
          <form onSubmit={subir} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Lista etiqueta="Que contiene el archivo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
                {(tipos ?? []).map((t) => (
                  <option key={t.clave} value={t.clave}>
                    {t.etiqueta}
                  </option>
                ))}
              </Lista>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Archivo (.xlsx o .csv)</span>
                <input
                  type="file"
                  accept=".xlsx,.xlsm,.csv,.txt"
                  onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-emerald-700 file:px-3 file:py-1 file:text-white"
                />
              </label>
            </div>

            {definicion ? (
              <p className="text-xs text-slate-500">
                Datos que se pueden cargar: {definicion.campos.map((c) => c.etiqueta + (c.obligatorio ? "*" : "")).join(", ")}.
                Los marcados con * son obligatorios.
              </p>
            ) : null}

            {fallo ? <Aviso>{fallo}</Aviso> : null}

            <Boton type="submit" disabled={ocupado}>
              {ocupado ? "Leyendo..." : "Leer archivo"}
            </Boton>
          </form>
        </Tarjeta>
      ) : (
        <>
          <Tarjeta
            titulo={`2. Empareja las columnas de ${analisis.archivo}`}
            acciones={
              <Boton tono="suave" onClick={reiniciar}>
                Cambiar archivo
              </Boton>
            }
          >
            <p className="mb-3 text-sm text-slate-500">
              {analisis.filas_totales} fila(s) leidas{analisis.hoja ? ` de la hoja "${analisis.hoja}"` : ""}. Lo que
              pudimos reconocer ya viene marcado.
            </p>

            {analisis.plantillas.length > 0 ? (
              <div className="mb-4">
                <Lista
                  etiqueta="Usar una plantilla guardada"
                  onChange={(e) => {
                    const elegida = analisis.plantillas.find((p) => String(p.id) === e.target.value);
                    if (elegida) setMapeo(elegida.mapeo);
                  }}
                >
                  <option value="">Sin plantilla</option>
                  {analisis.plantillas.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </Lista>
              </div>
            ) : null}

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {analisis.campos.map((campo) => (
                <Lista
                  key={campo.clave}
                  etiqueta={campo.etiqueta + (campo.obligatorio ? " *" : "")}
                  value={mapeo[campo.clave] ?? ""}
                  onChange={(e) => setMapeo({ ...mapeo, [campo.clave]: e.target.value })}
                >
                  <option value="">No esta en el archivo</option>
                  {analisis.columnas.map((columna) => (
                    <option key={columna} value={columna}>
                      {columna}
                    </option>
                  ))}
                </Lista>
              ))}
            </div>

            {analisis.tipo === "entrada_inventario" ? (
              <div className="mt-4 grid gap-3 rounded-lg border border-dashed border-slate-300 p-3 sm:grid-cols-2">
                <Lista etiqueta="A que bodega entra" value={bodegaId} onChange={(e) => setBodegaId(e.target.value)}>
                  <option value="">Elige la bodega</option>
                  {(bodegas ?? []).map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.nombre}
                    </option>
                  ))}
                </Lista>
                <label className="flex items-end gap-2 pb-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={crearArticulos}
                    onChange={(e) => setCrearArticulos(e.target.checked)}
                  />
                  Crear los articulos que no existan
                </label>
              </div>
            ) : null}

            <div className="mt-4 overflow-x-auto">
              <p className="mb-2 text-sm font-medium text-slate-700">Asi viene el archivo</p>
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    {analisis.columnas.map((columna) => (
                      <th key={columna} className="whitespace-nowrap px-2 py-1">
                        {columna}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {analisis.vista_previa.map((fila, indice) => (
                    <tr key={indice}>
                      {analisis.columnas.map((columna) => (
                        <td key={columna} className="whitespace-nowrap px-2 py-1 text-slate-600">
                          {String(fila[columna] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {fallo ? <Aviso>{fallo}</Aviso> : null}

            <div className="mt-4 flex flex-wrap items-end gap-3">
              <Boton onClick={revisar} disabled={ocupado} tono="suave">
                {ocupado ? "Revisando..." : "Revisar antes de guardar"}
              </Boton>
              <div className="flex items-end gap-2">
                <Campo
                  etiqueta="Guardar este emparejamiento como"
                  placeholder="Formato del proveedor"
                  value={nombrePlantilla}
                  onChange={(e) => setNombrePlantilla(e.target.value)}
                />
                <Boton type="button" tono="suave" onClick={guardarPlantilla}>
                  Guardar plantilla
                </Boton>
              </div>
            </div>
          </Tarjeta>

          {validacion ? (
            <Tarjeta titulo="3. Revision">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-200 p-3">
                  <p className="text-xs uppercase text-slate-500">Filas leidas</p>
                  <p className="text-xl font-semibold">{validacion.filas_totales}</p>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <p className="text-xs uppercase text-emerald-700">Listas para guardar</p>
                  <p className="text-xl font-semibold text-emerald-800">{validacion.filas_ok}</p>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-xs uppercase text-red-700">Con problemas</p>
                  <p className="text-xl font-semibold text-red-800">{validacion.filas_error}</p>
                </div>
              </div>

              {validacion.errores.length > 0 ? (
                <div className="mt-4">
                  <p className="mb-2 text-sm font-medium text-slate-700">Que hay que corregir</p>
                  <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-red-700">
                    {validacion.errores.map((error) => (
                      <li key={error.numero}>
                        Fila {error.numero}: {error.error}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-slate-500">
                    Las filas con problemas no se guardan; puedes corregirlas en el archivo y volver a subirlo.
                  </p>
                </div>
              ) : null}

              <div className="mt-4">
                <Boton onClick={guardar} disabled={ocupado || validacion.filas_ok === 0}>
                  {ocupado ? "Guardando..." : `Guardar ${validacion.filas_ok} fila(s)`}
                </Boton>
              </div>
            </Tarjeta>
          ) : null}
        </>
      )}

      <Tarjeta titulo="Importaciones anteriores">
        {!historial ? (
          <Cargando />
        ) : historial.length === 0 ? (
          <Vacio>Todavia no has importado nada.</Vacio>
        ) : (
          <Tabla columnas={["Fecha", "Archivo", "Que contenia", "Guardadas", "Con problemas", "Estado", ""]}>
            {historial.map((fila) => (
              <tr key={fila.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2 text-slate-500">
                  {new Date(fila.creado_en).toLocaleString("es-CO")}
                </td>
                <td className="px-3 py-2 font-medium text-slate-700">{fila.archivo}</td>
                <td className="px-3 py-2 text-xs">{fila.etiqueta_tipo}</td>
                <td className="px-3 py-2">{fila.filas_ok}</td>
                <td className="px-3 py-2">{fila.filas_error}</td>
                <td className="px-3 py-2">
                  {fila.estado === "aplicada" ? (
                    <Insignia tono="verde">Aplicada</Insignia>
                  ) : fila.estado === "revertida" ? (
                    <Insignia tono="rojo">Deshecha</Insignia>
                  ) : (
                    <Insignia>Sin aplicar</Insignia>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {puede("importacion", "editar") && fila.estado === "aplicada" ? (
                    <Boton tono="peligro" onClick={() => deshacer(fila)}>
                      Deshacer
                    </Boton>
                  ) : null}
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>
    </>
  );
}
