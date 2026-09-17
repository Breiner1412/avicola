import { categoryService } from "../api/category.service.js";

let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let originalMail = null;
let createModalInstance = null; // Instancia del modal de creación

function createCatRow(cat) {
  const catId = cat.id_categoria;

  return `
    <tr data-id="${catId}">
      <td class="px-0">
        <div class="d-flex align-items-center">
          <div class="ms-3">
            <h6 class="mb-0">${cat.nombre}</h6>
          </div>
        </div>
      </td>
      <td class="px-0">${cat.descripcion}</td>
      <td class="px-0">
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-success" data-action="edit" data-id="${catId}">
          <i class="fa-regular fa-pen-to-square"></i></button>
          <button class="btn btn-sm btn-secondary" data-action="delete" data-id="${catId}">
          <i class="fa-regular fa-trash-can"></i></button>
        </div>
      </td>
    </tr>
  `;
}

async function handleCreateSubmit(e) {
  e.preventDefault();

  const nombre = document.getElementById("create-name-cat-inv").value.trim();
  const descripcion = document
    .getElementById("create-des-cat-inv")
    .value.trim();

  if (!nombre || !descripcion) {
    Swal.fire({
      title: "Por favor completa todos los campos",
      icon: "warning",
      draggable: true,
    });
    return;
  }

  try {
    await categoryService.createCategory({ nombre, descripcion });

    // Cerrar el modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("exampleModal")
    );
    if (modal) modal.hide();

    // Limpiar el formulario
    document.getElementById("create-cat-inv-form").reset();

    // Recargar la tabla
    await init();

    Swal.fire({
        icon: "success",
        title: `Categoría creada con éxito.`,
        showConfirmButton: false,
        timer: 1200
    });
  } catch (error) {
    console.error("Error al crear categoría:", error);
    Swal.fire({
        icon: "error",
        title: `Categoría creada con éxito.`,
        showConfirmButton: false,
        timer: 1200
    });
  }
}

async function handleUpdateSubmit(e) {
  e.preventDefault();

  const id = document.getElementById("edit-cat-inv-id").value;
  const nombre = document.getElementById("edit-name-cat-inv").value.trim();
  const descripcion = document.getElementById("edit-des-cat-inv").value.trim();

  if (!nombre || !descripcion) {
    Swal.fire({
      title: "Por favor completa todos los campos",
      icon: "warning",
      draggable: true,
    });
    return;
  }

  try {
    await categoryService.updateCategory(id, { nombre, descripcion });

    // Cerrar el modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("edit-cat-inv-modal")
    );
    if (modal) modal.hide();

    // Recargar la tabla
    await init();

    Swal.fire({
        icon: "success",
        title: `Categoría actualizada con éxito.`,
        showConfirmButton: false,
        timer: 1200
    });
  } catch (error) {
    console.error("Error al actualizar categoría:", error);
    Swal.fire({
        icon: "error",
        title: `Error al actualizar la categoría.`,
        showConfirmButton: false,
        timer: 1200
    });
  }
}

