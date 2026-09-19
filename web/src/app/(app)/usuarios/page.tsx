"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { FincaCompleta, Rol, Usuario } from "@/lib/tipos";
import { Aviso, Boton, Campo, Cargando, Insignia, Lista, Modal, Tabla, Tarjeta, Vacio } from "@/componentes/ui";
import { avisar } from "@/componentes/dialogos";

type Formulario = {
  nombres: string;
  apellidos: string;
  email: string;
  documento: string;
  telefono: string;
  rol: string;
  clave: string;
  fincas: { finca_id: number; solo_lectura: boolean }[];
};

const VACIO: Formulario = {
  nombres: "",
  apellidos: "",
  email: "",
  documento: "",
  telefono: "",
  rol: "operario",
  clave: "",
  fincas: [],
};

export default function Usuarios() {
  const { sesion, puede } = useSesion();
  const { datos, cargando, error, recargar } = useDatos<Usuario[]>("/usuarios");
  const { datos: roles } = useDatos<Rol[]>(puede("roles", "ver") ? "/roles" : null);
  const { datos: fincas } = useDatos<FincaCompleta[]>("/fincas");

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [formulario, setFormulario] = useState<Formulario>(VACIO);
  const [fallo, setFallo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [claveDe, setClaveDe] = useState<Usuario | null>(null);
  const [claveNueva, setClaveNueva] = useState("");

  const rolesDisponibles = roles ?? [
    { id: 0, clave: "supervisor", nombre: "Supervisor", descripcion: null, nivel: 3, de_plataforma: false },
    { id: 0, clave: "operario", nombre: "Operario", descripcion: null, nivel: 4, de_plataforma: false },
    { id: 0, clave: "cajero", nombre: "Cajero", descripcion: null, nivel: 4, de_plataforma: false },
  ];

  function abrir(usuario?: Usuario) {
    setFallo("");
    setEditando(usuario ?? null);
    setFormulario(
      usuario
        ? {
            nombres: usuario.nombres,
            apellidos: usuario.apellidos,
            email: usuario.email,
            documento: usuario.documento ?? "",
            telefono: usuario.telefono ?? "",
            rol: usuario.rol,
            clave: "",
            fincas: usuario.fincas,
          }
        : VACIO,
    );
    setAbierto(true);
  }

  function alternarFinca(fincaId: number) {
    setFormulario((actual) => {
      const existe = actual.fincas.find((f) => f.finca_id === fincaId);
      return {
        ...actual,
        fincas: existe
          ? actual.fincas.filter((f) => f.finca_id !== fincaId)
          : [...actual.fincas, { finca_id: fincaId, solo_lectura: false }],
      };
    });
  }

  function alternarLectura(fincaId: number) {
    setFormulario((actual) => ({
      ...actual,
      fincas: actual.fincas.map((f) =>
        f.finca_id === fincaId ? { ...f, solo_lectura: !f.solo_lectura } : f,
      ),
    }));
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setFallo("");
    try {
      if (editando) {
        const { clave, ...resto } = formulario;
        void clave;
        await api(`/usuarios/${editando.id}`, { metodo: "PATCH", cuerpo: resto });
      } else {
        await api("/usuarios", {
          metodo: "POST",
          cuerpo: { ...formulario, cuenta_id: sesion?.usuario.cuenta_id ?? undefined, debe_cambiar_clave: true },
        });
      }
      setAbierto(false);
      await recargar();
    } catch (error) {
      setFallo(mensajeDeError(error));
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarEstado(usuario: Usuario) {
    try {
      await api(`/usuarios/${usuario.id}`, { metodo: "PATCH", cuerpo: { activo: !usuario.activo } });
      await recargar();
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  async function asignarClave(evento: React.FormEvent) {
    evento.preventDefault();
    if (!claveDe) return;
    try {
      await api(`/usuarios/${claveDe.id}/clave`, {
        metodo: "POST",
        cuerpo: { clave: claveNueva, debe_cambiar_clave: true },
      });
      setClaveDe(null);
      setClaveNueva("");
      avisar.bien("Contrasena asignada. El usuario debera cambiarla al entrar.");
    } catch (error) {
      avisar.error(mensajeDeError(error));
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Usuarios</h1>
          <p className="text-sm text-slate-500">Quien entra al sistema y en que fincas trabaja</p>
        </div>
        {puede("usuarios", "crear") ? <Boton onClick={() => abrir()}>Nuevo usuario</Boton> : null}
      </div>

      {error ? <Aviso>{error}</Aviso> : null}

      <Tarjeta>
        {cargando ? (
          <Cargando />
        ) : !datos || datos.length === 0 ? (
          <Vacio>No hay usuarios registrados.</Vacio>
        ) : (
          <Tabla columnas={["Nombre", "Correo", "Rol", "Fincas", "Estado", ""]}>
            {datos.map((usuario) => (
              <tr key={usuario.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">
                  {usuario.nombres} {usuario.apellidos}
                </td>
                <td className="px-3 py-2">{usuario.email}</td>
                <td className="px-3 py-2">{usuario.rol_nombre}</td>
                <td className="px-3 py-2 text-xs text-slate-500">
                  {usuario.fincas.length === 0
                    ? "Todas las de la cuenta"
                    : usuario.fincas
                        .map((asignada) => {
                          const finca = fincas?.find((f) => f.id === asignada.finca_id);
                          return `${finca?.nombre ?? asignada.finca_id}${asignada.solo_lectura ? " (consulta)" : ""}`;
                        })
                        .join(", ")}
                </td>
                <td className="px-3 py-2">
                  {usuario.activo ? <Insignia tono="verde">Activo</Insignia> : <Insignia tono="gris">Inactivo</Insignia>}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    {puede("usuarios", "editar") ? (
                      <>
                        <Boton tono="suave" onClick={() => abrir(usuario)}>
                          Editar
                        </Boton>
                        <Boton tono="suave" onClick={() => setClaveDe(usuario)}>
                          Contrasena
                        </Boton>
                        <Boton tono={usuario.activo ? "peligro" : "suave"} onClick={() => cambiarEstado(usuario)}>
                          {usuario.activo ? "Desactivar" : "Activar"}
                        </Boton>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </Tarjeta>

      <Modal titulo={editando ? "Editar usuario" : "Nuevo usuario"} abierto={abierto} onCerrar={() => setAbierto(false)}>
        <form onSubmit={guardar} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Nombres"
              required
              value={formulario.nombres}
              onChange={(e) => setFormulario({ ...formulario, nombres: e.target.value })}
            />
            <Campo
              etiqueta="Apellidos"
              value={formulario.apellidos}
              onChange={(e) => setFormulario({ ...formulario, apellidos: e.target.value })}
            />
            <Campo
              etiqueta="Correo"
              type="email"
              required
              value={formulario.email}
              onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
            />
            <Campo
              etiqueta="Documento"
              value={formulario.documento}
              onChange={(e) => setFormulario({ ...formulario, documento: e.target.value })}
            />
            <Campo
              etiqueta="Telefono"
              value={formulario.telefono}
              onChange={(e) => setFormulario({ ...formulario, telefono: e.target.value })}
            />
            <Lista
              etiqueta="Rol"
              value={formulario.rol}
              onChange={(e) => setFormulario({ ...formulario, rol: e.target.value })}
            >
              {rolesDisponibles.map((rol) => (
                <option key={rol.clave} value={rol.clave}>
                  {rol.nombre}
                </option>
              ))}
            </Lista>
          </div>

          {!editando ? (
            <Campo
              etiqueta="Contrasena inicial (minimo 8 caracteres)"
              type="text"
              minLength={8}
              required
              value={formulario.clave}
              onChange={(e) => setFormulario({ ...formulario, clave: e.target.value })}
            />
          ) : null}

          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Fincas donde trabaja</p>
            <p className="mb-2 text-xs text-slate-500">
              Si no marcas ninguna y el rol es administrador o propietario, vera todas las fincas de la cuenta.
            </p>
            <div className="space-y-2 rounded-lg border border-slate-200 p-3">
              {(fincas ?? []).map((finca) => {
                const asignada = formulario.fincas.find((f) => f.finca_id === finca.id);
                return (
                  <div key={finca.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={Boolean(asignada)} onChange={() => alternarFinca(finca.id)} />
                      {finca.nombre}
                    </label>
                    {asignada ? (
                      <label className="flex items-center gap-2 text-xs text-slate-500">
                        <input
                          type="checkbox"
                          checked={asignada.solo_lectura}
                          onChange={() => alternarLectura(finca.id)}
                        />
                        solo consulta
                      </label>
                    ) : null}
                  </div>
                );
              })}
            </div>
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

      <Modal
        titulo={`Contrasena de ${claveDe?.nombres ?? ""}`}
        abierto={Boolean(claveDe)}
        onCerrar={() => setClaveDe(null)}
      >
        <form onSubmit={asignarClave} className="space-y-4">
          <Campo
            etiqueta="Contrasena nueva (minimo 8 caracteres)"
            type="text"
            minLength={8}
            required
            value={claveNueva}
            onChange={(e) => setClaveNueva(e.target.value)}
          />
          <Aviso tipo="info">Al guardar se cierran las sesiones abiertas de ese usuario.</Aviso>
          <div className="flex justify-end gap-2">
            <Boton type="button" tono="suave" onClick={() => setClaveDe(null)}>
              Cancelar
            </Boton>
            <Boton type="submit">Guardar</Boton>
          </div>
        </form>
      </Modal>
    </>
  );
}
