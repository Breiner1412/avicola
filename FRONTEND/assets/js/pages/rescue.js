import { rescueService } from "../api/salvamento.service.js";
import { selectDataManager } from "../utils/select-data-manager.js";

import { exportar } from "../utils/exportar.js";
let modalInstance = null;
let createModalInstance = null;

// --- VARIABLES DE PAGINACIÓN Y BÚSQUEDA ---
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
let totalRescues = 0;
let fechaInicio = null;
let fechaFin = null;
let searchTerm = "";

// --- FUNCIONES PARA CERRAR MODALES CORRECTAMENTE ---

function setupModalCloseHandlers() {
  // Modal de edición
  const editModal = document.getElementById("editRescueModal");
  if (editModal) {
    editModal.addEventListener("hidden.bs.modal", function () {
      document.getElementById("edit-rescue-form").reset();
    });
  }

  // Modal de creación
  const createModal = document.getElementById("createRescueModal");
  if (createModal) {
    createModal.addEventListener("hidden.bs.modal", function () {
      document.getElementById("create-rescue-form").reset();
    });
  }
}

// --- FUNCIÓN PARA CERRAR MODALES MANUALMENTE ---

function closeAllModals() {
  // Remover foco de cualquier elemento activo primero
  if (document.activeElement) {
    document.activeElement.blur();
  }

  const modals = document.querySelectorAll(".modal");
  modals.forEach((modal) => {
    const modalInstance = bootstrap.Modal.getInstance(modal);
    if (modalInstance) {
      modalInstance.hide();
    }
  });

  const backdrops = document.querySelectorAll(".modal-backdrop");
  backdrops.forEach((backdrop) => {
    backdrop.remove();
  });

  document.body.classList.remove("modal-open");
  document.body.style.overflow = "";
  document.body.style.paddingRight = "";

  // Forzar el foco al body después de cerrar
  document.body.focus();
}

function createRescueRow(rescue) {
  const rescueId = rescue.id_salvamento;

  const idRol = JSON.parse(localStorage.getItem("user"))?.id_rol;

  const tabla = `
        <tr>
            <td class="px-0">${rescue.nombre || `${rescue.id_galpon}`}</td>
            <td class="px-0">${rescue.fecha}</td>
            <td class="px-0">${rescue.raza || `${rescue.id_tipo_gallina}`}</td>
            <td class="px-0">${rescue.cantidad_gallinas} gallinas</td>
            <td class="px-0 text-end">
                <button class="btn btn-success btn-sm btn-edit-rescue" data-rescue-id="${rescueId}" aria-label="Editar">
                    <i class="fa-regular fa-pen-to-square me-0"></i>
                </button>
                ${
                  idRol === 1 || idRol === 2
                    ? `
                    <button class="btn btn-secondary btn-sm btn-delete-rescue" data-rescue-id="${rescueId}">
                        <i class="fa fa-trash me-0"></i>
                    </button>
                `
                    : ""
                }
            </td>
        </tr>
    `;

  return tabla;
}

// --- FUNCIONES PARA CARGAR SELECTS ---

function populateShedSelect(selectElement, selectedId = null) {
  const sheds = selectDataManager.getShedOptions();
  selectElement.innerHTML = '<option value="">Seleccionar Galpón</option>';

  sheds.forEach((shed) => {
    const option = document.createElement("option");
    option.value = shed.value;
    option.textContent = shed.text;
    if (selectedId && shed.value === selectedId) {
      option.selected = true;
    }
    selectElement.appendChild(option);
  });
}

function populateChickenTypeSelect(selectElement, selectedId = null) {
  const chickenTypes = selectDataManager.getChickenTypeOptions();
  selectElement.innerHTML =
    '<option value="">Seleccionar Tipo de Gallina</option>';

  chickenTypes.forEach((type) => {
    const option = document.createElement("option");
    option.value = type.value;
    option.textContent = type.text;
    if (selectedId && type.value === selectedId) {
      option.selected = true;
    }
    selectElement.appendChild(option);
  });
}

// --- BÚSQUEDA INTELIGENTE ---

function setupSearchListener() {
  const searchInput = document.getElementById("buscador-salvamentos");
  if (searchInput) {
    searchInput.addEventListener("input", function (e) {
      searchTerm = e.target.value.toLowerCase().trim();
      currentPage = 1;
      loadRescuesWithPagination();
    });
  }
}

