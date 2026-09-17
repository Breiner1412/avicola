import { consumoService } from "../api/consumo-alimento.service.js";
import { shedsService } from "../api/shed.service.js";
import { alimentoService } from "../api/alimento.service.js";
import ApexCharts from "../../plugins/apexcharts/apexcharts.esm.js";

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
const PAGE_SIZE = 10;
let currentPage = 1;
let cacheGalpones = null;
let cacheAlimentos = null;
let filteredConsumos = [];
let chartInstance = null;

//______________________boton alimentos__________________________
// Navega con el cargador central (main.js)
document.addEventListener("click", (e) => {
  const btn = e.target.closest("#alimentos");
  if (!btn) return;
  e.preventDefault();
  window.loadContent("alimentos");
});

function formatDateDDMMYYYY(dateStr) {
  if (!dateStr) return "";
  return dateStr.split("-").reverse().join("/");
}

function createConsumoRow(consumo) {
  const consumoId = consumo.id_consumo;
  const fechaFormateada = formatDateDDMMYYYY(consumo.fecha_registro);

  const tabla = `
        <tr>
            <td class="px-0">${consumo.alimento || "-"}</td>
            <td class="px-0">${consumo.cantidad_alimento} Kg</td>
            <td class="px-0">${fechaFormateada}</td>
            <td class="px-0">${consumo.galpon || "-"}</td>
            <td class="text-end">
                <div class="d-flex justify-content-end gap-2">
                    <button class="btn btn-sm btn-success btn-edit-consumo" aria-label="Editar" title="Editar" data-consumo-id="${consumoId}">
                        <i class="fa-regular fa-pen-to-square me-0"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;

  return tabla;
}

async function cargarSelectGalponesModals(force = false) {
  const selectEdit = document.getElementById("edit-id_galpon");

  try {
    if (!cacheGalpones || force) {
      cacheGalpones = await shedsService.getSheds();
    }

    const galponesActivos = cacheGalpones.filter((g) => g.estado === true);

    if (selectEdit) {
      selectEdit.innerHTML =
        `<option value="" disabled selected>Seleccione un galpón</option>` +
        galponesActivos
          .map((g) => {
            return `<option value="${g.id_galpon}">
                                ${g.nombre}
                            </option>`;
          })
          .join("");
    }
  } catch (error) {
    console.error("Error cargando galpones:", error);
    if (selectEdit) {
      selectEdit.innerHTML = `<option>Error al cargar</option>`;
    }
  }
}

async function cargarSelectAlimentosModals(force = false) {
  const selectEdit = document.getElementById("edit-id_alimento");

  try {
    if (!cacheAlimentos || force) {
      const data = await consumoService.getAlimentos(1, 100);
      cacheAlimentos = data.alimento || [];
    }

    if (selectEdit) {
      selectEdit.innerHTML =
        `<option value="" disabled selected>Seleccione un alimento</option>` +
        cacheAlimentos
          .map((a) => `<option value="${a.id_alimento}">${a.nombre}</option>`)
          .join("");
    }
  } catch (error) {
    console.error("Error cargando alimentos:", error);
    if (selectEdit) {
      selectEdit.innerHTML = `<option>Error al cargar</option>`;
    }
  }
}

async function cargarSelectFilterAlimentos() {
  const selectFilter = document.getElementById("filter-alimento");

  try {
    if (!cacheAlimentos) {
      const data = await consumoService.getAlimentos(1, 100);
      cacheAlimentos = data.alimento || [];
    }

    // Filtrar solo alimentos con cantidad mayor a 0
    const alimentosDisponibles = cacheAlimentos.filter((a) => a.cantidad > 0);

    const options = alimentosDisponibles
      .map((a) => {
        return `
                <option value="${a.id_alimento}">
                    ${a.nombre} - ${a.cantidad} Kg
                </option>
            `;
      })
      .join("");

    if (selectFilter) {
      selectFilter.innerHTML = `<option value="">Todos los alimentos</option>${options}`;
    }
  } catch (error) {
    if (selectFilter) {
      selectFilter.innerHTML = `<option>Error al cargar alimentos</option>`;
    }
    console.error("Error en cargarSelectFilterAlimentos:", error);
  }
}

function renderTabla(registros) {
  const tbody = document.getElementById("consumo-table-body");
  if (!tbody) return;

  if (!registros || registros.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center">No hay registros de consumo.</td></tr>';
    return;
  }

  tbody.innerHTML = registros.map(createConsumoRow).join("");
}

// =======================
// CARGAR TODOS LOS REGISTROS (PAGINADO)
// =======================
async function cargarTodosRegistrosPaginados(page = 1) {
  currentPage = page; // Actualizar página actual

  const tbody = document.getElementById("consumo-table-body");
  tbody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando registros...</td></tr>';

  try {
    const data = await consumoService.getConsumo(page, PAGE_SIZE);
    const registros = data.consumos || [];
    filteredConsumos = registros;

    renderTabla(registros);

    const paginationNav = document.querySelector(
      "nav[aria-label='Page navigation']"
    );
    if (paginationNav) {
      if (data.total_pages > 1) {
        paginationNav.style.display = "block";
        renderPagination(data.total_pages || 1);
      } else {
        paginationNav.style.display = "none";
      }
    }
  } catch (error) {
    console.error("Error cargando registros:", error);
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center text-danger">Error al cargar registros.</td></tr>';
  }
}

// =======================
// MODALES (SOLO EDITAR)
// =======================
async function openEditModal(consumoId) {
  try {
    const consumo = await consumoService.getConsumoById(consumoId);

    await cargarSelectGalponesModals();
    await cargarSelectAlimentosModals();

    document.getElementById("edit-consumo-id").value = consumo.id_consumo;
    document.getElementById("edit-id_galpon").value = consumo.id_galpon;
    document.getElementById("edit-id_alimento").value = consumo.id_alimento;
    document.getElementById("edit-cantidad_alimento").value =
      consumo.cantidad_alimento;

    const alimento = await alimentoService.getAlimentoById(consumo.id_alimento);

    const maxText = document.getElementById("consumo-cantidad-max-text");
    if (maxText) {
      maxText.textContent = `Cantidad disponible: ${alimento.cantidad} Kg`;
    }

    const modalElement = document.getElementById("editConsumoModal");
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  } catch (error) {
    console.error(`Error al obtener el consumo ${consumoId}:`, error);
    Swal.fire({
      icon: "error",
      text: "No se pudieron cargar los datos del consumo.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function handleUpdateSubmit(event) {
  event.preventDefault();
  const consumoId = document.getElementById("edit-consumo-id").value;
  const updatedData = {
    id_galpon: parseInt(document.getElementById("edit-id_galpon").value),
    id_alimento: parseInt(document.getElementById("edit-id_alimento").value),
    cantidad_alimento: parseInt(
      document.getElementById("edit-cantidad_alimento").value
    ),
  };

  try {
    await consumoService.updateConsumo(consumoId, updatedData);

    const modalElement = document.getElementById("editConsumoModal");
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();

    // Recargar datos actuales (con los filtros aplicados)
    await filtrarConsumos();

    // Actualizar la gráfica según los mismos filtros
    const startDate = document.getElementById("filter-start-date")?.value;
    const endDate = document.getElementById("filter-end-date")?.value;
    await renderChart(startDate, endDate);

    Swal.fire({
      icon: "success",
      title: "Actualizado",
      text: "Registro actualizado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  } catch (error) {
    console.error(`Error al actualizar el consumo ${consumoId}:`, error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: error?.message || "No se pudo actualizar el registro.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-consumo");
  if (editButton) {
    const consumoId = editButton.dataset.consumoId;
    await openEditModal(consumoId);
    return;
  }
}

// =======================
// PAGINACIÓN
// =======================
function renderPagination(total_pages) {
  const container = document.querySelector("#pagination");
  if (!container) {
    console.error("Elemento #pagination no encontrado");
    return;
  }

  container.innerHTML = "";

  // Botón anterior
  const prevItem = document.createElement("li");
  prevItem.classList.add("page-item");
  if (currentPage === 1) {
    prevItem.classList.add("disabled");
  }

  const prevLink = document.createElement("a");
  prevLink.classList.add("page-link", "text-success");
  prevLink.href = "#";
  prevLink.innerHTML = '<i class="fas fa-chevron-left"></i>';
  prevLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage > 1) {
      currentPage--;
      filtrarConsumos(currentPage);
    }
  });

  prevItem.appendChild(prevLink);
  container.appendChild(prevItem);

  // Números de página
  const maxVisible = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  let endPage = Math.min(total_pages, startPage + maxVisible - 1);

  if (endPage - startPage + 1 < maxVisible) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  // Primera página + ...
  if (startPage > 1) {
    const firstPageLi = createPageLi(1);
    container.appendChild(firstPageLi);
    if (startPage > 2) {
      container.appendChild(createDotsLi());
    }
  }

  // Números de página
  for (let i = startPage; i <= endPage; i++) {
    const pageLi = createPageLi(i);
    container.appendChild(pageLi);
  }

  // ... + Última página
  if (endPage < total_pages) {
    if (endPage < total_pages - 1) {
      container.appendChild(createDotsLi());
    }
    const lastPageLi = createPageLi(total_pages);
    container.appendChild(lastPageLi);
  }

  // Botón siguiente
  const nextItem = document.createElement("li");
  nextItem.classList.add("page-item");
  if (currentPage === total_pages) {
    nextItem.classList.add("disabled");
  }

  const nextLink = document.createElement("a");
  nextLink.classList.add("page-link", "text-success");
  nextLink.href = "#";
  nextLink.innerHTML = '<i class="fas fa-chevron-right"></i>';
  nextLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage < total_pages) {
      currentPage++;
      filtrarConsumos(currentPage);
    }
  });

  nextItem.appendChild(nextLink);
  container.appendChild(nextItem);
}

function createPageLi(pageNumber) {
  const li = document.createElement("li");
  li.className = `page-item ${pageNumber === currentPage ? "active" : ""}`;

  const pageLink = document.createElement("a");
  pageLink.className = `page-link ${
    pageNumber === currentPage
      ? "bg-success border-success text-white"
      : "text-success"
  }`;
  pageLink.href = "#";
  pageLink.textContent = pageNumber;

  pageLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (pageNumber !== currentPage) {
      currentPage = pageNumber;
      filtrarConsumos(currentPage);
    }
  });

  li.appendChild(pageLink);
  return li;
}

function createDotsLi() {
  const li = document.createElement("li");
  li.className = "page-item disabled";
  const dotsLink = document.createElement("a");
  dotsLink.className = "page-link text-success";
  dotsLink.textContent = "...";
  li.appendChild(dotsLink);
  return li;
}

// =======================
// FILTROS
// =======================
async function filtrarConsumos(page = 1) {
  // Actualizar la página actual
  currentPage = page;

  const alimentoId = document.getElementById("filter-alimento")?.value;
  let startDate = document.getElementById("filter-start-date")?.value;
  let endDate = document.getElementById("filter-end-date")?.value;

  const tableBody = document.getElementById("consumo-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando registros...</td></tr>';

  // Si no hay fecha fin, usar hoy
  if (!endDate) {
    const now = new Date();
    const pad = (n) => n.toString().padStart(2, "0");
    endDate = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(
      now.getDate()
    )}`;
  }

  // Si no hay fecha inicio, usar fecha muy antigua
  if (!startDate) startDate = "2000-01-01";

  try {
    let data;
    let consumos = [];
    let total_pages = 1;

    // Si hay filtro por alimento Y fecha
    if (alimentoId && startDate && endDate) {
      // Primero obtener todos los consumos
      data = await consumoService.getConsumoByRangeDate(
        startDate,
        endDate,
        1,
        100
      );
      let todosRegistros = data?.consumos || [];

      // Filtrar por alimento
      let registrosFiltrados = todosRegistros.filter(
        (c) => String(c.id_alimento) === String(alimentoId)
      );

      // Paginar manualmente
      total_pages = Math.ceil(registrosFiltrados.length / PAGE_SIZE);
      const inicio = (page - 1) * PAGE_SIZE;
      const fin = inicio + PAGE_SIZE;
      consumos = registrosFiltrados.slice(inicio, fin);
    }
    // Si solo hay filtro por fechas
    else if (startDate && endDate) {
      data = await consumoService.getConsumoByRangeDate(
        startDate,
        endDate,
        page,
        PAGE_SIZE
      );
      consumos = data.consumos || [];
      total_pages = data.total_pages || 1;
    }
    // Si no hay filtros, traer todos
    else {
      data = await consumoService.getConsumo(page, PAGE_SIZE);
      consumos = data.consumos || [];
      total_pages = data.total_pages || 1;
    }

    filteredConsumos = consumos;

    tableBody.innerHTML =
      consumos.length > 0
        ? consumos.map(createConsumoRow).join("")
        : '<tr><td colspan="5" class="text-center">No se encontraron registros.</td></tr>';

    // Mostrar/ocultar paginación
    const paginationNav = document.querySelector(
      "nav[aria-label='Page navigation']"
    );
    if (paginationNav) {
      if (total_pages > 1) {
        paginationNav.style.display = "block";
        renderPagination(total_pages);
      } else {
        paginationNav.style.display = "none";
      }
    }
  } catch (error) {
    console.error("Error al filtrar registros:", error);
    tableBody.innerHTML =
      '<tr><td colspan="5" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }
}

