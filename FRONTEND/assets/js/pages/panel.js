import { API_BASE_URL } from "../config.js";
import { handleResponse, sanitizeData } from "../api/apiClient.js";
// Panel de Control - Inicialización y lógica
// Detectar rol del usuario para personalizar el panel
const currentUser = JSON.parse(localStorage.getItem("user") || "{}");
const currentRole = (currentUser?.nombre_rol || "").toLowerCase();

// Servicio de Dashboard integrado

/**
 * Envoltorio de fetch: si la sesión expiró cierra sesión (vía handleResponse)
 * y devuelve los datos ya escapados para poder usarlos con innerHTML.
 */
async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401 || res.status === 403) {
    await handleResponse(res); // lanza el error correspondiente
  }
  return {
    ok: res.ok,
    status: res.status,
    json: async () => sanitizeData(await res.json()),
  };
}

class DashboardService {
  constructor() {
    this.token = localStorage.getItem("access_token");
  }

  getHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.token}`,
    };
  }

  async getMetricas() {
    const url = `${API_BASE_URL}/dashboard/metricas`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (!res.ok) throw new Error(`Metricas ${res.status}`);
    return res.json();
  }

  async getProduccionSemanal() {
    const url = `${API_BASE_URL}/dashboard/produccion-semanal`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (!res.ok) throw new Error(`ProduccionSemanal ${res.status}`);
    return res.json();
  }

  async getDistribucionTipos() {
    const url = `${API_BASE_URL}/dashboard/distribucion-tipos`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (!res.ok) throw new Error(`DistribucionTipos ${res.status}`);
    return res.json();
  }

  async getProduccionRango(dias = 7) {
    const url = `${API_BASE_URL}/dashboard/produccion-rango?dias=${dias}`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (res.status === 404 && dias === 7) {
      // Fallback a semanal si el endpoint nuevo no existe
      return this.getProduccionSemanal();
    }
    if (!res.ok) throw new Error(`ProduccionRango ${dias} -> ${res.status}`);
    return res.json();
  }

  async getOcupacionGalpones() {
    const url = `${API_BASE_URL}/dashboard/ocupacion-galpones`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (!res.ok) throw new Error(`OcupacionGalpones ${res.status}`);
    return res.json();
  }

  async getIncidentesRecientes() {
    const url = `${API_BASE_URL}/dashboard/incidentes-recientes`;
    const res = await apiFetch(url, { method: "GET", headers: this.getHeaders() });
    if (!res.ok) throw new Error(`IncidentesRecientes ${res.status}`);
    return res.json();
  }

  async getSensores() {
    try {
      const response = await apiFetch(`${API_BASE_URL}/dashboard/sensores`, {
        method: "GET",
        headers: this.getHeaders(),
      });

      if (!response.ok) {
        throw new Error("Error al obtener datos de sensores");
      }

      return await response.json();
    } catch (error) {
      console.error("Error en getSensores:", error);
      throw error;
    }
  }

  async getActividadReciente() {
    try {
      const response = await apiFetch(
        `${API_BASE_URL}/dashboard/actividad-reciente`,
        {
          method: "GET",
          headers: this.getHeaders(),
        }
      );
      if (!response.ok) {
        throw new Error("Error al obtener actividad reciente");
      }
      return await response.json();
    } catch (error) {
      console.error("Error en getActividadReciente:", error);
      throw error;
    }
  }
}

const dashboardService = new DashboardService();

// Configuración de colores Chart.js
const chartColors = {
  primary: "#5b99ea",
  success: "#75c181",
  warning: "#f6c23e",
  danger: "#e74a3b",
  info: "#36b9cc",
  gray: "#a9b5c9",
  border: "#e7e9ed",
};

// Variables globales para los gráficos
let produccionChart = null;
let tipoGallinaChart = null;
let galponesChart = null;

// Función principal para cargar todos los datos del dashboard
async function cargarDatosDashboard() {
  // Configuración de widgets por rol (qué mostrar primero y qué ocultar)
  aplicarLayoutPorRol();
  // Mostrar indicadores de carga básicos
  const setSpinner = (id) =>
    (document.getElementById(id).innerHTML =
      '<div class="spinner-border spinner-border-sm" role="status"></div>');
  [
    "total-gallinas",
    "produccion-hoy",
    "galpones-activos",
    "alertas-activas",
  ].forEach(setSpinner);

  // 1) Métricas principales (independiente)
  try {
    const metricas = await dashboardService.getMetricas();
    actualizarMetricas(metricas);
  } catch (e) {
    console.warn("No se pudieron cargar métricas:", e);
  }

  // 2) Producción con filtros (por defecto 7 días)
  try {
    await cargarGraficoProduccionRango(7);
  } catch (e) {
    console.error("No se pudo cargar producción semanal:", e);
    // Fallback local: 7 días con fechas YYYY-MM-DD
    const hoy = new Date();
    const inicio = new Date(hoy);
    inicio.setDate(inicio.getDate() - 6);

    const fechas = [];
    for (let i = 0; i < 7; i++) {
      const fecha = new Date(inicio);
      fecha.setDate(fecha.getDate() + i);
      const ano = fecha.getFullYear();
      const mes = String(fecha.getMonth() + 1).padStart(2, "0");
      const dia = String(fecha.getDate()).padStart(2, "0");
      fechas.push(`${ano}-${mes}-${dia}`);
    }

    const fallback = {
      labels: fechas,
      data_actual: [0, 0, 0, 0, 0, 0, 0],
      data_anterior: [0, 0, 0, 0, 0, 0, 0],
    };
    try {
      const cache = localStorage.getItem("produccion_semanal_cache");
      if (cache) {
        const parsed = JSON.parse(cache);
        if (Array.isArray(parsed.labels) && Array.isArray(parsed.data_actual)) {
          cargarGraficoProduccion(parsed);
          return;
        }
      }
    } catch {}
    cargarGraficoProduccion(fallback);
  }

  // 3) Gráficos secundarios (best-effort)
  let distData = null;
  let galponesData = null;

  try {
    distData = await dashboardService.getDistribucionTipos();
  } catch (e) {
    console.warn("Distribución tipos no disponible:", e);
  }

  try {
    galponesData = await dashboardService.getOcupacionGalpones();
  } catch (e) {
    console.warn("Ocupación de galpones no disponible:", e);
  }

  // Cargar gráfico combinado si hay datos de ambos
  if (distData && galponesData) {
    cargarGraficoCombinado(distData, galponesData);
  }

  try {
    const inc = await dashboardService.getIncidentesRecientes();
    // Solo cargar incidentes si el elemento existe en la página
    if (document.getElementById("incidentes-list")) {
      cargarIncidentes(inc);
    }
  } catch (e) {
    console.warn("Incidentes recientes no disponibles:", e);
  }

  // 4) Sensores y Actividad en intervalos (si fallan, continúan)
  try {
    const sensores = await dashboardService.getSensores();
    actualizarSensoresData(sensores);
  } catch (e) {
    console.warn("Sensores no disponibles por ahora:", e);
  }

  try {
    const actividades = await dashboardService.getActividadReciente();
    cargarActividadReciente(actividades);
  } catch (e) {
    console.warn("Actividad reciente no disponible:", e);
  }

  // Actualizar sensores (cada 15s) y actividad (cada 3 min) mientras el panel esté abierto
  detenerActualizaciones();
  intervalos.push(setInterval(async () => {
    if (window.currentPage !== "panel") return detenerActualizaciones();
    try {
      const sensores = await dashboardService.getSensores();
      actualizarSensoresData(sensores);
    } catch (error) {
      console.error("Error actualizando sensores:", error);
    }
  }, 15000));

  intervalos.push(setInterval(async () => {
    if (window.currentPage !== "panel") return detenerActualizaciones();
    try {
      const actividades = await dashboardService.getActividadReciente();
      cargarActividadReciente(actividades);
    } catch (error) {
      console.error("Error actualizando actividad reciente:", error);
    }
  }, 180000));
}

// Temporizadores activos del panel (se detienen al salir de la página)
const intervalos = [];
function detenerActualizaciones() {
  while (intervalos.length) clearInterval(intervalos.pop());
}

// Mostrar/ocultar widgets del panel según el rol
function aplicarLayoutPorRol() {
  const role = currentRole;
  // Elementos: secciones y tarjetas
  const el = {
    produccionCard: document
      .querySelector("#produccion-semanal-cards")
      ?.closest(".card"),
    distribucionCard: document
      .getElementById("tipoGallinaChart")
      ?.closest(".card"),
    galponesCard: document.getElementById("galponesChart")?.closest(".card"),
    incidentesCard: document
      .getElementById("incidentes-list")
      ?.closest(".card"),
    sensoresCard: document
      .getElementById("sensores-container")
      ?.closest(".card"),
    actividadCard: document
      .getElementById("actividad-reciente")
      ?.closest(".card"),
  };

  // Siempre mostrar métricas principales (producción hoy, gallinas, galpones, alertas)

  // Reordenar accesos directos según rol
  const shortcuts = document.getElementById("panel-shortcuts");
  if (shortcuts) {
    const orderByRole = {
      superadmin: [
        "produccion_huevos",
        "incidentes",
        "sensors",
        "ventas",
        "galpones",
        "chickens",
      ],
      administrador: [
        "produccion_huevos",
        "incidentes",
        "sensors",
        "ventas",
        "galpones",
        "chickens",
      ],
      supervisor: [
        "tareas",
        "incidentes",
        "chickens",
        "produccion_huevos",
        "galpones",
        "sensors",
      ],
      operario: [
        "tareas",
        "incidentes",
        "chickens",
        "produccion_huevos",
        "rescue",
      ],
    };
    const desired = orderByRole[role] || orderByRole["administrador"];
    let links = Array.from(shortcuts.querySelectorAll(".shortcut-link"));

    // Eliminamos totalmente el shortcut de sensores para operario por seguridad
    if (role === "operario") {
      links
        .filter((l) => l.dataset.page === "sensors")
        .forEach((l) => l.remove());
      // actualizar la lista tras eliminar
      links = Array.from(shortcuts.querySelectorAll(".shortcut-link"));
    }

    // Mostrar/ocultar shortcuts según rol
    links.forEach((link) => {
      const page = link.dataset.page;
      if (role === "operario") {
        // Operario: solo mostrar tareas, incidentes, chickens, produccion_huevos, rescue
        if (["galpones", "ventas", "sensors"].includes(page)) {
          link.style.display = "none";
        } else {
          link.style.display = "";
          link.classList.remove("d-none");
        }
      } else if (role === "supervisor") {
        // Supervisor: ocultar ventas
        if (page === "ventas") {
          link.style.display = "none";
        } else {
          link.style.display = "";
          link.classList.remove("d-none");
        }
      } else {
        // Admin/SuperAdmin: mostrar todo
        link.style.display = "";
        link.classList.remove("d-none");
      }
    });

    links.sort(
      (a, b) =>
        desired.indexOf(a.dataset.page) - desired.indexOf(b.dataset.page)
    );
    links.forEach((l) => shortcuts.appendChild(l));
  }

  // Visibilidad de widgets
  const hide = (node) => {
    if (node) {
      node.style.display = "none";
    }
  };
  const show = (node) => {
    if (node) {
      node.style.display = "";
    }
  };

  switch (role) {
    case "operario":
      // Operario: layout simplificado y ordenado
      hide(el.produccionCard);
      hide(el.actividadCard);
      hide(el.incidentesCard);

      // Ocultar columna de producción y expandir accesos directos a ancho completo
      const produccionCol = document.querySelector(
        ".row.g-3.mb-4 > .col-12.col-lg-8"
      );
      const shortcutsCol = document.querySelector(
        ".row.g-3.mb-4 > .col-12.col-lg-4"
      );
      if (produccionCol) produccionCol.style.display = "none";
      // Colocar Monitoreo de Sensores al lado de Accesos Directos
      const sensoresCol = document
        .getElementById("sensores-container")
        ?.closest(".col-12.col-lg-6");
      if (shortcutsCol && sensoresCol && shortcutsCol.parentElement) {
        const produccionRow = shortcutsCol.parentElement;
        sensoresCol.className = "col-12 col-lg-6";
        shortcutsCol.className = "col-12 col-lg-6";
        produccionRow.insertBefore(sensoresCol, shortcutsCol);
      }

      const actividadCol = document
        .getElementById("actividad-reciente")
        ?.closest(".col-12.col-lg-6");
      if (actividadCol) actividadCol.style.display = "none";

      // Asegurar que la sección de gráficas adicionales (galpones+distribución) se muestre completa
      const graficasRow = document.getElementById("graficas-adicionales-row");
      if (graficasRow) graficasRow.style.display = "";

      // Crear secciones destacadas para Tareas e Incidentes si es operario
      crearSeccionesOperario();
      break;
    case "supervisor":
      // Mostrar producción pero mantener enfoque operativo
      show(el.produccionCard);
      show(el.incidentesCard);
      show(el.galponesCard);
      show(el.sensoresCard);
      show(el.actividadCard);
      show(el.distribucionCard);
      break;
    case "administrador":
    case "superadmin":
    default:
      // Mostrar todo
      show(el.produccionCard);
      show(el.distribucionCard);
      show(el.galponesCard);
      show(el.incidentesCard);
      show(el.sensoresCard);
      show(el.actividadCard);
      break;
  }
}

// Crear secciones destacadas para operarios: Tareas e Incidentes principales
async function crearSeccionesOperario() {
  // Buscar el contenedor principal después de las métricas
  const mainContent = document.querySelector("#main-content");
  if (!mainContent) return;

  // Verificar si ya existen las secciones
  if (document.getElementById("operario-tareas-destacadas")) return;

  // Crear HTML para secciones destacadas
  const seccionesHTML = `
    <div class="row g-3 mb-4" id="operario-secciones-destacadas">
      <!-- Tareas Pendientes Destacadas -->
      <div class="col-12 col-lg-6">
        <div class="card border-0 shadow-sm h-100 border-start border-warning border-4">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="card-title mb-0"><i class="fas fa-tasks text-warning me-2"></i>Mis Tareas Pendientes</h5>
              <a href="#" class="btn btn-sm btn-warning shortcut-link" data-page="tareas">Ver Todas</a>
            </div>
            <div id="operario-tareas-destacadas" class="list-group list-group-flush">
              <div class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-warning" role="status"></div>
                <p class="text-muted small mt-2">Cargando tareas...</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Incidentes Activos Destacados -->
      <div class="col-12 col-lg-6">
        <div class="card border-0 shadow-sm h-100 border-start border-danger border-4">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="card-title mb-0"><i class="fas fa-exclamation-triangle text-danger me-2"></i>Incidentes Activos</h5>
              <a href="#" class="btn btn-sm btn-danger shortcut-link" data-page="incidentes">Ver Todos</a>
            </div>
            <div id="operario-incidentes-destacados" class="list-group list-group-flush">
              <div class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-danger" role="status"></div>
                <p class="text-muted small mt-2">Cargando incidentes...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Insertar después de las métricas principales
  const metricasRow = document.querySelector(".row.g-3.mb-4");
  if (metricasRow) {
    metricasRow.insertAdjacentHTML("afterend", seccionesHTML);

    // Cargar datos de tareas e incidentes
    cargarTareasOperario();
    cargarIncidentesOperario();
  }
}

