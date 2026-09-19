"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useDatos, mensajeDeError } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Galpon } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";
import { avisar, useDialogos } from "@/componentes/dialogos";

const TIPOS = [
  { valor: "postura", texto: "Postura" },
  { valor: "levante", texto: "Levante" },
  { valor: "engorde", texto: "Engorde" },
  { valor: "cria", texto: "Cria" },
];

const VACIO = { codigo: "", nombre: "", tipo: "postura", capacidad: 0, observaciones: "" };

export default function Galpones() {
  const { confirmar } = useDialogos();
  const { sesion, puede } = useSesion();
  const [verInactivos, setVerInactivos] = useState(false);
  const ruta = `/galpones?incluir_inactivos=${verInactivos}`;
  const { datos, cargando, error, recargar } = useDatos<Galpon[]>(
    ruta,
    `${sesion?.finca_activa?.id ?? 0}-${verInactivos}`,
  );

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Galpon | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(galpon?: Galpon) {
    setFallo("");
    setEditando(galpon ?? null);
    setFormulario(
      galpon
        ? {
            codigo: galpon.codigo,
            nombre: galpon.nombre,
            tipo: galpon.tipo,
            capacidad: galpon.capacidad,
            observaciones: galpon.observaciones ?? "",
          }
        : VACIO,
    );
    setAbierto(true);
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    const cuerpo = { ...formulario, capacidad: Number(formulario.capacidad) };
    try {
      if (editando) {
        await api(`/galpones/${editando.id}`, { metodo: "PATCH", cuerpo });
      } else {
        await api("/galpones", { metodo: "POST", cuerpo });
      }
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function desactivar(galpon: Galpon) {
    const seguro = await confirmar({
      titulo: `Desactivar ${galpon.nombre}`,
      mensaje: "Deja de aparecer para registrar lotes. Su historial se conserva.",
      aceptar: "Desactivar",
      peligro: true,
    });
    if (!seguro) return;
    try {
      await api(`/galpones/${galpon.id}`, { metodo: "DELETE" });
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Galpones</h1>
          <p className="text-sm text-slate-500">Galpones de {sesion?.finca_activa?.nombre}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={verInactivos} onChange={(e) => setVerInactivos(e.target.checked)} />
            Ver inactivos
          </label>
          {puede("galpones", "crear") ? <Boton onClick={() => abrir()}>Nuevo galpon</Boton> : null}
        </div>
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>Todavia no hay galpones registrados.</Vacio>
        ) : (
          <Tabla columnas={["Codigo", "Nombre", "Tipo", "Capacidad", "Aves", "Estado", ""]}>
            {datos.map((galpon) => (
              <tr key={galpon.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{galpon.codigo}</td>
                <td className="px-3 py-2">{galpon.nombre}</td>
                <td className="px-3 py-2 capitalize">{galpon.tipo}</td>
                <td className="px-3 py-2">{galpon.capacidad.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2">{galpon.aves_actuales.toLocaleString("es-CO")}</td>
                <td className="px-3 py-2">
                  {galpon.activo ? <Insignia tono="verde">Activo</Insignia> : <Insignia tono="gris">Inactivo</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("galpones", "editar") ? (
                      <Boton tono="suave" onClick={() => abrir(galpon)}>
                        Editar
                      </Boton>
                    ) : null}
                    {puede("galpones", "borrar") && galpon.activo ? (
                      <Boton tono="peligro" onClick={() => desactivar(galpon)}>
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

      <Modal titulo={editando ? "Editar galpon" : "Nuevo galpon"} abierto={abierto} onCerrar={() => setAbierto(false)}>
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
            <Lista
              etiqueta="Tipo"
              value={formulario.tipo}
              onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value })}
            >
              {TIPOS.map((tipo) => (
                <option key={tipo.valor} value={tipo.valor}>
                  {tipo.texto}
                </option>
              ))}
            </Lista>
            <Campo
              etiqueta="Capacidad (aves)"
              type="number"
              min={0}
              required
              value={formulario.capacidad}
              onChange={(e) => setFormulario({ ...formulario, capacidad: Number(e.target.value) })}
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
