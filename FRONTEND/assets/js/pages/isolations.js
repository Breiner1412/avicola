import { isolationService } from '../api/aislamiento.service.js';

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
let modalInstance = null;
let createModalInstance = null;
let activeFechaInicio = "";
let activeFechaFin = "";

//______________________boton incidente__________________________
// Botón "Incidentes": navega con el cargador central (main.js)
document.addEventListener('click', (e) => {
  const btn = e.target.closest('#incident_chickens');
  if (!btn) return;
  e.preventDefault();
  window.loadContent('incidentes_gallina');
});


// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---
function createIsolationRow(isolation) {
  const isolationId = isolation.id_aislamiento;

  const fecha = new Date(isolation.fecha_hora);
  const fechaFormateada = fecha.toLocaleString('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
    hour12: true
  });
  return `
    <tr>
      <td class="px-0">${isolation.id_incidente_gallina}</td>
      <td class="px-0">${fechaFormateada}</td>
      <td class="px-0">${isolation.nombre}</td>
    </tr>
  `;
}

//____________________formato_para_exportar_por_fechas______________________________


function formatDateForAPI(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}


//______________________________paginación para todos los datos y filtrados_____________

async function fetchIsolations(page = 1, page_size = 10, fechaInicio = "", fechaFin = "") {
  try {
    let response;
    if (fechaInicio && fechaFin) {
      response = await isolationService.getIsolationAllDate(fechaInicio, fechaFin, page, page_size);
    } else {
      response = await isolationService.getIsolationAll(page, page_size);
    }

    if (!response || response.length === 0) {
      return [];
    }

    return response;
  } catch (error) {
    if (error.message.includes("No hay asilamiento en ese rango de fechas") || error.response?.status === 404) {
      return [];
    }
    throw error;
  }
}

// Modificar la función init para que pase correctamente los filtros a la paginación
function renderPagination(total_pages, currentPage = 1) {
    const container = document.querySelector("#pagination");
    if (!container) return;

    container.innerHTML = "";

    // ---------- BOTÓN ANTERIOR ----------
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
    prevLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${currentPage - 1}">
            <i class="fas fa-chevron-left"></i>
        </a>
    `;
    prevLi.addEventListener("click", () => {
        if (currentPage !== 1) {
            const prevPage = currentPage - 1;
            init(prevPage, 10, activeFechaInicio, activeFechaFin);
        }
    });
    container.appendChild(prevLi);

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(total_pages, startPage + maxVisible - 1);

    if (endPage - startPage + 1 < maxVisible) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    // ---------- PRIMERA PÁGINA + ... ----------
    if (startPage > 1) {
        container.appendChild(createPageLi(1, currentPage));
        if (startPage > 2) container.appendChild(createDotsLi());
    }

    // ---------- NÚMEROS DE PÁGINA ----------
    for (let i = startPage; i <= endPage; i++) {
        container.appendChild(createPageLi(i, currentPage));
    }

    // ---------- ... + ÚLTIMA PÁGINA ----------
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) container.appendChild(createDotsLi());
        container.appendChild(createPageLi(total_pages, currentPage));
    }

    // ---------- BOTÓN SIGUIENTE ----------
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${currentPage === total_pages ? "disabled" : ""}`;
    nextLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${currentPage + 1}">
            <i class="fas fa-chevron-right"></i>
        </a>
    `;
    nextLi.addEventListener("click", () => {
        if (currentPage !== total_pages) {
            const nextPage = currentPage + 1;
            init(nextPage, 10, activeFechaInicio, activeFechaFin);
        }
    });
    container.appendChild(nextLi);
}

// ========== BOTÓN DE NÚMERO DE PÁGINA ==========
function createPageLi(page, currentPage) {
    const li = document.createElement("li");

    const isActive = page === currentPage;

    li.className = `page-item ${isActive ? 'active' : ''}`;
    li.innerHTML = `
        <a class="page-link ${isActive ? "bg-success border-success text-white" : "text-success"}"
           href="#" data-page="${page}">
           ${page}
        </a>
    `;

    li.addEventListener("click", () => {
        if (!isActive) {
            init(page, 10, activeFechaInicio, activeFechaFin);
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

//______________________ para filtrar por fechas_______________________________________
function inicializarFiltroFechas() {
  const btnApplyFilter = document.getElementById("btn-apply-date-filter");
  const btnClear = document.getElementById('btn_clear_filters');
  
  if (btnApplyFilter) {
    // Remover listeners anteriores
    btnApplyFilter.replaceWith(btnApplyFilter.cloneNode(true));
    const nuevoBtn = document.getElementById("btn-apply-date-filter");
    
    nuevoBtn.addEventListener("click", () => {
      const fechaInicio = document.getElementById("fecha-inicio").value;
      const fechaFin = document.getElementById("fecha-fin").value;
      filtrarAislamientos(fechaInicio, fechaFin);
    });
  }
  
  if (btnClear) {
    btnClear.replaceWith(btnClear.cloneNode(true));
    const nuevoBtnClear = document.getElementById('btn_clear_filters');
    
    nuevoBtnClear.addEventListener('click', limpiarFiltros);
  }
}

function filtrarAislamientos(fechaInicio, fechaFin) {
  if (!fechaInicio || !fechaFin || fechaInicio == ""|| fechaFin=="") {
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: 'Debe seleccionar ambas fechas',
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success"
      },
      buttonsStyling: false
    });
    return;
  }

  // Guardar fechas para usar en fetchIsolations
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  // Recargar la tabla desde la página 1 con el filtro
  init(1, 10);
}

//____________________________________buscador inteligente____________________________________
function inicializarBuscador() {
  const BuscarAislamiento = document.getElementById('search-isolation');

  if (BuscarAislamiento) {
    // Remover event listener anterior si existe
    BuscarAislamiento.replaceWith(BuscarAislamiento.cloneNode(true));
    const nuevoInput = document.getElementById('search-isolation');
    
    nuevoInput.addEventListener('input', () => {
      const filter = nuevoInput.value.toLowerCase();
      const tableBody = document.getElementById('isolations-table-body');
      if (!tableBody) return;

      const rows = tableBody.querySelectorAll('tr');
      rows.forEach(row => {
        const idCell = row.cells[0]?.textContent.toLowerCase() || '';
        const fechaCell = row.cells[1]?.textContent.toLowerCase() || '';
        const galponCell = row.cells[2]?.textContent.toLowerCase() || '';
        row.style.display = idCell.includes(filter) || fechaCell.includes(filter) || galponCell.includes(filter) ? '' : 'none';
      });
    });
  }
}

//______________________________________________________________________________________________

//_______________________________ limpiador de filtros__________________________________________
function limpiarFiltros() {
  activeFechaInicio = "";
  activeFechaFin = "";
  document.getElementById("fecha-inicio").value = "";
  document.getElementById("fecha-fin").value = "";
  const searchInput = document.getElementById('search-isolation');
  if (searchInput) searchInput.value = "";
  init(1, 10);
}
//_____________________________________________________________________________________________

async function init(page = 1, page_size = 10, fechaInicio = activeFechaInicio, fechaFin = activeFechaFin) {
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  const tableBody = document.getElementById('isolations-table-body');
  if (!tableBody) {
    return;
  }

  tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Cargando aislamientos...</td></tr>';

  try {
    const data = await fetchIsolations(page, page_size, activeFechaInicio, activeFechaFin);
    const aislamientos = data.isolation || [];

    if (aislamientos.length > 0) {
      tableBody.innerHTML = aislamientos.map(createIsolationRow).join('');
    } else {
      tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No se encontraron aislamientos.</td></tr>';
    
      if (activeFechaInicio && activeFechaFin) {
            tableBody.innerHTML = `
              <tr>
                <td colspan="7" class="text-center">
                  <div class="alert alert-success mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No se encontraron aislamientos en el rango de fechas:<br>
                    <strong>${activeFechaInicio} a ${activeFechaFin}</strong>
                  </div>
                </td>
              </tr>
            `;
      } else {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No se encontraron aislamientos.</td></tr>';
        }
      }

    renderPagination(data.total_pages || 1, page);
    inicializarBuscador();
    inicializarFiltroFechas();

  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>`;
  }
}

