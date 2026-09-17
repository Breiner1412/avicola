import { metodoPagoService } from '../api/pay_methods.service.js';

import { exportarCSV, exportarExcel } from "../utils/exportar.js";
let modalInstance = null;
let createModalInstance = null;
let originalNombre = null;

let allMetodos = [];
let filteredMetodos = [];

// -----------------------------------------------------
// ROW TEMPLATE
// -----------------------------------------------------

function createMetodoPagoRow(metodo) {
  const metodoId = metodo.id_tipo;

  return `
    <tr>
      <td class="cell">${metodoId}</td>
      <td class="cell">${metodo.nombre}</td>
      <td class="cell">${metodo.descripcion}</td>

      <td class="cell">
        <div class="form-check form-switch d-inline-block">
          <input class="form-check-input metodo-status-switch" type="checkbox"
            data-metodo-id="${metodoId}"
            ${metodo.estado ? "checked" : ""}
          >
        </div>
      </td>

      <td class="cell text-end">
      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-sm btn-success btn-edit-metodo" data-metodo-id="${metodoId}">
          <i class="fa-regular fa-pen-to-square"></i>
        </button>
      </div>
      </td>
    </tr>
  `;
}



// -----------------------------------------------------
//       EXPORT FUNCTIONS (CSV / XLSX)
// -----------------------------------------------------





// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_tipo" },
  { header: "Nombre", key: "nombre" },
  { header: "Descripción", key: "descripcion" },
  { header: "Estado", key: (r) => (r.estado ? "Activo" : "Inactivo") },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Métodos Pago");
}

