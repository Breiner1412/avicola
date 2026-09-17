import { incident_chickenService } from "../api/incidente-gallina.service.js";
import { isolationService } from "../api/aislamiento.service.js";

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
let modalInstance = null;
let activeFechaInicio = "";
let activeFechaFin = "";

// Variables para manejar todos los datos
let allIncidents = [];
let filteredIncidents = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 10;

// Variables del nuevo código
let cacheGalpones = null;
let currentSelectedGalponId = null;
let isCurrentGalponActive = false;

// Variable para controlar si ya se inicializó la exportación
let exportInitialized = false;

// =======================
// 1. CARGA DE SELECTS (Filtros y Modales) - VERSIÓN INTEGRADA
// =======================

async function cargarSelectFilterGalpones() {
  const selectFilter = document.getElementById("filter-galpon-inci");

  if (!selectFilter) {
    return;
  }

  try {
    if (!cacheGalpones) {
      cacheGalpones = await incident_chickenService.getGalponesAll();
    }

    const options = cacheGalpones
      .map((g) => {
        const label = g.estado ? g.nombre : `${g.nombre} (Inactivo)`;
        return `<option value="${g.id_galpon}">${label}</option>`;
      })
      .join("");

    selectFilter.innerHTML = `
            <option value="">Seleccione un galpón</option>
            <option value="todos">Ver todos los galpones</option>
            ${options}
        `;

    selectFilter.removeEventListener("change", onGalponChange);
    selectFilter.addEventListener("change", onGalponChange);
  } catch (error) {
    console.error("Error cargando filtro galpones:", error);
    selectFilter.innerHTML = `<option value="">Error al cargar</option>`;
  }
}

// =======================
// 2. FUNCIÓN PARA OBTENER INCIDENTES CON PAGINACIÓN
// =======================

async function fetchIncidentesGallina(
  page = 1,
  page_size = 10,
  fechaInicio = "",
  fechaFin = ""
) {
  try {
    let data;

    if (fechaInicio && fechaFin) {
      const fechaInicioFormateada = formatDateForAPI(fechaInicio);
      const fechaFinFormateada = formatDateForAPI(fechaFin);

      data = await incident_chickenService.getIsolationAllDate(
        fechaInicioFormateada,
        fechaFinFormateada
      );
    } else {
      data = await incident_chickenService.getIsolationAll(page, page_size);
    }

    return {
      incidents: data.incidents || [],
      total: data.total || 0,
      currentPage: data.currentPage || page,
      totalPages: data.totalPages || 1,
    };
  } catch (error) {
     console.error("Error al obtener incidentes:", error);
    if (
      error.message.includes("No hay incidentes") ||
      error.message.includes("422") ||
      error.response?.status === 422 ||
      error.response?.status === 404
    ) {
      return {
        incidents: [],
        total: 0,
        currentPage: page,
        totalPages: 1,
      };
    }

    throw error;
  }
}

// =======================
// 3. MANEJO DEL CAMBIO DE GALPÓN EN FILTRO
// =======================

async function onGalponChange(e) {
  const galponId = e.target.value;
  currentSelectedGalponId = galponId || null;

  const tbody = document.getElementById("incidente-gallina-table-body");
  if (!tbody) return;

  if (galponId === "") {
    tbody.innerHTML =
      '<tr><td colspan="7" class="text-center">Seleccione un galpón para ver los incidentes.</td></tr>';
    ocultarFiltrosYPaginacion();
    actualizarBotonAgregar();
    return;
  }

  if (galponId !== "todos" && galponId !== "") {
    isCurrentGalponActive = verificarEstadoGalpon(galponId);
  } else if (galponId === "todos") {
    isCurrentGalponActive = true;
  }

  tbody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando incidentes...</td></tr>';

  try {
    currentPage = 1;
    await aplicarFiltros();
    actualizarBotonAgregar();
  } catch (error) {
    console.error("Error al cargar incidentes:", error);
    tbody.innerHTML =
      '<tr><td colspan="7" class="text-center">Error al cargar incidentes</td></tr>';
    mostrarFiltrosYPaginacion();
    actualizarBotonAgregar();
  }
}

function verificarEstadoGalpon(galponId) {
  if (!cacheGalpones || !galponId) return false;
  const galpon = cacheGalpones.find(
    (g) => String(g.id_galpon) === String(galponId)
  );
  return galpon && galpon.estado === true;
}

// =======================
// 4. FUNCIONES DE UI/UX
// =======================

function mostrarFiltrosYPaginacion() {
  const dateFilters = document.getElementById("filters");
  const paginationContainer = document.getElementById("pagination-container");
  if (dateFilters) dateFilters.classList.remove("d-none");
  if (paginationContainer) paginationContainer.classList.remove("d-none");
}

function ocultarFiltrosYPaginacion() {
  const dateFilters = document.getElementById("filters");
  const paginationContainer = document.getElementById("pagination-container");
  if (dateFilters) dateFilters.classList.add("d-none");
  if (paginationContainer) paginationContainer.classList.add("d-none");
}