//_____________________para exportar archivos excel, CSV, pdf_______________________________________
function formatDateTime(datetimeStr) {
  if (!datetimeStr) return "";

  const date = new Date(datetimeStr);

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
}







// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_aislamiento" },
  { header: "Fecha y hora", key: "fecha_hora" },
  { header: "Incidente N.", key: "id_incidente_gallina" },
  { header: "id galpon", key: "id_galpon" },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Aislamientos");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Aislamientos");
}

async function handleExportClick(event) {

  const item = event.target.closest(".export-format");
  if (!item) return;
  // Solo responder si la página visible es la de aislamientos
  if (window.currentPage !== "aislamientos") return;

  event.preventDefault();

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  let response;

  // 👉 Si NO hay filtros, llamar API normal
  if (!activeFechaInicio || !activeFechaFin) {
    response = await fetchIsolations(1, 1000);
  } 
  // 👉 Si hay filtros, enviarlos formateados
  else {
    const fechaInicio = formatDateForAPI(activeFechaInicio);
    const fechaFin = formatDateForAPI(activeFechaFin);
    response = await fetchIsolations(1, 1000, fechaInicio, fechaFin);
  }

  const data = response?.isolation || [];

  if (data.length === 0) {
    Swal.fire({ 
      title: "No hay datos para exportar.",
      icon: "info",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success"
      },
      buttonsStyling: false });
    return;
  }

  if (fmt === "csv") {
    exportToCSV(data, `aislamientos_${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `aislamientos_${dateTag}.xlsx`);
  } else if (fmt === "pdf") {
    exportToPDF(data, `aislamientos_${dateTag}.pdf`);
  }
}

// Inicializar event listener para exportación
function inicializarExportacion() {
  document.addEventListener("click", (e) => {
    const item = e.target.closest(".export-format");
    if (!item) return;
    handleExportClick(e);
  });
}

// Llamar inicialización de exportación una sola vez
inicializarExportacion();

export { init };