// Cargar tareas pendientes del operario
async function cargarTareasOperario() {
  const container = document.getElementById("operario-tareas-destacadas");
  if (!container) return;

  try {
    const idUsuario =
      currentUser?.id_usuario || currentUser?.id || currentUser?.idUsuario;
    if (!idUsuario) throw new Error("Usuario no identificado");

    // Backend expone GET /tareas/usuario/{id_usuario}
    const response = await apiFetch(
      `${API_BASE_URL}/tareas/usuario/${idUsuario}`,
      {
        headers: dashboardService.getHeaders(),
      }
    );

    if (!response.ok) throw new Error("Error al cargar tareas");

    let tareas = await response.json();
    // Tomar solo las primeras 5 para la vista del panel
    if (Array.isArray(tareas)) {
      tareas = tareas.slice(0, 5);
    }

    if (!tareas || tareas.length === 0) {
      container.innerHTML =
        '<div class="text-center py-3 text-muted small">AÚN NO TIENE TAREAS ASIGNADAS</div>';
      return;
    }

    container.innerHTML = tareas
      .map(
        (tarea) => `
      <div class="list-group-item border-0 px-0 py-2">
        <div class="d-flex justify-content-between align-items-start">
          <div class="flex-grow-1">
            <p class="mb-1">${tarea.descripcion || "Sin descripción"}</p>
            <div class="d-flex gap-2 align-items-center">
              <span class="badge bg-${
                tarea.estado === "activo" || tarea.estado === "pendiente"
                  ? "warning"
                  : tarea.estado === "completado" ||
                    tarea.estado === "finalizado"
                  ? "success"
                  : "secondary"
              }">${tarea.estado || "Sin estado"}</span>
              <small class="text-muted"><i class="far fa-calendar me-1"></i>${
                tarea.fecha_hora_init || tarea.fecha || "Sin fecha"
              }</small>
            </div>
          </div>
          <i class="fas fa-chevron-right text-muted"></i>
        </div>
      </div>
    `
      )
      .join("");
  } catch (error) {
    container.innerHTML =
      '<div class="text-center py-3 text-muted small">AÚN NO TIENE TAREAS ASIGNADAS</div>';
  }
}