function actualizarBotonAgregar() {
  const btnAgregar = document.querySelector(
    '[data-bs-target="#createIncidenteGallinaModal"]'
  );
  if (btnAgregar) {
    if (currentSelectedGalponId === "todos") {
      btnAgregar.disabled = false;
      btnAgregar.classList.remove("btn-secondary");
      btnAgregar.classList.add("btn-success");
    } else if (
      isCurrentGalponActive &&
      currentSelectedGalponId &&
      currentSelectedGalponId !== ""
    ) {
      btnAgregar.disabled = false;
      btnAgregar.classList.remove("btn-secondary");
      btnAgregar.classList.add("btn-success");
    } else {
      btnAgregar.disabled = true;
      btnAgregar.classList.remove("btn-success");
      btnAgregar.classList.add("btn-secondary");
    }
  }
}

// =======================
// 5. FORMATO DE FECHAS PARA API
// =======================
function formatDateForAPI(dateStr) {
  if (!dateStr) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return dateStr;
  }
  const date = new Date(dateStr);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

// =======================
// 6. APLICAR TODOS LOS FILTROS CON PAGINACIÓN
// =======================

async function aplicarFiltros() {
  const tableBody = document.getElementById("incidente-gallina-table-body");
  if (!tableBody) {
  
    return;
  }

  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando incidentes...</td></tr>';

  try {
    const response = await fetchIncidentesGallina(
      currentPage,
      ITEMS_PER_PAGE,
      activeFechaInicio,
      activeFechaFin
    );

    allIncidents = response.incidents || [];
    const totalItems = response.total || 0;
    const totalPages = response.totalPages || 1;

    if (currentSelectedGalponId === "todos") {
      filteredIncidents = [...allIncidents];
    } else if (
      currentSelectedGalponId &&
      currentSelectedGalponId !== "" &&
      currentSelectedGalponId !== "todos"
    ) {
      filteredIncidents = allIncidents.filter(
        (inc) => String(inc.galpon_origen) === String(currentSelectedGalponId)
      );
    } else {
      filteredIncidents = [];
    }

    renderizarResultados(totalPages, totalItems);
  } catch (error) {
    tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
                    <div class="alert alert-danger mt-3">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error al cargar los datos: ${
                          error.message || "Error desconocido"
                        }
                    </div>
                </td>
            </tr>
        `;
  }
}

function renderizarResultados(totalPages = 1, totalItems = 0) {
  const tableBody = document.getElementById("incidente-gallina-table-body");
  if (!tableBody) return;

  if (filteredIncidents.length === 0) {
    let mensaje = '<tr><td colspan="7" class="text-center">';

    if (currentSelectedGalponId === "todos") {
      mensaje += `
                <div class="alert alert-info mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No se encontraron incidentes en el sistema.
                </div>
            `;
    } else if (
      currentSelectedGalponId &&
      currentSelectedGalponId !== "" &&
      currentSelectedGalponId !== "todos"
    ) {
      const galponNombre =
        cacheGalpones?.find(
          (g) => String(g.id_galpon) === String(currentSelectedGalponId)
        )?.nombre || "seleccionado";

      const galponEstado = cacheGalpones?.find(
        (g) => String(g.id_galpon) === String(currentSelectedGalponId)
      )?.estado;

      if (!galponEstado) {
        mensaje += `
                  <div class="alert alert-warning mt-3">
                      <i class="fas fa-exclamation-triangle me-2"></i>
                      El galpón <strong>${galponNombre}</strong> está inactivo.
                  </div>
              `;
      } else {
        mensaje += `
                <div class="alert alert-info mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No se encontraron incidentes para el galpón: 
                    <strong>${galponNombre}</strong>
                </div>
            `;
      }
    } else if (activeFechaInicio && activeFechaFin) {
      mensaje += `
                <div class="alert alert-info mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No se encontraron incidentes en el rango de fechas:<br>
                    <strong>${activeFechaInicio} a ${activeFechaFin}</strong>
                </div>
            `;
    }

    mensaje += "</td></tr>";
    tableBody.innerHTML = mensaje;
    renderPagination(totalPages, currentPage);
    return;
  }

  mostrarFiltrosYPaginacion();

  tableBody.innerHTML = filteredIncidents.map(createIncidentRow).join("");

  renderPagination(totalPages, currentPage);
}

function createIncidentRow(incident) {
  const incidentId = incident.id_inc_gallina;

  const fecha = new Date(incident.fecha_hora);
  const fechaFormateada = fecha.toLocaleString("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
    hour12: true,
  });

  const galpon = cacheGalpones?.find(
    (g) => String(g.id_galpon) === String(incident.galpon_origen)
  );
  const nombreGalpon = galpon
    ? galpon.estado
      ? galpon.nombre
      : `${galpon.nombre} (Inactivo)`
    : incident.nombre;

  const isMobile = window.innerWidth < 768;

  if (isMobile) {
    return `
      <tr>
        <td class="px-0 ${galpon && !galpon.estado ? "text-danger" : ""}">
          <div class="d-flex flex-column">
            <small class="fw-bold">${nombreGalpon}</small>
            <small class="text-muted">${incident.tipo_incidente}</small>
          </div>
        </td>
        <td class="px-0">
          <div class="d-flex flex-column">
            <small class="fw-bold">${incident.cantidad}</small>
            <small class="text-muted">Cantidad</small>
          </div>
        </td>
        <td class="px-0">
          <div class="d-flex flex-column align-items-end">
            <div class="form-check form-switch mb-1">
              <input class="form-check-input incident-status-switch" type="checkbox" role="switch" 
                     id="switch-${incidentId}" data-incident-id="${incidentId}" 
                     ${incident.esta_resuelto ? "checked" : ""}>
              <label class="form-check-label small" for="switch-${incidentId}">
                ${incident.esta_resuelto ? "Resuelto" : "Pendiente"}
              </label>
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-success btn-sm btn-edit-incident" data-incident-id="${incidentId}" aria-label="Editar">
                <i class="fa-regular fa-pen-to-square"></i>
              </button>
              <button class="btn btn-success btn-sm btn-aislar" data-id-inc-gallina="${incidentId}" data-id-galpon="${
      incident.galpon_origen
    }" aria-label="Aislar">
                <i class="fa-solid fa-kit-medical"></i>
              </button>
            </div>
          </div>
        </td>
      </tr>
    `;
  }

  return `
    <tr>
      <td class="px-0 ${galpon && !galpon.estado ? "text-danger" : ""}">
        ${nombreGalpon}
      </td>
      <td class="px-0">${incident.tipo_incidente}</td>
      <td class="px-0">${incident.cantidad}</td>
      <td class="px-0">${incident.descripcion}</td>
      <td class="px-0">
        <div class="form-check form-switch ms-2 d-inline-block">
          <input class="form-check-input incident-status-switch" type="checkbox" role="switch" 
                 id="switch-${incidentId}" data-incident-id="${incidentId}" 
                 ${incident.esta_resuelto ? "checked" : ""}>
          <label class="form-check-label" for="switch-${incidentId}">
            ${incident.esta_resuelto ? "Resuelto" : "Pendiente"}
          </label>
        </div>
      </td>
      <td class="px-0">${fechaFormateada}</td>
      <td class="text-end">
        <div class="btn-group btn-group-sm">
          <button class="btn btn-sm btn-success btn-edit-incident" data-incident-id="${incidentId}" aria-label="Editar">
            <i class="fa-regular fa-pen-to-square me-0"></i>
          </button>
          <button class="btn btn-sm btn-success btn-aislar" data-id-inc-gallina="${incidentId}" data-id-galpon="${
    incident.galpon_origen
  }" aria-label="Aislar">
            <i class="fa-solid fa-kit-medical me-0"></i>
          </button>
        </div>
      </td>
    </tr>
  `;
}

// =======================
// 7. PAGINACIÓN PARA TODOS LOS DATOS Y FILTRADOS
// =======================

function renderPagination(total_pages, currentPageNum = 1) {
  const container = document.querySelector("#pagination");
  if (!container) return;

  container.innerHTML = "";

  // ---------- BOTÓN ANTERIOR ----------
  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPageNum === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPageNum - 1
        }">
            <i class="fas fa-chevron-left"></i>
        </a>
    `;
  prevLi.addEventListener("click", () => {
    if (currentPageNum !== 1) {
      const prevPage = currentPageNum - 1;
      init(prevPage, ITEMS_PER_PAGE, activeFechaInicio, activeFechaFin);
    }
  });
  container.appendChild(prevLi);

  const maxVisible = 5;
  let startPage = Math.max(1, currentPageNum - Math.floor(maxVisible / 2));
  let endPage = Math.min(total_pages, startPage + maxVisible - 1);

  if (endPage - startPage + 1 < maxVisible) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  // ---------- PRIMERA PÁGINA + ... ----------
  if (startPage > 1) {
    container.appendChild(createPageLi(1, currentPageNum));
    if (startPage > 2) container.appendChild(createDotsLi());
  }

  // ---------- NÚMEROS DE PÁGINA ----------
  for (let i = startPage; i <= endPage; i++) {
    container.appendChild(createPageLi(i, currentPageNum));
  }

  // ---------- ... + ÚLTIMA PÁGINA ----------
  if (endPage < total_pages) {
    if (endPage < total_pages - 1) container.appendChild(createDotsLi());
    container.appendChild(createPageLi(total_pages, currentPageNum));
  }

  // ---------- BOTÓN SIGUIENTE ----------
  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${
    currentPageNum === total_pages ? "disabled" : ""
  }`;
  nextLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPageNum + 1
        }">
            <i class="fas fa-chevron-right"></i>
        </a>
    `;
  nextLi.addEventListener("click", () => {
    if (currentPageNum !== total_pages) {
      const nextPage = currentPageNum + 1;
      init(nextPage, ITEMS_PER_PAGE, activeFechaInicio, activeFechaFin);
    }
  });
  container.appendChild(nextLi);
}

