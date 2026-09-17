"use client";

import { useCallback, useEffect, useState } from "react";
import { api, FalloApi } from "./api";

/** Carga datos de la API y los vuelve a pedir cuando cambia la ruta o la finca. */
export function useDatos<T>(ruta: string | null, clave: string | number = "") {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(Boolean(ruta));
  const [error, setError] = useState("");

  const cargar = useCallback(async () => {
    if (!ruta) return;
    setCargando(true);
    setError("");
    try {
      setDatos(await api<T>(ruta));
    } catch (fallo) {
      setError(fallo instanceof FalloApi ? fallo.message : "No se pudieron cargar los datos");
    } finally {
      setCargando(false);
    }
  }, [ruta]);

  useEffect(() => {
    void cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargar, clave]);

  return { datos, cargando, error, recargar: cargar };
}

export function mensajeDeError(fallo: unknown, porDefecto = "No se pudo completar la operacion") {
  return fallo instanceof FalloApi ? fallo.message : porDefecto;
}