// =======================
// LIMPIAR FILTROS
// =======================
function limpiarFiltros() {
  const startDate = document.getElementById("filter-start-date");
  const endDate = document.getElementById("filter-end-date");
  const alimentoSelect = document.getElementById("filter-alimento");

  if (startDate) startDate.value = "";
  if (endDate) endDate.value = "";
  if (alimentoSelect) alimentoSelect.value = "";

  // Cargar todos los registros sin filtros
  cargarTodosRegistrosPaginados(1);
  renderChart();
}

// =======================
// EXPORTACIÓN
// =======================

// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_consumo" },
  { header: "Alimento", key: "alimento" },
  { header: "Cantidad (Kg)", key: "cantidad_alimento" },
  { header: "Fecha Registro", key: "fecha_registro" },
  { header: "Galpón", key: "galpon" },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Consumos");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Consumos de Alimento");
}

function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;

  // IMPORTANTE: Usar stopPropagation igual que en gallinas.js
  event.preventDefault();
  event.stopPropagation();

  // PREVENIR MÚLTIPLES DESCARGAS
  if (item.classList.contains("exporting")) return;
  item.classList.add("exporting");

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  let dataToExport = [];
  if (filteredConsumos && filteredConsumos.length > 0) {
    dataToExport = filteredConsumos;
  }

  if (!dataToExport || dataToExport.length === 0) {
    Swal.fire({
      title: "No hay datos para exportar.",
      icon: "info",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    item.classList.remove("exporting");
    return;
  }

  try {
    if (fmt === "csv") {
      exportToCSV(dataToExport, `Consumos_${dateTag}.csv`);
    } else if (fmt === "excel") {
      exportToExcel(dataToExport, `Consumos_${dateTag}.xlsx`);
    } else if (fmt === "pdf") {
      exportToPDF(dataToExport, `Consumos_${dateTag}.pdf`);
    }

    item.classList.remove("exporting");
  } catch (error) {
    console.error("Error en exportación:", error);
    Swal.fire({
      title: "Error",
      text: "No se pudo generar el archivo de exportación.",
      icon: "error",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    item.classList.remove("exporting");
  }
}







// =======================
// INICIALIZACIÓN
// =======================
function setupEventListeners() {
  const btnFilter = document.getElementById("btn-filter");
  if (btnFilter) {
    btnFilter.removeEventListener("click", handleFilterClick);
    btnFilter.addEventListener("click", handleFilterClick);
  }

  async function handleFilterClick() {
    // Obtener fechas del filtro
    const start = document.getElementById("filter-start-date").value;
    const end = document.getElementById("filter-end-date").value;

    // Actualizar tabla (tu función actual)
    filtrarConsumos(1);

    // Actualizar gráfica
    await renderChart(start, end);
  }

  const btnClear = document.getElementById("btn_clear_filters");
  if (btnClear) {
    btnClear.removeEventListener("click", limpiarFiltros);
    btnClear.addEventListener("click", limpiarFiltros);
  }

  const editForm = document.getElementById("edit-consumo-form");
  if (editForm) {
    editForm.removeEventListener("submit", handleUpdateSubmit);
    editForm.addEventListener("submit", handleUpdateSubmit);
  }

  // IMPORTANTE: Usar el mismo patrón que en gallinas.js
  const exportItems = document.querySelectorAll(".export-format");
  exportItems.forEach((item) => {
    item.removeEventListener("click", handleExportClick);
    item.addEventListener("click", handleExportClick);
  });

  const tableBody = document.getElementById("consumo-table-body");
  if (tableBody) {
    tableBody.removeEventListener("click", handleTableClick);
    tableBody.addEventListener("click", handleTableClick);
  }
}

async function init() {
  // Verificar que estamos en la página correcta
  const tbody = document.getElementById("consumo-table-body");
  if (!tbody) {
    console.warn(
      "Elemento consumo-table-body no encontrado. No se inicializará el módulo de consumos."
    );
    return;
  }

  // Cargar select de alimentos para filtros
  await cargarSelectFilterAlimentos();

  // Cargar todos los registros al entrar
  await cargarTodosRegistrosPaginados(1);
  setupEventListeners();
  await renderChart();
}

export { init };

export async function renderChart(fecha_inicio, fecha_fin) {
  const chartDiv = document.querySelector("#chart");
  const chartTitle = document.getElementById("chart-title");
  if (!chartDiv) return;

  try {
    // Si no hay fechas, usar mes actual
    if (!fecha_inicio || !fecha_fin) {
      const today = new Date();
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      fecha_inicio = firstDay.toISOString().split("T")[0]; // YYYY-MM-DD
      fecha_fin = lastDay.toISOString().split("T")[0]; // YYYY-MM-DD
    }

    // Obtener todos los consumos
    const response = await consumoService.getAllConsumos();
    const consumos = response?.consumos || [];

    if (!consumos.length) {
      chartDiv.innerHTML =
        "<p class='text-center'>No hay datos para el rango seleccionado</p>";
      if (chartTitle) chartTitle.textContent = "Consumo de Alimento";
      return;
    }

    // Filtrar por fechas
    const start = new Date(fecha_inicio);
    const end = new Date(fecha_fin);
    const consumosFiltrados = consumos.filter((c) => {
      const fecha = new Date(c.fecha_registro);
      return fecha >= start && fecha <= end;
    });

    if (!consumosFiltrados.length) {
      chartDiv.innerHTML =
        "<p class='text-center'>No hay datos en este rango de fechas</p>";
      if (chartTitle) chartTitle.textContent = "Consumo de Alimento";
      return;
    }

    // Agrupar por alimento
    const agrupados = {};
    const registrosPorAlimento = {};

    consumosFiltrados.forEach((c) => {
      const alimento = (c.alimento || "Desconocido").trim().toLowerCase();
      agrupados[alimento] =
        (agrupados[alimento] || 0) + (c.cantidad_alimento || 0);
      registrosPorAlimento[alimento] =
        (registrosPorAlimento[alimento] || 0) + 1;
    });

    const sorted = Object.entries(agrupados).sort((a, b) => b[1] - a[1]);
    const labels = sorted.map(
      ([alimento]) => alimento.charAt(0).toUpperCase() + alimento.slice(1)
    );
    const cantidades = sorted.map(([_, cantidad]) => cantidad);

    const promedioSeries = sorted.map(([alimento, _]) => {
      const total = agrupados[alimento];
      const count = registrosPorAlimento[alimento];
      return total / count;
    });

    // Título de la gráfica
    if (chartTitle) {
      chartTitle.textContent =
        start.getMonth() === end.getMonth() &&
        start.getFullYear() === end.getFullYear()
          ? `Consumo de Alimento - ${start.toLocaleString("es-ES", {
              month: "long",
              year: "numeric",
            })}`
          : `Consumo de Alimento - ${start.toLocaleDateString()} a ${end.toLocaleDateString()}`;
    }

    // Destruir chart anterior si existe
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }

    // Configuración y render
    const options = {
      series: [
        { name: "Consumo Total (Kg)", data: cantidades },
        {
          name: "Promedio",
          data: promedioSeries,
          type: "line",
          stroke: { width: 3 },
          markers: { size: 4 },
        },
      ],
      colors: ["#69d45bff", "#adacacff"],
      chart: { type: "bar", height: 380 },
      plotOptions: {
        bar: { horizontal: false, columnWidth: "50%", borderRadius: 4 },
      },
      xaxis: {
        categories: labels,
        labels: { rotate: -45, style: { fontSize: "13px" } },
      },
      yaxis: {
        title: { text: "Cantidad consumida (Kg)" },
        labels: { formatter: (val) => val.toFixed(0) },
      },
      dataLabels: { enabled: false },
      tooltip: { y: { formatter: (val) => `${val} Kg` } },
    };

    // Crear la nueva instancia y renderizar
    chartInstance = new ApexCharts(chartDiv, options);
    await chartInstance.render();
  } catch (err) {
    console.error("Error al renderizar la gráfica:", err);
    chartDiv.innerHTML =
      "<p class='text-center text-danger'>Error al cargar la gráfica</p>";
    if (chartTitle) chartTitle.textContent = "Consumo de Alimento";
  }
}