// ========== BOTÓN DE NÚMERO DE PÁGINA ==========
function createPageLi(page, currentPageNum) {
  const li = document.createElement("li");

  const isActive = page === currentPageNum;

  li.className = `page-item ${isActive ? "active" : ""}`;
  li.innerHTML = `
        <a class="page-link ${
          isActive ? "bg-success border-success text-white" : "text-success"
        }"
           href="#" data-page="${page}">
           ${page}
        </a>
    `;

  li.addEventListener("click", () => {
    if (!isActive) {
      init(page, ITEMS_PER_PAGE, activeFechaInicio, activeFechaFin);
    }
  });

  return li;
}

// ========== PUNTOS SUSPENSIVOS ==========
function createDotsLi() {
  const li = document.createElement("li");
  li.className = "page-item disabled";
  li.innerHTML = `<a class="page-link text-success">...</a>`;
  return li;
}

// =======================
// 8. FUNCIONES PARA AISLAMIENTOS
// =======================

async function renderIncidentes() {
  try {
    const [incidentes, isolations] = await Promise.all([
      incident_chickenService.getChickenIncidents(),
      isolationService.getIsolations(),
    ]);

    const aislados = new Set(isolations.map((i) => i.id_incidente_gallina));

    incidentes.forEach((inc) => {
      const btn = document.querySelector(
        `[data-id-inc-gallina="${inc.id_inc_gallina}"]`
      );
      if (!btn) return;

      if (aislados.has(inc.id_inc_gallina)) {
        btn.disabled = true;
        btn.classList.add("disabled");
      }
    });
  } catch (error) {
    console.error("Error al renderizar incidentes:", error);
  }
}

