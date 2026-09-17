import { sensorService } from "../api/sensor.service.js";
import { sensorTypeService } from "../api/sensorType.service.js";
import { shedService } from "../api/shed.service.js";

let modalInstance = null;
let createModalInstance = null;
let allSensors = [];
let allTipos = [];
let allGalpones = [];

function createSensorRow(sensor) {
  const sensorId = sensor.id_sensor;

  return `
    <tr>
      <td class="cell">${sensor.nombre}</td>
      <td class="cell">${sensor.nombre_tipo} - ${sensor.modelo_tipo}</td>
      <td class="cell">${sensor.nombre_galpon}</td>
      <td class="cell">${sensor.descripcion}</td>
      <td class="cell">
        <div class="form-check form-switch d-inline-block">
          <input class="form-check-input sensor-status-switch" type="checkbox" role="switch" 
                 id="switch-sensor-${sensorId}" data-sensor-id="${sensorId}" 
                 ${sensor.estado ? 'checked' : ''}>
          <label class="form-check-label" for="switch-sensor-${sensorId}">
            ${sensor.estado ? 'Activo' : 'Inactivo'}
          </label>
        </div>
      </td>
      <td class="cell">
        <button class="btn btn-sm btn-success btn-edit-sensor" data-sensor-id="${sensorId}">
          <i class="fa-regular fa-pen-to-square"></i>
        </button>
      </td>
    </tr>
  `;
}

