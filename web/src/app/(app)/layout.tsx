"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSesion } from "@/lib/sesion";
import { GRUPOS, moduloDeRuta } from "@/lib/menu";
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
      <main className="flex min-h-screen items-center justify-center bg-cal">
        <Cargando />
      </main>
    );
  }

  // En la demo no se pueden cambiar claves: no se obliga a hacerlo
  if (sesion.usuario.debe_cambiar_clave && !sesion.demo) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-cal px-4">
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
      <main className="flex min-h-screen items-center justify-center bg-cal px-4">
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
                      className="flex min-h-16 w-full items-center justify-between gap-3 rounded-lg border-[1.5px] border-linea bg-superficie px-4 py-3 text-left transition hover:border-galpon hover:bg-cal"
                    >
                      <span className="flex items-center gap-3">
                        <span className="grid h-10 w-10 place-items-center rounded-lg bg-cal text-galpon">
                          <Icono nombre="finca" className="h-5 w-5" />
                        </span>
                        <span>
                          <span className="block font-semibold text-tinta">{finca.nombre}</span>
                          <span className="block text-sm text-tinta-2">
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

  // La API ya rechaza lo que el rol no puede ver; aqui ademas no se abre la pantalla
  const moduloActual = moduloDeRuta(ruta);
  const puedeVerPantalla = moduloActual === null || puede(moduloActual, "ver");

  const iniciales = `${sesion.usuario.nombres[0] ?? ""}${sesion.usuario.apellidos[0] ?? ""}`.toUpperCase();

  function fijarMenu(fijo: boolean) {
    setMenuFijo(fijo);
    setMenuAbierto(false);
    try {
      localStorage.setItem("avicola.menu.fijo", fijo ? "1" : "0");
    } catch {}
  }

  return (
    <div className="min-h-screen bg-cal">
      {/* Fondo oscuro detras del menu cuando esta abierto encima de la pagina */}
      <div
        aria-hidden="true"
        onClick={() => setMenuAbierto(false)}
        className={`fixed inset-0 z-30 bg-galpon-honda/55 transition-opacity duration-200 ${
          menuAbierto ? "opacity-100" : "pointer-events-none opacity-0"
        } ${menuFijo ? "lg:hidden" : ""}`}
      />

      <aside
        aria-label="Menu principal"
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-galpon text-galpon-suave transition-transform duration-200 ease-out ${
          menuAbierto ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        } ${menuFijo ? "lg:translate-x-0 lg:shadow-none" : ""}`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-2 px-4">
          <Link href="/panel" className="flex items-center gap-2.5 pl-1" onClick={() => setMenuAbierto(false)}>
            <span aria-hidden="true" className="block h-8 w-[26px] rounded-[50%_50%_46%_46%/58%_58%_42%_42%] bg-yema" />
            <span className="font-cifra text-xl font-bold text-white [font-stretch:115%]">Avícola</span>
          </Link>
          <div className="flex items-center gap-1">
            <button
              onClick={() => fijarMenu(!menuFijo)}
              aria-label={menuFijo ? "Soltar el menu" : "Dejar el menu fijo"}
              title={menuFijo ? "Ocultar el menu" : "Dejar el menu fijo al lado"}
              className="hidden h-10 w-10 place-items-center rounded-lg text-galpon-claro transition hover:bg-white/10 hover:text-white lg:grid"
            >
              <Icono nombre={menuFijo ? "izquierda" : "fijar"} className="h-4 w-4" />
            </button>
            <button
              onClick={() => setMenuAbierto(false)}
              aria-label="Cerrar el menu"
              title="Cerrar"
              className={`grid h-10 w-10 place-items-center rounded-lg text-galpon-claro transition hover:bg-white/10 hover:text-white ${menuFijo ? "lg:hidden" : ""}`}
            >
              <Icono nombre="cerrar" className="h-4 w-4" />
            </button>
          </div>
        </div>

        <MenuLateral grupos={grupos} ruta={ruta} alNavegar={() => setMenuAbierto(false)} />

        <div className="shrink-0 border-t border-white/10 px-5 py-3 text-sm text-galpon-claro">
          {sesion.usuario.cuenta_nombre ?? "Plataforma"}
        </div>
      </aside>

      <div className={`flex min-h-screen min-w-0 flex-col transition-[padding] duration-200 ${menuFijo ? "lg:pl-64" : ""}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-linea bg-superficie px-3 sm:px-4 lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg text-tinta transition hover:bg-cal-honda ${menuFijo ? "lg:hidden" : ""}`}
              onClick={() => setMenuAbierto(true)}
              aria-label="Menu"
              aria-expanded={menuAbierto}
              title="Abrir el menu"
            >
              <Icono nombre="menu" className="h-6 w-6" />
            </button>
            {/* En el celular, si hay varias fincas, ya la muestra la lista de la derecha */}
            <div className={`min-w-0 ${sesion.fincas.length > 1 ? "hidden sm:block" : ""}`}>
              <p className="truncate font-cifra text-base font-bold text-tinta [font-stretch:105%]">{sesion.finca_activa.nombre}</p>
              <p className="truncate text-sm text-tinta-2">
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
                aria-label="Cambiar de finca"
                className="min-h-11 max-w-[9rem] rounded-lg border-[1.5px] border-linea bg-superficie px-3 text-sm text-tinta focus:border-galpon focus:ring-3 focus:ring-galpon/15 focus:outline-none sm:max-w-none"
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
                className="flex min-h-11 items-center gap-2 rounded-lg p-1.5 transition hover:bg-cal-honda"
                aria-label="Mi cuenta"
              >
                <span className="grid h-9 w-9 place-items-center rounded-full bg-galpon font-cifra text-sm font-bold text-white">
                  {iniciales || "AV"}
                </span>
                <span className="hidden text-base text-tinta sm:block">{sesion.usuario.nombres}</span>
              </button>

              {usuarioAbierto ? (
                <div className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-linea bg-superficie shadow-[0_16px_40px_-12px_rgb(22_58_44/0.35)]">
                  <div className="border-b border-linea-suave px-4 py-3">
                    <p className="font-semibold text-tinta">
                      {sesion.usuario.nombres} {sesion.usuario.apellidos}
                    </p>
                    <p className="truncate text-sm text-tinta-2">{sesion.usuario.email}</p>
                  </div>
                  <Link
                    href="/mi-cuenta"
                    onClick={() => setUsuarioAbierto(false)}
                    className="flex min-h-12 items-center gap-3 px-4 text-base text-tinta hover:bg-cal"
                  >
                    <Icono nombre="usuario" className="h-4 w-4 text-tinta-3" />
                    Mi cuenta
                  </Link>
                  <Link
                    href="/alertas"
                    onClick={() => setUsuarioAbierto(false)}
                    className="flex min-h-12 items-center gap-3 px-4 text-base text-tinta hover:bg-cal"
                  >
                    <Icono nombre="campana" className="h-4 w-4 text-tinta-3" />
                    Avisos
                  </Link>
                  <button
                    onClick={() => salir()}
                    className="flex min-h-12 w-full items-center gap-3 border-t border-linea-suave px-4 text-left text-base text-alerta hover:bg-alerta-suave"
                  >
                    <Icono nombre="salir" className="h-4 w-4" />
                    Cerrar sesion
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-6 px-4 pt-5 pb-16 lg:px-8 lg:pt-7">
          {sesion.demo ? (
            <Aviso tipo="info">
              Estas en la demo: puedes probar todo, pero no cambiar contrasenas, correos, permisos ni
              desactivar usuarios o fincas. Los datos vuelven a quedar como al principio cada noche.
            </Aviso>
          ) : null}
          {puedeVerPantalla ? (
            children
          ) : (
            <Aviso>
              Tu rol no tiene acceso a esta pantalla.{" "}
              <Link href="/panel" className="font-medium underline">
                Volver al panel
              </Link>
            </Aviso>
          )}
        </main>
      </div>
    </div>
  );
}