function filterRescues(rescues) {
  if (!searchTerm) return rescues;

  return rescues.filter((rescue) => {
    const galpon = (
      rescue.nombre || `Galpón ${rescue.id_galpon}`
    ).toLowerCase();
    const tipoGallina = (
      rescue.raza || `Tipo ${rescue.id_tipo_gallina}`
    ).toLowerCase();
    const cantidad = rescue.cantidad_gallinas.toString();
    const fecha = rescue.fecha.toLowerCase();
    const id = rescue.id_salvamento.toString();

    return (
      galpon.includes(searchTerm) ||
      tipoGallina.includes(searchTerm) ||
      cantidad.includes(searchTerm) ||
      fecha.includes(searchTerm) ||
      id.includes(searchTerm)
    );
  });
}

// --- FUNCIONES DE EXPORTACIÓN MEJORADAS ---

function setupExportButtons() {
  // Exportar a Excel
  document
    .getElementById("export-excel")
    ?.addEventListener("click", exportToExcel);
  // Exportar a PDF
  document.getElementById("export-pdf")?.addEventListener("click", exportToPDF);
  // Exportar a CSV
  document.getElementById("export-csv")?.addEventListener("click", exportToCSV);
  // Imprimir
  document
    .getElementById("export-print")
    ?.addEventListener("click", exportToPrint);
}