// Cargar incidentes activos para el operario
async function cargarIncidentesOperario() {
  const container = document.getElementById("operario-incidentes-destacados");
  if (!container) return;

  try {
    // Backend expone GET /incidentes_generales/by-estado/{esta_resuelta}?skip&limit
    // Para mostrar incidentes activos usamos esta_resuelta=false
    const response = await apiFetch(
      `${API_BASE_URL}/incidentes_generales/by-estado/false?skip=0&limit=5`,
      { headers: dashboardService.getHeaders() }
    );

    if (!response.ok) throw new Error("Error al cargar incidentes");

    let incidentes = await response.json();

    // Adaptar según forma de respuesta (array directo o paginado)
    if (Array.isArray(incidentes)) {
      incidentes = incidentes.slice(0, 5);
    } else if (incidentes && Array.isArray(incidentes.items)) {
      incidentes = incidentes.items.slice(0, 5);
    } else if (incidentes && Array.isArray(incidentes.results)) {
      incidentes = incidentes.results.slice(0, 5);
    } else if (incidentes && Array.isArray(incidentes.data)) {
      incidentes = incidentes.data.slice(0, 5);
    } else if (incidentes && Array.isArray(incidentes.incidentes)) {
      incidentes = incidentes.incidentes.slice(0, 5);
    } else {
      incidentes = [];
    }

    if (!incidentes || incidentes.length === 0) {
      container.innerHTML =
        '<div class="text-center py-3 text-muted small">No hay incidentes activos</div>';
      return;
    }

    // Mostrar solo el primer incidente y un resumen del resto
    const primero = incidentes[0];
    const restantes = incidentes.length - 1;

    const itemHTML = `
      <div class="list-group-item border-0 px-0 py-2">
        <div class="d-flex justify-content-between align-items-start">
          <div class="flex-grow-1">
            <div class="d-flex gap-2 align-items-center mb-1">
              <span class="badge bg-${
                (primero.estado || "pendiente").toLowerCase() === "pendiente"
                  ? "warning"
                  : "success"
              }">${(primero.estado || "pendiente").toUpperCase()}</span>
              <small class="text-muted">${primero.fecha || "Hoy"}</small>
            </div>
            <p class="mb-0 small">${
              primero.descripcion || "Sin descripción"
            }</p>
            <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${
              primero.galpon || primero.ubicacion || "No especificado"
            }</small>
          </div>
        </div>
      </div>`;

    const resumenHTML =
      restantes > 0
        ? `<div class="px-0 py-2 small text-muted">+ ${restantes} incidentes pendientes más</div>`
        : "";

    container.innerHTML = itemHTML + resumenHTML;
  } catch (error) {
    console.error("Error cargando incidentes operario:", error);
    container.innerHTML =
      '<div class="text-center py-3 text-danger small">Error al cargar incidentes</div>';
  }
}