function filterSensors() {
  const estadoFilter = document.getElementById("filter-sensor-estado").value;
  const tipoFilter = document.getElementById("filter-tipo").value;
  const galponFilter = document.getElementById("filter-galpon").value;

  let filteredSensors = allSensors;

  if (estadoFilter === "active") {
    filteredSensors = filteredSensors.filter(s => s.estado === 1 || s.estado === true);
  } else if (estadoFilter === "inactive") {
    filteredSensors = filteredSensors.filter(s => s.estado === 0 || s.estado === false);
  }

  if (tipoFilter !== "all") {
    filteredSensors = filteredSensors.filter(s => s.id_tipo_sensor == tipoFilter);
  }

  if (galponFilter !== "all") {
    filteredSensors = filteredSensors.filter(s => s.id_galpon == galponFilter);
  }

  const tableBody = document.getElementById("sensors-table-body");
  if (!tableBody) return;

  if (filteredSensors.length > 0) {
    tableBody.innerHTML = filteredSensors.map(createSensorRow).join("");
  } else {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center">No hay sensores con esos filtros.</td>
      </tr>
    `;
  }
}

async function cargarFiltros() {
  try {
    allTipos = await sensorTypeService.getSensorTypes();
    const filterTipo = document.getElementById("filter-tipo");
    if (filterTipo) {
      filterTipo.innerHTML = '<option value="all">Todos los tipos</option>';
      allTipos.forEach((t) => {
        filterTipo.innerHTML += `<option value="${t.id_tipo}">${t.nombre} - ${t.modelo}</option>`;
      });
    }

    allGalpones = await shedService.getActiveSheds();
    const filterGalpon = document.getElementById("filter-galpon");
    if (filterGalpon) {
      filterGalpon.innerHTML = '<option value="all">Todos los galpones</option>';
      allGalpones.forEach((g) => {
        filterGalpon.innerHTML += `<option value="${g.id_galpon}">${g.nombre}</option>`;
      });
    }
  } catch (error) {
    console.error("Error al cargar filtros:", error);
  }
}

async function cargarTiposSensores() {
  try {
    const tipos = await sensorTypeService.getActiveSensorTypes();

    const selectCrear = document.getElementById("create-sensor-id_tipo_sensor");
    if (selectCrear) {
      selectCrear.innerHTML = '<option value="" disabled selected>Seleccione un tipo</option>';
      tipos.forEach((t) => {
        if (t.id_tipo !== null && t.id_tipo !== undefined)
          selectCrear.innerHTML += `<option value="${t.id_tipo}">${t.nombre} - ${t.modelo}</option>`;
      });
    }

    const selectEditar = document.getElementById("edit-sensor-id_tipo_sensor");
    if (selectEditar) {
      selectEditar.innerHTML = '<option value="" disabled selected>Seleccione un tipo</option>';
      tipos.forEach((t) => {
        if (t.id_tipo !== null && t.id_tipo !== undefined)
          selectEditar.innerHTML += `<option value="${t.id_tipo}">${t.nombre} - ${t.modelo}</option>`;
      });
    }
  } catch (error) {
    console.error("Error al cargar tipos de sensores:", error);
  }
}

async function cargarGalpones() {
  try {
    const galpones = await shedService.getActiveSheds();

    const selectCrear = document.getElementById("create-sensor-id_galpon");
    if (selectCrear) {
      selectCrear.innerHTML = '<option value="" disabled selected>Seleccione un galpón</option>';
      galpones.forEach((g) => {
        selectCrear.innerHTML += `<option value="${g.id_galpon}">${g.nombre}</option>`;
      });
    }

    const selectEditar = document.getElementById("edit-sensor-id_galpon");
    if (selectEditar) {
      selectEditar.innerHTML = '<option value="" disabled selected>Seleccione un galpón</option>';
      galpones.forEach((g) => {
        selectEditar.innerHTML += `<option value="${g.id_galpon}">${g.nombre}</option>`;
      });
    }
  } catch (error) {
    console.error("Error al cargar galpones:", error);
  }
}

async function openEditModal(sensorId) {
  const modalElement = document.getElementById("edit-sensor-modal");
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }
  try {
    const sensor = await sensorService.getSensorById(sensorId);
    document.getElementById("edit-sensor-id").value = sensor.id_sensor;
    document.getElementById("edit-sensor-nombre").value = sensor.nombre;
    document.getElementById("edit-sensor-id_tipo_sensor").value = sensor.id_tipo_sensor;
    document.getElementById("edit-sensor-id_galpon").value = sensor.id_galpon;
    document.getElementById("edit-sensor-descripcion").value = sensor.descripcion;
    modalInstance.show();
  } catch (error) {
    console.error("Error al obtener sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del sensor.",
    });
  }
}

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const sensorId = document.getElementById("edit-sensor-id").value;
  const descripcion = document.getElementById("edit-sensor-descripcion").value;

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

  const updatedData = {
    nombre: document.getElementById("edit-sensor-nombre").value,
    id_tipo_sensor: Number(document.getElementById("edit-sensor-id_tipo_sensor").value),
    id_galpon: Number(document.getElementById("edit-sensor-id_galpon").value),
    descripcion: document.getElementById("edit-sensor-descripcion").value,
  };

  try {
    await sensorService.updateSensor(sensorId, updatedData);
    modalInstance.hide();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Sensor actualizado exitosamente.",
      showConfirmButton: false,
      timer: 1200
    });
    init();
  } catch (error) {
    console.error("Error al actualizar sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo actualizar el sensor.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
  }
}

async function handleCreateSubmit(event) {
  event.preventDefault();

  const nombre = document.getElementById("create-sensor-nombre").value.trim();
  const id_tipo_sensor = Number(document.getElementById("create-sensor-id_tipo_sensor").value);
  const id_galpon = Number(document.getElementById("create-sensor-id_galpon").value);
  const descripcion = document.getElementById("create-sensor-descripcion").value.trim();

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

  const newSensorData = { nombre, id_tipo_sensor, id_galpon, descripcion, estado: true };

  try {
    await sensorService.createSensor(newSensorData);
    if (createModalInstance) createModalInstance.hide();
    document.getElementById("create-sensor-form").reset();
    Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Sensor creado exitosamente.",
      showConfirmButton: false,
      timer: 1400
    });
    init();
  } catch (error) {
    console.error("Error al crear sensor:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo crear el sensor.",
      confirmButtonText: 'Aceptar',
      customClass: {
        confirmButton: 'btn btn-success'
      }
    });
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains("sensor-status-switch")) return;

  const sensorId = switchElement.dataset.sensorId;
  const newStatus = switchElement.checked;

  const confirmacion = await Swal.fire({
    title: `¿Deseas ${switchElement.checked ? 'activar' : 'desactivar'} este sensor?`,
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
      await sensorService.changeSensorStatus(sensorId, newStatus);
      Swal.fire({
        icon: "success",
        title: `El sensor ha sido ${newStatus ? 'activado' : 'desactivado'} exitosamente.`,
        showConfirmButton: false,
        timer: 1500
      });
      init(); // Recargamos la tabla
    } catch (error) {
      console.error(`Error al cambiar estado del sensor ${sensorId}:`, error);
      Swal.fire({
        icon: "error",
        title: `No se pudo ${newStatus ? 'activar' : 'desactivar'} el sensor.`,
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
  const editButton = event.target.closest(".btn-edit-sensor");
  if (editButton) {
    const sensorId = editButton.dataset.sensorId;
    openEditModal(sensorId);
  }
}

function handleFilterChange() {
  filterSensors();
}

async function init() {
  const tableBody = document.getElementById("sensors-table-body");
  if (!tableBody) return;

  const colspan = 6;
  tableBody.innerHTML = `<tr><td colspan="${colspan}" class="text-center">Cargando sensores</td></tr>`;

  const createModalElement = document.getElementById("create-sensor-modal");
  if (createModalElement && !createModalInstance) {
    createModalInstance = new bootstrap.Modal(createModalElement);
  }

  await cargarFiltros();
  await cargarTiposSensores();
  await cargarGalpones();

  try {
    const sensors = await sensorService.getSensors();
    allSensors = sensors || [];

    if (allSensors.length > 0) {
      tableBody.innerHTML = allSensors.map(createSensorRow).join("");
    } else {
      tableBody.innerHTML = `<tr><td colspan="${colspan}" class="text-center">No hay sensores registrados.</td></tr>`;
    }
  } catch (error) {
    console.error("Error al cargar sensores:", error);
    tableBody.innerHTML = `<tr><td colspan="${colspan}" class="text-center text-danger">Error al cargar datos.</td></tr>`;
  }

  const editForm = document.getElementById("edit-sensor-form");
  const createForm = document.getElementById("create-sensor-form");
  const filterEstado = document.getElementById("filter-sensor-estado");
  const filterTipo = document.getElementById("filter-tipo");
  const filterGalpon = document.getElementById("filter-galpon");

  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);

  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);

  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);

  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  if (filterEstado) {
    filterEstado.removeEventListener("change", handleFilterChange);
    filterEstado.addEventListener("change", handleFilterChange);
  }

  if (filterTipo) {
    filterTipo.removeEventListener("change", handleFilterChange);
    filterTipo.addEventListener("change", handleFilterChange);
  }

  if (filterGalpon) {
    filterGalpon.removeEventListener("change", handleFilterChange);
    filterGalpon.addEventListener("change", handleFilterChange);
  }
}

document.addEventListener("sensorTypesUpdated", async () => {
  // Solo aplica si la vista de sensores está abierta
  if (!document.getElementById("filter-sensor-estado")) return;
  try {
    await cargarFiltros();
    await cargarTiposSensores();
    const sensors = await sensorService.getSensors();
    allSensors = sensors || [];
    filterSensors();
  } catch (err) {
    console.error("Error al procesar sensorTypesUpdated:", err);
  }
});

export { init };
