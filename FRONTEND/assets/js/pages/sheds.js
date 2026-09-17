import { shedService } from "../api/shed.service.js";

let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let originalId = null;

function createShedRow(shed) {
  const statusBadge = shed.estado
    ? `<span class="badge bg-success">Activo</span>`
    : `<span class="badge bg-danger">Inactivo</span>`;

  const shedId = shed.id_galpon;

  const puedeEditar =
    window.tienePermiso && window.tienePermiso("galpones", "editar");
  const btnEditar = puedeEditar
    ? `<button class="btn btn-sm btn-success btn-edit-shed" data-shed-id="${shed.id_galpon}" data-action="edit">
         <i class="fa-regular fa-pen-to-square"></i>
       </button>`
    : "";

  return `
    <tr>
      <td class="cell">${shed.nombre_finca}</td>
      <td class="cell">${shed.nombre}</td>
      <td class="cell">${shed.capacidad}</td>
      <td class="cell">${shed.cant_actual}</td>
      <td class="cell">
        <div class="form-check form-switch">
            <input class="form-check-input shed-status-switch" type="checkbox" role="switch" 
                   id="switch-${shedId}" data-shed-id="${shedId}" 
                   ${shed.estado ? "checked" : ""}>
            <label class="form-check-label" for="switch-${shedId}">
              ${shed.estado ? "Activo" : "Inactivo"}
            </label>
        </div>
      </td>
      <td class="text-end">
        ${btnEditar}
      </td>
    </tr>
  `;
}

// --- LÓGICA DE MODAL ---

async function openEditModal(id_galpon) {
  const modalElement = document.getElementById("edit-shed-modal");
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const shed = await shedService.getShedById(id_galpon);
    originalId = shed.id_galpon;

    document.getElementById("edit-shed-id").value = shed.id_galpon;
    await loadLandsSelect("edit-nombre_finca", shed.id_finca);

    document.getElementById("edit-nombre_finca").value = shed.id_finca;
    document.getElementById("edit-nombre-galpon").value = shed.nombre;
    document.getElementById("edit-capacidad").value = shed.capacidad;
    document.getElementById("edit-cant-actual").value = shed.cant_actual;

    modalInstance.show();
  } catch (error) {
    console.error("Error al obtener datos del galpón ${shedId}: ", error);
    alert("No se pudieron cargar los datos del galpón.");
  }
}

// --- MANEJADORES DE EVENTOS ---

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const shedId = document.getElementById("edit-shed-id").value;
  const updatedData = {
    id_finca: document.getElementById("edit-nombre_finca").value,
    nombre: document.getElementById("edit-nombre-galpon").value,
    capacidad: document.getElementById("edit-capacidad").value,
    cant_actual: document.getElementById("edit-cant-actual").value,
  };

  try {
    await shedService.updateShed(shedId, updatedData);

    bootstrap.Modal.getInstance("#edit-shed-modal").hide();
    Swal.fire({
      icon: "success",
      title: `Galpón actualizado con éxito.`,
      showConfirmButton: false,
      timer: 1200,
    });

    init();
  } catch (error) {
    console.error("Error al actualizar el galpón ${shedId}:", error);
    alert("No se pudo actualizar el galpón.");
  }
}

// ============ CREAR GALPONES ============
async function handleCreateSubmit(event) {
  event.preventDefault();

  const newShedData = {
    id_finca: document.getElementById("create-nombre_finca").value,
    nombre: document.getElementById("create-nombre-galpon").value,
    capacidad: document.getElementById("create-capacidad").value,
    cant_actual: document.getElementById("create-cant-actual").value,
    estado: true, // Por defecto, los galpones se crean activos
  };

  try {
    await shedService.createShed(newShedData);

    bootstrap.Modal.getInstance("#create-shed-modal").hide();
    document.getElementById("create-shed-form").reset();

    Swal.fire({
      icon: "success",
      title: `Galpón creado con éxito.`,
      showConfirmButton: false,
      timer: 1400,
    });

    init(); // Recargamos la tabla para ver el nuevo usuario
  } catch (error) {
    console.error("Error al crear el galpón:", error);
    Swal.fire({
      position: "top-center",
      icon: "danger",
      title: `No se pudo crear el galpón.`,
      showConfirmButton: false,
      timer: 1500,
    });
  }
}

