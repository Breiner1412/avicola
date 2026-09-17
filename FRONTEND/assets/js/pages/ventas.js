import { ventaService } from "../api/venta.service.js";
import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
// import {loadContent} from "../main.js";

let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let createModalInstance = null; // Guardará la instancia del modal de Bootstrap
let originalMail = null;

const swalWithBootstrapButtons = Swal.mixin({
  customClass: {
    confirmButton: "btn btn-success ms-2",
    cancelButton: "btn btn-secondary",
  },
  buttonsStyling: false,
});

function createVentaRow(venta) {
  const fecha = new Date(venta.fecha_hora);
  const fechaFormateada = fecha.toLocaleString("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
    hour12: true,
  });

  return `
        <tr>
            <td class="cell">${venta.id_venta}</td>
            <td class="cell">${fechaFormateada}</td>
            <td class="cell">${venta.nombre_usuario}</td>
            <td class="cell">${venta.metodo_pago}</td>
            <td class="cell">${venta.total}</td>
            <td class="cell">
                <div class="form-check form-switch d-inline-block">
                    <input class="form-check-input venta-status-switch" type="checkbox" role="switch" 
                            id="switch-${venta.id_venta}" data-venta-id="${
    venta.id_venta
  }" 
                            ${venta.estado ? "checked" : ""}>
                    <label class="form-check-label" for="switch-${
                      venta.id_venta
                    }">
                          ${venta.estado ? "Completada" : "Cancelada"}
                    </label>
                </div>
            </td>
            <td class="cell d-flex justify-content-end gap-2">
              <button class="btn btn-success btn-sm btn-edit-venta me-1" data-venta-id="${
                venta.id_venta
              }" aria-label="Editar" ${venta.estado ? "" : "disabled"}>
                <i class="fa-regular fa-pen-to-square"></i>
              </button>
              <button class="btn btn-success btn-sm btn-detalles-venta me-1" data-venta-id="${
                venta.id_venta
              }" data-page="info_venta" ${venta.estado ? "" : "disabled"}>
                    <i class="fas fa-search"></i>
                </button>
            </td>
        </tr>
    `;
}

// Inicializar con fecha actual
let fecha_actual = new Date();
let activeFechaInicio = convertirFecha(fecha_actual);
let activeFechaFin = convertirFecha(fecha_actual);

async function fetchVentas(
  page = 1,
  page_size = 10,
  fechaInicio = "",
  fechaFin = ""
) {
  try {
    let response;
    if (fechaInicio && fechaFin) {
      response = await ventaService.getVentasByDate(
        fechaInicio,
        fechaFin,
        page,
        page_size
      );
    }

    if (!response || response.length === 0) {
      return [];
    }

    return response;
  } catch (error) {
    if (
      error.message.includes("No hay ventas en ese rango de fechas") ||
      error.response?.status === 404
    ) {
      return [];
    }
    throw error;
  }
}

