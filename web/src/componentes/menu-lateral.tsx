"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Enlace } from "@/lib/menu";
import { Icono } from "@/componentes/iconos";

type Grupo = { titulo: string; enlaces: Enlace[] };

const CLAVE_GRUPOS = "avicola.menu.grupos";
const CLAVE_SCROLL = "avicola.menu.scroll";

function leer<T>(clave: string, almacen: "local" | "sesion", porDefecto: T): T {
  try {
    const guardado = (almacen === "local" ? localStorage : sessionStorage).getItem(clave);
    return guardado ? (JSON.parse(guardado) as T) : porDefecto;
  } catch {
    return porDefecto;
  }
}

function guardar(clave: string, almacen: "local" | "sesion", valor: unknown) {
  try {
    (almacen === "local" ? localStorage : sessionStorage).setItem(clave, JSON.stringify(valor));
  } catch {
    // Sin almacenamiento el menu sigue funcionando, solo no recuerda.
  }
}

export function esActivo(ruta: string, enlace: Enlace) {
  return ruta === enlace.ruta || ruta.startsWith(`${enlace.ruta}/`);
}

export function MenuLateral({
  grupos,
  ruta,
  alNavegar,
}: {
  grupos: Grupo[];
  ruta: string;
  alNavegar: () => void;
}) {
  const [abiertos, setAbiertos] = useState<Record<string, boolean>>({});
  const [listo, setListo] = useState(false);
  const caja = useRef<HTMLElement>(null);

  // Recupera los grupos abiertos y la posicion del menu.
  useLayoutEffect(() => {
    setAbiertos(leer<Record<string, boolean>>(CLAVE_GRUPOS, "local", {}));
    setListo(true);
    if (caja.current) caja.current.scrollTop = leer<number>(CLAVE_SCROLL, "sesion", 0);
  }, []);

  // El grupo de la pantalla actual siempre queda abierto.
  useEffect(() => {
    if (!listo) return;
    const actual = grupos.find((grupo) => grupo.enlaces.some((enlace) => esActivo(ruta, enlace)));
    if (actual && !abiertos[actual.titulo]) {
      const nuevos = { ...abiertos, [actual.titulo]: true };
      setAbiertos(nuevos);
      guardar(CLAVE_GRUPOS, "local", nuevos);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ruta, listo]);

  function alternar(titulo: string) {
    const nuevos = { ...abiertos, [titulo]: !abiertos[titulo] };
    setAbiertos(nuevos);
    guardar(CLAVE_GRUPOS, "local", nuevos);
  }

  function enlaceHtml(enlace: Enlace, sangria: boolean) {
    const activo = esActivo(ruta, enlace);
    return (
      <li key={enlace.ruta}>
        <Link
          href={enlace.ruta}
          onClick={alNavegar}
          aria-current={activo ? "page" : undefined}
          className={`flex min-h-11 items-center gap-3 rounded-lg pr-3 text-base transition ${sangria ? "pl-4" : "pl-3"} ${
            activo
              ? "bg-yema font-bold text-tinta"
              : "text-galpon-suave hover:bg-white/10 hover:text-white"
          }`}
        >
          <Icono
            nombre={enlace.icono}
            className={`h-[18px] w-[18px] shrink-0 ${activo ? "text-tinta" : "text-galpon-claro"}`}
          />
          <span className="truncate">{enlace.etiqueta}</span>
        </Link>
      </li>
    );
  }

  return (
    <nav
      ref={caja}
      onScroll={(e) => guardar(CLAVE_SCROLL, "sesion", e.currentTarget.scrollTop)}
      className="menu-lateral flex-1 overflow-y-auto overscroll-contain px-3 pb-6"
    >
      {grupos.map((grupo, indice) => {
        // El primer grupo (Panel y Avisos) va siempre a la vista.
        if (indice === 0) {
          return (
            <ul key={grupo.titulo} className="mb-3 space-y-0.5">
              {grupo.enlaces.map((enlace) => enlaceHtml(enlace, false))}
            </ul>
          );
        }
        const abierto = !!abiertos[grupo.titulo];
        const tieneActivo = grupo.enlaces.some((enlace) => esActivo(ruta, enlace));
        const id = `grupo-${grupo.titulo.toLowerCase()}`;
        return (
          <div key={grupo.titulo} className="mt-1">
            <button
              type="button"
              onClick={() => alternar(grupo.titulo)}
              aria-expanded={abierto}
              aria-controls={id}
              className={`flex min-h-10 w-full items-center justify-between rounded-lg px-3 text-sm font-semibold transition hover:bg-white/10 ${
                tieneActivo ? "text-white" : "text-galpon-claro"
              }`}
            >
              <span className="flex items-center gap-2">
                {grupo.titulo}
                {tieneActivo && !abierto ? <span className="h-2 w-2 rounded-full bg-yema" /> : null}
              </span>
              <span className="flex items-center gap-2">
                <span className="cifra rounded-md bg-galpon-honda px-1.5 text-xs font-medium text-galpon-claro">
                  {grupo.enlaces.length}
                </span>
                <Icono
                  nombre="abajo"
                  className={`h-3.5 w-3.5 transition-transform duration-200 ${abierto ? "rotate-180" : ""}`}
                />
              </span>
            </button>
            <div
              id={id}
              className={`grid transition-[grid-template-rows] duration-200 ease-out ${
                abierto ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <ul className="min-h-0 space-y-0.5 overflow-hidden" inert={!abierto}>
                <li aria-hidden className="h-0.5" />
                {grupo.enlaces.map((enlace) => enlaceHtml(enlace, true))}
                <li aria-hidden className="h-1" />
              </ul>
            </div>
          </div>
        );
      })}
    </nav>
  );
}
