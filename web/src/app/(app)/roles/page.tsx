"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { mensajeDeError, useDatos } from "@/lib/hooks";
import { useSesion } from "@/lib/sesion";
import type { Acciones, Permisos } from "@/lib/tipos";
import { Aviso, Cargando, Tarjeta } from "@/componentes/ui";

type Matriz = Record<string, Permisos>;
type Modulo = { id: number; clave: string; nombre: string; grupo: string; orden: number };
type Rol = { id: number; clave: string; nombre: string; nivel: number; de_plataforma: boolean };

const ACCIONES: (keyof Acciones)[] = ["ver", "crear", "editar", "borrar"];

export default function Roles() {
  const { puede } = useSesion();
  const { datos: modulos } = useDatos<Modulo[]>("/modulos");
  const { datos: roles } = useDatos<Rol[]>("/roles");
  const { datos: matrizInicial, cargando, error } = useDatos<Matriz>("/permisos");

  const [matriz, setMatriz] = useState<Matriz>({});
  const [aviso, setAviso] = useState("");
  const editable = puede("roles", "editar");

  useEffect(() => {
    if (matrizInicial) setMatriz(matrizInicial);
  }, [matrizInicial]);

  async function alternar(rol: string, modulo: string, accion: keyof Acciones) {
    const actuales: Acciones = matriz[rol]?.[modulo] ?? { ver: false, crear: false, editar: false, borrar: false };
    const nuevos: Acciones = { ...actuales, [accion]: !actuales[accion] };
    if (accion !== "ver" && nuevos[accion]) nuevos.ver = true;
    if (accion === "ver" && !nuevos.ver) {
      nuevos.crear = false;
      nuevos.editar = false;
      nuevos.borrar = false;
    }

    setMatriz((actual) => ({ ...actual, [rol]: { ...(actual[rol] ?? {}), [modulo]: nuevos } }));
    setAviso("");
    try {
      await api(`/permisos/${rol}/${modulo}`, { metodo: "PUT", cuerpo: nuevos });
    } catch (fallo) {
      setAviso(mensajeDeError(fallo));
      setMatriz((actual) => ({ ...actual, [rol]: { ...(actual[rol] ?? {}), [modulo]: actuales } }));
    }
  }

  if (cargando) return <Cargando />;

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Roles y permisos</h1>
        <p className="text-sm text-slate-500">
          Marca lo que puede hacer cada rol. Los cambios se guardan al instante.
        </p>
      </div>

      {error ? <Aviso>{error}</Aviso> : null}
      {aviso ? <Aviso>{aviso}</Aviso> : null}
      {!editable ? <Aviso tipo="info">Solo puedes consultar esta informacion.</Aviso> : null}

      {(roles ?? []).map((rol) => (
        <Tarjeta key={rol.clave} titulo={rol.nombre}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Modulo</th>
                  {ACCIONES.map((accion) => (
                    <th key={accion} className="px-3 py-2 text-center capitalize">
                      {accion}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(modulos ?? []).map((modulo) => {
                  const permisos = matriz[rol.clave]?.[modulo.clave];
                  return (
                    <tr key={modulo.clave}>
                      <td className="px-3 py-1.5">
                        {modulo.nombre}
                        <span className="ml-2 text-xs text-slate-400">{modulo.grupo}</span>
                      </td>
                      {ACCIONES.map((accion) => (
                        <td key={accion} className="px-3 py-1.5 text-center">
                          <input
                            type="checkbox"
                            disabled={!editable}
                            checked={Boolean(permisos?.[accion])}
                            onChange={() => alternar(rol.clave, modulo.clave, accion)}
                          />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Tarjeta>
      ))}
    </>
  );
}
