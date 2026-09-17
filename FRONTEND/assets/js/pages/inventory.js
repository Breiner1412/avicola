import { inventoryService } from "../api/inventory.service.js";
import { categoryService } from "../api/category.service.js";
import { landService } from "../api/land.service.js";

let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let originalMail = null;
let createModalInstance = null; // Instancia del modal de creación
// Mapas en memoria para resolver id -> nombre
const categoryMap = new Map();
const fincaMap = new Map();
// Paginación (cliente)
let cachedInventory = [];
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
// Valor actual del input de búsqueda (por nombre)
let currentSearch = "";
// Filtro de categoria seleccionado (id o texto)
let currentCategory = "";

function createInvRow(inv) {
  const invId = inv.id_inventario || inv.id;

  // Normalizar campos para evitar undefined y manejar objetos anidados
  const nombre = inv.nombre || inv.name || "";
  const cantidad = inv.cantidad ?? inv.cant ?? inv.quantity ?? "";
  const unidad_medida = inv.unidad_medida || inv.um || inv.unit || "";
  const descripcion = inv.descripcion || inv.description || "";

  // Categoria puede venir como string, id o objeto { nombre }
  let categoriaText = "";
  if (inv.categoria) {
    if (typeof inv.categoria === "string") categoriaText = inv.categoria;
    else if (typeof inv.categoria === "object")
      categoriaText = inv.categoria.nombre || inv.categoria.name || "";
    else categoriaText = String(inv.categoria);
  }
  // Si aún no tenemos texto, intentar resolver por id usando los mapas cargados
  if (!categoriaText) {
    const possibleIds = [
      inv.id_categoria,
      inv.id_cat,
      inv.categoria,
      inv.category_id,
      inv.category,
    ];
    for (const pid of possibleIds) {
      if (pid !== undefined && pid !== null) {
        const name = categoryMap.get(String(pid));
        if (name) {
          categoriaText = name;
          break;
        }
      }
    }
  }

  // Finca puede venir anidada
  let fincaText = "";
  if (inv.finca) {
    if (typeof inv.finca === "string") fincaText = inv.finca;
    else if (typeof inv.finca === "object")
      fincaText = inv.finca.nombre || inv.finca.name || "";
    else fincaText = String(inv.finca);
  }
  // Resolver por id desde el mapa si es necesario
  if (!fincaText) {
    const possibleIds = [
      inv.id_finca,
      inv.idFarm,
      inv.finca,
      inv.farm_id,
      inv.farm,
    ];
    for (const pid of possibleIds) {
      if (pid !== undefined && pid !== null) {
        const name = fincaMap.get(String(pid));
        if (name) {
          fincaText = name;
          break;
        }
      }
    }
  }

  return `
    <tr data-id="${invId}">
      <td class="px-0 ">${nombre}</td>
      <td class="px-0 ">${cantidad}</td>
      <td class="px-0 ">${unidad_medida}</td>
      <td class="px-0 ">${descripcion}</td>
      <td class="px-0 ">${categoriaText}</td>
      <td class="px-0 ">${fincaText}</td>
      <td class="px-0">
        <div class="d-flex gap-2 justify-content-center">
          <button class="btn btn-sm btn-success" data-action="edit" data-id="${invId}"><i class="fa-regular fa-pen-to-square"></i></button>
          <button class="btn btn-sm btn-secondary" data-action="delete" data-id="${invId}"><i class="fa-regular fa-trash-can"></i></button>
        </div>
      </td>
    </tr>
  `;
}