const observer = new MutationObserver(() => {
  const botones = document.querySelectorAll(".btn-aislar");
  if (botones.length > 0) {
    renderIncidentes();
  }
});

observer.observe(document.getElementById("main-content"), {
  childList: true,
  subtree: true,
});

function obtenerFecha() {
  const fechaLocal = new Date();
  const pad = (n) => n.toString().padStart(2, "0");
  const fechaPC = `${fechaLocal.getFullYear()}-${pad(
    fechaLocal.getMonth() + 1
  )}-${pad(fechaLocal.getDate())} ${pad(fechaLocal.getHours())}:${pad(
    fechaLocal.getMinutes()
  )}:${pad(fechaLocal.getSeconds())}`;
  return fechaPC;
}

// =======================
// 9. EVENT LISTENERS PARA AISLAMIENTOS
// =======================

// Botón "Aislamientos": navega con el cargador central (main.js)
document.addEventListener("click", (e) => {
  const btn = e.target.closest("#isolations");
  if (!btn) return;
  e.preventDefault();
  window.loadContent("aislamientos");
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn-aislar");
  if (!btn) return;

  const id_inc_gallina = btn.dataset.idIncGallina;
  const id_galpon = btn.dataset.idGalpon;

  if (!id_inc_gallina || !id_galpon) return;

  aislarGallina(id_inc_gallina, id_galpon, btn);
});

async function aislarGallina(id_incidente_gallina, galpon_origen, btn) {
  try {
    const newIsolationData = {
      id_incidente_gallina: id_incidente_gallina,
      id_galpon: galpon_origen,
      fecha_hora: obtenerFecha(),
    };

    await isolationService.createIsolation(newIsolationData);
    btn.disabled = true;
    btn.classList.add("disabled");

    Swal.fire({
      icon: "success",
      title: "¡Gallina enviada a aislamiento!",
      text: "El aislamiento se registró correctamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "Ocurrió un error al registrar el aislamiento",
      confirmButtonColor: "#d33",
    });
  }
}

// =======================
// 10. FUNCIONES PARA FILTROS
// =======================