// Llamar funcion init de acuerdo al numero de pagina
function renderPagination(total_pages, currentPage = 1) {
  const container = document.querySelector("#pagination");
  if (!container) return;

  container.innerHTML = "";

  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage - 1
        }">
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

  if (startPage > 1) {
    container.appendChild(createPageLi(1, currentPage));
    if (startPage > 2) container.appendChild(createDotsLi());
  }

  for (let i = startPage; i <= endPage; i++) {
    container.appendChild(createPageLi(i, currentPage));
  }

  if (endPage < total_pages) {
    if (endPage < total_pages - 1) container.appendChild(createDotsLi());
    container.appendChild(createPageLi(total_pages, currentPage));
  }

  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${
    currentPage === total_pages ? "disabled" : ""
  }`;
  nextLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage + 1
        }">
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

// boton numero de pagina
function createPageLi(page, currentPage) {
  const li = document.createElement("li");

  const isActive = page === currentPage;

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
      init(page, 10, activeFechaInicio, activeFechaFin);
    }
  });

  return li;
}

// puntos suspensivos
function createDotsLi() {
  const li = document.createElement("li");
  li.className = "page-item disabled";
  li.innerHTML = `<a class="page-link text-success">...</a>`;
  return li;
}

function filtrarVentas(fechaInicio, fechaFin) {
  if (!fechaInicio || !fechaFin) {
    swalWithBootstrapButtons.fire({
      icon: "info",
      title: "Error",
      text: "Debe seleccionar ambas fechas",
    });
    return;
  }

  if (fechaInicio > fechaFin) {
    swalWithBootstrapButtons.fire({
      icon: "info",
      title: "Error",
      text: "La fecha de inicio debe ser anterior a la fecha fin",
    });
    return;
  }

  // Guardar fechas para usar en fetchVentas
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  // Recargar la tabla desde la página 1 con el filtro
  init(1, 10);
}

function limpiarFiltros() {
  let fecha_actual = new Date();
  activeFechaInicio = convertirFecha(fecha_actual);
  activeFechaFin = convertirFecha(fecha_actual);

  document.getElementById("fecha-inicio").value = activeFechaInicio;
  document.getElementById("fecha-fin").value = activeFechaFin;
  init(1, 10);
}

function aplicarFiltros() {
  const fechaInicio = document.getElementById("fecha-inicio").value;
  const fechaFin = document.getElementById("fecha-fin").value;
  filtrarVentas(fechaInicio, fechaFin);
}

// funcion para dar formato a la fecha YYYY-MM-DD
function convertirFecha(fechaEntrante) {
  // Crear el objeto Date sin usar la zona horaria UTC
  const fecha = new Date(fechaEntrante);
  const formato =
    fecha.getFullYear() +
    "-" +
    String(fecha.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(fecha.getDate()).padStart(2, "0");
  return formato;
}

// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---
async function init(
  page = 1,
  page_size = 10,
  fechaInicio = activeFechaInicio,
  fechaFin = activeFechaFin
) {
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;
  document.getElementById("fecha-inicio").value = activeFechaInicio;
  document.getElementById("fecha-fin").value = activeFechaFin;

  const tableBody = document.getElementById("ventas-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando ventas ... </td></tr>';

  try {
    const data = await fetchVentas(
      page,
      page_size,
      activeFechaInicio,
      activeFechaFin
    );
    const ventas = data.ventas || [];
    if (ventas.length > 0) {
      tableBody.innerHTML = ventas.map(createVentaRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="text-center">No se encontraron ventas en ese rango de fechas.</td></tr>';
    }

    renderPagination(data.total_pages || 1, page);
  } catch (error) {
    console.error("Error al obtener las ventas:", error);
    tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>`;
  }

  // Aplicamos el patrón remove/add para evitar listeners duplicados

  // Boton para crear venta
  const btnCreateVenta = document.getElementById("btnCreateVenta");

  // modal para editar
  const modalEditar = document.getElementById("edit-venta-modal");

  // formulario para actualizar venta
  const editForm = document.getElementById("edit-venta-form");

  btnCreateVenta.removeEventListener("click", handleCreateVentaClick);
  btnCreateVenta.addEventListener("click", handleCreateVentaClick);

  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);

  // para boton ver detalles
  tableBody.removeEventListener("click", handleDetallesClick);
  tableBody.addEventListener("click", handleDetallesClick);

  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);

  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);

  // al abrir modal cargar los métodos de pago
  modalEditar.removeEventListener("show.bs.modal", cargarMetodosPago);
  modalEditar.addEventListener("show.bs.modal", cargarMetodosPago);

  // Botón para aplicar filtro
  const btnAplicarFiltros = document.getElementById("btn-apply-date-filter");
  btnAplicarFiltros.removeEventListener("click", aplicarFiltros);
  btnAplicarFiltros.addEventListener("click", aplicarFiltros);

  //Boton para limpiar filtros
  const btnClear = document.getElementById("btn_clear_filters");
  btnClear.removeEventListener("click", limpiarFiltros);
  btnClear.addEventListener("click", limpiarFiltros);

  const pageUtilities = document.querySelector(".page-utilities");
  pageUtilities.removeEventListener("click", handleExportClick);
  pageUtilities.addEventListener("click", handleExportClick);
}

export { init };

// --- MANEJADORES DE EVENTOS ---