async function handleCreateSubmit(e) {
  e.preventDefault();

  const nombre = document.getElementById("create-name-inv").value.trim();
  const cantidad = document.getElementById("create-cant-inv").value.trim();
  const unidad_medida = document.getElementById("create-um-inv").value.trim();
  const descripcion = document.getElementById("create-des-inv").value.trim();
  const id_categoria = document.getElementById("create-cat-inv").value.trim();
  const id_finca = document.getElementById("create-fin-inv").value.trim();

  if (
    !nombre ||
    !cantidad ||
    !unidad_medida ||
    !descripcion ||
    !id_categoria ||
    !id_finca
  ) {
    Swal.fire({
      title: "Por favor completa todos los campos",
      icon: "warning",
      draggable: true,
    });
    return;
  }

  try {
    await inventoryService.createInventory({
      nombre,
      cantidad,
      unidad_medida,
      descripcion,
      id_categoria,
      id_finca,
    });

    // Cerrar el modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("exampleModal")
    );
    if (modal) modal.hide();

    // Limpiar el formulario
    document.getElementById("create-inv-form").reset();

    // Recargar la tabla
    await init();

    Swal.fire({
      icon: "success",
      title: `Item creado con éxito.`,
      showConfirmButton: false,
      timer: 1200,
    });
  } catch (error) {
    console.error("Error al crear Item Inventario:", error);
    Swal.fire({
      icon: "error",
      title: `Error al crear el Item Inventario: ${error.message}`,
      showConfirmButton: false,
      timer: 1200,
    });
  }
}

async function handleUpdateSubmit(e) {
  e.preventDefault();

  const id = document.getElementById("edit-inv-id").value;
  const nombre = document.getElementById("edit-name-inv").value.trim();
  const cantidad = document.getElementById("edit-cant-inv").value.trim();
  const unidad_medida = document.getElementById("edit-um-inv").value.trim();
  const descripcion = document.getElementById("edit-des-inv").value.trim();
  const id_categoria = document.getElementById("edit-cat-inv").value.trim();
  const id_finca = document.getElementById("edit-fin-inv").value.trim();

  if (!nombre || !descripcion) {
    Swal.fire({
      title: "Por favor completa todos los campos",
      icon: "warning",
      draggable: true,
    });
    return;
  }

  try {
    await inventoryService.updateInventory(id, {
      nombre,
      cantidad,
      unidad_medida,
      descripcion,
      id_categoria,
      id_finca,
    });

    // Cerrar el modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("edit-inv-modal")
    );
    if (modal) modal.hide();

    // Recargar la tabla
    await init();

    Swal.fire({
      icon: "success",
      title: `Item actualizado con éxito.`,
      showConfirmButton: false,
      timer: 1200,
    });
  } catch (error) {
    console.error("Error al actualizar inventario:", error);
    Swal.fire({
      icon: "error",
      title: `Error al actualizar el Item.`,
      showConfirmButton: false,
      timer: 1200,
    });
  }
}

