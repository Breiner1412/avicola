"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Galpon, Lote, Raza } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const PROPOSITOS = [
  { valor: "postura", texto: "Postura (huevos)" },
  { valor: "engorde", texto: "Engorde (carne)" },
  { valor: "levante", texto: "Levante (pollitas)" },
];

function hoy() {
  return new Date().toISOString().slice(0, 10);
}

const VACIO = {
  codigo: "",
  galpon_id: "",
  raza_id: "",
  proposito: "postura",
  fecha_ingreso: hoy(),
  edad_dias_ingreso: "1",
  aves_iniciales: "",
  costo_ave: "",
  observaciones: "",
};

export default function Lotes() {
  const { sesion, puede } = useSesion();
  const [soloActivos, setSoloActivos] = useState(true);
  const ruta = `/lotes?solo_activos=${soloActivos}`;
  const { datos, cargando, error, recargar } = useDatos<Lote[]>(ruta, `${sesion?.finca_activa?.id ?? 0}-${soloActivos}`);
  const { datos: galpones } = useDatos<Galpon[]>("/galpones", sesion?.finca_activa?.id ?? 0);
  const { datos: razas } = useDatos<Raza[]>("/razas");

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      await api("/lotes", {
        metodo: "POST",
        cuerpo: {
          codigo: formulario.codigo,
          galpon_id: Number(formulario.galpon_id),
          raza_id: formulario.raza_id ? Number(formulario.raza_id) : null,
          proposito: formulario.proposito,
          fecha_ingreso: formulario.fecha_ingreso,
          edad_dias_ingreso: Number(formulario.edad_dias_ingreso || 1),
          aves_iniciales: Number(formulario.aves_iniciales),
          costo_ave: Number(formulario.costo_ave || 0),
          observaciones: formulario.observaciones || null,
        },
      });
      setAbierto(false);
      setFormulario(VACIO);
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
          <h1 className="text-xl font-semibold text-slate-800">Lotes de aves</h1>
          <p className="text-sm text-slate-500">Cada grupo de aves que entra a un galpon, con su historia</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)} />
            Solo activos
          </label>
          {puede("lotes", "crear") ? <Boton onClick={() => setAbierto(true)}>Ingresar lote</Boton> : null}
        </div>
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>Todavia no hay lotes registrados.</Vacio>
        ) : (
          <Tabla columnas={["Lote", "Galpon", "Proposito", "Edad", "Aves", "Descarte", "Mortalidad", ""]}>
            {datos.map((lote) => (
              <tr key={lote.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  <span className="font-medium text-slate-700">{lote.codigo}</span>
                  <span className="block text-xs text-slate-500">{lote.raza_nombre ?? "sin raza"}</span>
                </td>
                <td className="px-3 py-2">{lote.galpon_nombre}</td>
                <td className="px-3 py-2 capitalize">{lote.proposito}</td>
                <td className="px-3 py-2">
                  {lote.edad_semanas} sem
                  <span className="block text-xs text-slate-400">{lote.edad_dias} dias</span>
                </td>
                <td className="px-3 py-2">{lote.aves_actuales.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2">{lote.aves_descarte.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2">
                  {lote.mortalidad.toLocaleString("es-CO")}
                  <span className="block text-xs text-slate-400">{lote.mortalidad_porcentaje}%</span>
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {lote.estado === "cerrado" ? <Insignia>Cerrado</Insignia> : null}
                    <Link
                      href={`/lotes/${lote.id}`}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
                    >
                      Abrir
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo="Ingresar un lote" abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Codigo del lote"
              required
              placeholder="L1"
              value={formulario.codigo}
              onChange={(e) => setFormulario({ ...formulario, codigo: e.target.value })}
            />
            <Lista
              etiqueta="Galpon"
              required
              value={formulario.galpon_id}
              onChange={(e) => setFormulario({ ...formulario, galpon_id: e.target.value })}
            >
              <option value="">Elige un galpon</option>
              {(galpones ?? []).map((galpon) => (
                <option key={galpon.id} value={galpon.id}>
                  {galpon.nombre} ({galpon.aves_actuales}/{galpon.capacidad})
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Proposito"
              value={formulario.proposito}
              onChange={(e) => setFormulario({ ...formulario, proposito: e.target.value })}
            >
              {PROPOSITOS.map((p) => (
                <option key={p.valor} value={p.valor}>
                  {p.texto}
                </option>
              ))}
            </Lista>
            <Lista
              etiqueta="Raza"
              value={formulario.raza_id}
              onChange={(e) => setFormulario({ ...formulario, raza_id: e.target.value })}
            >
              <option value="">Sin especificar</option>
              {(razas ?? []).map((raza) => (
                <option key={raza.id} value={raza.id}>
                  {raza.nombre}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Fecha de ingreso"
              type="date"
              required
              value={formulario.fecha_ingreso}
              onChange={(e) => setFormulario({ ...formulario, fecha_ingreso: e.target.value })}
            />
            <Campo
              etiqueta="Edad al ingresar (dias)"
              type="number"
              min={0}
              value={formulario.edad_dias_ingreso}
              onChange={(e) => setFormulario({ ...formulario, edad_dias_ingreso: e.target.value })}
            />
            <Campo
              etiqueta="Cuantas aves entran"
              type="number"
              min={1}
              required
              value={formulario.aves_iniciales}
              onChange={(e) => setFormulario({ ...formulario, aves_iniciales: e.target.value })}
            />
            <Campo
              etiqueta="Costo por ave"
              type="number"
              min={0}
              value={formulario.costo_ave}
              onChange={(e) => setFormulario({ ...formulario, costo_ave: e.target.value })}
            />
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