// ============ SELECCIONAR FINCA ============
async function loadLandsSelect(selectId, selectedValue = "") {
  const select = document.getElementById(selectId);
  if (!select) return;

  select.innerHTML = '<option value="">Cargando fincas...</option>';

  try {
    const lands = await shedService.getLandsActive();

    select.innerHTML = '<option value="">Seleccione una finca</option>';

    lands.forEach((land) => {
      const option = document.createElement("option");
      option.value = land.id_finca;
      option.textContent = land.nombre;

      if (String(land.id_finca) === String(selectedValue)) {
        option.selected = true;
      }

      select.appendChild(option);
    });
  } catch (error) {
    console.error("Error al cargar las fincas activas:", error);
    select.innerHTML = '<option value="">Error al cargar fincas</option>';
    Swal.fire("Error", "No se pudieron cargar las fincas.", "error");
  }
}

// ============ FILTROS ============
async function loadShedsFilter() {
  const selectElement = document.getElementById("filtro-galpones");
  const select = selectElement ? selectElement.value : "all";
  const tableBody = document.getElementById("sheds-table-body");
  if (!tableBody) return;

  try {
    // Obtener todos los galpones y luego aplicar el filtro seleccionado
    const sheds = await shedService.getSheds();
    let filtro = sheds || [];

    if (select === "active") {
      filtro = filtro.filter((g) => g.estado === 1 || g.estado === true);
    } else if (select === "inactive") {
      filtro = filtro.filter((g) => g.estado === 0 || g.estado === false);
    }

    if (filtro.length > 0) {
      tableBody.innerHTML = filtro.map(createShedRow).join("");
    } else {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center">No hay galpones con ese filtro.</td>
        </tr>
      `;
    }
  } catch (error) {
    console.error("Error al filtrar galpones:", error);
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error cargando galpones.</td></tr>`;
  }
}

// ============ INICIALIZACIÓN Y EVENTOS ============
async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-shed");
  if (editButton) {
    const id_galpon = editButton.dataset.shedId;
    openEditModal(id_galpon);
    return;
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains("shed-status-switch")) return;

  const shedId = switchElement.dataset.shedId;
  const newStatus = switchElement.checked;
  const actionText = newStatus ? "activar" : "desactivar";

  const confirmacion = await Swal.fire({
    title: `¿Deseas ${
      switchElement.checked ? "activar" : "desactivar"
    } este galpón?`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: `Sí ${switchElement.checked ? "activar" : "desactivar"}`,
    cancelButtonText: "No, cancelar",
    customClass: {
      confirmButton: "btn btn-success",
      cancelButton: "btn btn-secondary",
    },
  });

  if (confirmacion.isConfirmed) {
    try {
      await shedService.deleteShed(shedId, newStatus);
      Swal.fire({
        icon: "success",
        title: `El galpón ha sido ${
          newStatus ? "activado" : "desactivado"
        } exitosamente.`,
        showConfirmButton: false,
        timer: 1500,
      });
      init(); // Recargamos la tabla
    } catch (error) {
      Swal.fire({
        icon: "warning",
        title: `No se pudo ${actionText} el galpón.`,
        showConfirmButton: false,
        timer: 1500,
      });
      switchElement.checked = !newStatus;
    }
  } else {
    switchElement.checked = !newStatus;
  }
}

// ============= INIT =============
async function init() {
  const tableBody = document.getElementById("sheds-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="6" class="text-center">Cargando galpones ... </td></tr>';

  try {
    const sheds = await shedService.getSheds();
    if (sheds && sheds.length > 0) {
      tableBody.innerHTML = sheds.map(createShedRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="6" class="text-center">No se encontraron galpones.</td></tr>';
    }
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">No tienes permiso para ver este modulo.</td></tr>`;
  }

  const createModal = document.getElementById("create-shed-modal");
  if (createModal) {
    createModal.addEventListener("show.bs.modal", () => {
      loadLandsSelect("create-nombre_finca");
    });
  }

  // Registrar listener para el select de filtro de galpones
  const filtroGalpones = document.getElementById("filtro-galpones");
  if (filtroGalpones) {
    filtroGalpones.removeEventListener("change", loadShedsFilter);
    filtroGalpones.addEventListener("change", loadShedsFilter);
  }

  // Aplicamos el patrón remove/add para evitar listeners duplicados
  const editForm = document.getElementById("edit-shed-form");
  const createForm = document.getElementById("create-shed-form");
  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);
  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);
  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);
  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  // Aplicar permisos después de cargar todo
  if (window.aplicarPermisos) {
    window.aplicarPermisos("galpones");
  }
}

export { init };
