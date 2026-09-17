"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { PuntoVenta, Turno } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;
const VACIO = { codigo: "", nombre: "", direccion: "", finca_id: "" };

export default function PuntosVenta() {
  const { sesion, puede } = useSesion();
  const [recargas, setRecargas] = useState(0);
  const { datos, cargando, error, recargar } = useDatos<PuntoVenta[]>(
    "/puntos-venta?incluir_inactivos=true",
    `${sesion?.finca_activa?.id ?? 0}-${recargas}`,
  );
  const { datos: turnos } = useDatos<Turno[]>(puede("caja", "ver") ? "/caja/turnos?limite=20" : null, recargas);

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<PuntoVenta | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(punto?: PuntoVenta) {
    setFallo("");
    setEditando(punto ?? null);
    setFormulario(
      punto
        ? {
            codigo: punto.codigo,
            nombre: punto.nombre,
            direccion: punto.direccion ?? "",
            finca_id: punto.finca_id ? String(punto.finca_id) : "",
          }
        : { ...VACIO, finca_id: sesion?.finca_activa ? String(sesion.finca_activa.id) : "" },
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
      direccion: formulario.direccion || null,
      finca_id: formulario.finca_id ? Number(formulario.finca_id) : null,
    };
    try {
      if (editando) await api(`/puntos-venta/${editando.id}`, { metodo: "PATCH", cuerpo });
      else await api("/puntos-venta", { metodo: "POST", cuerpo });
      setAbierto(false);
      setRecargas((n) => n + 1);
      await recargar();
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
          <h1 className="text-xl font-semibold text-slate-800">Puntos de venta</h1>
          <p className="text-sm text-slate-500">Puede haber uno por finca y uno o varios centrales</p>
        </div>
        {puede("puntos_venta", "crear") ? <Boton onClick={() => abrir()}>Nuevo punto</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay puntos de venta.</Vacio>
        ) : (
          <Tabla columnas={["Codigo", "Nombre", "Donde", "Numeracion", "Estado", ""]}>
            {datos.map((punto) => (
              <tr key={punto.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{punto.codigo}</td>
                <td className="px-3 py-2">
                  {punto.nombre}
                  {punto.direccion ? <span className="block text-xs text-slate-500">{punto.direccion}</span> : null}
                </td>
                <td className="px-3 py-2">
                  {punto.es_central ? (
                    <Insignia tono="azul">Central</Insignia>
                  ) : (
                    <Insignia>{sesion?.fincas.find((f) => f.id === punto.finca_id)?.nombre ?? "Finca"}</Insignia>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">
                  {punto.prefijo}-{String(punto.consecutivo + 1).padStart(6, "0")}
                </td>
                <td className="px-3 py-2">
                  {punto.activo ? <Insignia tono="verde">Activo</Insignia> : <Insignia>Inactivo</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  {puede("puntos_venta", "editar") ? (
                    <Boton tono="suave" onClick={() => abrir(punto)}>
                      Editar
                    </Boton>
                  ) : null}
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      {turnos && turnos.length > 0 ? (
        <Tarjeta titulo="Turnos de caja">
          <Tabla columnas={["Punto", "Cajero", "Abierto", "Ventas", "Vendido", "Contado", "Diferencia"]}>
            {turnos.map((turno) => (
              <tr key={turno.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">{turno.punto_venta_nombre}</td>
                <td className="px-3 py-2">{turno.usuario_nombre}</td>
                <td className="whitespace-nowrap px-3 py-2 text-xs text-slate-500">
                  {new Date(turno.abierto_en).toLocaleString("es-CO")}
                  {turno.estado === "abierto" ? (
                    <span className="ml-2">
                      <Insignia tono="verde">abierto</Insignia>
                    </span>
                  ) : null}
                </td>
                <td className="px-3 py-2">{turno.ventas}</td>
                <td className="px-3 py-2">{moneda(turno.total_vendido)}</td>
                <td className="px-3 py-2">
                  {turno.efectivo_contado !== null ? moneda(turno.efectivo_contado) : "-"}
                </td>
                <td className="px-3 py-2">
                  {turno.diferencia === null ? (
                    "-"
                  ) : turno.diferencia === 0 ? (
                    <Insignia tono="verde">cuadro</Insignia>
                  ) : (
                    <Insignia tono="rojo">{moneda(turno.diferencia)}</Insignia>
                  )}
                </td>
              </tr>
            ))}
          </Tabla>
        </Tarjeta>
      ) : null}

      <Modal titulo={editando ? "Editar punto" : "Nuevo punto de venta"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Codigo"
              required
              maxLength={10}
              placeholder="PV1"
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
            etiqueta="Direccion"
            value={formulario.direccion}
            onChange={(e) => setFormulario({ ...formulario, direccion: e.target.value })}
          />
          <Lista
            etiqueta="Donde queda"
            value={formulario.finca_id}
            onChange={(e) => setFormulario({ ...formulario, finca_id: e.target.value })}
          >
            <option value="">Central (no es de una finca)</option>
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
