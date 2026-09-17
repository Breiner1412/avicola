import { userService } from "../api/user.service.js";

import { exportarCSV, exportarExcel } from "../utils/exportar.js";
const currentUser = JSON.parse(localStorage.getItem("user"));

let modalInstance = null;
let createModalInstance = null;
let originalMail = null;

let allUsers = [];
let filteredUsers = [];

// -----------------------------------------------------
// ROW TEMPLATE
// -----------------------------------------------------

function createUserRow(usuario) {
  const userId = usuario.id_usuario;

  return `
    <tr>
      <td class="cell">${usuario.nombre}</td>
      <td class="cell">${usuario.documento}</td>
      <td class="cell">${usuario.email}</td>
      <td class="cell">${usuario.telefono}</td>
      <td class="cell">${usuario.nombre_rol}</td>

      <td class="cell text-center">
        <div class="form-check form-switch">
          <input 
            class="form-check-input user-status-switch"
            type="checkbox"
            data-user-id="${userId}"
            ${usuario.estado ? "checked" : ""}
          >
        </div>
      </td>

      <td class="cell text-center">
        <button class="btn btn-success btn-sm btn-edit-user" aria-label="Editar" data-user-email="${
          usuario.email
        }">
          <i class="fa-regular fa-pen-to-square"></i>
        </button>
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
  { header: "ID", key: "id_usuario" },
  { header: "Nombre", key: "nombre" },
  { header: "Documento", key: "documento" },
  { header: "Correo", key: "email" },
  { header: "Teléfono", key: "telefono" },
  { header: "Rol", key: "nombre_rol" },
  { header: "Estado", key: (r) => (r.estado ? "Activo" : "Inactivo") },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Usuarios");
}

function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;

  event.preventDefault();

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  const data = filteredUsers.length ? filteredUsers : allUsers;

  if (!data || data.length === 0) {
    Swal.fire({ title: "No hay datos para exportar.", icon: "info" });
    return;
  }

  if (fmt === "csv") {
    exportToCSV(data, `usuarios_${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `usuarios_${dateTag}.xlsx`);
  }
}

function limpiarFiltros() {
  document.getElementById("filter-role").value = "all";
  document.getElementById("filter-status").value = "all";
  init();
}

function populateRoleSelects() {
  const roleFilter = document.getElementById("filter-role");
  const roleCreate = document.getElementById("create-id_rol");

  const userString = localStorage.getItem("user");
  if (!userString) return;
  const currentUser = JSON.parse(userString);

  // LIMPIAR SELECTS
  roleFilter.innerHTML = '<option value="all">Todos los roles</option>';
  roleCreate.innerHTML = "";

  // ------------------------------
  // 1) ROLES PARA EL FILTRO (NO SUPERADMIN)
  // ------------------------------

  let filterRoles = [];

  if (currentUser.id_rol === 1) {
    filterRoles = [
      { value: "administrador", label: "Admin" },
      { value: "supervisor", label: "Supervisor" },
      { value: "operario", label: "Operario" },
    ];
  } else {
    filterRoles = [
      { value: "supervisor", label: "Supervisor" },
      { value: "operario", label: "Operario" },
    ];
  }

  filterRoles.forEach((r) => {
    const option = document.createElement("option");
    option.value = r.value;
    option.textContent = r.label;
    roleFilter.appendChild(option);
  });

  // ------------------------------
  // 2) ROLES PARA CREAR USUARIO
  // ------------------------------
  const createRoles = [];

  // SuperAdmin puede crear SuperAdmin y Admin
  if (currentUser.id_rol === 1) {
    createRoles.push({ value: "1", label: "SuperAdmin" });
    createRoles.push({ value: "2", label: "Admin" });
  }

  // Todos pueden ver Supervisor + Operario en CREAR
  createRoles.push({ value: "3", label: "Supervisor" });
  createRoles.push({ value: "4", label: "Operario" });

  createRoles.forEach((r) => {
    const option = document.createElement("option");
    option.value = r.value;
    option.textContent = r.label;
    roleCreate.appendChild(option);
  });
}

// -----------------------------------------------------
//       EDIT MODAL
// -----------------------------------------------------