//  Cambiar estado
async function handleStatusSwitch(event) {
  const switchElement = event.target;

  if (!switchElement.classList.contains("venta-status-switch")) return;

  const ventaId = switchElement.dataset.ventaId;

  const previousStatus = !switchElement.checked;
  const newStatus = switchElement.checked;

  // Si la venta estaba cancelada y está intentando habilitar
  if (previousStatus === false && newStatus === true) {
    swalWithBootstrapButtons.fire({
      icon: "error",
      title: "Ups...",
      text: "La venta ya fue cancelada, no se puede habilitar",
    });
    switchElement.checked = false;
    return;
  }

  // Confirmación con SweetAlert2
  const result = await swalWithBootstrapButtons.fire({
    title: "¿Estás seguro de cancelar esta venta?",
    text: "Una vez cancelada no se puede revertir.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Sí, cancelar",
    cancelButtonText: "No, volver",
    reverseButtons: true,
  });

  if (result.isConfirmed) {
    try {
      await ventaService.cambiarEstado(ventaId, false);

      swalWithBootstrapButtons.fire({
        icon: "success",
        title: "Éxito",
        text: "Venta cancelada con éxito",
      });

      init();
    } catch (error) {
      console.error("Error al cancelar venta:", error);
      swalWithBootstrapButtons.fire({
        icon: "error",
        title: "Ups...",
        text: "Hubo un error al cancelar la venta",
      });

      switchElement.checked = true; // revertir el cambio
    }
  } else {
    // si el usuario cancela, revierte el switch
    switchElement.checked = true;
  }
}

// manejador para crear usuario (al dar click en el botón)
async function handleCreateVentaClick(event) {
  event.preventDefault();

  // Obtener datos del usuario
  let user_token_objeto = JSON.parse(localStorage.getItem("user"));
  let usuario_token = user_token_objeto.id_usuario;

  // Crear fecha/hora actual
  const fechaHoraLocal = new Date();
  const offset = fechaHoraLocal.getTimezoneOffset();
  fechaHoraLocal.setMinutes(fechaHoraLocal.getMinutes() - offset);
  const fechaHoraISO = fechaHoraLocal.toISOString();

  const ventaData = {
    id_usuario: usuario_token,
    fecha_hora: fechaHoraISO,
  };

  try {
    swalWithBootstrapButtons.fire({
      icon: "success",
      title: "Creando venta...",
      showConfirmButton: false,
      timer: 2000,
    });

    // Crear la venta en la base de datos
    const response = await ventaService.createVenta(ventaData);
    let dataVenta = response.data_venta;

    // Guardar en localStorage
    localStorage.setItem("data_venta", JSON.stringify(dataVenta));

    // Si se hizo click en el icono o en el span siempre busca el boton
    const boton = event.target.closest("button");
    const pageToLoad = boton.dataset.page;
    loadContent(pageToLoad);
  } catch (error) {
    swalWithBootstrapButtons.fire({
      icon: "error",
      title: "Ups...",
      text: "No se pudo crear la venta",
    });
  }
}

async function handleTableClick(event) {
  // Manejador para el botón de editar
  const editButton = event.target.closest(".btn-edit-venta");
  if (editButton) {
    const ventaId = editButton.dataset.ventaId;
    openEditModal(ventaId);
    return;
  }
}

async function handleDetallesClick(event) {
  // Manejador para el botón de ver detalles
  const detallesButton = event.target.closest(".btn-detalles-venta");
  if (detallesButton) {
    const ventaId = detallesButton.dataset.ventaId;

    localStorage.setItem("id_venta_ver", JSON.stringify(ventaId));

    const pageToLoad = detallesButton.dataset.page;
    loadContent(pageToLoad);
  }
}

async function openEditModal(ventaId) {
  // Manejador para abrir modal editar con datos
  const modalElement = document.getElementById("edit-venta-modal");
  if (modalElement) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const venta = await ventaService.getVentaById(ventaId);

    document.getElementById("edit-venta-id").value = venta.id_venta;
    document.getElementById("edit-tipo-pago").value = venta.metodo_pago;

    modalInstance.show();
  } catch (error) {
    swalWithBootstrapButtons.fire({
      icon: "error",
      title: "Ups...",
      text: "Error al cargar datos de la venta.",
    });
  }
}