function filtrarIncidentes(fechaInicio, fechaFin) {
  if (!fechaInicio || !fechaFin) {
    Swal.fire({
      icon: "info",
      title: "Error",
      text: "Debe seleccionar ambas fechas",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    return;
  }

  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;
  currentPage = 1;
  aplicarFiltros();
}

function limpiarFiltros() {
  activeFechaInicio = "";
  activeFechaFin = "";
  currentSelectedGalponId = null;
  currentPage = 1;

  document.getElementById("fecha-inicio").value = "";
  document.getElementById("fecha-fin").value = "";
  document.getElementById("search-incidente-gallina").value = "";

  const galponSelect = document.getElementById("filter-galpon-inci");
  if (galponSelect) {
    galponSelect.value = "";
  }

  const tbody = document.getElementById("incidente-gallina-table-body");
  if (tbody) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="text-center">Seleccione un galpón para ver los incidentes.</td></tr>';
  }

  ocultarFiltrosYPaginacion();
  actualizarBotonAgregar();
}

// =======================
// 11. FUNCIONES PARA MODALES
// =======================

// Función unificada para cargar selects de modales
async function initializeSelects(selectType, selectedValue = null) {
  try {
    if (!cacheGalpones) {
      cacheGalpones = await incident_chickenService.getGalponesAll();
    }

    const galponesActivos = cacheGalpones.filter((g) => g.estado === true);

    switch (selectType) {
      case "galpones-create-modal":
        const selectCreate = document.getElementById("create_id_galpon");
        if (!selectCreate) return;

        if (
          currentSelectedGalponId &&
          currentSelectedGalponId !== "" &&
          currentSelectedGalponId !== "todos"
        ) {
          const galponSeleccionado = cacheGalpones.find(
            (g) => String(g.id_galpon) === String(currentSelectedGalponId)
          );
          if (galponSeleccionado) {
            if (galponSeleccionado.estado) {
              selectCreate.innerHTML = `
                        <option value="${galponSeleccionado.id_galpon}" selected>
                            ${galponSeleccionado.nombre}
                        </option>`;
              selectCreate.disabled = true;
            } else {
              selectCreate.innerHTML = `
                        <option value="" disabled selected>
                            No se puede crear en galpones inactivos
                        </option>`;
              selectCreate.disabled = true;
            }
          }
        } else {
          selectCreate.innerHTML =
            '<option value="">Seleccione un galpón</option>' +
            galponesActivos
              .map((g) => `<option value="${g.id_galpon}">${g.nombre}</option>`)
              .join("");
          selectCreate.disabled = false;
        }

        if (window.$ && $(selectCreate).select2) {
          $(selectCreate).select2({
            dropdownParent: $("#createIncidenteGallinaModal"),
            width: "100%",
            placeholder: "Selecciona un galpón",
            allowClear: true,
          });
        }
        break;

      case "galpones-edit-modal":
        const selectEdit = document.getElementById("edit_id_galpon");
        if (!selectEdit) return;

        selectEdit.innerHTML =
          `<option value="" disabled selected>Seleccione un galpón</option>` +
          galponesActivos
            .map(
              (g) =>
                `<option value="${g.id_galpon}" ${
                  g.id_galpon == selectedValue ? "selected" : ""
                }>${g.nombre}</option>`
            )
            .join("");
        break;

      case "tipos-incidente-create":
        const selectTipoCreate = document.getElementById(
          "tipo_incidente_create"
        );
        if (!selectTipoCreate) return;

        const tiposCreate = [
          "Enfermedad",
          "Herida",
          "Muerte",
          "Fuga",
          "Ataque Depredador",
          "Produccion",
          "Alimentacion",
          "Plaga",
          "Estres termico",
          "Otro",
        ];

        selectTipoCreate.innerHTML =
          '<option value="" disabled selected>Seleccione un tipo</option>' +
          tiposCreate
            .map((tipo) => `<option value="${tipo}">${tipo}</option>`)
            .join("");
        break;

      case "tipos-incidente-edit":
        const selectTipoEdit = document.getElementById("edit-tipo_incidente");
        if (!selectTipoEdit) return;

        const tiposEdit = [
          "Enfermedad",
          "Herida",
          "Muerte",
          "Fuga",
          "Ataque Depredador",
          "Produccion",
          "Alimentacion",
          "Plaga",
          "Estres termico",
          "Otro",
        ];

        selectTipoEdit.innerHTML =
          '<option value="" disabled selected>Seleccione un tipo</option>' +
          tiposEdit
            .map(
              (tipo) =>
                `<option value="${tipo}" ${
                  tipo === selectedValue ? "selected" : ""
                }>${tipo}</option>`
            )
            .join("");
        break;

      default:
        console.warn("Tipo de select no reconocido:", selectType);
    }
  } catch (error) {
    console.error(`Error al inicializar select ${selectType}:`, error);
  }
}

async function openEditModal(id_incidente_gallina) {
  const modalElement = document.getElementById("editIncidenteGallinaModal");
  modalInstance = bootstrap.Modal.getOrCreateInstance(modalElement);

  try {
    const incident = await incident_chickenService.getChickenIncidentById(
      id_incidente_gallina
    );

    document.getElementById("edit-id_inc_gallina").value =
      incident.id_inc_gallina;
    document.getElementById("edit-cantidad").value = incident.cantidad;
    document.getElementById("edit-descripcion").value = incident.descripcion;

    await initializeSelects("galpones-edit-modal", incident.galpon_origen);
    await initializeSelects("tipos-incidente-edit", incident.tipo_incidente);

    modalInstance.show();
  } catch (error) {
    console.error("Error al abrir modal:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del incidente",
      confirmButtonColor: "#d33",
    });
  }
}

async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-incident");
  if (editButton) {
    const idIncidente = editButton.dataset.incidentId;
    await openEditModal(idIncidente);
    return;
  }
}

async function handleUpdateSubmit(event) {
  event.preventDefault();
  const incidentId = document.getElementById("edit-id_inc_gallina").value;

  const updatedData = {
    galpon_origen: parseInt(document.getElementById("edit_id_galpon").value),
    tipo_incidente: document.getElementById("edit-tipo_incidente").value,
    cantidad: parseInt(document.getElementById("edit-cantidad").value),
    descripcion: document.getElementById("edit-descripcion").value,
  };

  try {
    await incident_chickenService.updateChickenIncident(
      incidentId,
      updatedData
    );
    modalInstance.hide();
    aplicarFiltros();

    const isolations = await isolationService.getIsolations();
    const existingIsolation = isolations.find(
      (i) => i.id_incidente_gallina == incidentId
    );

    if (existingIsolation) {
      const nuevoGalpon = updatedData.galpon_origen;
      await isolationService.updateIsolation(existingIsolation.id_aislamiento, {
        id_galpon: nuevoGalpon,
      });
    }

    Swal.fire({
      icon: "success",
      title: "¡Actualizado!",
      text: "Incidente y aislamiento actualizados correctamente.",
      confirmButtonColor: "#28a745",
    });
  } catch (error) {
    console.error("Error al actualizar:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo actualizar el incidente",
      confirmButtonColor: "#d33",
    });
  }
}

