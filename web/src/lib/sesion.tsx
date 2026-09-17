"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, alCerrarSesion, alRenovarSesion, fijarFinca, fijarToken } from "./api";
import type { Sesion } from "./tipos";

type Estado = {
  sesion: Sesion | null;
  cargando: boolean;
  entrar: (email: string, clave: string, fincaId?: number) => Promise<Sesion>;
  salir: () => Promise<void>;
  elegirFinca: (fincaId: number) => Promise<void>;
  recargar: () => Promise<void>;
  puede: (modulo: string, accion?: "ver" | "crear" | "editar" | "borrar") => boolean;
};

const Contexto = createContext<Estado | null>(null);

export function ProveedorSesion({ children }: { children: React.ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [cargando, setCargando] = useState(true);

  const guardar = useCallback((datos: Sesion | null) => {
    setSesion(datos);
    fijarToken(datos?.token ?? null);
    fijarFinca(datos?.finca_activa?.id ?? null);
  }, []);

  useEffect(() => {
    alRenovarSesion((datos) => guardar(datos));
    alCerrarSesion(() => guardar(null));

    (async () => {
      try {
        const datos = await api<Sesion>("/auth/refrescar", { metodo: "POST", sinSesion: true });
        guardar(datos);
      } catch {
        guardar(null);
      } finally {
        setCargando(false);
      }
    })();
  }, [guardar]);

  const entrar = useCallback(
    async (email: string, clave: string, fincaId?: number) => {
      const datos = await api<Sesion>("/auth/login", {
        metodo: "POST",
        cuerpo: { email, clave, finca_id: fincaId ?? null },
        sinSesion: true,
      });
      guardar(datos);
      return datos;
    },
    [guardar],
  );

  const salir = useCallback(async () => {
    try {
      await api("/auth/salir", { metodo: "POST" });
    } catch {
      // aunque falle, se limpia la sesion local
    }
    guardar(null);
  }, [guardar]);

  const elegirFinca = useCallback(
    async (fincaId: number) => {
      const datos = await api<Sesion>("/auth/finca", { metodo: "POST", cuerpo: { finca_id: fincaId } });
      guardar(datos);
    },
    [guardar],
  );

  const recargar = useCallback(async () => {
    const datos = await api<Sesion>("/auth/yo");
    guardar(datos);
  }, [guardar]);

  const puede = useCallback(
    (modulo: string, accion: "ver" | "crear" | "editar" | "borrar" = "ver") => {
      if (!sesion) return false;
      if (accion !== "ver" && sesion.finca_activa?.solo_lectura) return false;
      return Boolean(sesion.permisos[modulo]?.[accion]);
    },
    [sesion],
  );

  const valor = useMemo(
    () => ({ sesion, cargando, entrar, salir, elegirFinca, recargar, puede }),
    [sesion, cargando, entrar, salir, elegirFinca, recargar, puede],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): Estado {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useSesion debe usarse dentro de ProveedorSesion");
  return valor;
}
