import type { Sesion } from "./tipos";

const BASE = "/api/v1";

let token: string | null = null;
let fincaId: number | null = null;
let alRenovar: ((sesion: Sesion) => void) | null = null;
let alCerrar: (() => void) | null = null;

export function fijarToken(nuevo: string | null) {
  token = nuevo;
}

export function fijarFinca(id: number | null) {
  fincaId = id;
}

export function alRenovarSesion(fn: (sesion: Sesion) => void) {
  alRenovar = fn;
}

export function alCerrarSesion(fn: () => void) {
  alCerrar = fn;
}

export class FalloApi extends Error {
  codigo: string;
  estado: number;
  detalles: Record<string, unknown>;

  constructor(estado: number, codigo: string, mensaje: string, detalles: Record<string, unknown> = {}) {
    super(mensaje);
    this.name = "FalloApi";
    this.estado = estado;
    this.codigo = codigo;
    this.detalles = detalles;
  }
}

type Opciones = {
  metodo?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  cuerpo?: unknown;
  finca?: number | null;
  sinSesion?: boolean;
};

async function leer(respuesta: Response) {
  const texto = await respuesta.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    return { mensaje: texto };
  }
}

function extraerError(estado: number, cuerpo: unknown): FalloApi {
  const datos = (cuerpo ?? {}) as Record<string, unknown>;
  const detalle = (datos.detail ?? datos) as Record<string, unknown>;
  const codigo = typeof detalle.codigo === "string" ? detalle.codigo : "error";
  const mensaje =
    typeof detalle.mensaje === "string" ? detalle.mensaje : "No se pudo completar la operacion";
  const detalles = (detalle.detalles ?? {}) as Record<string, unknown>;
  return new FalloApi(estado, codigo, mensaje, detalles);
}

async function enviar(ruta: string, opciones: Opciones): Promise<Response> {
  const cabeceras: Record<string, string> = { "Content-Type": "application/json" };
  if (token && !opciones.sinSesion) cabeceras.Authorization = `Bearer ${token}`;

  const finca = opciones.finca !== undefined ? opciones.finca : fincaId;
  if (finca) cabeceras["X-Finca-Id"] = String(finca);

  return fetch(`${BASE}${ruta}`, {
    method: opciones.metodo ?? "GET",
    headers: cabeceras,
    body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
    credentials: "include",
  });
}

export async function api<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  let respuesta = await enviar(ruta, opciones);

  // Si el token vencio, se intenta renovar una sola vez con la cookie de refresco.
  if (respuesta.status === 401 && !opciones.sinSesion && !ruta.startsWith("/auth/refrescar")) {
    const renovada = await fetch(`${BASE}/auth/refrescar`, { method: "POST", credentials: "include" });
    if (renovada.ok) {
      const sesion = (await renovada.json()) as Sesion;
      token = sesion.token;
      fincaId = sesion.finca_activa?.id ?? fincaId;
      alRenovar?.(sesion);
      respuesta = await enviar(ruta, opciones);
    } else {
      token = null;
      alCerrar?.();
    }
  }

  const cuerpo = await leer(respuesta);
  if (!respuesta.ok) throw extraerError(respuesta.status, cuerpo);
  return cuerpo as T;
}