async function handleCreateSubmit(event) {
  event.preventDefault();

  const fechaLocal = new Date();
  const pad = (n) => n.toString().padStart(2, "0");
  const fechaPC = `${fechaLocal.getFullYear()}-${pad(
    fechaLocal.getMonth() + 1
  )}-${pad(fechaLocal.getDate())} ${pad(fechaLocal.getHours())}:${pad(
    fechaLocal.getMinutes()
  )}:${pad(fechaLocal.getSeconds())}`;

  let galponSeleccionado;
  if (
    currentSelectedGalponId &&
    currentSelectedGalponId !== "" &&
    currentSelectedGalponId !== "todos"
  ) {
    galponSeleccionado = parseInt(currentSelectedGalponId);
  } else {
    galponSeleccionado = parseInt(
      document.getElementById("create_id_galpon").value
    );
  }

  const newIncidentData = {
    galpon_origen: galponSeleccionado,
    tipo_incidente: document.getElementById("tipo_incidente_create").value,
    cantidad: parseInt(document.getElementById("cantidad").value),
    descripcion: document.getElementById("description").value,
    fecha_hora: fechaPC,
    esta_resuelto: false,
  };

  if (!newIncidentData.galpon_origen || newIncidentData.galpon_origen <= 0) {
    Swal.fire({
      icon: "error",
      title: "Error de validación",
      text: "Debe seleccionar un galpón válido",
      confirmButtonColor: "#d33",
    });
    return;
  }

  if (!newIncidentData.tipo_incidente) {
    Swal.fire({
      icon: "error",
      title: "Error de validación",
      text: "Debe seleccionar un tipo de incidente",
      confirmButtonColor: "#d33",
    });
    return;
  }

  if (!newIncidentData.cantidad || newIncidentData.cantidad < 0) {
    Swal.fire({
      icon: "error",
      title: "Error de validación",
      text: "La cantidad debe ser un número positivo",
      confirmButtonColor: "#d33",
    });
    return;
  }

  try {
    await incident_chickenService.createChickenIncident(newIncidentData);

    const createIncidenteModalEl = document.getElementById(
      "createIncidenteGallinaModal"
    );
    const createIncidenteModalInstance = bootstrap.Modal.getInstance(
      createIncidenteModalEl
    );
    createIncidenteModalInstance.hide();

    createIncidenteModalEl.addEventListener(
      "hidden.bs.modal",
      function handler() {
        createIncidenteModalEl.removeEventListener("hidden.bs.modal", handler);
        document.getElementById("create-incidente-gallina-form").reset();

        Swal.fire({
          icon: "success",
          title: "¡Guardado!",
          text: "Incidente creado correctamente.",
          confirmButtonColor: "#28a745",
        });

        aplicarFiltros();
      }
    );
  } catch (error) {
    console.error("Error al crear incidente:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "Error al crear el incidente",
      confirmButtonColor: "#d33",
    });
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;

  if (!switchElement.classList.contains("incident-status-switch")) return;

  const incidentId = switchElement.dataset.incidentId;
  const newStatus = switchElement.checked;
  const actionText = newStatus ? "resuelto" : "pendiente";

  const result = await Swal.fire({
    title: "¿Estás seguro?",
    text: `¿Deseas cambiar a ${actionText} este incidente?`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#28a745",
    cancelButtonColor: "#6c757d",
    confirmButtonText: "Sí, cambiar",
    cancelButtonText: "Cancelar",
  });

  if (result.isConfirmed) {
    try {
      await incident_chickenService.changeChickenStatus(incidentId, newStatus);

      const label = switchElement.nextElementSibling;
      if (label) label.textContent = newStatus ? "Resuelto" : "Pendiente";

      await Swal.fire({
        icon: "success",
        title: "¡Guardado!",
        text: "Se cambio exitosamente.",
        confirmButtonColor: "#28a745",
      });
    } catch (error) {
      console.error("Error:", error);
      switchElement.checked = !newStatus;
      await Swal.fire({
        title: "Error",
        text: "No se pudo cambiar el estado del incidente",
        icon: "error",
        confirmButtonText: "Aceptar",
      });
    }
  } else {
    switchElement.checked = !newStatus;
  }
}

// =======================
// 12. BUSCADOR INTELIGENTE
// =======================

function inicializarBuscador() {
  const BuscarIncidente = document.getElementById("search-incidente-gallina");

  if (BuscarIncidente) {
    BuscarIncidente.replaceWith(BuscarIncidente.cloneNode(true));
    const nuevoInput = document.getElementById("search-incidente-gallina");

    nuevoInput.addEventListener("input", () => {
      const filter = nuevoInput.value.toLowerCase();
      const tableBody = document.getElementById("incidente-gallina-table-body");
      if (!tableBody) return;

      const rows = tableBody.querySelectorAll("tr");

      rows.forEach((row) => {
        const galponCell = row.cells[0]?.textContent.toLowerCase() || "";
        const tipoCell = row.cells[1]?.textContent.toLowerCase() || "";
        const cantidadCell = row.cells[2]?.textContent.toLowerCase() || "";
        const descripcionCell = row.cells[3]?.textContent.toLowerCase() || "";
        const estadoCell = row.cells[4]?.textContent.toLowerCase() || "";
        const fechaCell = row.cells[5]?.textContent.toLowerCase() || "";

        const match =
          galponCell.includes(filter) ||
          tipoCell.includes(filter) ||
          cantidadCell.includes(filter) ||
          descripcionCell.includes(filter) ||
          estadoCell.includes(filter) ||
          fechaCell.includes(filter);
        row.style.display = match ? "" : "none";
      });
    });
  }
}

