"use client";

import { useSesion } from "@/lib/sesion";
import { CambiarClave } from "@/componentes/cambiar-clave";
import { Aviso, Tarjeta } from "@/componentes/ui";

export default function MiCuenta() {
  const { sesion } = useSesion();
  if (!sesion) return null;

  return (
    <>
      <h1 className="titulo-pantalla">Mi cuenta</h1>

      <div className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
        <Tarjeta titulo="Mis datos">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-tinta-2">Nombre</dt>
              <dd className="font-medium text-tinta">
                {sesion.usuario.nombres} {sesion.usuario.apellidos}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-tinta-2">Correo</dt>
              <dd className="font-medium text-tinta">{sesion.usuario.email}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-tinta-2">Rol</dt>
              <dd className="font-medium text-tinta">{sesion.usuario.rol_nombre}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-tinta-2">Cuenta</dt>
              <dd className="font-medium text-tinta">{sesion.usuario.cuenta_nombre ?? "Plataforma"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-tinta-2">Fincas</dt>
              <dd className="font-medium text-tinta">{sesion.fincas.map((f) => f.nombre).join(", ")}</dd>
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
