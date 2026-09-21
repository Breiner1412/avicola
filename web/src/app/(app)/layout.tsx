"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSesion } from "@/lib/sesion";
import { GRUPOS } from "@/lib/menu";
import { CambiarClave } from "@/componentes/cambiar-clave";
import { Campana } from "@/componentes/campana";
import { Icono } from "@/componentes/iconos";
import { MenuLateral } from "@/componentes/menu-lateral";
import { Aviso, Boton, Cargando, Insignia, Tarjeta } from "@/componentes/ui";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { sesion, cargando, salir, elegirFinca, puede } = useSesion();
  const router = useRouter();
  const ruta = usePathname();
  const [menuAbierto, setMenuAbierto] = useState(false);
  // En pantallas grandes el menu se puede dejar fijo al lado; si no, se abre encima.
  const [menuFijo, setMenuFijo] = useState(false);
  const [usuarioAbierto, setUsuarioAbierto] = useState(false);
  const [cambiandoFinca, setCambiandoFinca] = useState(false);
  const cajaUsuario = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!cargando && !sesion) router.replace("/login");
  }, [cargando, sesion, router]);

  // Recuerda si el menu quedo fijo en el computador.
  useEffect(() => {
    try {
      if (localStorage.getItem("avicola.menu.fijo") === "1") setMenuFijo(true);
    } catch {}
  }, []);

  // En el celular: Esc cierra el menu y la pagina de atras no se mueve.
  useEffect(() => {
    if (!menuAbierto) return;
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setMenuAbierto(false);
    document.addEventListener("keydown", tecla);
    const antes = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", tecla);
      document.body.style.overflow = antes;
    };
  }, [menuAbierto]);

  useEffect(() => {
    function fuera(evento: MouseEvent) {
      if (cajaUsuario.current && !cajaUsuario.current.contains(evento.target as Node)) setUsuarioAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  if (cargando || !sesion) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <Cargando />
      </main>
    );
  }

  if (sesion.usuario.debe_cambiar_clave) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-md">
          <Tarjeta titulo="Cambia tu contrasena" icono="llave">
            <CambiarClave obligatorio />
          </Tarjeta>
        </div>
      </main>
    );
  }

  if (!sesion.finca_activa) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-md space-y-4">
          <Tarjeta titulo="Elige la finca" descripcion="Donde vas a trabajar hoy" icono="finca">
            {sesion.fincas.length === 0 ? (
              <Aviso>Todavia no tienes fincas asignadas. Habla con el administrador.</Aviso>
            ) : (
              <ul className="space-y-2">
                {sesion.fincas.map((finca) => (
                  <li key={finca.id}>
                    <button
                      onClick={() => elegirFinca(finca.id)}
                      className="flex w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left ring-1 ring-slate-200 transition hover:bg-emerald-50 hover:ring-emerald-600"
                    >
                      <span className="flex items-center gap-3">
                        <span className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                          <Icono nombre="finca" className="h-4 w-4" />
                        </span>
                        <span>
                          <span className="block font-medium text-slate-800">{finca.nombre}</span>
                          <span className="block text-xs text-slate-500">
                            {finca.codigo}
                            {finca.municipio ? ` · ${finca.municipio}` : ""}
                          </span>
                        </span>
                      </span>
                      {finca.solo_lectura ? <Insignia tono="azul">Solo consulta</Insignia> : null}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4">
              <Boton tono="suave" icono="salir" onClick={() => salir()}>
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

  const iniciales = `${sesion.usuario.nombres[0] ?? ""}${sesion.usuario.apellidos[0] ?? ""}`.toUpperCase();

  function fijarMenu(fijo: boolean) {
    setMenuFijo(fijo);
    setMenuAbierto(false);
    try {
      localStorage.setItem("avicola.menu.fijo", fijo ? "1" : "0");
    } catch {}
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Fondo oscuro detras del menu cuando esta abierto encima de la pagina */}
      <div
        aria-hidden="true"
        onClick={() => setMenuAbierto(false)}
        className={`fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-[1px] transition-opacity duration-200 ${
          menuAbierto ? "opacity-100" : "pointer-events-none opacity-0"
        } ${menuFijo ? "lg:hidden" : ""}`}
      />

      <aside
        aria-label="Menu principal"
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-emerald-950 text-emerald-50 transition-transform duration-200 ease-out ${
          menuAbierto ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        } ${menuFijo ? "lg:translate-x-0 lg:shadow-none" : ""}`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-2 px-4">
          <Link href="/panel" className="flex items-center gap-2.5 pl-1" onClick={() => setMenuAbierto(false)}>
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-500/15 text-emerald-300">
              <Icono nombre="huevo" className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-tight">Avícola</span>
          </Link>
          <div className="flex items-center gap-1">
            <button
              onClick={() => fijarMenu(!menuFijo)}
              aria-label={menuFijo ? "Soltar el menu" : "Dejar el menu fijo"}
              title={menuFijo ? "Ocultar el menu" : "Dejar el menu fijo al lado"}
              className="hidden rounded-lg p-1.5 text-emerald-300 transition hover:bg-emerald-900 hover:text-white lg:block"
            >
              <Icono nombre={menuFijo ? "izquierda" : "fijar"} className="h-4 w-4" />
            </button>
            <button
              onClick={() => setMenuAbierto(false)}
              aria-label="Cerrar el menu"
              title="Cerrar"
              className={`rounded-lg p-1.5 text-emerald-300 transition hover:bg-emerald-900 hover:text-white ${menuFijo ? "lg:hidden" : ""}`}
            >
              <Icono nombre="cerrar" className="h-4 w-4" />
            </button>
          </div>
        </div>

        <MenuLateral grupos={grupos} ruta={ruta} alNavegar={() => setMenuAbierto(false)} />

        <div className="shrink-0 border-t border-emerald-900 px-5 py-3 text-[11px] text-emerald-300/70">
          {sesion.usuario.cuenta_nombre ?? "Plataforma"}
        </div>
      </aside>

      <div className={`flex min-h-screen min-w-0 flex-col transition-[padding] duration-200 ${menuFijo ? "lg:pl-64" : ""}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              className={`rounded-xl p-2 text-slate-600 transition hover:bg-slate-100 ${menuFijo ? "lg:hidden" : ""}`}
              onClick={() => setMenuAbierto(true)}
              aria-label="Menu"
              aria-expanded={menuAbierto}
              title="Abrir el menu"
            >
              <Icono nombre="menu" className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-800">{sesion.finca_activa.nombre}</p>
              <p className="truncate text-xs text-slate-500">
                {sesion.usuario.rol_nombre}
                {sesion.finca_activa.solo_lectura ? " · solo consulta" : ""}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
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
                className="max-w-[9rem] rounded-xl border-0 bg-white px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-300 focus:ring-2 focus:ring-emerald-600 sm:max-w-none"
              >
                {sesion.fincas.map((finca) => (
                  <option key={finca.id} value={finca.id}>
                    {finca.nombre}
                    {finca.solo_lectura ? " (consulta)" : ""}
                  </option>
                ))}
              </select>
            ) : null}

            <Campana fincaId={sesion.finca_activa.id} />

            <div className="relative" ref={cajaUsuario}>
              <button
                onClick={() => setUsuarioAbierto((v) => !v)}
                className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-slate-100"
                aria-label="Mi cuenta"
              >
                <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-700 text-xs font-semibold text-white">
                  {iniciales || "AV"}
                </span>
                <span className="hidden text-sm text-slate-700 sm:block">{sesion.usuario.nombres}</span>
              </button>

              {usuarioAbierto ? (
                <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
                  <div className="border-b border-slate-100 px-4 py-3">
                    <p className="text-sm font-medium text-slate-800">
                      {sesion.usuario.nombres} {sesion.usuario.apellidos}
                    </p>
                    <p className="truncate text-xs text-slate-500">{sesion.usuario.email}</p>
                  </div>
                  <Link
                    href="/mi-cuenta"
                    onClick={() => setUsuarioAbierto(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    <Icono nombre="usuario" className="h-4 w-4 text-slate-400" />
                    Mi cuenta
                  </Link>
                  <Link
                    href="/alertas"
                    onClick={() => setUsuarioAbierto(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    <Icono nombre="campana" className="h-4 w-4 text-slate-400" />
                    Avisos
                  </Link>
                  <button
                    onClick={() => salir()}
                    className="flex w-full items-center gap-2.5 border-t border-slate-100 px-4 py-2.5 text-left text-sm text-rose-700 hover:bg-rose-50"
                  >
                    <Icono nombre="salir" className="h-4 w-4" />
                    Cerrar sesion
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="flex-1 space-y-5 p-4 pb-16 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