// =======================
// 13. FILTRO POR FECHAS
// =======================

function inicializarFiltroFechas() {
  const btnApplyFilter = document.getElementById("btn-apply-date-filter");
  const btnClear = document.getElementById("btn_clear_filters");

  if (btnApplyFilter) {
    btnApplyFilter.replaceWith(btnApplyFilter.cloneNode(true));
    const nuevoBtn = document.getElementById("btn-apply-date-filter");

    nuevoBtn.addEventListener("click", () => {
      const fechaInicio = document.getElementById("fecha-inicio").value;
      const fechaFin = document.getElementById("fecha-fin").value;
      filtrarIncidentes(fechaInicio, fechaFin);
    });
  }

  if (btnClear) {
    btnClear.replaceWith(btnClear.cloneNode(true));
    const nuevoBtnClear = document.getElementById("btn_clear_filters");

    nuevoBtnClear.addEventListener("click", limpiarFiltros);
  }
}

// =======================
// 14. MANEJO DEL MODAL DE CREAR
// =======================

function setupCreateModalHandler() {
  const createModalElement = document.getElementById(
    "createIncidenteGallinaModal"
  );
  if (!createModalElement) {
    console.warn("No se encontró el modal de crear incidente");
    return;
  }

  createModalElement.addEventListener("show.bs.modal", async function () {
    await initializeSelects("galpones-create-modal");
    await initializeSelects("tipos-incidente-create");

    if (
      currentSelectedGalponId &&
      currentSelectedGalponId !== "" &&
      currentSelectedGalponId !== "todos"
    ) {
      const selectCreate = document.getElementById("create_id_galpon");
      if (selectCreate) {
        selectCreate.value = currentSelectedGalponId;
        selectCreate.disabled = true;

        if (window.$ && $(selectCreate).data("select2")) {
          $(selectCreate).val(currentSelectedGalponId).trigger("change");
          $(selectCreate).prop("disabled", true);
        }
      }
    } else {
      const selectCreate = document.getElementById("create_id_galpon");
      if (selectCreate) {
        selectCreate.disabled = false;
        if (window.$ && $(selectCreate).data("select2")) {
          $(selectCreate).prop("disabled", false);
        }
      }
    }
  });

  createModalElement.addEventListener("hidden.bs.modal", function () {
    const createForm = document.getElementById("create-incidente-gallina-form");
    if (createForm) {
      createForm.reset();

      const selectCreate = document.getElementById("create_id_galpon");
      if (selectCreate) {
        selectCreate.disabled = false;
      }
    }
  });
}

// =======================
// 15. FUNCIONES DE EXPORTACIÓN
// =======================

function formatDateTimeExport(datetimeStr) {
  if (!datetimeStr) return "";

  try {
    const date = new Date(datetimeStr);

    if (isNaN(date.getTime())) {
      return datetimeStr;
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    let hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");

    const ampm = hours >= 12 ? "pm" : "am";
    hours = hours % 12;
    hours = hours === 0 ? 12 : hours;

    return `${year}-${month}-${day}, ${hours}:${minutes}:${seconds} ${ampm}`;
  } catch (error) {
    return datetimeStr;
  }
}






const COLUMNAS_EXPORTACION = [
  { header: "ID Incidente", key: "id_inc_gallina" },
  { header: "Galpón", key: (r) => r.nombre || r.galpon_origen },
  { header: "Tipo de Incidente", key: "tipo_incidente" },
  { header: "Cantidad", key: "cantidad" },
  { header: "Descripción", key: "descripcion" },
  { header: "Estado", key: (r) => (r.esta_resuelto ? "Resuelto" : "Pendiente") },
  { header: "Fecha y Hora", key: (r) => formatDateTimeExport(r.fecha_hora) },
];

// Filtros activos para el encabezado del PDF
function subtitulosExportacion() {
  const lineas = [];
  if (currentSelectedGalponId === "todos") {
    lineas.push("Filtro: Todos los galpones");
  } else if (currentSelectedGalponId) {
    const nombre =
      cacheGalpones?.find((g) => String(g.id_galpon) === String(currentSelectedGalponId))?.nombre ||
      "Galpón seleccionado";
    lineas.push(`Filtro: ${nombre}`);
  }
  if (activeFechaInicio && activeFechaFin) {
    lineas.push(`Rango de fechas: ${activeFechaInicio} a ${activeFechaFin}`);
  }
  return lineas;
}

function exportIncidentesToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportIncidentesToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Incidentes Gallina");
}

async function exportIncidentesToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Incidentes de Gallina", subtitulosExportacion());
}

