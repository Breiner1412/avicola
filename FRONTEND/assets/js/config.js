// Configuración central del frontend.
//
// Por defecto la API se consume en la ruta relativa /api: nginx (docker compose)
// la redirige al backend, así no hay problemas de CORS y sirve en cualquier dominio.
// Si abres el frontend con Live Server (puerto 5500) se usa la API local en el 8000.
const esLiveServer = ["5500", "5501"].includes(window.location.port);

export const API_BASE_URL = esLiveServer ? "http://localhost:8000" : "/api";