// Actualizar métricas principales
function actualizarMetricas(metricas) {
  document.getElementById("total-gallinas").textContent =
    metricas.total_gallinas.toLocaleString();
  document.getElementById("produccion-hoy").textContent =
    metricas.produccion_hoy.toLocaleString();
  document.getElementById("galpones-activos").textContent =
    metricas.galpones_activos;
  document.getElementById("alertas-activas").textContent =
    metricas.alertas_activas;
  document.getElementById("gallinas-trend").textContent =
    metricas.gallinas_trend;
  document.getElementById("produccion-trend").textContent =
    metricas.produccion_trend;
}

// Cargar Producción Semanal como gráfica (con fallback a tarjetas)
function cargarGraficoProduccion(data) {
  const container = document.getElementById("produccion-semanal-cards");
  if (!container) {
    console.error("Contenedor produccion-semanal-cards no encontrado");
    return;
  }

  // Aceptar tanto estructura nueva {labels,data} como antigua {labels,data_actual,data_anterior}
  const labels = data.labels || [];
  const datasetActual = Array.isArray(data.data)
    ? data.data
    : Array.isArray(data.data_actual)
    ? data.data_actual
    : [];
  const datasetAnterior = Array.isArray(data.data_anterior)
    ? data.data_anterior
    : new Array(datasetActual.length).fill(0);

  // Totales
  const totalActual = datasetActual.reduce((s, v) => s + (v || 0), 0);
  const promedioDiario = Math.round(totalActual / (datasetActual.length || 1));
  const totalEl = document.getElementById("total-semana-actual");
  const promEl = document.getElementById("promedio-diario");
  const maxEl = document.getElementById("maximo-dia");
  if (totalEl) totalEl.textContent = totalActual.toLocaleString();
  if (promEl) promEl.textContent = promedioDiario.toLocaleString();
  const maximo = datasetActual.length ? Math.max(...datasetActual) : 0;
  if (maxEl) maxEl.textContent = maximo.toLocaleString();

  // Crear contenedor canvas
  container.innerHTML =
    '<div style="height:300px"><canvas id="produccionChart"></canvas></div>';
  const canvas = document.getElementById("produccionChart");
  if (!canvas) return;

  // Destruir gráfica previa
  if (produccionChart) {
    produccionChart.destroy();
  }

  // Crear gráfica de barras
  const ctx2d = canvas.getContext("2d");

  // Determinar número de puntos para ajustar visualización
  const manyPoints = labels.length > 31;
  const showAllLabels = labels.length <= 7;

  produccionChart = new Chart(ctx2d, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Producción Actual",
          data: datasetActual,
          backgroundColor: "#28a745",
          borderColor: "#1e7e34",
          borderWidth: 2,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: labels.length > 30 ? 0.95 : 0.8,
        },
        {
          label: "Período Anterior",
          data: datasetAnterior,
          backgroundColor: "#6c757d",
          borderColor: "#545b62",
          borderWidth: 2,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: labels.length > 30 ? 0.95 : 0.8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      devicePixelRatio: 2,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            font: { size: 13, weight: "bold" },
            padding: 15,
            usePointStyle: true,
            pointStyle: "rect",
          },
        },
        tooltip: {
          intersect: false,
          mode: "index",
          backgroundColor: "rgba(0,0,0,0.85)",
          padding: 12,
          titleFont: { size: 13, weight: "bold" },
          bodyFont: { size: 12 },
          borderColor: "#28a745",
          borderWidth: 2,
          callbacks: {
            title: (ctx) => `📅 ${ctx[0].label}`,
            label: (ctx) =>
              `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} 🥚`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Huevos (Unidades)",
            font: { size: 12, weight: "bold" },
          },
          ticks: {
            callback: (value) => Number(value).toLocaleString(),
            font: { size: 11 },
          },
          grid: { color: "rgba(0,0,0,0.1)", drawBorder: false },
          max: Math.max(...datasetActual, ...datasetAnterior) * 1.1 || 100,
        },
        x: {
          grid: {
            display: true,
            color: "rgba(0,0,0,0.15)",
            lineWidth: 2,
            drawBorder: true,
            drawTicks: true,
          },
          ticks: {
            maxRotation: labels.length > 10 ? 45 : 0,
            minRotation: labels.length > 10 ? 45 : 0,
            font: { size: 10 },
            callback: function (index) {
              // Mostrar cada label para 7 días, cada 2 para 30, cada 3 para 90+
              if (showAllLabels || index % Math.ceil(labels.length / 7) === 0) {
                return labels[index];
              }
              return "";
            },
          },
        },
      },
      animation: {
        duration: 750,
        easing: "easeInOutQuart",
      },
    },
  });

  // Guardar cache local por si el backend falla luego
  try {
    const cachePayload = {
      labels,
      data_actual: datasetActual,
      data_anterior: datasetAnterior,
    };
    localStorage.setItem(
      "produccion_semanal_cache",
      JSON.stringify(cachePayload)
    );
  } catch {}
}

