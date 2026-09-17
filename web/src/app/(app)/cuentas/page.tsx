"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Cuenta } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";

const VACIO = { tipo: "empresa", nombre: "", documento: "", email_contacto: "", telefono: "" };

export default function Cuentas() {
  const { puede } = useSesion();
  const { datos, cargando, error, recargar } = useDatos<Cuenta[]>("/cuentas");

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Cuenta | null>(null);
  const [formulario, setFormulario] = useState(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir(cuenta?: Cuenta) {
    setFallo("");
    setEditando(cuenta ?? null);
    setFormulario(
      cuenta
        ? {
            tipo: cuenta.tipo,
            nombre: cuenta.nombre,
            documento: cuenta.documento ?? "",
            email_contacto: cuenta.email_contacto ?? "",
            telefono: cuenta.telefono ?? "",
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
      ...formulario,
      documento: formulario.documento || null,
      email_contacto: formulario.email_contacto || null,
      telefono: formulario.telefono || null,
    };
    try {
      if (editando) {
        await api(`/cuentas/${editando.id}`, { metodo: "PATCH", cuerpo });
      } else {
        await api("/cuentas", { metodo: "POST", cuerpo });
      }
      setAbierto(false);
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
          <h1 className="text-xl font-semibold text-slate-800">Cuentas</h1>
          <p className="text-sm text-slate-500">Empresas o personas que usan el sistema</p>
        </div>
        {puede("cuentas", "crear") ? <Boton onClick={() => abrir()}>Nueva cuenta</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay cuentas registradas.</Vacio>
        ) : (
          <Tabla columnas={["Nombre", "Tipo", "Documento", "Contacto", "Estado", ""]}>
            {datos.map((cuenta) => (
              <tr key={cuenta.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">{cuenta.nombre}</td>
                <td className="px-3 py-2 capitalize">{cuenta.tipo}</td>
                <td className="px-3 py-2">{cuenta.documento ?? "-"}</td>
                <td className="px-3 py-2">{cuenta.email_contacto ?? cuenta.telefono ?? "-"}</td>
                <td className="px-3 py-2">
                  {cuenta.activo ? <Insignia tono="verde">Activa</Insignia> : <Insignia tono="gris">Inactiva</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  {puede("cuentas", "editar") ? (
                    <Boton tono="suave" onClick={() => abrir(cuenta)}>
                      Editar
                    </Boton>
                  ) : null}
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar cuenta" : "Nueva cuenta"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <Lista etiqueta="Tipo" value={formulario.tipo} onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value })}>
            <option value="empresa">Empresa</option>
            <option value="persona">Persona</option>
          </Lista>
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
            etiqueta="Correo de contacto"
            type="email"
            value={formulario.email_contacto}
            onChange={(e) => setFormulario({ ...formulario, email_contacto: e.target.value })}
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
