"use client";

import { useSesion } from "@/lib/sesion";
import { CambiarClave } from "@/componentes/cambiar-clave";
import { Aviso, Tarjeta } from "@/componentes/ui";

export default function MiCuenta() {
  const { sesion } = useSesion();
  if (!sesion) return null;

  return (
    <>
      <h1 className="text-xl font-semibold text-slate-800">Mi cuenta</h1>

      <div className="grid gap-5 lg:grid-cols-2">
        <Tarjeta titulo="Mis datos">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Nombre</dt>
              <dd className="font-medium text-slate-800">
                {sesion.usuario.nombres} {sesion.usuario.apellidos}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Correo</dt>
              <dd className="font-medium text-slate-800">{sesion.usuario.email}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Rol</dt>
              <dd className="font-medium text-slate-800">{sesion.usuario.rol_nombre}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Cuenta</dt>
              <dd className="font-medium text-slate-800">{sesion.usuario.cuenta_nombre ?? "Plataforma"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Fincas</dt>
              <dd className="font-medium text-slate-800">{sesion.fincas.map((f) => f.nombre).join(", ")}</dd>
            </div>
          </dl>
        </Tarjeta>

        <Tarjeta titulo="Cambiar contrasena">
          <CambiarClave />
        </Tarjeta>
      </div>

      <Aviso tipo="info">
        Todo lo que registras queda guardado con tu nombre en el registro de cambios.
      </Aviso>
    </>
  );
}
