// Fechas, horas y dinero con el formato de Colombia.
//
// La API guarda las horas en UTC sin zona ("2026-09-18T20:15:00"). Si se le pasa
// eso a `new Date` el navegador lo toma como hora local y queda corrido 5 horas,
// por eso todo pasa por `aFecha`.

const ZONA = /[zZ]|[+-]\d\d:?\d\d$/;

export function aFecha(valor: string | Date): Date {
  if (valor instanceof Date) return valor;
  if (/^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    const [a, m, d] = valor.split("-").map(Number);
    return new Date(a, m - 1, d); // solo fecha: medianoche local
  }
  return new Date(ZONA.test(valor) ? valor : `${valor}Z`);
}

/** Fecha de hoy en la hora del dispositivo, como la espera la API (AAAA-MM-DD). */
export function hoy(): string {
  return fechaIso(new Date());
}

export function haceDias(dias: number): string {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - dias);
  return fechaIso(fecha);
}

export function fechaIso(fecha: Date): string {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

/** 18 sep 2026 */
export function fecha(valor: string | null | undefined): string {
  if (!valor) return "—";
  return aFecha(valor).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
}

/** 18 sep, 3:15 p. m. */
export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return "—";
  return aFecha(valor).toLocaleString("es-CO", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** 3:15 p. m. */
export function hora(valor: string | null | undefined): string {
  if (!valor) return "—";
  return aFecha(valor).toLocaleTimeString("es-CO", { hour: "numeric", minute: "2-digit" });
}

/** hace 5 min, hace 2 h, ayer, 12 sep */
export function haceCuanto(valor: string | null | undefined): string {
  if (!valor) return "sin datos";
  const momento = aFecha(valor);
  const minutos = Math.round((Date.now() - momento.getTime()) / 60000);
  if (minutos < 1) return "hace un momento";
  if (minutos < 60) return `hace ${minutos} min`;
  if (minutos < 60 * 24) return `hace ${Math.round(minutos / 60)} h`;
  if (minutos < 60 * 48) return "ayer";
  return momento.toLocaleDateString("es-CO", { day: "numeric", month: "short" });
}

export const moneda = (valor: number) => `$${Math.round(valor).toLocaleString("es-CO")}`;
export const numero = (valor: number) => valor.toLocaleString("es-CO");

/** "C" se muestra como "°C". */
export function unidad(valor: string | null | undefined): string {
  if (!valor) return "";
  return valor === "C" ? "°C" : valor;
}