async function fetchIncidentesForExport() {
  try {
    let data;

    if (activeFechaInicio && activeFechaFin) {
      const fechaInicioFormateada = formatDateForAPI(activeFechaInicio);
      const fechaFinFormateada = formatDateForAPI(activeFechaFin);

      try {
        const response = await incident_chickenService.getIsolationAllDate(
          fechaInicioFormateada,
          fechaFinFormateada
        );
        data = response.incidents || [];
      } catch (error) {
        console.warn("Error al obtener datos con fechas:", error);
        data = [];
      }
    } else {
      try {
        const response = await incident_chickenService.getIsolationAll(
          1,
          1000
        );
        data = response.incidents || [];
      } catch (error) {
        console.warn("Error al obtener todos los incidentes:", error);
        data = [];
      }
    }

    return data;
  } catch (error) {
    console.error("Error al obtener incidentes para exportar:", error);
    return [];
  }
}

async function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;
  // Solo responder si la página visible es la de incidentes de gallinas
  if (window.currentPage !== "incidentes_gallina") return;
  event.preventDefault();

  if (item.classList.contains("exporting")) {
    return;
  }

  item.classList.add("exporting");

  const format = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  try {
    let data = await fetchIncidentesForExport();

    if (currentSelectedGalponId === "todos") {
      // Ya está mostrando todos
    } else if (
      currentSelectedGalponId &&
      currentSelectedGalponId !== "" &&
      currentSelectedGalponId !== "todos"
    ) {
      data = data.filter(
        (inc) => String(inc.galpon_origen) === String(currentSelectedGalponId)
      );
    }

    if (data.length === 0) {
      return;
    }

    const enrichedData = data.map((incident) => {
      const galpon = cacheGalpones?.find(
        (g) => String(g.id_galpon) === String(incident.galpon_origen)
      );
      return {
        ...incident,
        nombre: galpon
          ? galpon.estado
            ? galpon.nombre
            : `${galpon.nombre} (Inactivo)`
          : `Galpón ${incident.galpon_origen}`,
      };
    });

    switch (format) {
      case "csv":
        exportIncidentesToCSV(
          enrichedData,
          `incidentes_gallina_${dateTag}.csv`
        );
        break;

      case "excel":
        await exportIncidentesToExcel(
          enrichedData,
          `incidentes_gallina_${dateTag}.xlsx`
        );
        break;

      case "pdf":
        await exportIncidentesToPDF(
          enrichedData,
          `incidentes_gallina_${dateTag}.pdf`
        );
        break;

      default:
    }
  } catch (error) {
    console.error("Error en exportación:", error);
  } finally {
    setTimeout(() => {
      item.classList.remove("exporting");
    }, 1000);
  }
}

// =======================
// 16. INICIALIZAR EXPORTACIÓN
// =======================

function inicializarExportacion() {
  document.removeEventListener("click", handleExportClickDocument);

  function handleExportClickDocument(e) {
    const item = e.target.closest(".export-format");
    if (!item) return;

    e.preventDefault();
    e.stopPropagation();

    handleExportClick(e);
  }

  document.addEventListener("click", handleExportClickDocument);

  document.querySelectorAll(".export-format").forEach((item) => {
    const newItem = item.cloneNode(true);
    item.parentNode.replaceChild(newItem, item);

    newItem.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      handleExportClick(e);
    });
  });
}

// =======================
// 17. INICIALIZACIÓN PRINCIPAL
// =======================

async function init(
  page = 1,
  page_size = ITEMS_PER_PAGE,
  fechaInicio = activeFechaInicio,
  fechaFin = activeFechaFin
) {
  currentPage = page;
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  const tableBody = document.getElementById("incidente-gallina-table-body");
  if (!tableBody) {

    return;
  }

  await cargarSelectFilterGalpones();

  // Si no hay galpón seleccionado, mostrar mensaje inicial
  if (!currentSelectedGalponId) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="text-center">Seleccione un galpón para ver los incidentes.</td></tr>';
    ocultarFiltrosYPaginacion();
    actualizarBotonAgregar();
  } else {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="text-center">Cargando incidentes...</td></tr>';
    await aplicarFiltros();
  }

  const editForm = document.getElementById("edit-incidente-gallina-form");
  const createForm = document.getElementById("create-incidente-gallina-form");

  if (tableBody) {
    tableBody.removeEventListener("click", handleTableClick);
    tableBody.removeEventListener("change", handleStatusSwitch);
    tableBody.addEventListener("click", handleTableClick);
    tableBody.addEventListener("change", handleStatusSwitch);
  }

  if (editForm) {
    editForm.removeEventListener("submit", handleUpdateSubmit);
    editForm.addEventListener("submit", handleUpdateSubmit);
  }

  if (createForm) {
    createForm.removeEventListener("submit", handleCreateSubmit);
    createForm.addEventListener("submit", handleCreateSubmit);
  }

  setupCreateModalHandler();
  inicializarBuscador();
  inicializarFiltroFechas();

  if (!exportInitialized) {
    inicializarExportacion();
    exportInitialized = true;
  }
}

// =======================
// 18. INICIALIZACIÓN AUTOMÁTICA
// =======================

export { init };
