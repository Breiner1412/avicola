import { rolesService } from "../api/roles.service.js";

function createRolRow(rol) {
  return `
    <tr>
        <td data-label="Nombre Rol">${rol.nombre_rol}</td>
        <td data-label="Descripción">${rol.descripcion}</td>

        <td class="text-center" data-label="Estado" class="estado-cell">
          <div class="form-check form-switch">
            <input 
              class="form-check-input switch-estado" 
              type="checkbox"
              data-id="${rol.rol_id}"
              ${rol.estado == 1 ? "checked" : ""}
            >
          </div>
        </td>
    </tr>
  `;
}

// =============================
// Cambiar estado (Switch)
// =============================
async function handleStatusSwitch(event) {
  const switchElement = event.target;
  if (!switchElement.classList.contains("switch-estado")) return;

  const id = switchElement.dataset.id;
  const newStatus = switchElement.checked ? 1 : 0;
  const actionText = newStatus ? "activar" : "desactivar";

  const result = await Swal.fire({
    title: "¿Estás seguro?",
    text: `Estás a punto de ${actionText} este rol.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Aceptar",
    cancelButtonText: "Cancelar",
    reverseButtons: true,
    confirmButtonColor: "#28a745",
    cancelButtonColor: "#6c757d",
  });

  if (!result.isConfirmed) {
    switchElement.checked = !switchElement.checked;
    return;
  }

  try {
    await rolesService.CambiarRolEstado(id, newStatus);

    await Swal.fire({
      icon: "success",
      title: "Éxito",
      text: "Estado del rol actualizado correctamente.",
      confirmButtonColor: "#28a745",
    });
  } catch (error) {
    switchElement.checked = !switchElement.checked;

    await Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo cambiar el estado del rol.",
      confirmButtonColor: "#28a745",
    });
  }
}

// =============================
// INIT
// =============================
export async function init() {
  const tbody = document.getElementById("roles-table-body");

  tbody.innerHTML = `
      <tr><td colspan="6" class="text-center">Cargando...</td></tr>
  `;

  try {
    const result = await rolesService.GetRoles();
    const backendRoles = result.roles || [];

    const roles = backendRoles.map((r) => ({
      rol_id: r.id_rol,
      nombre_rol: r.nombre_rol,
      descripcion: r.descripcion,
      estado: r.estado ? 1 : 0,
    }));

    tbody.innerHTML = roles.length
      ? roles.map(createRolRow).join("")
      : `<tr><td colspan="6" class="text-center">No hay registros.</td></tr>`;
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">Error al cargar datos.</td></tr>`;
  }

  // EVENTOS
  document.addEventListener("change", handleStatusSwitch);
  document
    .getElementById("create-rol-form")
    .addEventListener("submit", handleCreateSubmit);
}

// =============================
// Crear Rol Nuevo
// =============================
async function handleCreateSubmit(event) {
  event.preventDefault();

  const newRol = {
    nombre_rol: document.getElementById("create-nombre-rol").value,
    descripcion: document.getElementById("create-descripcion").value,
    estado: true,
  };

  try {
    await rolesService.CreateRol(newRol);

    Swal.fire({
      icon: "success",
      title: "Rol creado",
      text: "El rol se registró correctamente.",
      confirmButtonColor: "#28a745",
    });

    const modal = bootstrap.Modal.getInstance(
      document.getElementById("create-rol-modal")
    );
    modal.hide();

    event.target.reset();
    init();
  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo crear el rol.",
      confirmButtonColor: "#28a745",
    });
  }
}