async function handleTableClick(e) {
  const editBtn = e.target.closest('[data-action="edit"]');
  const deleteBtn = e.target.closest('[data-action="delete"]');

  if (editBtn) {
    const catId = editBtn.dataset.id;
    // Obtener datos de la categoría (por id) y abrir el modal de edición
    try {
      const cat = await categoryService.getCategoriesById(catId);

      // Rellenar inputs del modal
      const idInput = document.getElementById("edit-cat-inv-id");
      const nameInput = document.getElementById("edit-name-cat-inv");
      const descInput = document.getElementById("edit-des-cat-inv");

      if (idInput) idInput.value = cat.id_categoria || cat.id || catId;
      if (nameInput) nameInput.value = cat.nombre || cat.name || "";
      if (descInput) descInput.value = cat.descripcion || cat.description || "";

      // Abrir modal
      const modalEl = document.getElementById("edit-cat-inv-modal");
      if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      }
    } catch (error) {
      console.error("Error al obtener la categoría por id:", error);
      Swal.fire({
        title: "No se pudo cargar la categoría: " + (error.message || error),
        icon: "error",
        draggable: true,
      });
    }
  }

  if (deleteBtn) {
    const catId = deleteBtn.dataset.id;

    // Configurar SweetAlert con estilos de Bootstrap
    const swalWithBootstrapButtons = Swal.mixin({
      customClass: {
        confirmButton: "btn btn-success",
        cancelButton: "btn btn-secondary",
        actions: "gap-3",
      },
      buttonsStyling: false,
    });

    // Mostrar confirmación
    swalWithBootstrapButtons
      .fire({
        title: "¿Estás seguro que deseas eliminar?",
        text: "¡No podrás revertir esto!",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, eliminar!",
        cancelButtonText: "No, cancelar!",
        reverseButtons: true,
      })
      .then(async (result) => {
        // SOLO si el usuario confirma
        if (result.isConfirmed) {
          try {
            // Llamada a la API para eliminar
            await categoryService.deleteCategory(catId);

            // Recargar la tabla
            await init();

            // Mostrar mensaje de éxito
            swalWithBootstrapButtons.fire({
              title: "¡Eliminado!",
              text: "Categoría eliminada exitosamente.",
              icon: "success",
              draggable: true,
            });
          } catch (error) {
            console.error("Error al eliminar categoría:", error);

            // Mostrar mensaje de error
            swalWithBootstrapButtons.fire({
              title: "Error",
              // text: "Error al eliminar la categoría: " + (error.message || error),
              text: "Error al eliminar la categoría: Puede que esté en uso.",
              icon: "error",
              draggable: true,
            });
          }
        } else if (result.dismiss === Swal.DismissReason.cancel) {
          // Si el usuario cancela
          swalWithBootstrapButtons.fire({
            title: "Cancelado",
            text: "La categoría está segura",
            icon: "info",
            draggable: true,
          });
        }
      });
  }
}

function handleStatusSwitch(e) {
  // Implementar según tus necesidades
}

async function init() {
  const tableBody = document.getElementById("cat-inv-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="6" class="text-center">Cargando Categorias...</td></tr>'; // ✅ CORRECCIÓN: colspan="6"

  try {
    const categories = await categoryService.getCategories();
    if (categories && categories.length > 0) {
      tableBody.innerHTML = categories.map(createCatRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="6" class="text-center">No se encontraron Categorias.</td></tr>'; // ✅ CORRECCIÓN: colspan="6"
    }
  } catch (error) {
    console.error("Error al obtener los categorias:", error);
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error al cargar los datos.</td></tr>`; // ✅ CORRECCIÓN: colspan="6"
  }

  // Aplicamos el patrón remove/add para evitar listeners duplicados
  const editForm = document.getElementById("edit-cat-inv-form");
  const createForm = document.getElementById("create-cat-inv-form");
  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);
  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);
  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);
  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  // Delegated handler dentro del módulo Categorias para ir al Inventario (sin tocar main.js)
  try {
    const pageRoot =
      tableBody.closest(".card") ||
      document.getElementById("main-content") ||
      document;
    if (pageRoot.__inventarioHandler) {
      pageRoot.removeEventListener("click", pageRoot.__inventarioHandler);
      pageRoot.__inventarioHandler = null;
    }

    const inventarioHandler = function (ev) {
      const target = ev.target;
      const shortcut =
        target.closest('[data-page="inventario"]') ||
        target.closest("#btn-ir-inventario") ||
        target.closest("button.app-nav") ||
        target.closest("a.app-nav");
      if (!shortcut) return;
      if (!pageRoot.contains(shortcut)) return;
      ev.preventDefault();

      // Intentar disparar el enlace del nav principal
      const shellLink = document.querySelector(
        '.app-nav a[data-page="inventario"]'
      );
      if (shellLink) {
        shellLink.dispatchEvent(
          new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            composed: true,
          })
        );
        return;
      }

      // Usar navigateTo si está disponible
      if (typeof window.navigateTo === "function") {
        window.navigateTo("inventario");
        return;
      }

      // Fallback: redirigir a dashboard.html
      window.location.href = "dashboard.html?page=inventario";
    };

    pageRoot.addEventListener("click", inventarioHandler);
    pageRoot.__inventarioHandler = inventarioHandler;
  } catch (err) {
    console.error("Error wiring inventario shortcut in init():", err);
  }
}

export { init };
