import { typeChickenService } from "../api/tipo-gallina.service.js";

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let createModalInstance = null;
let allTypeChickens = [];

function createTypeChickenRow(typeChicken) {
  return `
    <tr>
      <td class="px-0">${typeChicken.raza}</td>
      <td class="px-0">${typeChicken.descripcion}</td>
      <td class="px-0 text-end">
          <button class="btn btn-success btn-sm btn-edit-tipo-gallina" aria-label="Editar" title="Editar" data-tipo-gallina-id="${typeChicken.id_tipo_gallinas}">
            <i class="fa-regular fa-pen-to-square me-0"></i>
          </button>
      </td>
    </tr>
  `;
}

// --- LÓGICA DE MODAL ---

async function openEditModal(id) {
  const modalElement = document.getElementById("edit-tipo-gallina-modal");
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }
  try {
    const typeChicken = await typeChickenService.getTypeChickenById(id);
    document.getElementById("edit-tipo-gallina-id").value =
      typeChicken.id_tipo_gallinas;
    document.getElementById("edit-raza").value = typeChicken.raza;
    document.getElementById("edit-descripcion").value = typeChicken.descripcion;
    modalInstance.show();
  } catch (error) {
    await Swal.fire({
      icon: "error",
      text: "No se pudieron cargar los datos del tipo de gallina.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

// --- MANEJADORES DE EVENTOS ---

async function handleUpdateSubmit(event) {
  event.preventDefault();
  const typeChickenId = document.getElementById("edit-tipo-gallina-id").value;
  const updatedData = {
    raza: document.getElementById("edit-raza").value,
    descripcion: document.getElementById("edit-descripcion").value,
  };

  try {
    await typeChickenService.updateTypeChicken(typeChickenId, updatedData);
    modalInstance.hide();
    await Swal.fire({
      icon: "success",
      text: "Tipo de gallina actualizado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    init(); // Recargamos la tabla para ver los cambios
  } catch (error) {
    if (
      error.message ===
      "El tipo de gallina con esa raza y descripción ya existe."
    ) {
      await Swal.fire({
        icon: "error",
        text: "El tipo de gallina con esa raza y descripción ya existe.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    } else {
      await Swal.fire({
        icon: "error",
        text: "Error al actualizar tipo de gallina.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    }
  }
}

async function handleTableClick(event) {
  // Manejador para el botón de editar
  const editButton = event.target.closest(".btn-edit-tipo-gallina");
  if (editButton) {
    const id = editButton.dataset.tipoGallinaId;
    openEditModal(id);
    return;
  }
}

// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---

// manejador de formulario crear tipos
async function handleCreateSubmit(event) {
  event.preventDefault();

  const newtypeChikenData = {
    raza: document.getElementById("create-raza").value,
    descripcion: document.getElementById("create-descripcion").value,
  };

  try {
    await typeChickenService.createTypeChicken(newtypeChikenData);
    if (createModalInstance) createModalInstance.hide();
    document.getElementById("create-tipo-gallina-form").reset(); // Limpiamos el formulario
    await Swal.fire({
      icon: "success",
      text: "Tipo de gallina creado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    init(); // Recargamos la tabla para ver el nuevo tipo
  } catch (error) {
    if (
      error.message ===
      "El tipo de gallina con esa raza y descripción ya existe."
    ) {
      await Swal.fire({
        icon: "error",
        text: "El tipo de gallina con esa raza y descripción ya existe.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    } else {
      await Swal.fire({
        icon: "error",
        text: "Error al crear tipo de gallina.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    }
  }
}

//EXPORTACION
document.addEventListener("click", function (event) {
  const exportBtn = event.target.closest(".export-format");
  if (!exportBtn) return;
  event.preventDefault();
  handleExportClick(event);
});

// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_tipo_gallinas" },
  { header: "Raza", key: "raza" },
  { header: "Descripcion", key: "descripcion" },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Tipos de gallinas");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Tipos de Gallinas");
}

function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;
  // Solo responder si la página visible es la de tipos de gallinas
  if (window.currentPage !== "tipos_gallinas") return;
  event.preventDefault();

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);
  const data = allTypeChickens;
  if (!data || data.length === 0) {
    Swal.fire({
      title: "No hay datos para exportar.",
      icon: "info",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    return;
  }

  if (fmt === "csv") {
    exportToCSV(data, `Tipos de gallinas${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `Tipos de gallinas${dateTag}.xlsx`);
  } else if (fmt === "pdf") {
    exportToPDF(data, `Tipos de gallinas${dateTag}.pdf`);
  }
}







async function init() {
  const tableBody = document.getElementById("tipo-gallina-table-body");
  if (!tableBody) return;

  if (!createModalInstance) {
    const createModalElement = document.getElementById(
      "create-tipo-gallina-modal"
    );
    createModalInstance = new bootstrap.Modal(createModalElement);
  }

  tableBody.innerHTML =
    '<tr><td colspan="4" class="text-center">Cargando tipos de gallinas ... </td></tr>'; // ✅ CORRECCIÓN: colspan="4"

  try {
    const typeChicken = await typeChickenService.getTypeChicken();
    allTypeChickens = typeChicken;
    if (typeChicken && typeChicken.length > 0) {
      tableBody.innerHTML = typeChicken.map(createTypeChickenRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="4" class="text-center">No se encontraron tipos de gallinas.</td></tr>'; // ✅ CORRECCIÓN: colspan="4"
    }
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Error al cargar los datos.</td></tr>`; // ✅ CORRECCIÓN: colspan="4"
  }

  // Aplicamos el patrón remove/add para evitar listeners duplicados
  const editForm = document.getElementById("edit-tipo-gallina-form");
  const createForm = document.getElementById("create-tipo-gallina-form");
  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);
  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);
  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);
}

export { init };
