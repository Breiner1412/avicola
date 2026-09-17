"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSesion } from "@/lib/sesion";
import { GRUPOS } from "@/lib/menu";
import { CambiarClave } from "@/componentes/cambiar-clave";
import { Aviso, Boton, Cargando, Insignia, Tarjeta } from "@/componentes/ui";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { sesion, cargando, salir, elegirFinca, puede } = useSesion();
  const router = useRouter();
  const ruta = usePathname();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [cambiandoFinca, setCambiandoFinca] = useState(false);

  useEffect(() => {
    if (!cargando && !sesion) router.replace("/login");
  }, [cargando, sesion, router]);

  if (cargando || !sesion) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Cargando />
      </main>
    );
  }

  if (sesion.usuario.debe_cambiar_clave) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
        <div className="w-full max-w-md">
          <Tarjeta titulo="Cambia tu contrasena">
            <CambiarClave obligatorio />
          </Tarjeta>
        </div>
      </main>
    );
  }

  if (!sesion.finca_activa) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
        <div className="w-full max-w-md space-y-4">
          <Tarjeta titulo="Elige la finca">
            {sesion.fincas.length === 0 ? (
              <Aviso>Todavia no tienes fincas asignadas. Habla con el administrador.</Aviso>
            ) : (
              <ul className="space-y-2">
                {sesion.fincas.map((finca) => (
                  <li key={finca.id}>
                    <button
                      onClick={() => elegirFinca(finca.id)}
                      className="flex w-full items-center justify-between rounded-lg border border-slate-200 px-4 py-3 text-left hover:border-emerald-600 hover:bg-emerald-50"
                    >
                      <span>
                        <span className="block font-medium text-slate-800">{finca.nombre}</span>
                        <span className="block text-xs text-slate-500">
                          {finca.codigo}
                          {finca.municipio ? ` · ${finca.municipio}` : ""}
                        </span>
                      </span>
                      {finca.solo_lectura ? <Insignia tono="azul">Solo consulta</Insignia> : null}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4">
              <Boton tono="suave" onClick={() => salir()}>
                Salir
              </Boton>
            </div>
          </Tarjeta>
        </div>
      </main>
    );
  }

  const grupos = GRUPOS.map((grupo) => ({
    ...grupo,
    enlaces: grupo.enlaces.filter((enlace) => puede(enlace.modulo, "ver")),
  })).filter((grupo) => grupo.enlaces.length > 0);

  return (
    <div className="flex min-h-screen">
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform bg-emerald-900 text-emerald-50 transition-transform lg:static lg:translate-x-0 ${
          menuAbierto ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center px-5 text-lg font-bold tracking-tight">AVISENA</div>
        <nav className="space-y-6 px-3 py-4">
          {grupos.map((grupo) => (
            <div key={grupo.titulo}>
              <p className="px-3 pb-1 text-xs uppercase tracking-wide text-emerald-300/80">{grupo.titulo}</p>
              <ul className="space-y-1">
                {grupo.enlaces.map((enlace) => {
                  const activo = ruta.startsWith(enlace.ruta);
                  return (
                    <li key={enlace.ruta}>
                      <Link
                        href={enlace.ruta}
                        onClick={() => setMenuAbierto(false)}
                        className={`block rounded-lg px-3 py-2 text-sm ${
                          activo ? "bg-emerald-700 font-medium text-white" : "text-emerald-100 hover:bg-emerald-800"
                        }`}
                      >
                        {enlace.etiqueta}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              className="rounded p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
              onClick={() => setMenuAbierto((v) => !v)}
              aria-label="Menu"
            >
              ☰
            </button>
            <div>
              <p className="text-sm font-semibold text-slate-800">{sesion.finca_activa.nombre}</p>
              <p className="text-xs text-slate-500">
                {sesion.usuario.cuenta_nombre ?? "Plataforma"}
                {sesion.finca_activa.solo_lectura ? " · solo consulta" : ""}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {sesion.fincas.length > 1 ? (
              <select
                value={sesion.finca_activa.id}
                disabled={cambiandoFinca}
                onChange={async (e) => {
                  setCambiandoFinca(true);
                  try {
                    await elegirFinca(Number(e.target.value));
                  } finally {
                    setCambiandoFinca(false);
                  }
                }}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
              >
                {sesion.fincas.map((finca) => (
                  <option key={finca.id} value={finca.id}>
                    {finca.nombre}
                    {finca.solo_lectura ? " (consulta)" : ""}
                  </option>
                ))}
              </select>
            ) : null}

            <Link href="/mi-cuenta" className="hidden text-sm text-slate-600 hover:text-emerald-700 sm:block">
              {sesion.usuario.nombres}
            </Link>
            <Boton tono="suave" onClick={() => salir()}>
              Salir
            </Boton>
          </div>
        </header>

        <main className="flex-1 space-y-5 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