// Cargar por rango (7, 30, 90, 180)
async function cargarGraficoProduccionRango(dias = 7) {
  try {
    const data = await dashboardService.getProduccionRango(dias);
    // Normalizar estructura del backend nuevo/antiguo
    if (Array.isArray(data.data)) {
      // Nuevo endpoint
      cargarGraficoProduccion({
        labels: data.labels,
        data: data.data,
        data_anterior: new Array(data.data.length).fill(0),
      });
    } else {
      // Antiguo semanal
      cargarGraficoProduccion(data);
    }
  } catch (err) {
    console.error("Fallo al cargar rango de producción", dias, err);
    if (dias === 7) {
      // intentar semanal
      try {
        const sem = await dashboardService.getProduccionSemanal();
        cargarGraficoProduccion(sem);
        return;
      } catch {}
    }
    // Fallback vacío
    cargarGraficoProduccion({ labels: [], data: [] });
  }
}

// Gráfico de Distribución por Tipo de Gallina
// Gráfico Combinado: Distribución de Tipos + Ocupación de Galpones
function cargarGraficoCombinado(distData, galponesData) {
  const container = document.getElementById("graficas-adicionales-row");
  if (!container) return;

  if (
    (!distData || distData.length === 0) &&
    (!galponesData || galponesData.length === 0)
  ) {
    container.innerHTML = `
      <div class="col-12">
        <div class="card border-0 shadow-sm">
          <div class="card-body text-center py-5">
            <i class="fas fa-chart-bar fa-3x text-muted mb-3"></i>
            <p class="text-muted">No hay datos disponibles para mostrar</p>
          </div>
        </div>
      </div>
    `;
    return;
  }

  if (
    (!galponesData || galponesData.length === 0) &&
    distData &&
    distData.length > 0
  ) {
    return;
  }

  // Paleta de colores para tipos de gallinas
  const paletaColores = [
    "#3498db",
    "#e74c3c",
    "#f39c12",
    "#9b59b6",
    "#1abc9c",
    "#e67e22",
    "#16a085",
    "#d35400",
    "#8e44ad",
    "#27ae60",
  ];

  // Recolectar todos los tipos únicos de todos los galpones
  const tiposUnicos = new Set();
  galponesData.forEach((galpon) => {
    if (galpon.tipos && Array.isArray(galpon.tipos)) {
      galpon.tipos.forEach((t) => tiposUnicos.add(t.tipo));
    }
  });

  // Crear mapa de colores para cada tipo único
  const mapaColores = {};
  Array.from(tiposUnicos).forEach((tipo, idx) => {
    mapaColores[tipo] = paletaColores[idx % paletaColores.length];
  });

  // Calcular distribución total desde distData
  const totalGallinas = distData.reduce((sum, item) => sum + item.cantidad, 0);
  const distribucion = distData.map((item) => ({
    tipo: item.tipo,
    cantidad: item.cantidad,
    porcentaje: ((item.cantidad / totalGallinas) * 100).toFixed(1),
    color: mapaColores[item.tipo] || "#6c757d",
  }));

  const galponesHTML = galponesData
    .map((gal) => {
      const ocupacion = gal.ocupacion_porcentaje;
      const cantidadActual = gal.cantidad_actual;
      const capacidadDisponible = gal.capacidad - cantidadActual;
      const colorBorde = "#28a745";

      // Usar los tipos del galpón directamente desde gal.tipos
      let tiposGalpon = [];
      if (gal.tipos && Array.isArray(gal.tipos) && gal.tipos.length > 0) {
        tiposGalpon = gal.tipos.map((tipo) => ({
          tipo: tipo.tipo,
          cantidad: tipo.cantidad,
          porcentaje: tipo.porcentaje,
          color: mapaColores[tipo.tipo] || "#6c757d",
        }));
      }

      let rotacion = -90;
      const circunferencia = 283;

      const segmentos = tiposGalpon
        .map((tipo) => {
          const arcLength =
            (parseFloat(tipo.porcentaje) / 100) * circunferencia;
          const segmento = `
          <circle cx="60" cy="60" r="45" fill="none" stroke="${tipo.color}" stroke-width="12" 
            stroke-dasharray="${arcLength} ${circunferencia}"
            stroke-linecap="butt"
            style="transform: rotate(${rotacion}deg); transform-origin: 60px 60px;"/>
        `;
          rotacion += (parseFloat(tipo.porcentaje) / 100) * 360;
          return segmento;
        })
        .join("");

      return `
        <div class="galpon-card-item">
          <div class="card border-0 shadow-sm h-100" style="background: linear-gradient(135deg, ${colorBorde}10 0%, white 100%); border-left: 4px solid ${colorBorde};">
            <div class="card-body text-center p-3">
              <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                <h6 class="card-title mb-0" style="font-weight: 600;">${
                  gal.nombre
                }</h6>
                <div style="position: relative; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center;">
                  <svg viewBox="0 0 120 120" style="width: 130px; height: 130px; display: block;">
                    ${
                      tiposGalpon.length === 0
                        ? '<!-- Círculo base gris claro solo si no hay tipos --><circle cx="60" cy="60" r="45" fill="none" stroke="#e9ecef" stroke-width="12"/>'
                        : ""
                    }
                    <!-- Segmentos por tipo -->
                    ${segmentos}
                    <!-- Borde exterior -->
                    <circle cx="60" cy="60" r="51" fill="none" stroke="${colorBorde}" stroke-width="1" opacity="0.3"/>
                  </svg>
                  <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <div style="font-size: 28px; font-weight: bold; color: ${colorBorde}; line-height: 1;">${ocupacion}%</div>
                    <div style="font-size: 10px; color: #666; font-weight: 500; line-height: 1.2;">Ocupación</div>
                  </div>
                </div>
              </div>
              
              <!-- Información de capacidad -->
              <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 6px; font-size: 11px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="color: #666;">Actuales:</span>
                  <strong style="color: #333;">${cantidadActual}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                  <span style="color: #666;">Capacidad:</span>
                  <strong style="color: #333;">${gal.capacidad}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; border-top: 1px solid #dee2e6; padding-top: 5px; margin-top: 5px;">
                  <span style="color: #28a745;">Disponible:</span>
                  <strong style="color: #28a745;">${capacidadDisponible}</strong>
                </div>
              </div>

              <!-- Detalles por tipo (datos reales) -->
              <div style="margin-top: 10px; font-size: 10px; text-align: left;">
                ${
                  tiposGalpon.length > 0
                    ? tiposGalpon
                        .slice(0, 3)
                        .map(
                          (dt) => `
                      <div style="display: flex; align-items: center; gap: 6px; margin: 4px 0;">
                        <span style="width: 10px; height: 10px; background: ${dt.color}; border-radius: 2px; flex-shrink: 0;"></span>
                        <span style="flex: 1; color: #666;">${dt.tipo}:</span>
                        <strong style="color: #333;">${dt.cantidad}</strong>
                      </div>
                    `
                        )
                        .join("")
                    : '<div style="text-align: center; color: #999; padding: 8px;">Sin tipos registrados</div>'
                }
              </div>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  // Crear HTML completo
  const htmlCompleto = `
    <div class="col-12">
      <div class="card border-0 shadow-sm">
        <div class="card-body">
          <h5 class="card-title mb-4" style="font-weight: 600;">
            <i class="fas fa-warehouse me-2"></i>Estado de Galpones y Distribución
          </h5>
          <!-- Tarjetas de Galpones con scroll horizontal -->
          <div class="galpones-scroll overflow-auto mb-4" style="-ms-overflow-style: none; scrollbar-width: thin;">
            <div class="d-flex flex-row flex-nowrap gap-3">
              ${galponesHTML}
            </div>
          </div>
          <!-- Distribución Total -->
          <div class="row">
            <div class="col-12">
              <div style="padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;">
                <h6 class="mb-3" style="font-size: 14px; font-weight: 600;">
                  <i class="fas fa-chart-pie me-2"></i>Distribución Total
                </h6>
                <div class="row align-items-center">
                  <div class="col-md-9">
                    <div class="row">
                      ${distribucion
                        .map(
                          (dist) => `
                        <div class="col-md-4 col-6 mb-2">
                          <div style="display: flex; align-items: center; gap: 10px; padding: 8px; background: white; border-radius: 6px; border-left: 3px solid ${dist.color};">
                            <span style="width: 14px; height: 14px; background: ${dist.color}; border-radius: 3px; flex-shrink: 0;"></span>
                            <div style="flex: 1;">
                              <div style="font-size: 12px; font-weight: 600; color: #333;">${dist.tipo}</div>
                              <div style="font-size: 11px; color: #666;">${dist.cantidad} (${dist.porcentaje}%)</div>
                            </div>
                          </div>
                        </div>
                      `
                        )
                        .join("")}
                    </div>
                  </div>
                  <div class="col-md-3 text-center">
                    <div style="padding: 20px; background: white; border-radius: 8px; border: 2px solid #28a745;">
                      <div style="font-size: 12px; color: #666; margin-bottom: 8px; font-weight: 500;">Total General</div>
                      <div style="font-size: 36px; font-weight: bold; color: #28a745;">${totalGallinas}</div>
                      <div style="font-size: 11px; color: #666;">gallinas</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <style>
      .galpon-card-item { min-width: 260px; }
      .galpones-scroll::-webkit-scrollbar { height: 8px; }
      .galpones-scroll::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
      .galpones-scroll::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
      .galpones-scroll::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }
    </style>
  `;

  container.innerHTML = htmlCompleto;
}

// Nota: Las funciones cargarGraficoTipoGallina y cargarGraficoGalpones
// fueron removidas porque ya no se usan - el gráfico combinado las reemplaza

// Cargar incidentes recientes
function cargarIncidentes(incidentes) {
  const incidentesList = document.getElementById("incidentes-list");
  if (!incidentesList) {
    console.error("Elemento incidentes-list no encontrado");
    return;
  }

  if (!incidentes || incidentes.length === 0) {
    incidentesList.innerHTML =
      '<div class="text-center py-3 text-muted">No hay incidentes recientes</div>';
    return;
  }

  incidentesList.innerHTML = incidentes
    .map(
      (inc) => `
        <div class="list-group-item border-0 px-0">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <span class="badge bg-${inc.severidad} mb-1">${inc.tipo}</span>
                    <p class="mb-0 small">${inc.descripcion}</p>
                    <small class="text-muted">${inc.tiempo}</small>
                </div>
                <i class="fas fa-chevron-right text-muted"></i>
            </div>
        </div>
    `
    )
    .join("");
}

// Actualizar datos de sensores
function actualizarSensoresData(sensores) {
  const tempEl = document.getElementById("sensor-temp");
  const humEl = document.getElementById("sensor-hum");
  // const co2El = document.getElementById("sensor-co2");
  // const luzEl = document.getElementById("sensor-luz");

  if (tempEl) tempEl.textContent = sensores.temperatura.toFixed(1) + "°C";
  if (humEl) humEl.textContent = sensores.humedad.toFixed(0) + "%";
  // if (co2El) co2El.textContent = sensores.co2 + " ppm";
  // if (luzEl) luzEl.textContent = sensores.luminosidad + " lux";
}

// Cargar actividad reciente
function cargarActividadReciente(actividades) {
  const actividadContainer = document.getElementById("actividad-reciente");
  if (!actividadContainer) {
    console.error("Elemento actividad-reciente no encontrado");
    return;
  }

  if (!actividades || actividades.length === 0) {
    actividadContainer.innerHTML =
      '<div class="text-center py-3 text-muted">No hay actividad reciente</div>';
    return;
  }

  actividadContainer.innerHTML = actividades
    .map(
      (act) => `
        <div class="timeline-item">
            <div class="timeline-marker bg-${act.color}"></div>
            <div class="timeline-content">
                <small class="text-muted d-block">${act.tiempo}</small>
                <p class="mb-0">${act.descripcion}</p>
            </div>
        </div>
    `
    )
    .join("");
}

// Mostrar mensaje de error
function mostrarError(mensaje) {
  console.error(mensaje);
  Swal.fire({
    icon: "error",
    title: "Error",
    text: mensaje,
    confirmButtonText: "Aceptar",
  });
}

// Función de inicialización
export function init() {
  // Cargar datos inmediatamente (el servicio ya está disponible)
  setTimeout(() => {
    cargarDatosDashboard();
  }, 100);

  // Filtros de producción
  const radios = document.querySelectorAll('input[name="rangoProduccion"]');
  radios.forEach((r) => {
    r.addEventListener("change", async (e) => {
      const dias = parseInt(e.target.value, 10) || 7;
      await cargarGraficoProduccionRango(dias);
    });
  });
}
