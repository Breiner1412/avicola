"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { FincaCompleta } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const VACIO = { codigo: "", nombre: "", municipio: "", departamento: "", direccion: "", telefono: "" };

export default function Fincas() {
  const { sesion, puede, recargar: recargarSesion } = useSesion();
  const { datos, cargando, error, recargar } = useDatos<FincaCompleta[]>("/fincas");

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<FincaCompleta | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(finca?: FincaCompleta) {
    setFallo("");
    setEditando(finca ?? null);
    setFormulario(
      finca
        ? {
            codigo: finca.codigo,
            nombre: finca.nombre,
            municipio: finca.municipio ?? "",
            departamento: finca.departamento ?? "",
            direccion: finca.direccion ?? "",
            telefono: finca.telefono ?? "",
          }
        : VACIO,
    );
    setAbierto(true);
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      if (editando) {
        await api(`/fincas/${editando.id}`, { metodo: "PATCH", cuerpo: formulario });
      } else {
        await api("/fincas", {
          metodo: "POST",
          cuerpo: { ...formulario, cuenta_id: sesion?.usuario.cuenta_id ?? undefined },
        });
      }
      setAbierto(false);
      await recargar();
      await recargarSesion();
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
          <h1 className="text-xl font-semibold text-slate-800">Fincas</h1>
          <p className="text-sm text-slate-500">Fincas a las que tienes acceso</p>
        </div>
        {puede("fincas", "crear") ? <Boton onClick={() => abrir()}>Nueva finca</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay fincas registradas.</Vacio>
        ) : (
          <Tabla columnas={["Codigo", "Nombre", "Municipio", "Telefono", "Estado", ""]}>
            {datos.map((finca) => (
              <tr key={finca.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{finca.codigo}</td>
                <td className="px-3 py-2">{finca.nombre}</td>
                <td className="px-3 py-2">
                  {finca.municipio ?? "-"}
                  {finca.departamento ? `, ${finca.departamento}` : ""}
                </td>
                <td className="px-3 py-2">{finca.telefono ?? "-"}</td>
                <td className="px-3 py-2">
                  {finca.activo ? <Insignia tono="verde">Activa</Insignia> : <Insignia tono="gris">Inactiva</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  {puede("fincas", "editar") ? (
                    <Boton tono="suave" onClick={() => abrir(finca)}>
                      Editar
                    </Boton>
                  ) : null}
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar finca" : "Nueva finca"} abierto={abierto} onCerrar={() => setAbierto(false)}>
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
            <Campo
              etiqueta="Municipio"
              value={formulario.municipio}
              onChange={(e) => setFormulario({ ...formulario, municipio: e.target.value })}
            />
            <Campo
              etiqueta="Departamento"
              value={formulario.departamento}
              onChange={(e) => setFormulario({ ...formulario, departamento: e.target.value })}
            />
            <Campo
              etiqueta="Direccion"
              value={formulario.direccion}
              onChange={(e) => setFormulario({ ...formulario, direccion: e.target.value })}
            />
            <Campo
              etiqueta="Telefono"
              value={formulario.telefono}
              onChange={(e) => setFormulario({ ...formulario, telefono: e.target.value })}
            />
          </div>

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
