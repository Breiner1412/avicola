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
  // Para subir archivos: se manda tal cual (multipart), sin JSON
  formulario?: FormData;
  finca?: number | null;
  sinSesion?: boolean;
};

async function leer(respuesta: Response) {
  const texto = await respuesta.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    // HTML de un proxy (502, 504...) u otra respuesta que no es de la API
    return null;
  }
}

function extraerError(estado: number, cuerpo: unknown): FalloApi {
  const datos = (cuerpo ?? {}) as Record<string, unknown>;
  const detalle = (datos.detail ?? datos) as Record<string, unknown>;
  const codigo = typeof detalle.codigo === "string" ? detalle.codigo : "error";
  let mensaje = typeof detalle.mensaje === "string" ? detalle.mensaje : "No se pudo completar la operacion";
  if (cuerpo === null && estado >= 500) {
    mensaje = "El servidor no respondio. Intenta de nuevo en un momento.";
  }
  const detalles = (detalle.detalles ?? {}) as Record<string, unknown>;
  return new FalloApi(estado, codigo, mensaje, detalles);
}

const SIN_CONEXION = () => new FalloApi(0, "sin_conexion", "No hay conexion con el servidor. Revisa tu internet.");

async function enviar(ruta: string, opciones: Opciones): Promise<Response> {
  const cabeceras: Record<string, string> = {};
  if (!opciones.formulario) cabeceras["Content-Type"] = "application/json";
  if (token && !opciones.sinSesion) cabeceras.Authorization = `Bearer ${token}`;

  const finca = opciones.finca !== undefined ? opciones.finca : fincaId;
  if (finca) cabeceras["X-Finca-Id"] = String(finca);

  const cuerpo = opciones.formulario ?? (opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo));
  try {
    return await fetch(`${BASE}${ruta}`, {
      method: opciones.metodo ?? "GET",
      headers: cabeceras,
      body: cuerpo,
      credentials: "include",
    });
  } catch {
    throw SIN_CONEXION();
  }
}

let renovando: Promise<Sesion | null> | null = null;

/**
 * Renueva el token de acceso con la cookie de refresco. Si varias peticiones lo
 * necesitan a la vez, todas esperan la misma renovacion (el servidor cambia la
 * cookie en cada uso). Devuelve null solo si la sesion ya no sirve (401).
 */
export function renovarSesion(): Promise<Sesion | null> {
  if (!renovando) {
    renovando = (async () => {
      let respuesta: Response;
      try {
        respuesta = await fetch(`${BASE}/auth/refrescar`, { method: "POST", credentials: "include" });
      } catch {
        throw SIN_CONEXION();
      }
      if (respuesta.status === 401) return null;
      if (!respuesta.ok) throw extraerError(respuesta.status, await leer(respuesta));
      return (await respuesta.json()) as Sesion;
    })().finally(() => {
      renovando = null;
    });
  }
  return renovando;
}

/** Hace la peticion y, si el token vencio, lo renueva una vez y la repite. */
async function pedir(ruta: string, opciones: Opciones): Promise<Response> {
  const respuesta = await enviar(ruta, opciones);
  if (respuesta.status !== 401 || opciones.sinSesion || ruta.startsWith("/auth/")) return respuesta;

  const sesion = await renovarSesion();
  if (!sesion) {
    token = null;
    alCerrar?.();
    return respuesta;
  }
  token = sesion.token;
  fincaId = sesion.finca_activa?.id ?? fincaId;
  alRenovar?.(sesion);
  return enviar(ruta, opciones);
}

export async function api<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const respuesta = await pedir(ruta, opciones);
  const cuerpo = await leer(respuesta);
  if (!respuesta.ok) throw extraerError(respuesta.status, cuerpo);
  return cuerpo as T;
}

/** Descarga un archivo (CSV) con la misma sesion y renovacion que api(). */
export async function descargar(ruta: string): Promise<Blob> {
  const respuesta = await pedir(ruta, {});
  if (!respuesta.ok) throw extraerError(respuesta.status, await leer(respuesta));
  return respuesta.blob();
}