async function handleTableClick(e) {
  const editBtn = e.target.closest('[data-action="edit"]');
  const deleteBtn = e.target.closest('[data-action="delete"]');

  if (editBtn) {
    const invId = editBtn.dataset.id;
    // Obtener datos del inventario (por id) y abrir el modal de edición
    try {
      const inv = await inventoryService.getInventoryById(invId);

      // Rellenar inputs del modal
      const idInput = document.getElementById("edit-inv-id");
      const nameInput = document.getElementById("edit-name-inv");
      const cantInput = document.getElementById("edit-cant-inv");
      const umInput = document.getElementById("edit-um-inv");
      const descInput = document.getElementById("edit-des-inv");
      const catInput = document.getElementById("edit-cat-inv");
      const finInput = document.getElementById("edit-fin-inv");

      if (idInput) idInput.value = inv.id_inventario || inv.id || invId;
      if (nameInput) nameInput.value = inv.nombre || inv.name || "";
      if (cantInput) cantInput.value = inv.cantidad || inv.cant || "";
      if (umInput) umInput.value = inv.unidad_medida || inv.um || "";
      if (descInput) descInput.value = inv.descripcion || inv.description || "";

      // Extraer id de categoría robustamente (soporta id directo, objeto anidado o otras variantes)
      const catId =
        inv.id_categoria ||
        (inv.categoria &&
          (inv.categoria.id_categoria ||
            inv.categoria.id ||
            inv.categoria.id_cat)) ||
        inv.category ||
        "";
      if (catInput)
        catInput.value =
          catId !== undefined && catId !== null ? String(catId) : "";

      // Extraer id de finca/land robustamente (igual que categoría)
      const finId =
        inv.id_finca ||
        (inv.finca &&
          (inv.finca.id_finca ||
            inv.finca.id ||
            inv.finca.idLand ||
            inv.finca._id)) ||
        inv.farm ||
        "";
      if (finInput)
        finInput.value =
          finId !== undefined && finId !== null ? String(finId) : "";

      // Abrir modal
      const modalEl = document.getElementById("edit-inv-modal");
      if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      }
    } catch (error) {
      console.error("Error al obtener el inventario por id:", error);
      Swal.fire({
        title: "Error",
        text: "No se pudo cargar el inventario para editar.",
        icon: "error",
        draggable: true,
      });
    }
  }

  if (deleteBtn) {
    const invId = deleteBtn.dataset.id;

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
            await inventoryService.deleteInventory(invId);

            // Recargar la tabla
            await init();

            // Mostrar mensaje de éxito
            swalWithBootstrapButtons.fire({
              title: "¡Eliminado!",
              text: "Item eliminado correctamente.",
              icon: "success",
              draggable: true,
            });
          } catch (error) {
            console.error("Error al eliminar item:", error);

            // Mostrar mensaje de error
            swalWithBootstrapButtons.fire({
              title: "Error",
              text: "No se pudo eliminar el item: " + (error.message || error),
              icon: "error",
              draggable: true,
            });
          }
        } else if (result.dismiss === Swal.DismissReason.cancel) {
          // Si el usuario cancela
          swalWithBootstrapButtons.fire({
            title: "Cancelado",
            text: "El item está seguro",
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

/* ---------------------------------
   PAGINACIÓN (cliente)
---------------------------------- */
function renderPagination(page, total) {
  const list = document.getElementById("pagination-list");
  if (!list) return;
  list.innerHTML = "";

  const createLi = (content, disabled = false) => {
    const li = document.createElement("li");
    li.className = `page-item ${disabled ? "disabled" : ""}`;
    li.innerHTML = content;
    return li;
  };

  // Prev
  const prevDisabled = page === 1;
  const prevLi = createLi(
    `
    <a class="page-link text-success" href="#" data-page="${page - 1}">
      <i class="fas fa-chevron-left"></i>
    </a>
  `,
    prevDisabled
  );
  list.appendChild(prevLi);

  // Pages
  for (let i = 1; i <= total; i++) {
    const isActive = i === page;
    const li = createLi(`
      <a class="page-link ${
        isActive ? "bg-success border-success text-white" : "text-success"
      }" href="#" data-page="${i}">${i}</a>
    `);
    list.appendChild(li);
  }

  // Next
  const nextDisabled = page === total;
  const nextLi = createLi(
    `
    <a class="page-link text-success" href="#" data-page="${page + 1}">
      <i class="fas fa-chevron-right"></i>
    </a>
  `,
    nextDisabled
  );
  list.appendChild(nextLi);
}

function handlePaginationClick(e) {
  e.preventDefault();
  const a = e.target.closest ? e.target.closest("a[data-page]") : null;
  if (!a) return;
  const p = parseInt(a.dataset.page, 10);
  if (isNaN(p) || p < 1 || p > totalPages) return;
  currentPage = p;
  renderInventoryPage();
}

function renderInventoryPage() {
  const tableBody = document.getElementById("inv-table-body");
  if (!tableBody) return;
  // Aplicar búsqueda (cliente) sobre la caché
  const source = Array.isArray(cachedInventory) ? cachedInventory : [];
  const q = (currentSearch || "").toString().trim().toLowerCase();

  // Filtrar por búsqueda y por categoria
  let filtered = source.filter((inv) => {
    // Nombre match
    const nombre = (inv.nombre || inv.name || "").toString().toLowerCase();
    const matchesSearch = !q || nombre.includes(q);

    // Categoria match (si hay filtro)
    if (!currentCategory) return matchesSearch;

    const catFilter = String(currentCategory).trim();
    // intentar comparar por id's posibles
    const possibleCatIds = [
      inv.id_categoria,
      inv.id_cat,
      inv.category_id,
      inv.category,
      inv.categoria &&
        (inv.categoria.id_categoria ||
          inv.categoria.id ||
          inv.categoria.id_cat),
      inv.categoria && (inv.categoria.nombre || inv.categoria.name),
    ].filter((x) => x !== undefined && x !== null);

    const matchesCategory = possibleCatIds.some((pid) => {
      const pidStr = String(pid).toLowerCase();
      if (pidStr === catFilter.toLowerCase()) return true;
      const mapped = categoryMap.get(String(pid));
      if (mapped && mapped.toLowerCase() === catFilter.toLowerCase())
        return true;
      return false;
    });

    return matchesSearch && matchesCategory;
  });

  if (!filtered || filtered.length === 0) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="text-center">No se encontraron Items en el inventario.</td></tr>';
    renderPagination(1, 1);
    return;
  }

  totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * pageSize;
  const slice = filtered.slice(start, start + pageSize);

  tableBody.innerHTML = slice.map(createInvRow).join("");
  renderPagination(currentPage, totalPages);
}

// Maneja el input de búsqueda y refresca la página
function handleSearchInput(e) {
  currentSearch = e.target.value || "";
  currentPage = 1;
  renderInventoryPage();
}

function handleCategoryChange(e) {
  currentCategory = e.target.value || "";
  currentPage = 1;
  renderInventoryPage();
}

async function cargarCategorias() {
  try {
    const categorias = await categoryService.getCategories();
    const normalizeTipo = (cat) => {
      const id = cat.id_categoria || cat.id || cat.id_cat || null;
      const nombre = cat.nombre || cat.name || cat.label || "";
      return { id, nombre };
    };

    // Los selects en el HTML actual se llaman 'create-cat-inv' y 'edit-cat-inv'
    const selectCrear = document.getElementById("create-cat-inv");
    if (selectCrear) {
      // Limpiar opciones previas (conservar placeholder si existe) y añadir las categorías
      const placeholderOpt = selectCrear.querySelector('option[value=""]')
        ? selectCrear.querySelector('option[value=""]').outerHTML
        : '<option value="">Seleccionar categoría</option>';
      selectCrear.innerHTML = placeholderOpt;
      const opts = categorias
        .map((tipoOrig) => {
          const { id, nombre } = normalizeTipo(tipoOrig);
          // guardar en mapa
          if (id !== null && id !== undefined)
            categoryMap.set(String(id), nombre);
          if (id !== null && id !== undefined) {
            return `<option value="${id}">${nombre}</option>`;
          }
          return "";
        })
        .join("");
      selectCrear.insertAdjacentHTML("beforeend", opts);
    }

    // Poblar select de filtro por categoria si existe
    const filterSelect = document.getElementById("filter-cat-inv");
    if (filterSelect) {
      const placeholder = '<option value="">Todas las categorias</option>';
      filterSelect.innerHTML = placeholder;
      const optsF = categorias
        .map((tipoOrig) => {
          const { id, nombre } = normalizeTipo(tipoOrig);
          if (id !== null && id !== undefined) {
            // guardar en mapa por si se necesita
            categoryMap.set(String(id), nombre);
            return `<option value="${id}">${nombre}</option>`;
          }
          // si no hay id pero hay nombre, permitir filtrar por nombre
          if (nombre) return `<option value="${nombre}">${nombre}</option>`;
          return "";
        })
        .join("");
      filterSelect.insertAdjacentHTML("beforeend", optsF);
    }

    let selectEditar = document.getElementById("edit-cat-inv");
    if (selectEditar) {
      if (selectEditar.tagName !== "SELECT") {
        const wrapper = selectEditar.parentNode;
        const newSelect = document.createElement("select");
        newSelect.id = selectEditar.id;
        newSelect.className = selectEditar.className || "form-select";
        newSelect.required = selectEditar.required || false;
        wrapper.replaceChild(newSelect, selectEditar);
        selectEditar = newSelect;
      }

      // limpiar opciones previas (conservar placeholder si existe)
      const placeholderOptE = selectEditar.querySelector('option[value=""]')
        ? selectEditar.querySelector('option[value=""]').outerHTML
        : '<option value="">Seleccionar categoría</option>';
      selectEditar.innerHTML = placeholderOptE;

      const opts = categorias
        .map((tipoOrig) => {
          const { id, nombre } = normalizeTipo(tipoOrig);
          if (id !== null && id !== undefined)
            categoryMap.set(String(id), nombre);
          if (id !== null && id !== undefined) {
            return `<option value="${id}">${nombre}</option>`;
          }
          return "";
        })
        .join("");
      selectEditar.insertAdjacentHTML("beforeend", opts);
    }
  } catch (error) {
    console.error("Error al cargar categorias:", error);
  }
}

async function cargarFincas() {
  try {
    const fincas = await landService.getLands();

    // Filtrar solo fincas activas (estado === 1)
    const fincasActivas = (Array.isArray(fincas) ? fincas : []).filter((f) => {
      return f.estado === 1 || f.estado === true;
    });

    const normalizeFinca = (f) => {
      const id = f.id_finca || f.id || f.idLand || f.id_land || null;
      const nombre = f.nombre || f.name || f.label || f.nombre_finca || "";
      return { id, nombre };
    };

    const selectCrear = document.getElementById("create-fin-inv");
    if (selectCrear) {
      // limpiar opciones previas (conservar placeholder si existe)
      const placeholderOptF = selectCrear.querySelector('option[value=""]')
        ? selectCrear.querySelector('option[value=""]').outerHTML
        : '<option value="">Seleccionar finca</option>';
      selectCrear.innerHTML = placeholderOptF;
      const opts = (Array.isArray(fincasActivas) ? fincasActivas : [])
        .map((fOrig) => {
          const { id, nombre } = normalizeFinca(fOrig);
          if (id !== null && id !== undefined) fincaMap.set(String(id), nombre);
          if (id !== null && id !== undefined)
            return `<option value="${id}">${nombre}</option>`;
          return "";
        })
        .join("");
      selectCrear.insertAdjacentHTML("beforeend", opts);
    }

    // Poblar select de filtro si existe
    const filterSelect = document.getElementById("filter-fin-inv");
    if (filterSelect) {
      // placeholder: mostrar 'Seleccione la finca' y dejarla deshabilitada/seleccionada
      const placeholder = filterSelect.querySelector('option[value=""]')
        ? filterSelect.querySelector('option[value=""]').outerHTML
        : '<option value="" disabled selected>Seleccione la finca</option>';
      filterSelect.innerHTML = placeholder;
      const optsF = (Array.isArray(fincasActivas) ? fincasActivas : [])
        .map((fOrig) => {
          const { id, nombre } = normalizeFinca(fOrig);
          if (id !== null && id !== undefined) {
            // guardar en mapa por si se necesita
            fincaMap.set(String(id), nombre);
            return `<option value="${id}">${nombre}</option>`;
          }
          return "";
        })
        .join("");
      filterSelect.insertAdjacentHTML("beforeend", optsF);
    }

    let selectEditar = document.getElementById("edit-fin-inv");
    if (selectEditar) {
      if (selectEditar.tagName !== "SELECT") {
        const wrapper = selectEditar.parentNode;
        const newSelect = document.createElement("select");
        newSelect.id = selectEditar.id;
        newSelect.className = selectEditar.className || "form-select";
        newSelect.required = selectEditar.required || false;
        wrapper.replaceChild(newSelect, selectEditar);
        selectEditar = newSelect;
      }

      // limpiar opciones previas (conservar placeholder si existe)
      const placeholderOptFE = selectEditar.querySelector('option[value=""]')
        ? selectEditar.querySelector('option[value=""]').outerHTML
        : '<option value="">Seleccionar finca</option>';
      selectEditar.innerHTML = placeholderOptFE;

      const opts = (Array.isArray(fincasActivas) ? fincasActivas : [])
        .map((fOrig) => {
          const { id, nombre } = normalizeFinca(fOrig);
          if (id !== null && id !== undefined) fincaMap.set(String(id), nombre);
          if (id !== null && id !== undefined)
            return `<option value="${id}">${nombre}</option>`;
          return "";
        })
        .join("");
      selectEditar.insertAdjacentHTML("beforeend", opts);
    }
  } catch (error) {
    console.error("Error al cargar fincas:", error);
  }
}

// Cargar inventario filtrado por finca (land)
async function loadInventoryByLand(landId) {
  const tableBody = document.getElementById("inv-table-body");
  if (!tableBody) return;
  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando Inventario...</td></tr>';
  try {
    const inventory = await inventoryService.getInventoryByLand(landId);
    // almacenar en caché para permitir búsqueda y filtrado por categoría
    cachedInventory = Array.isArray(inventory) ? inventory : [];
    currentPage = 1;
    renderInventoryPage();
  } catch (err) {
    console.error("Error al obtener inventario por finca:", err);
    tableBody.innerHTML =
      '<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }
}

async function init() {
  const tableBody = document.getElementById("inv-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando Inventario...</td></tr>';
  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando Inventario...</td></tr>';

  await cargarCategorias();
  await cargarFincas();
  // Intentar obtener inventario y almacenar en caché para paginación cliente
  try {
    const inventory = await inventoryService.getInventory();
    cachedInventory = Array.isArray(inventory) ? inventory : [];
    currentPage = 1;
    renderInventoryPage();
  } catch (error) {
    console.error("Error al obtener los Inventario:", error);
    tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>`;
    renderPagination(1, 1);
  }

  // Aplicamos el patrón remove/add para evitar listeners duplicados
  const editForm = document.getElementById("edit-inv-form");
  const createForm = document.getElementById("create-inv-form");
  tableBody.removeEventListener("click", handleTableClick);
  tableBody.addEventListener("click", handleTableClick);
  tableBody.removeEventListener("change", handleStatusSwitch);
  tableBody.addEventListener("change", handleStatusSwitch);
  editForm.removeEventListener("submit", handleUpdateSubmit);
  editForm.addEventListener("submit", handleUpdateSubmit);
  createForm.removeEventListener("submit", handleCreateSubmit);
  createForm.addEventListener("submit", handleCreateSubmit);

  // Paginación: vincular listener al UL de paginación
  const pagList = document.getElementById("pagination-list");
  if (pagList) {
    pagList.removeEventListener("click", handlePaginationClick);
    pagList.addEventListener("click", handlePaginationClick);
  }

  // Vincular input de búsqueda
  const searchEl = document.getElementById("search-inv");
  if (searchEl) {
    searchEl.removeEventListener("input", handleSearchInput);
    searchEl.addEventListener("input", handleSearchInput);
  }
  // Vincular filtro por categoria
  const filterCat = document.getElementById("filter-cat-inv");
  if (filterCat) {
    filterCat.removeEventListener("change", handleCategoryChange);
    filterCat.addEventListener("change", handleCategoryChange);
  }

  // Delegated handler dentro del módulo Inventario para accesos directos (p. ej. categorias)
  try {
    const pageRoot =
      tableBody.closest(".card") ||
      document.getElementById("main-content") ||
      document;
    // limpiar handler previo si existe
    if (pageRoot.__categoriasHandler) {
      pageRoot.removeEventListener("click", pageRoot.__categoriasHandler);
      pageRoot.__categoriasHandler = null;
    }

    const categoriasHandler = function (ev) {
      const target = ev.target;
      const shortcut =
        target.closest('[data-page="categorias_inventario"]') ||
        target.closest("#btn-categorias-inv") ||
        target.closest("button.app-nav") ||
        target.closest("a.app-nav");
      if (!shortcut) return;
      // asegurar que el click ocurrió dentro de esta página
      if (!pageRoot.contains(shortcut)) return;
      ev.preventDefault();
      // Intentar disparar el enlace del nav principal
      const shellLink = document.querySelector(
        '.app-nav a[data-page="categorias_inventario"]'
      );
      if (shellLink) {
        shellLink.click();
        return;
      }
      // Usar navigateTo si está disponible
      if (typeof window.navigateTo === "function") {
        window.navigateTo("categorias_inventario");
        return;
      }
      // Fallback: redirigir a .html
      window.location.href = "dashboard.html?page=categorias_inventario";
    };

    pageRoot.addEventListener("click", categoriasHandler);
    pageRoot.__categoriasHandler = categoriasHandler;
  } catch (err) {
    console.error("Error wiring categorias shortcut in init():", err);
  }
}

// Handler separado para el evento change del filtro
function onFilterChange(e) {
  const val = e.target.value;
  if (val) loadInventoryByLand(val);
  else init();
}

export { init };