async function openEditModal(email) {
  const modalElement = document.getElementById("edit-user-modal");

  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const user = await userService.getUserByEmail(email);
    originalMail = user.email;

    document.getElementById("edit-user-id").value = user.id_usuario;
    document.getElementById("edit-nombre").value = user.nombre;
    document.getElementById("edit-documento").value = user.documento;
    document.getElementById("edit-email").value = user.email;
    document.getElementById("edit-telefono").value = user.telefono;

    modalInstance.show();
  } catch (error) {
    alert("No se pudieron cargar los datos del usuario.");
  }
}

// -----------------------------------------------------
//       HANDLERS
// -----------------------------------------------------

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const userId = document.getElementById("edit-user-id").value;
  const updatedData = {
    nombre: document.getElementById("edit-nombre").value.trim(),
    telefono: document.getElementById("edit-telefono").value.trim(),
    documento: document.getElementById("edit-documento").value.trim(),
  };

  let newEmail = document.getElementById("edit-email").value;

  if (newEmail != originalMail) {
    updatedData.email = newEmail;
  }
  const swalWithBootstrapButtonsEdit = Swal.mixin({
    customClass: {
      confirmButton: "btn btn-success ms-2",
      cancelButton: "btn btn-danger",
    },
    buttonsStyling: false,
  });
  try {
    await userService.updateUser(userId, updatedData);
    modalInstance.hide();
    document.getElementById("create-user-form").reset();
    await swalWithBootstrapButtonsEdit.fire({
      title: "Exito!",
      text: `Usuario actualizado correctamente.`,
      icon: "success",
    });
    await init();
    applyUserFilters();
  } catch (error) {
    if (error.message == "El correo ya está registrado.") {
      await swalWithBootstrapButtonsEdit.fire({
        title: "Error",
        text: error,
        icon: "error",
      });
    }
    if (error.message == "El número de documento ya existe.") {
      await swalWithBootstrapButtonsEdit.fire({
        title: "Error",
        text: error,
        icon: "error",
      });
    }
  }
}

async function handleTableClick(event) {
  const editButton = event.target.closest(".btn-edit-user");
  if (editButton) {
    const email = editButton.dataset.userEmail;
    openEditModal(email);
    return;
  }
}

