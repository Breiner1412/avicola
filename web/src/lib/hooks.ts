"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, FalloApi } from "./api";
import { useSesion } from "./sesion";

/**
 * Carga datos de la API y los vuelve a pedir cuando cambia la ruta o la clave
 * (por ejemplo, la finca).
 *
 * Solo la ultima peticion actualiza la pantalla: si el usuario cambia de finca o de
 * filtro mientras una respuesta lenta viene en camino, esa respuesta vieja se
 * descarta en lugar de pisar los datos nuevos. Al cambiar de finca se limpian los
 * datos anteriores para no mostrar los de la otra finca mientras carga.
 */
export function useDatos<T>(ruta: string | null, clave: string | number = "") {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(Boolean(ruta));
  const [error, setError] = useState("");
  const ultima = useRef(0);
  const montado = useRef(true);
  const finca = useSesion().sesion?.finca_activa?.id ?? null;

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  const cargar = useCallback(async () => {
    if (!ruta) return;
    const numero = ++ultima.current;
    const vigente = () => montado.current && numero === ultima.current;

    setCargando(true);
    setError("");
    try {
      const respuesta = await api<T>(ruta);
      if (vigente()) setDatos(respuesta);
    } catch (fallo) {
      if (vigente()) setError(fallo instanceof FalloApi ? fallo.message : "No se pudieron cargar los datos");
    } finally {
      if (vigente()) setCargando(false);
    }
  }, [ruta]);

  useEffect(() => {
    setDatos(null);
  }, [finca]);

  useEffect(() => {
    void cargar();
  }, [cargar, clave]);

  return { datos, cargando, error, recargar: cargar };
}

export function mensajeDeError(fallo: unknown, porDefecto = "No se pudo completar la operacion") {
  return fallo instanceof FalloApi ? fallo.message : porDefecto;
}