async function getAllRescuesForExport() {
  try {
    let allRescues = [];
    let currentPage = 1;
    let hasMoreData = true;

    Swal.fire({
      title: "Obteniendo datos...",
      text: "Recopilando información para exportar",
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    // Obtener datos paginados hasta que no haya más
    while (hasMoreData) {
      const response = await fetchWithoutDates(currentPage, 100); // 100 por página
      if (response && response.rescues && response.rescues.length > 0) {
        allRescues = allRescues.concat(response.rescues);
        currentPage++;

        // Actualizar progreso
        Swal.update({
          text: `Recopilando datos... (${allRescues.length} registros)`,
        });

        // Verificar si hay más páginas
        if (currentPage > response.total_pages) {
          hasMoreData = false;
        }

        // Pequeña pausa para no saturar el servidor
        await new Promise((resolve) => setTimeout(resolve, 100));
      } else {
        hasMoreData = false;
      }
    }

    Swal.close();
    return allRescues;
  } catch (error) {
    Swal.close();
    throw error;
  }
}




const COLUMNAS_EXPORTACION = [
  { header: "ID Salvamento", key: "id_salvamento" },
  { header: "Galpón", key: (r) => r.nombre || `Galpón ${r.id_galpon}` },
  { header: "Fecha", key: "fecha" },
  { header: "Tipo Gallina", key: (r) => r.raza || `Tipo ${r.id_tipo_gallina}` },
  { header: "Cantidad Gallinas", key: "cantidad_gallinas" },
];

async function exportarSalvamentos(formato, event) {
  event?.preventDefault();
  try {
    const data = await getAllRescuesForExport();
    const fecha = new Date().toISOString().split("T")[0];
    await exportar(formato, data, {
      columnas: COLUMNAS_EXPORTACION,
      nombre: `salvamentos_${fecha}`,
      titulo: "Reporte de Salvamentos",
      hoja: "Salvamentos",
    });
  } catch (error) {
    console.error("Error exportando salvamentos:", error);
    Swal.fire({ icon: "error", title: "Error", text: "No se pudo exportar" });
  }
}

const exportToExcel = (e) => exportarSalvamentos("excel", e);
const exportToPDF = (e) => exportarSalvamentos("pdf", e);
const exportToCSV = (e) => exportarSalvamentos("csv", e);

function exportToPrint() {
  const table = document.querySelector(".table");
  const printWindow = window.open("", "_blank");

  printWindow.document.write(`
        <html>
            <head>
                <title>Reporte de Salvamentos</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #198754; color: white; }
                    h1 { color: #198754; }
                    @media print { body { margin: 0; } }
                </style>
            </head>
            <body>
                <h1>Reporte de Salvamentos</h1>
                <p>Generado: ${new Date().toLocaleDateString()}</p>
                ${table.outerHTML}
            </body>
        </html>
    `);

  printWindow.document.close();
  printWindow.print();
}

// --- LÓGICA DE MODAL MEJORADA ---

async function openEditModal(rescueId) {
  const modalElement = document.getElementById("editRescueModal");

  if (!modalElement) {
    return;
  }

  try {
    // Cerrar modales existentes
    closeAllModals();

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Crear nueva instancia de modal
    modalInstance = new bootstrap.Modal(modalElement, {
      backdrop: true,
      keyboard: true,
      focus: true,
    });

    const rescue = await rescueService.getRescueById(rescueId);

    // Llenar selects con datos reales
    const shedSelect = document.getElementById("edit-id_galpon");
    const chickenTypeSelect = document.getElementById("edit-id_tipo_gallina");

    if (shedSelect) populateShedSelect(shedSelect, rescue.id_galpon);
    if (chickenTypeSelect)
      populateChickenTypeSelect(chickenTypeSelect, rescue.id_tipo_gallina);

    // Llenar otros campos
    document.getElementById("edit-rescue-id").value = rescue.id_salvamento;
    document.getElementById("edit-fecha").value = rescue.fecha;
    document.getElementById("edit-cantidad_gallinas").value =
      rescue.cantidad_gallinas;

    // EVENTO PARA MANEJAR EL FOCO
    modalElement.addEventListener("shown.bs.modal", function () {
      // Forzar el foco al primer elemento del modal
      const firstInput = modalElement.querySelector("input, select, textarea");
      if (firstInput) {
        firstInput.focus();
      }
    });

    modalInstance.show();
  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del salvamento.",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
  }
}

function openCreateModal() {
  // Cerrar cualquier modal abierto primero
  closeAllModals();

  // Pequeño delay para asegurar que Bootstrap esté listo
  setTimeout(() => {
    const createModalElement = document.getElementById("createRescueModal");
    if (!createModalElement) {
      return;
    }

    // Crear nueva instancia de modal
    createModalInstance = new bootstrap.Modal(createModalElement, {
      backdrop: true,
      keyboard: true,
      focus: true,
    });

    // Llenar selects con datos reales
    const shedSelect = document.getElementById("create-id_galpon");
    const chickenTypeSelect = document.getElementById("create-id_tipo_gallina");

    if (shedSelect) populateShedSelect(shedSelect);
    if (chickenTypeSelect) populateChickenTypeSelect(chickenTypeSelect);

    // Establecer fecha actual por defecto
    document.getElementById("create-fecha").value = new Date()
      .toISOString()
      .split("T")[0];
    document.getElementById("create-cantidad_gallinas").value = "";

    createModalInstance.show();
  }, 50);
}

// --- MANEJADORES DE EVENTOS ---

async function handleUpdateSubmit(event) {
  event.preventDefault();
  const rescueId = document.getElementById("edit-rescue-id").value;
  const updatedData = {
    id_galpon: parseInt(document.getElementById("edit-id_galpon").value),
    fecha: document.getElementById("edit-fecha").value,
    id_tipo_gallina: parseInt(
      document.getElementById("edit-id_tipo_gallina").value
    ),
    cantidad_gallinas: parseInt(
      document.getElementById("edit-cantidad_gallinas").value
    ),
  };

  // Validación básica
  if (
    !updatedData.id_galpon ||
    !updatedData.id_tipo_gallina ||
    !updatedData.cantidad_gallinas
  ) {
    Swal.fire({
      icon: "warning",
      title: "Campos incompletos",
      text: "Por favor complete todos los campos obligatorios",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
    return;
  }

  try {
    await rescueService.updateRescue(rescueId, updatedData);
    if (modalInstance) modalInstance.hide();
    await loadRescuesWithPagination();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Salvamento actualizado exitosamente.",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo actualizar el salvamento",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
  }
}

async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-rescue");
  if (editButton) {
    const rescueId = editButton.dataset.rescueId;
    openEditModal(rescueId);
    return;
  }

  const deleteButton = event.target.closest(".btn-delete-rescue");
  if (deleteButton) {
    const rescueId = deleteButton.dataset.rescueId;
    await handleDeleteRescue(rescueId);
    return;
  }
}

async function handleDeleteRescue(rescueId) {
  const result = await Swal.fire({
    title: "¿Estás seguro?",
    text: "¿Estás seguro de que deseas eliminar este salvamento?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#198754",
    cancelButtonColor: "#6c757d",
    confirmButtonText: "Sí, eliminar",
    cancelButtonText: "Cancelar",
  });

  if (result.isConfirmed) {
    try {
      await rescueService.deleteRescue(rescueId);
      Swal.fire({
        icon: "success",
        title: "Eliminado",
        text: "Salvamento eliminado exitosamente.",
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#198754",
      });
      await loadRescuesWithPagination();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo eliminar el salvamento.",
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#198754",
      });
    }
  }
}

async function handleCreateSubmit(event) {
  event.preventDefault();

  const newRescueData = {
    id_galpon: parseInt(document.getElementById("create-id_galpon").value),
    fecha: document.getElementById("create-fecha").value,
    id_tipo_gallina: parseInt(
      document.getElementById("create-id_tipo_gallina").value
    ),
    cantidad_gallinas: parseInt(
      document.getElementById("create-cantidad_gallinas").value
    ),
  };

  // Validación básica
  if (
    !newRescueData.id_galpon ||
    !newRescueData.id_tipo_gallina ||
    !newRescueData.cantidad_gallinas
  ) {
    Swal.fire({
      icon: "warning",
      title: "Campos incompletos",
      text: "Por favor complete todos los campos obligatorios",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
    return;
  }

  try {
    await rescueService.createRescue(newRescueData);

    if (createModalInstance) {
      createModalInstance.hide();
    }

    document.getElementById("create-rescue-form").reset();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Salvamento creado exitosamente.",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
    await loadRescuesWithPagination();
  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo crear el salvamento",
      confirmButtonText: "Aceptar",
      confirmButtonColor: "#198754",
    });
  }
}

// --- CONFIGURAR BOTONES DE CANCELAR ---

function setupCancelButtons() {
  // Botones de cancelar en modales
  const cancelButtons = document.querySelectorAll('[data-bs-dismiss="modal"]');
  cancelButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      closeAllModals();
    });
  });
}

