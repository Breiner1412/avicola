import type { NextConfig } from "next";

// La API se consume por el mismo dominio (/api) para que las cookies funcionen
// sin configuraciones extra de CORS.
const apiInterna = process.env.API_INTERNA ?? "http://127.0.0.1:8000";
const produccion = process.env.NODE_ENV === "production";

// Todo sale del mismo dominio. Next necesita scripts y estilos en linea; en
// desarrollo ademas usa eval para recargar en caliente.
const politicaDeContenido = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${produccion ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const cabecerasDeSeguridad = [
  { key: "Content-Security-Policy", value: politicaDeContenido },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
];

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:ruta*", headers: cabecerasDeSeguridad }];
  },
  async rewrites() {
    return [{ source: "/api/:ruta*", destination: `${apiInterna}/api/:ruta*` }];
  },
};

export default config;
