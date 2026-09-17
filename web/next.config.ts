import type { NextConfig } from "next";

// La API se consume por el mismo dominio (/api) para que las cookies funcionen
// sin configuraciones extra de CORS.
const apiInterna = process.env.API_INTERNA ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:ruta*", destination: `${apiInterna}/api/:ruta*` }];
  },
};

export default config;