async function handleUpdateSubmit(event) {
  // manejador de formulario para actualizar venta (enviar informacion)
  event.preventDefault();
  const ventaId = document.getElementById("edit-venta-id").value;
  const ventaData = {
    tipo_pago: document.getElementById("edit-tipo-pago").value,
  };

  try {
    await ventaService.updateVenta(ventaId, ventaData);
    modalInstance.hide();
    swalWithBootstrapButtons.fire({
      icon: "success",
      title: "Exito",
      text: "Venta actualizada exitosamente.",
    });
    init(); // Recargamos la tabla para ver los cambios
  } catch (error) {
    swalWithBootstrapButtons.fire({
      icon: "error",
      title: "Ups...",
      text: "Error al actualizar venta.",
    });
  }
}

async function cargarMetodosPago() {
  try {
    const metodosPago = await ventaService.getMetodosPago();

    const selectTipoPago = document.getElementById("edit-tipo-pago");

    selectTipoPago.innerHTML = "";

    if (Array.isArray(metodosPago)) {
      const activos = metodosPago.filter((m) => m.estado === true);

      if (activos.length === 0) {
        selectTipoPago.innerHTML =
          "<option disabled>No hay métodos de pago activos</option>";
        return;
      }

      // Insertar solo los activos
      activos.forEach((metodo) => {
        const option = document.createElement("option");
        option.value = metodo.id_tipo;
        option.textContent = metodo.nombre;
        selectTipoPago.appendChild(option);
      });
    } else {
      // Si no hay métodos de pago disponibles, mostramos un mensaje
      selectTipoPago.innerHTML +=
        "<option disabled>No se encontraron métodos de pago</option>";
    }
  } catch (error) {
    swalWithBootstrapButtons.fire({
      icon: "error",
      title: "Ups...",
      text: "Error al cargar los métodos de pago.",
    });
  }
}

// Export: manejar clicks en el dropdown (CSV / Excel)







// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_venta" },
  { header: "fecha_hora", key: "fecha_hora" },
  { header: "nombre_usuario", key: "nombre_usuario" },
  { header: "metodo_pago", key: "metodo_pago" },
  { header: "total", key: "total" },
  { header: "Estado", key: (r) => (r.estado ? "Activo" : "Inactivo") },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Ventas");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de ventas");
}

async function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;
  event.preventDefault();
  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  let response;
  // Si no se aplicaron filtros, llamar API con las ventas del dia de hoy
  if (!activeFechaInicio || !activeFechaFin) {
    let fecha_actual = new Date();
    const hoy = convertirFecha(fecha_actual);
    response = await obtenerVentasExport(hoy, hoy);
  } else {
    // la fecha ya esta en formato YYYY/MM/DD por eso no se convierte
    const fechaInicio = activeFechaInicio;
    const fechaFin = activeFechaFin;

    response = await obtenerVentasExport(fechaInicio, fechaFin);
  }

  const data = response || [];

  if (!data || data.length === 0) {
    swalWithBootstrapButtons.fire({
      title: "No hay datos para exportar.",
      icon: "info",
    });
    return;
  }

  if (fmt === "csv") {
    exportToCSV(data, `ventas_${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `ventas_${dateTag}.xls`);
  } else if (fmt === "pdf") {
    exportToPDF(data, `ventas_${dateTag}.pdf`);
  }
}
// end exportar

async function obtenerVentasExport(fechaInicio = "", fechaFin = "") {
  "Esta funcion se hizo con el proposito de obtener ventas solo para exportar; ya que utiliza un endpoint sin paginacion";
  try {
    let response;
    if (fechaInicio && fechaFin) {
      response = await ventaService.getVentasByDateSinPag(
        fechaInicio,
        fechaFin
      );
    }

    if (!response || response.length === 0) {
      return [];
    }

    return response;
  } catch (error) {
    if (
      error.message.includes("No hay ventas en ese rango de fechas") ||
      error.response?.status === 404
    ) {
      return [];
    }
    throw error;
  }
}
