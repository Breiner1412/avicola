"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Proveedor } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const VACIO = { nombre: "", documento: "", telefono: "", email: "", direccion: "" };

export default function Proveedores() {
  const { puede } = useSesion();
  const { datos, cargando, error, recargar } = useDatos<Proveedor[]>("/proveedores?incluir_inactivos=true");

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Proveedor | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(proveedor?: Proveedor) {
    setFallo("");
    setEditando(proveedor ?? null);
    setFormulario(
      proveedor
        ? {
            nombre: proveedor.nombre,
            documento: proveedor.documento ?? "",
            telefono: proveedor.telefono ?? "",
            email: proveedor.email ?? "",
            direccion: proveedor.direccion ?? "",
          }
        : VACIO,
    );
    setAbierto(true);
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    const cuerpo = {
      nombre: formulario.nombre,
      documento: formulario.documento || null,
      telefono: formulario.telefono || null,
      email: formulario.email || null,
      direccion: formulario.direccion || null,
    };
    try {
      if (editando) await api(`/proveedores/${editando.id}`, { metodo: "PATCH", cuerpo });
      else await api("/proveedores", { metodo: "POST", cuerpo });
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarEstado(proveedor: Proveedor) {
    try {
      if (proveedor.activo) await api(`/proveedores/${proveedor.id}`, { metodo: "DELETE" });
      else await api(`/proveedores/${proveedor.id}`, { metodo: "PATCH", cuerpo: { activo: true } });
      await recargar();
    } catch (error) {
      alert(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Proveedores</h1>
          <p className="text-sm text-slate-500">A quien se le compra el alimento, las vacunas y los insumos</p>
        </div>
        {puede("proveedores", "crear") ? <Boton onClick={() => abrir()}>Nuevo proveedor</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay proveedores registrados.</Vacio>
        ) : (
          <Tabla columnas={["Nombre", "Documento", "Telefono", "Correo", "Estado", ""]}>
            {datos.map((proveedor) => (
              <tr key={proveedor.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{proveedor.nombre}</td>
                <td className="px-3 py-2">{proveedor.documento ?? "-"}</td>
                <td className="px-3 py-2">{proveedor.telefono ?? "-"}</td>
                <td className="px-3 py-2">{proveedor.email ?? "-"}</td>
                <td className="px-3 py-2">
                  {proveedor.activo ? <Insignia tono="verde">Activo</Insignia> : <Insignia>Inactivo</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("proveedores", "editar") ? (
                      <Boton tono="suave" onClick={() => abrir(proveedor)}>
                        Editar
                      </Boton>
                    ) : null}
                    {puede("proveedores", "borrar") ? (
                      <Boton tono={proveedor.activo ? "peligro" : "suave"} onClick={() => cambiarEstado(proveedor)}>
                        {proveedor.activo ? "Desactivar" : "Activar"}
                      </Boton>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar proveedor" : "Nuevo proveedor"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <Campo
            etiqueta="Nombre"
            required
            value={formulario.nombre}
            onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Documento (NIT o cedula)"
              value={formulario.documento}
              onChange={(e) => setFormulario({ ...formulario, documento: e.target.value })}
            />
            <Campo
              etiqueta="Telefono"
              value={formulario.telefono}
              onChange={(e) => setFormulario({ ...formulario, telefono: e.target.value })}
            />
          </div>
          <Campo
            etiqueta="Correo"
            type="email"
            value={formulario.email}
            onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
          />
          <Campo
            etiqueta="Direccion"
            value={formulario.direccion}
            onChange={(e) => setFormulario({ ...formulario, direccion: e.target.value })}
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