async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains("user-status-switch")) return;

  const userId = switchElement.dataset.userId;
  const newStatus = switchElement.checked;

  const actionText = newStatus ? "activar" : "desactivar";

  const swalWithBootstrapButtons = Swal.mixin({
    customClass: {
      confirmButton: "btn btn-success ms-2",
      cancelButton: "btn btn-secondary",
    },
    buttonsStyling: false,
  });

  const resultado = await swalWithBootstrapButtons.fire({
    title: "¿Estás seguro?",
    text: `Estás a punto de ${actionText} este usuario.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: `Si, ${actionText}!`,
    cancelButtonText: "No, cancelar!",
    reverseButtons: true,
  });

  if (resultado.isConfirmed) {
    try {
      await userService.changeEstatusUser(userId, newStatus);

      await swalWithBootstrapButtons.fire({
        title: "Exito!",
        text: `Usuario ${
          newStatus ? "activado" : "desactivado"
        } correctamente.`,
        icon: "success",
      });
      await init();
      applyUserFilters();
    } catch (error) {
      await swalWithBootstrapButtons.fire({
        title: "Error",
        text: `No se pudo ${actionText} el usuario.`,
        icon: "error",
      });
      switchElement.checked = !newStatus;
    }
  } else {
    switchElement.checked = !newStatus;
  }
}

// -----------------------------------------------------
//       CREAR
// -----------------------------------------------------

async function handleCreateSubmit(event) {
  event.preventDefault();

  const newUserData = {
    nombre: document.getElementById("create-nombre").value.trim(),
    documento: document.getElementById("create-documento").value.trim(),
    email: document.getElementById("create-email").value.trim(),
    pass_hash: document.getElementById("create-password").value.trim(),
    telefono: document.getElementById("create-telefono").value.trim(),
    id_rol: parseInt(document.getElementById("create-id_rol").value),
    estado: true,
  };
  if (!newUserData.nombre || newUserData.nombre.length < 3) {
    Swal.fire({
      icon: "error",
      title: "Nombre inválido",
      text: "El nombre debe tener al menos 3 caracteres válidos.",
    });
    return;
  }
  if (!newUserData.documento || newUserData.documento.length < 8) {
    Swal.fire({
      icon: "error",
      title: "Documento inválido",
      text: "El documento debe tener al menos 8 caracteres válidos.",
    });
    return;
  }
  if (!newUserData.pass_hash || newUserData.documento.pass_hash < 8) {
    Swal.fire({
      icon: "error",
      title: "Pass_hash inválido",
      text: "El pass_hash debe tener al menos 8 caracteres válidos.",
    });
    return;
  }
  if (!newUserData.telefono || newUserData.telefono.pass_hash < 7) {
    Swal.fire({
      icon: "error",
      title: "Telefono inválido",
      text: "El telefono debe tener al menos 8 caracteres válidos.",
    });
    return;
  }
  const swalWithBootstrapButtonsCreate = Swal.mixin({
    customClass: {
      confirmButton: "btn btn-success ms-2",
      cancelButton: "btn btn-danger",
    },
    buttonsStyling: false,
  });
  try {
    await userService.createUser(newUserData);

    if (createModalInstance) {
      createModalInstance.hide();
    }

    document.getElementById("create-user-form").reset();
    await swalWithBootstrapButtonsCreate.fire({
      title: "Exito!",
      text: `Usuario creado correctamente.`,
      icon: "success",
    });
    await init();
    applyUserFilters();
  } catch (error) {
    if (error.message == "El correo ya está registrado.") {
      await swalWithBootstrapButtonsCreate.fire({
        title: "Error",
        text: error.message,
        icon: "error",
      });
    }
    if (error.message == "El número de documento ya existe.") {
      await swalWithBootstrapButtonsCreate.fire({
        title: "Error",
        text: error.message,
        icon: "error",
      });
    }
  }
}

// -----------------------------------------------------
//       INIT
// -----------------------------------------------------

async function init() {
  const createModalElement = document.getElementById("create-user-modal");
  createModalInstance = new bootstrap.Modal(createModalElement);

  createModalElement.addEventListener("hidden.bs.modal", () => {
    document.getElementById("create-user-form").reset();
  });

  const tableBody = document.getElementById("users-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando usuarios ...</td></tr>';

  try {
    if (currentUser.id_rol === 1) {
      // SuperAdmin
      allUsers = await userService.getUsersExceptSuperadmins();
    } else {
      allUsers = await userService.getUsers();
    }

    filteredUsers = [];

    if (allUsers && allUsers.length > 0) {
      tableBody.innerHTML = allUsers.map(createUserRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="text-center">No se encontraron usuarios.</td></tr>';
    }
  } catch (error) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }

  const editForm = document.getElementById("edit-user-form");
  const createForm = document.getElementById("create-user-form");

  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);

  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);

  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);

  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  // <<<------ EXPORT HOOK ----->>>
  const pageUtilities = document.querySelector(".page-utilities");
  if (pageUtilities) {
    pageUtilities.removeEventListener("click", handleExportClick);
    pageUtilities.addEventListener("click", handleExportClick);
  }

  const roleSelect = document.getElementById("filter-role");
  const statusSelect = document.getElementById("filter-status");
  const btnClear = document.getElementById("btn_clear_filters");

  if (roleSelect) {
    roleSelect.removeEventListener("change", applyUserFilters);
    roleSelect.addEventListener("change", applyUserFilters);
  }

  if (statusSelect) {
    statusSelect.removeEventListener("change", applyUserFilters);
    statusSelect.addEventListener("change", applyUserFilters);
  }

  if (btnClear) {
    btnClear.removeEventListener("click", limpiarFiltros);
    btnClear.addEventListener("click", limpiarFiltros);
  }
}

populateRoleSelects();

export { init };

function applyUserFilters() {
  const roleFilter = document.getElementById("filter-role")?.value || "all";
  const statusFilter = document.getElementById("filter-status")?.value || "all";

  const tableBody = document.getElementById("users-table-body");
  if (!allUsers.length) return;

  // Empieza con todos
  let result = [...allUsers];

  // Filtro por rol
  if (roleFilter !== "all") {
    result = result.filter((u) => u.nombre_rol === roleFilter);
  }

  // Filtro por estado
  if (statusFilter === "active") {
    result = result.filter((u) => u.estado === true);
  }
  if (statusFilter === "inactive") {
    result = result.filter((u) => u.estado === false);
  }

  filteredUsers = result;

  tableBody.innerHTML = result.length
    ? result.map(createUserRow).join("")
    : `<tr><td colspan="7" class="text-center">No hay usuarios con esos criterios.</td></tr>`;
}
