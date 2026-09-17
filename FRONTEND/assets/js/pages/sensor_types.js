import { sensorTypeService } from "../api/sensorType.service.js";

let modalInstance = null;
let createModalInstance = null;
let allSensorTypes = [];

function createSensorTypeRow(sensorType) {
  const tipoId = sensorType.id_tipo;

  const editButton = `<button class="btn btn-sm btn-success btn-edit-sensor-type" data-tipo-id="${tipoId}">
        <i class="fa-regular fa-pen-to-square"></i>
      </button>`;

  const statusCell = `<div class="form-check form-switch d-inline-block">
        <input class="form-check-input sensor-type-status-switch" type="checkbox" 
          id="switch-type-${tipoId}" data-tipo-id="${tipoId}"
          ${sensorType.estado ? "checked" : ""}>
        <label class="form-check-label" for="switch-type-${tipoId}">
          ${sensorType.estado ? "Activo" : "Inactivo"}
        </label>
      </div>`;

  return `
    <tr>
      <td class="cell">${sensorType.nombre}</td>
      <td class="cell">${sensorType.modelo}</td>
      <td class="cell">${sensorType.descripcion}</td>
      <td class="cell">${statusCell}</td>
      <td class="cell">${editButton}</td>
    </tr>
  `;
}

function filterSensorTypes(filterValue) {
  let filteredTypes = [];

  if (filterValue === "all") {
    filteredTypes = allSensorTypes;
  } else if (filterValue === "active") {
    filteredTypes = allSensorTypes.filter(t => t.estado === 1 || t.estado === true);
  } else if (filterValue === "inactive") {
    filteredTypes = allSensorTypes.filter(t => t.estado === 0 || t.estado === false);
  }

  const tableBody = document.getElementById("sensor-types-table-body");
  if (!tableBody) return;

  if (filteredTypes.length > 0) {
    tableBody.innerHTML = filteredTypes.map(createSensorTypeRow).join("");
  } else {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center">No hay tipos de sensores con ese filtro.</td>
      </tr>
    `;
  }
}

async function openEditModal(tipoId) {
  const modalElement = document.getElementById("edit-sensor-type-modal");
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }
  try {
    const tipo = await sensorTypeService.getSensorTypeById(tipoId);
    document.getElementById("edit-type-id").value = tipo.id_tipo;
    document.getElementById("edit-type-nombre").value = tipo.nombre;
    document.getElementById("edit-type-modelo").value = tipo.modelo;
    document.getElementById("edit-type-descripcion").value = tipo.descripcion;
    modalInstance.show();
  } catch (error) {
    console.error("Error al obtener tipo de sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del tipo de sensor.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
  }
}

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const tipoId = document.getElementById("edit-type-id").value;
  const nombre = document.getElementById("edit-type-nombre").value.trim();
  const modelo = document.getElementById("edit-type-modelo").value.trim();
  const descripcion = document.getElementById("edit-type-descripcion").value.trim();

  if (descripcion.length < 10) {
    Swal.fire({
      icon: "warning",
      title: "Descripción Inválida",
      text: "La descripción debe tener al menos 10 caracteres.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
    return;
  }

  const updatedData = { nombre, modelo, descripcion };

  try {
    await sensorTypeService.updateSensorType(tipoId, updatedData);
    modalInstance.hide();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Tipo de sensor actualizado exitosamente.",
      showConfirmButton: false,
      timer: 1200
    });
    init();
  } catch (error) {
    console.error("Error al actualizar tipo de sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo actualizar el tipo de sensor.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
  }
}

async function handleCreateSubmit(event) {
  event.preventDefault();

  const nombre = document.getElementById("create-type-nombre").value.trim();
  const modelo = document.getElementById("create-type-modelo").value.trim();
  const descripcion = document.getElementById("create-type-descripcion").value.trim();

  if (descripcion.length < 10) {
    Swal.fire({
      icon: "warning",
      title: "Descripción Inválida",
      text: "La descripción debe tener al menos 10 caracteres.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
    return;
  }

  const newTypeData = { nombre, modelo, descripcion, estado: true };

  try {
    await sensorTypeService.createSensorType(newTypeData);
    if (createModalInstance) createModalInstance.hide();
    document.getElementById("create-sensor-type-form").reset();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Tipo de sensor creado exitosamente.",
      showConfirmButton: false,
      timer: 1400
    });
    init();
  } catch (error) {
    console.error("Error al crear tipo de sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo crear el tipo de sensor.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains("sensor-type-status-switch")) return;

  const tipoId = switchElement.dataset.tipoId;
  const newStatus = switchElement.checked;

  const confirmacion = await Swal.fire({
    title: `¿Deseas ${switchElement.checked ? 'activar' : 'desactivar'} este tipo de sensor?`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Aceptar',
    cancelButtonText: 'Cancelar',
    reverseButtons: true,
    customClass: {
      confirmButton: 'btn btn-success',
      cancelButton: 'btn btn-secondary'
    }
  });

  if (confirmacion.isConfirmed) {
    try {
      await sensorTypeService.changeSensorTypeStatus(tipoId, newStatus);
      Swal.fire({
        icon: "success",
        title: `El tipo de sensor ha sido ${newStatus ? 'activado' : 'desactivado'} exitosamente.`,
        showConfirmButton: false,
        timer: 1500
      });
      init(); // Recargamos la tabla
    } catch (error) {
      console.error(`Error al cambiar estado del tipo de sensor ${tipoId}:`, error);
      Swal.fire({
        icon: "error",
        title: `No se pudo ${newStatus ? 'activar' : 'desactivar'} el tipo de sensor.`,
        confirmButtonText: 'Aceptar',
        customClass: {
          confirmButton: 'btn btn-success'
        }
      });
      switchElement.checked = !newStatus;
    }
  } else {
    switchElement.checked = !newStatus;
  }
}

async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-sensor-type");
  if (editButton) {
    const tipoId = editButton.dataset.tipoId;
    openEditModal(tipoId);
  }
}

function handleFilterChange(event) {
  filterSensorTypes(event.target.value);
}

async function init() {
  const tableBody = document.getElementById("sensor-types-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Cargando tipos de sensores</td></tr>';

  const createModalElement = document.getElementById("create-sensor-type-modal");
  if (createModalElement && !createModalInstance) {
    createModalInstance = new bootstrap.Modal(createModalElement);
  }

  try {
    const types = await sensorTypeService.getSensorTypes();
    allSensorTypes = types || [];

    try {
      document.dispatchEvent(new CustomEvent("sensorTypesUpdated", { detail: { types: allSensorTypes } }));
    } catch (e) {
      console.error("Error al emitir evento sensorTypesUpdated:", e);
    }

    if (allSensorTypes.length > 0) {
      tableBody.innerHTML = allSensorTypes.map(createSensorTypeRow).join("");
    } else {
      tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No hay tipos de sensores registrados.</td></tr>';
    }
  } catch (error) {
    console.error("Error al cargar tipos de sensores:", error);
    tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar datos.</td></tr>';
  }

  const editForm = document.getElementById("edit-sensor-type-form");
  const createForm = document.getElementById("create-sensor-type-form");
  const filterSelect = document.getElementById("filter-sensor-type-estado");

  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);

  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);

  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);

  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  if (filterSelect) {
    filterSelect.removeEventListener("change", handleFilterChange);
    filterSelect.addEventListener("change", handleFilterChange);
  }
}

export { init };