function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;

  event.preventDefault();

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  const data = filteredMetodos.length ? filteredMetodos : allMetodos;

  if (!data || data.length === 0) {
    Swal.fire({ title: "No hay datos para exportar.", icon: "info" });
    return;
  }

  if (fmt === "csv") {
    exportToCSV(data, `metodos_pago_${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `metodos_pago_${dateTag}.xlsx`);
  }
}



// -----------------------------------------------------
//       EDIT MODAL
// -----------------------------------------------------

async function openEditModal(id) {
  const modalElement = document.getElementById('edit-metodo_pago-modal');

  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const metodo = await metodoPagoService.getMetodoPagoById(id);
    originalNombre = metodo.nombre;

    document.getElementById('edit-metodo_pago-id').value = metodo.id_tipo;
    document.getElementById('edit-nombre').value = metodo.nombre;
    document.getElementById('edit-descripcion').value = metodo.descripcion;

    modalInstance.show();
  } catch (error) {
    console.error(`Error al obtener método de pago ${id}:`, error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del método de pago.",
    });
  }
}



// -----------------------------------------------------
//       HANDLERS
// -----------------------------------------------------

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const metodoId = document.getElementById('edit-metodo_pago-id').value;

  const updatedData = {
    nombre: document.getElementById('edit-nombre').value.trim(),
    descripcion: document.getElementById('edit-descripcion').value.trim(),
  };


  if (!updatedData.nombre || updatedData.nombre.length < 3) {
    Swal.fire({
      icon: "error",
      title: "Nombre inválido",
      text: "El nombre debe tener al menos 3 caracteres válidos.",
    });
    return;
  }

  if (!updatedData.descripcion || updatedData.descripcion.length < 1) {
    Swal.fire({
      icon: "error",
      title: "Descripción inválida",
      text: "La descripción no puede estar vacía.",
    });
    return;
  }

  try {
    await metodoPagoService.updateMetodoPago(metodoId, updatedData);
    modalInstance.hide();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Método de pago actualizado exitosamente.",
    });
    await init();  
    applyFilter();
  } catch (error) {
    if (error.message == "El nombre del método de pago ya existe.") {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "El nombre del método de pago ya está registrado. Por favor, use otro nombre.",
    });
      return;
    }


    console.error('Error al actualizar método de pago:', error);
   
  }
}


async function handleTableClick(event) {
  const editButton = event.target.closest('.btn-edit-metodo');
  if (editButton) {
    const id = editButton.dataset.metodoId;
    openEditModal(id);
    return;
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains('metodo-status-switch')) return;

  const metodoId = switchElement.dataset.metodoId;
  const newStatus = switchElement.checked;

  const actionText = newStatus ? "activar" : "desactivar";

  // SweetAlert de confirmación
  const result = await Swal.fire({
    title: `¿Estás seguro?`,
    text: `¿Deseas ${actionText} este método de pago?`,
    icon: "warning",
    showCancelButton: true,
    cancelButtonText: "Cancelar",
    confirmButtonText: `Sí, ${actionText}`,
    customClass: {
      confirmButton: "btn btn-success",   // clase de Bootstrap success
      cancelButton: "btn btn-secondary"   // clase de Bootstrap secondary
    },
    
  });


  if (!result.isConfirmed) {
    switchElement.checked = !newStatus; // revertir
    return;
  }

  try {
    await metodoPagoService.changeMetodoPagoStatus(metodoId, newStatus);

    await Swal.fire({
      icon: "success",
      title: "Éxito",
      text: `Método de pago ${newStatus ? "activado" : "desactivado"} exitosamente.`,
      timer: 1500,
      showConfirmButton: false,
    });

    await init();
    applyFilter();

  } catch (error) {
    console.error(`Error al ${actionText} el método de pago ${metodoId}:`, error);

    await Swal.fire({
      icon: "error",
      title: "Error",
      text: `No se pudo ${actionText} el método de pago.`,
    });

    switchElement.checked = !newStatus;
  }
}



// -----------------------------------------------------
//       CREAR
// -----------------------------------------------------

async function handleCreateSubmit(event) {
  event.preventDefault();

  const newMetodoData = {
    nombre: document.getElementById('create-nombre').value.trim(),
    descripcion: document.getElementById('create-descripcion').value.trim(),
    estado: true
  };


  if (!newMetodoData.nombre || newMetodoData.nombre.length < 3) {
    Swal.fire({
      icon: "error",
      title: "Nombre inválido",
      text: "El nombre debe tener al menos 3 caracteres válidos.",
    });
    return;
  }

  if (!newMetodoData.descripcion || newMetodoData.descripcion.length < 1) {
    Swal.fire({
      icon: "error",
      title: "Descripción inválida",
      text: "La descripción no puede estar vacía.",
    });
    return;
  }

  try {
    await metodoPagoService.createMetodoPago(newMetodoData);


  if (createModalInstance) {
    createModalInstance.hide();
  }
    document.getElementById('create-metodo_pago-form').reset();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Método de pago creado exitosamente.",
    });
    await init();
    applyFilter();
  } catch (error) {
    if (error.message == "El nombre del método de pago ya existe.") {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "El nombre del método de pago ya está registrado. Por favor, use otro nombre.",
    });
      return;
    }


    console.error('Error al crear método de pago:', error);
    
  }
}


// -----------------------------------------------------
//       INIT
// -----------------------------------------------------

async function init() {

  const filterSelect = document.getElementById("filter-metodos");
    filterSelect.removeEventListener("change", applyFilter);
    filterSelect.addEventListener("change", applyFilter);

  const createModalElement = document.getElementById('create-metodo_pago-modal');
    createModalInstance = new bootstrap.Modal(createModalElement);
    
  createModalElement.addEventListener("hidden.bs.modal", () => {
    document.getElementById("create-metodo_pago-form").reset();
  });


  const tableBody = document.getElementById('metodos_pago-table-body');
  if (!tableBody) return;

  tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Cargando métodos de pago ...</td></tr>';

  try {
    allMetodos = await metodoPagoService.getMetodosPago();
    filteredMetodos = [];

    if (allMetodos && allMetodos.length > 0) {
      tableBody.innerHTML = allMetodos.map(createMetodoPagoRow).join('');
    } else {
      tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No se encontraron métodos de pago.</td></tr>';
    }
  } catch (error) {
    console.error('Error al obtener métodos de pago:', error);
    tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }

  const editForm = document.getElementById('edit-metodo_pago-form');
  const createForm = document.getElementById('create-metodo_pago-form');

  tableBody.removeEventListener('click', handleTableClick);
  tableBody.addEventListener('click', handleTableClick);

  tableBody.removeEventListener('change', handleStatusSwitch);
  tableBody.addEventListener('change', handleStatusSwitch);

  editForm.removeEventListener('submit', handleUpdateSubmit);
  editForm.addEventListener('submit', handleUpdateSubmit);

  createForm.removeEventListener('submit', handleCreateSubmit);
  createForm.addEventListener('submit', handleCreateSubmit);

  // <<<------ EXPORT HOOK ----->>>
  const exportDropdownMenu = document.querySelector("#export-btn + .dropdown-menu");

  if (exportDropdownMenu) {
    exportDropdownMenu.removeEventListener("click", handleExportClick);
    exportDropdownMenu.addEventListener("click", handleExportClick);
  }
}


export { init };

function applyFilter() {
  const filterValue = document.getElementById("filter-metodos").value;
  const tableBody = document.getElementById("metodos_pago-table-body");

  if (!allMetodos.length) return;

  if (filterValue === "all") {
    filteredMetodos = [];
    tableBody.innerHTML = allMetodos.map(createMetodoPagoRow).join('');
    return;
  }

  if (filterValue === "active") {
    filteredMetodos = allMetodos.filter(m => m.estado === true);
  }

  if (filterValue === "inactive") {
    filteredMetodos = allMetodos.filter(m => m.estado === false);
  }

  tableBody.innerHTML = filteredMetodos.length
    ? filteredMetodos.map(createMetodoPagoRow).join('')
    : '<tr><td colspan="5" class="text-center">No hay métodos de pago que coincidan.</td></tr>';
}