// --- FUNCIONES DE PAGINACIÓN ---

function setupPaginationEventListeners() {
  // Select de tamaño de página
  const pageSizeSelect = document.getElementById("page-size");
  if (pageSizeSelect) {
    pageSizeSelect.addEventListener("change", function () {
      pageSize = parseInt(this.value);
      currentPage = 1;
      loadRescuesWithPagination();
    });
  }

  // Botón de filtrar
  const btnFiltrar = document.getElementById("btn-filtrar");
  if (btnFiltrar) {
    btnFiltrar.addEventListener("click", function () {
      fechaInicio = document.getElementById("fecha-inicio").value;
      fechaFin = document.getElementById("fecha-fin").value;

      // Validar fechas
      if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
        Swal.fire({
          icon: "warning",
          title: "Fechas inválidas",
          text: "La fecha de inicio no puede ser mayor que la fecha de fin",
          confirmButtonText: "Aceptar",
          confirmButtonColor: "#198754",
        });
        return;
      }

      currentPage = 1;
      loadRescuesWithPagination();
    });
  }

  // Botón de limpiar
  const btnLimpiar = document.getElementById("btn-limpiar");
  if (btnLimpiar) {
    btnLimpiar.addEventListener("click", function () {
      document.getElementById("fecha-inicio").value = "";
      document.getElementById("fecha-fin").value = "";
      fechaInicio = null;
      fechaFin = null;
      currentPage = 1;
      loadRescuesWithPagination();
    });
  }
}

