"use client";

import { useState } from "react";
import { api } from "@/lib/api";
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
import { fechaHora } from "@/lib/formato";
import { avisar, useDialogos } from "@/componentes/dialogos";

export default function Importar() {
  const { confirmar } = useDialogos();
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

      const datos = await api<AnalisisImportacion>("/importacion/analizar", { metodo: "POST", formulario: cuerpo });

      setAnalisis(datos);
      setMapeo(datos.mapeo_sugerido ?? {});
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
      avisar.bien("Plantilla guardada. La proxima vez puedes usarla para no volver a emparejar las columnas.");
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  async function deshacer(importacion: Importacion) {
    const seguro = await confirmar({
      titulo: "Deshacer la importacion",
      mensaje: `Se quitara lo que se creo al importar ${importacion.archivo}.`,
      aceptar: "Deshacer",
      peligro: true,
    });
    if (!seguro) return;
    try {
      await api(`/importacion/${importacion.id}/revertir`, { metodo: "POST" });
      setRecargas((n) => n + 1);
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  return (
    <>
      <div>
        <h1 className="titulo-pantalla">Importar desde Excel</h1>
        <p className="bajada">
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
                <span className="mb-1.5 block font-semibold text-tinta">Archivo (.xlsx o .csv)</span>
                <input
                  type="file"
                  accept=".xlsx,.xlsm,.csv,.txt"
                  onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                  className="min-h-12 w-full rounded-lg border-[1.5px] border-linea bg-superficie px-1.5 py-1.5 text-base text-tinta-2"
                />
              </label>
            </div>

            {definicion ? (
              <p className="text-sm text-tinta-2">
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
            <p className="mb-3 text-sm text-tinta-2">
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
              <div className="mt-4 grid gap-3 rounded-lg border border-dashed border-linea p-3 sm:grid-cols-2">
                <Lista etiqueta="A que bodega entra" value={bodegaId} onChange={(e) => setBodegaId(e.target.value)}>
                  <option value="">Elige la bodega</option>
                  {(bodegas ?? []).map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.nombre}
                    </option>
                  ))}
                </Lista>
                <label className="flex min-h-11 items-center gap-2.5 text-base text-tinta">
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
              <p className="mb-2 text-sm font-semibold text-tinta">Asi viene el archivo</p>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b-2 border-galpon text-tinta-2">
                    {analisis.columnas.map((columna) => (
                      <th key={columna} className="whitespace-nowrap px-2 py-2 font-semibold">
                        {columna}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-linea-suave">
                  {analisis.vista_previa.map((fila, indice) => (
                    <tr key={indice}>
                      {analisis.columnas.map((columna) => (
                        <td key={columna} className="whitespace-nowrap px-2 py-2 text-tinta-2">
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
                <div className="rounded-lg border border-linea p-3">
                  <p className="text-sm font-semibold text-tinta-2">Filas leidas</p>
                  <p className="cifra text-2xl font-bold">{validacion.filas_totales}</p>
                </div>
                <div className="rounded-lg border border-bien-borde bg-bien-suave p-3">
                  <p className="text-sm font-semibold text-bien">Listas para guardar</p>
                  <p className="cifra text-2xl font-bold text-bien">{validacion.filas_ok}</p>
                </div>
                <div className="rounded-lg border border-alerta-borde bg-alerta-suave p-3">
                  <p className="text-sm font-semibold text-alerta">Con problemas</p>
                  <p className="cifra text-2xl font-bold text-alerta">{validacion.filas_error}</p>
                </div>
              </div>

              {validacion.errores.length > 0 ? (
                <div className="mt-4">
                  <p className="mb-2 text-sm font-semibold text-tinta">Que hay que corregir</p>
                  <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-alerta">
                    {validacion.errores.map((error) => (
                      <li key={error.numero}>
                        Fila {error.numero}: {error.error}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-sm text-tinta-2">
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
              <tr key={fila.id} className="hover:bg-cal">
                <td className="whitespace-nowrap px-3 py-2 text-tinta-2">
                  {fechaHora(fila.creado_en)}
                </td>
                <td className="px-3 py-2 font-semibold text-tinta">{fila.archivo}</td>
                <td className="px-3 py-2 text-sm">{fila.etiqueta_tipo}</td>
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