function renderPagination() {
  const paginationElement = document.getElementById("pagination");
  if (!paginationElement) return;

  paginationElement.innerHTML = "";

  // Botón Anterior
  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage - 1
        }">
            <i class="fas fa-chevron-left"></i>
        </a>
    `;
  paginationElement.appendChild(prevLi);

  // Números de página
  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, currentPage + 2);

  for (let i = startPage; i <= endPage; i++) {
    const pageLi = document.createElement("li");
    pageLi.className = `page-item ${i === currentPage ? "active" : ""}`;
    pageLi.innerHTML = `
            <a class="page-link ${
              i === currentPage ? "bg-success border-success" : "text-success"
            }" href="#" data-page="${i}">${i}</a>
        `;
    paginationElement.appendChild(pageLi);
  }

  // Botón Siguiente
  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${
    currentPage === totalPages ? "disabled" : ""
  }`;
  nextLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage + 1
        }">
            <i class="fas fa-chevron-right"></i>
        </a>
    `;
  paginationElement.appendChild(nextLi);

  // Event listeners para los botones de paginación
  paginationElement.querySelectorAll(".page-link").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const page = parseInt(this.getAttribute("data-page"));
      if (page >= 1 && page <= totalPages && page !== currentPage) {
        currentPage = page;
        loadRescuesWithPagination();
      }
    });
  });
}

async function loadRescuesWithPagination() {
  const tableBody = document.getElementById("rescue-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando salvamentos...</td></tr>';

  try {
    let response;

    if (fechaInicio && fechaFin) {
      // Usar endpoint con filtro de fechas
      response = await fetchWithDates(
        fechaInicio,
        fechaFin,
        currentPage,
        pageSize
      );
    } else {
      // Usar endpoint normal
      response = await fetchWithoutDates(currentPage, pageSize);
    }

    if (response && response.rescues && response.rescues.length > 0) {
      let rescuesToShow = response.rescues;

      // Aplicar filtro de búsqueda si existe
      if (searchTerm) {
        rescuesToShow = filterRescues(response.rescues);
      }

      if (rescuesToShow.length > 0) {
        tableBody.innerHTML = rescuesToShow.map(createRescueRow).join("");
        totalPages = response.total_pages;
        totalRescues = response.total_rescues;
      } else {
        tableBody.innerHTML =
          '<tr><td colspan="5" class="text-center">No se encontraron salvamentos con ese criterio.</td></tr>';
        totalPages = 1;
        totalRescues = 0;
      }

      updatePaginationInfo();
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="5" class="text-center">No se encontraron salvamentos.</td></tr>';
      totalPages = 1;
      totalRescues = 0;
      updatePaginationInfo();
    }

    renderPagination();
  } catch (error) {
    tableBody.innerHTML =
      '<tr><td colspan="5" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }
}

async function fetchWithDates(fechaInicio, fechaFin, page, size) {
  // Validación de fechas antes de la petición
  if (!fechaInicio || !fechaFin) {
    throw new Error("Debe proporcionar fechas válidas en formato YYYY-MM-DD");
  }

  try {
    const data = await rescueService.getRescuesAllDate(
      fechaInicio,
      fechaFin,
      page,
      size
    );
    // Validación para cuando no hay datos
    if (!data || (Array.isArray(data.rescue) && data.rescue.length === 0)) {
      return {
        rescue: [],
        total_rescue: 0,
        total_pages: 0,
        page,
        size,
      };
    }

    return data;
  } catch (error) {
    throw error;
  }
}

async function fetchWithoutDates(page, size) {
  try {
    const data = await rescueService.getRescuesAll(page, size);
    return data;
  } catch (error) {
    throw error;
  }
}

function updatePaginationInfo() {}

// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---

async function init() {
  // Cargar datos para los selects primero
  if (!selectDataManager.isLoaded) {
    try {
      await selectDataManager.loadData();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "Error cargando datos",
        confirmButtonText: "Aceptar",
        confirmButtonColor: "#198754",
      });
    }
  }

  // Configurar event listeners de paginación
  setupPaginationEventListeners();

  // Configurar buscador inteligente
  setupSearchListener();

  // Configurar botones de exportación
  setupExportButtons();

  // Cargar datos con paginación
  await loadRescuesWithPagination();

  // Configurar event listeners existentes
  const tableBody = document.getElementById("rescue-table-body");
  const editForm = document.getElementById("edit-rescue-form");
  const createForm = document.getElementById("create-rescue-form");
  const createButton = document.querySelector(
    '[data-bs-target="#createRescueModal"]'
  );

  if (tableBody) {
    tableBody.removeEventListener("click", handleTableClick);
    tableBody.addEventListener("click", handleTableClick);
  }

  if (editForm) {
    editForm.removeEventListener("submit", handleUpdateSubmit);
    editForm.addEventListener("submit", handleUpdateSubmit);
  }

  if (createForm) {
    createForm.removeEventListener("submit", handleCreateSubmit);
    createForm.addEventListener("submit", handleCreateSubmit);
  }

  if (createButton) {
    createButton.removeEventListener("click", openCreateModal);
    createButton.addEventListener("click", openCreateModal);
  }

  // Configurar handlers para cerrar modales
  setupModalCloseHandlers();
  setupCancelButtons();
}

export { init };
