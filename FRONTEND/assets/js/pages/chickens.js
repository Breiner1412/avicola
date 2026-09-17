// chickens.js - Versión Completamente Corregida
import { chickenService } from "../api/chicken.service.js";
import { shedsService } from "../api/shed.service.js";
import { rescueService } from "../api/salvamento.service.js";

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
// =======================
// CONFIG & STATE
// =======================
const RECENT_PAGE_SIZE = 100; // max allowed by backend
let modalInstance = null;
let cacheGalpones = null;
let cacheTipos = null;

let allChickens = [];
let filteredChickens = [];

let currentSelectedGalponId = null;
let isVerMasMode = false; // when true, filters & pagination are active for "ver todos los registros"

// =======================
// HELPERS
// =======================
function formatDateDDMMYYYY(dateStr) {
  if (!dateStr) return "";
  return dateStr.split("-").reverse().join("/");
}

function uniqueJoin(arr) {
  return [...new Set(arr.filter(Boolean))].join(", ");
}

function setBtnVerTodosTextAndStyle() {
  const btn = document.getElementById("btn-ver-mas");
  if (!btn) return;
  btn.textContent = "Ver todos los registros";
  btn.className = "btn btn-success btn-sm"; // green as requested
}

// =======================
// ROW TEMPLATE
// =======================
function createChickenRow(chicken) {
  const chickenId = chicken.id_ingreso;

  const idRol = JSON.parse(localStorage.getItem("user"))?.id_rol;
  const fechaFormateada = formatDateDDMMYYYY(chicken.fecha);

  const mostrarBotonEspecial = !isVerMasMode && currentSelectedGalponId;

  const tabla = `
        <tr>
            <td class="px-0">${chicken.nombre_galpon}</td>
            <td class="px-0">${fechaFormateada}</td>
            <td class="px-0">${chicken.raza}</td>
            <td class="px-0">${chicken.cantidad_gallinas} gallinas</td>
            <td class="text-end">
                <div class="d-flex justify-content-end gap-2">
                    ${
                      mostrarBotonEspecial
                        ? `
                        <button class="btn btn-sm btn-success btn-rescue-chicken" aria-label="Salvamento" title="Salvamento" data-chicken-id="${chickenId}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="24" viewBox="0 0 48 48"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"><path d="M35.979 15.5a10.7 10.7 0 0 0-1.71-1.275l-1.466-.88a13.3 13.3 0 0 0-4.412-1.668l-.524-.096a27.1 27.1 0 0 1-8.051-2.855a2.792 2.792 0 1 0-2.965 3.396A22.8 22.8 0 0 1 21 17.647"/><path d="M11.307 25.02C11.045 25.3 8 28.65 8 32c0 3.5 1.558 5 3 6s3.72 2 5.61 2S28.5 41 33 40s5-2 7-4c1.081-1.081 1.882-2.602 2.39-3.77a22.5 22.5 0 0 0 1.175-3.502c.36-1.436.723-3.498.435-5.228c-.5-3-2-5-7-7.5c-4.604-2.302-8.647-1.212-9.258-1.025l-.161.054c-.8.283-7.265 2.596-10.01 4.471c-2.802 1.914-5.962 5.202-6.228 5.481z"/><path d="M6.103 20.01a2.792 2.792 0 1 1 2.965-3.396a27.1 27.1 0 0 0 8.051 2.854l.524.097c1.559.287 3.053.852 4.412 1.668l1.466.879a10.7 10.7 0 0 1 2.602 2.197l.406.472a6.6 6.6 0 0 1 1.532 5.17l-.028.211a5.95 5.95 0 0 1-1.637 3.367l-.462.473a6.67 6.67 0 0 1-5.875 1.924a8.34 8.34 0 0 1-4.425-2.23l-.739-.714a9.3 9.3 0 0 1-1.532-1.935l-2.172-3.652l-.634-1.27a22.8 22.8 0 0 0-4.454-6.116"/></g></svg>
                        </button>
                    `
                        : ""
                    }
                    <button class="btn btn-sm btn-success btn-edit-chicken" aria-label="Editar" title="Editar" data-chicken-id="${chickenId}">
                        <i class="fa-regular fa-pen-to-square me-0"></i>
                    </button>
                    ${
                      idRol === 1 || idRol === 2
                        ? `
                        <button class="btn btn-sm btn-secondary btn-delete-chicken" aria-label="Eliminar" title="Eliminar" data-chicken-id="${chickenId}">
                            <i class="fa fa-trash me-0"></i>
                        </button>
                    `
                        : ""
                    }
                </div>
            </td>
        </tr>
    `;

  return tabla;
}

// =======================
// CARGA DE SELECTS Y TYPES - CORREGIDO
// =======================
async function cargarSelectGalponesModals(force = false) {
  const selectCreate = document.getElementById("create-id_galpon");
  const selectEdit = document.getElementById("edit-id_galpon");

  try {
    if (!cacheGalpones || force) {
      cacheGalpones = await chickenService.getGalpones();
    }

    const galponesActivos = cacheGalpones.filter((g) => g.estado === true);

    if (selectCreate) {
      selectCreate.innerHTML =
        `<option value="" disabled selected>Seleccione un galpón</option>` +
        galponesActivos
          .map((g) => {
            const disponible = g.capacidad - g.cant_actual;
            return `<option value="${g.id_galpon}">
                                ${g.nombre} (${disponible} disponibles)
                            </option>`;
          })
          .join("");
      // If there's a selected galpón in the page, lock the create select accordingly
      if (currentSelectedGalponId) {
        selectCreate.value = String(currentSelectedGalponId);
        selectCreate.disabled = true;
      } else {
        selectCreate.disabled = false;
      }
    }

    if (selectEdit) {
      selectEdit.innerHTML =
        `<option value="" disabled selected>Seleccione un galpón</option>` +
        galponesActivos
          .map((g) => {
            const disponible = g.capacidad - g.cant_actual;
            return `<option value="${g.id_galpon}">
                                ${g.nombre} (${disponible} disponibles)
                            </option>`;
          })
          .join("");
    }
  } catch (error) {
    console.error("Error cargando galpones:", error);
    if (selectCreate) {
      selectCreate.innerHTML = `<option>Error al cargar</option>`;
    }
    if (selectEdit) {
      selectEdit.innerHTML = `<option>Error al cargar</option>`;
    }
  }
}


async function cargarSelectTypeChickensModals(force = false) {
  const selectCreate = document.getElementById("create-id_tipo_gallina");
  const selectEdit = document.getElementById("edit-id_tipo_gallina");

  try {
    if (!cacheTipos || force) {
      cacheTipos = await chickenService.getTypeChickens();
    }

    if (selectCreate) {
      selectCreate.innerHTML =
        `<option value="" disabled selected>Seleccione un tipo</option>` +
        cacheTipos
          .map(
            (t) => `<option value="${t.id_tipo_gallinas}">${t.raza}</option>`
          )
          .join("");
    }

    if (selectEdit) {
      selectEdit.innerHTML =
        `<option value="" disabled selected>Seleccione un tipo</option>` +
        cacheTipos
          .map(
            (t) => `<option value="${t.id_tipo_gallinas}">${t.raza}</option>`
          )
          .join("");
    }
  } catch (error) {
    console.error("Error cargando los tipos de gallinas:", error);
    if (selectCreate) {
      selectCreate.innerHTML = `<option>Error al cargar</option>`;
    }
    if (selectEdit) {
      selectEdit.innerHTML = `<option>Error al cargar</option>`;
    }
  }
}

// =======================
// SELECT FILTRO GALPONES (independiente)
// =======================
async function cargarSelectFilterGalpones() {
  const selectFilter = document.getElementById("filter-galpon");

  try {
    if (!cacheGalpones) {
      cacheGalpones = await chickenService.getGalpones();
    }

    const galponesActivos = cacheGalpones.filter((g) => g.estado === true);

    const options = galponesActivos
      .map(
        (g) => `
            <option value="${g.id_galpon}">
                ${g.nombre}
            </option>
        `
      )
      .join("");

    if (selectFilter) {
      selectFilter.innerHTML = `<option value="">Seleccione un Galpón</option>${options}`;
      // Assign listener
      selectFilter.removeEventListener("change", onGalponChange);
      selectFilter.addEventListener("change", onGalponChange);
      // ensure button style/text
      setBtnVerTodosTextAndStyle();
    }
  } catch (error) {
    if (selectFilter) {
      selectFilter.innerHTML = `<option>Error al cargar por filtros</option>`;
    }
  }
}

// =======================
// OBTENER REGISTROS RECIENTES (APLICA REGLA)
// =======================
function seleccionarRegistrosRecientes(registrosOrdenadosDesc, cantActual) {
  const resultado = [];
  let suma = 0;

  for (const r of registrosOrdenadosDesc) {
    if (resultado.length === 0 && r.cantidad_gallinas >= cantActual) {
      resultado.push(r);
      suma = r.cantidad_gallinas;
      break;
    }

    if (suma + r.cantidad_gallinas <= cantActual) {
      resultado.push(r);
      suma += r.cantidad_gallinas;
    }

    if (suma === cantActual) break;
  }

  return resultado;
}

// =======================
// MOSTRAR DATOS DEL GALPÓN (TARJETA) - MODIFICADO
// =======================
function mostrarDatosDelGalpon(galpon, registrosRecientes) {
  const el = document.getElementById("galpon-info");
  if (!el) return;

  // Build card style content
  const nombre = galpon?.nombre || "-";
  const capacidad = galpon?.capacidad ?? "-";
  const actual = galpon?.cant_actual ?? "-";
  const razas = (registrosRecientes?.map((r) => r.raza) || []).filter(Boolean);
  // MODIFICACIÓN: Mostrar "Sin tipo" cuando no hay razas
  const tiposText = razas.length ? uniqueJoin(razas) : "Sin tipo";

  el.innerHTML = `
        <div class="card border-success mb-3">
            <div class="card-body p-2">
                <h6 class="text-success fw-bold mb-2">Información del Galpón</h6>
                <p class="mb-1"><strong>Nombre:</strong> ${nombre}</p>
                <p class="mb-1"><strong>Capacidad:</strong> ${capacidad}</p>
                <p class="mb-1"><strong>Cantidad actual:</strong> ${actual}</p>
                <p class="mb-0"><strong>Tipo(s):</strong> ${tiposText}</p>
            </div>
        </div>
    `;
  el.classList.remove("d-none");
}

// =======================
// RENDER TABLA
// =======================
function renderTabla(registros) {
  const tbody = document.getElementById("chicken-table-body");
  if (!tbody) return;

  if (!registros || registros.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center">No hay registros para este galpón.</td></tr>';
    return;
  }

  tbody.innerHTML = registros.map(createChickenRow).join("");
}

// =======================
// MODO: RECENT vs VER TODOS
// =======================
function entrarModoReciente() {
  isVerMasMode = false;
  const dateFilters = document.getElementById("date-filters");
  const paginationContainer = document.getElementById("pagination-container");
  const btnVerMas = document.getElementById("btn-ver-mas");
  if (dateFilters) dateFilters.classList.add("d-none");
  if (paginationContainer) paginationContainer.classList.add("d-none");
  // MODIFICACIÓN: El botón "Ver todos" siempre se muestra en modo reciente
  if (btnVerMas) btnVerMas.classList.remove("d-none");
  setBtnVerTodosTextAndStyle();

  if (filteredChickens.length > 0 && currentSelectedGalponId) {
    renderTabla(filteredChickens);
  }
}

function entrarModoVerTodos() {
  isVerMasMode = true;
  const dateFilters = document.getElementById("date-filters");
  const paginationContainer = document.getElementById("pagination-container");
  const btnVerMas = document.getElementById("btn-ver-mas");
  if (dateFilters) dateFilters.classList.remove("d-none");
  if (paginationContainer) paginationContainer.classList.remove("d-none");
  // MODIFICACIÓN: El botón "Ver todos" se oculta solo cuando se presiona
  if (btnVerMas) btnVerMas.classList.add("d-none");

  if (filteredChickens.length > 0) {
    renderTabla(filteredChickens);
  }
}

// =======================
// RESET AFTER CLEAR SELECTION - NUEVA FUNCIÓN
// =======================
function resetAfterClearSelection() {
  const galponInfo = document.getElementById("galpon-info");
  if (galponInfo) galponInfo.classList.add("d-none");

  const tbody = document.getElementById("chicken-table-body");
  if (tbody) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center">Seleccione un galpón para ver los registros.</td></tr>';
  }

  // Resetear a modo reciente
  entrarModoReciente();
  currentSelectedGalponId = null;
  isVerMasMode = false;
}

// =======================
// CARGAR REGISTROS RECIENTES AL SELECCIONAR GALPÓN - MODIFICADO
// =======================
async function onGalponChange(e) {
  const galponId = e.target.value;
  currentSelectedGalponId = galponId || null;

  // Ensure button styled
  setBtnVerTodosTextAndStyle();

  if (!galponId) {
    resetAfterClearSelection();
    return;
  }

  let galpon = null;
  try {
    galpon = await shedsService.getShedById(galponId);
  } catch (err) {
    console.error(
      "Error obteniendo galpón desde API, usando cache si existe:",
      err
    );
    if (!cacheGalpones) {
      cacheGalpones = await chickenService.getGalpones();
    }
    galpon =
      cacheGalpones.find((g) => String(g.id_galpon) === String(galponId)) ||
      null;
  }

  // Enter recent mode
  entrarModoReciente();

  // Show loading message
  const tbody = document.getElementById("chicken-table-body");
  tbody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando registros recientes...</td></tr>';

  try {
    // Fetch recent page of records (desc expected)
    const data = await chickenService.getChickensByGalpon(
      galponId,
      1,
      RECENT_PAGE_SIZE
    );
    let registros = data.record_chickens || [];

    // MODIFICACIÓN: Mostrar información del galpón incluso si no hay registros
    if ((!registros || registros.length === 0) && galpon) {
      mostrarDatosDelGalpon(galpon, []); // Pasar array vacío para mostrar "Sin tipo"
      renderTabla([]); // will show "No hay registros para este galpón."
      filteredChickens = [];
      allChickens = [];

      // MODIFICACIÓN: El botón "Ver todos" se mantiene visible incluso sin registros
      const btnVerMas = document.getElementById("btn-ver-mas");
      if (btnVerMas) {
        btnVerMas.classList.remove("d-none");
      }
      return;
    }

    // Order by fecha desc, then id_ingreso desc
    registros.sort((a, b) => {
      if (a.fecha === b.fecha) return b.id_ingreso - a.id_ingreso;
      return new Date(b.fecha) - new Date(a.fecha);
    });

    // Select recent records using the rule
    const registrosRecientes = seleccionarRegistrosRecientes(
      registros,
      galpon?.cant_actual ?? 0
    );

    // Render recent records
    renderTabla(registrosRecientes);

    // Show galpon info (uses tipos from registrosRecientes o "Sin tipo")
    mostrarDatosDelGalpon(galpon || {}, registrosRecientes);

    filteredChickens = registrosRecientes;
    allChickens = registros;

    // MODIFICACIÓN: El botón "Ver todos" siempre se muestra cuando hay un galpón seleccionado
    const btnVerMas = document.getElementById("btn-ver-mas");
    if (btnVerMas) {
      btnVerMas.classList.remove("d-none");
    }
  } catch (error) {
    console.error("Error al cargar registros recientes:", error);
    const tbody = document.getElementById("chicken-table-body");
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center">No se encontraron registros.</td></tr>';

    // MODIFICACIÓN: Mostrar info del galpón incluso en caso de error
    if (galpon) {
      mostrarDatosDelGalpon(galpon, []);
    }
  }
}

// =======================
// BOTÓN "VER TODOS LOS REGISTROS" - MODIFICADO
// =======================
function setupVerMasButton() {
  const btnVerMas = document.getElementById("btn-ver-mas");
  if (btnVerMas) {
    btnVerMas.removeEventListener("click", handleVerMasClick);
    btnVerMas.addEventListener("click", handleVerMasClick);
  }
}

async function handleVerMasClick(e) {
  e.preventDefault();

  // NUEVO: Ocultar card de información del galpón
  const galponInfo = document.getElementById("galpon-info");
  if (galponInfo) galponInfo.classList.add("d-none");

  // NUEVO: Resetear el select de galpones
  const selectFilter = document.getElementById("filter-galpon");
  if (selectFilter) {
    selectFilter.value = "";
  }

  // **IMPORTANTE: Resetear currentSelectedGalponId**
  currentSelectedGalponId = null;

  // Enter ver todos mode
  entrarModoVerTodos();

  // MODIFICACIÓN: Siempre cargar todos los registros sin filtrar por galpón
  await cargarTodosRegistrosGalponPaginados(
    null,
    1,
    document.getElementById("pageSize").value
  );
}

// =======================
// CARGAR TODOS LOS REGISTROS DEL GALPÓN (PAGINADO / para Ver todos)
// =======================
async function cargarTodosRegistrosGalponPaginados(
  galponId,
  page = 1,
  page_size = 10
) {
  const tbody = document.getElementById("chicken-table-body");
  tbody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando registros...</td></tr>';

  try {
    let data;
    if (galponId) {
      data = await chickenService.getChickensByGalpon(
        galponId,
        page,
        page_size
      );
    } else {
      data = await chickenService.getChickens(page, page_size);
    }
    const registros = data.record_chickens || [];
    filteredChickens = registros;
    allChickens = registros; // current page

    renderTabla(registros);
    renderPagination(data.total_pages || 1, data.page || page);
  } catch (error) {
    console.error("Error cargando registros paginados del galpón:", error);
    tbody.innerHTML =
      '<tr><td colspan="5" class="text-center text-danger">Error al cargar registros.</td></tr>';
  }
}

// =======================
// MODALES - COMPLETAMENTE CORREGIDOS
// =======================
async function openEditModal(chickenId) {
  try {
    const chicken = await chickenService.getChickenById(chickenId);

    // Cargar selects antes de mostrar el modal
    await cargarSelectGalponesModals();
    await cargarSelectTypeChickensModals();

    // Llenar el formulario
    document.getElementById("edit-chicken-id").value = chicken.id_ingreso;
    document.getElementById("edit-id_galpon").value = chicken.id_galpon;
    document.getElementById("edit-id_tipo_gallina").value =
      chicken.id_tipo_gallina;
    document.getElementById("edit-cantidad_gallinas").value =
      chicken.cantidad_gallinas;

    // Mostrar el modal
    const modalElement = document.getElementById("editChickenModal");
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  } catch (error) {
    console.error(
      `Error al obtener los registros de gallinas ${chickenId}:`,
      error
    );
    Swal.fire({
      icon: "error",
      text: "No se pudieron cargar los datos de los registros.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function handleUpdateSubmit(event) {
  event.preventDefault();
  const chickenId = document.getElementById("edit-chicken-id").value;
  const updatedData = {
    id_galpon: parseInt(document.getElementById("edit-id_galpon").value),
    id_tipo_gallina: parseInt(
      document.getElementById("edit-id_tipo_gallina").value
    ),
    cantidad_gallinas: parseInt(
      document.getElementById("edit-cantidad_gallinas").value
    ),
  };

  try {
    await chickenService.updateChicken(chickenId, updatedData);

    // Cerrar modal
    const modalElement = document.getElementById("editChickenModal");
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();

    // Recargar datos
    if (currentSelectedGalponId && !isVerMasMode) {
      const select = document.getElementById("filter-galpon");
      if (select) select.dispatchEvent(new Event("change"));
    } else if (currentSelectedGalponId && isVerMasMode) {
      cargarTodosRegistrosGalponPaginados(
        currentSelectedGalponId,
        1,
        document.getElementById("pageSize").value
      );
    } else {
      init();
    }

    Swal.fire({
      icon: "success",
      title: "Actualizado",
      text: "Registro actualizado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  } catch (error) {
    console.error(`Error al actualizar el registro ${chickenId}:`, error);
    const msg = error?.message || error?.toString() || "";

    if (msg.includes("excede") || msg.includes("exced")) {
      Swal.fire({
        icon: "warning",
        title: "Capacidad excedida",
        text: "La cantidad de gallinas excede la capacidad del galpón.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    } else {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo actualizar el registro.",
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
  const rescueButton = event.target.closest(".btn-rescue-chicken");
  if (rescueButton) {
    const chickenId = rescueButton.dataset.chickenId;
    await openRescueModal(chickenId);
    return;
  }

  const editButton = event.target.closest(".btn-edit-chicken");
  if (editButton) {
    const chickenId = editButton.dataset.chickenId;
    await openEditModal(chickenId);
    return;
  }

  const deleteButton = event.target.closest(".btn-delete-chicken");
  if (deleteButton) {
    const chickenId = deleteButton.dataset.chickenId;
    await handleDeleteChicken(chickenId);
    return;
  }
}

// =======================
// ABRIR MODAL DE SALVAMENTO DESDE CHICKENS
// =======================
async function openRescueModal(chickenId) {
  try {
    // Obtener los datos del registro de gallinas
    const chicken = await chickenService.getChickenById(chickenId);
    const shed = await shedsService.getShedById(chicken.id_galpon);

    // Llenar los campos del modal
    document.getElementById("rescue-chicken-id").value = chickenId;
    document.getElementById("rescue-id-galpon").value = chicken.id_galpon;
    document.getElementById("rescue-id-tipo-gallina").value =
      chicken.id_tipo_gallina;
    document.getElementById("rescue-galpon-display").value =
      chicken.nombre_galpon || `Galpón ${chicken.id_galpon}`;
    document.getElementById("rescue-tipo-gallina-display").value =
      chicken.raza || `Tipo ${chicken.id_tipo_gallina}`;
    document.getElementById("rescue-cantidad-gallinas").value = "";
    document.getElementById("rescue-cantidad-gallinas").max = shed.cant_actual;

    // Establecer fecha actual por defecto
    const today = new Date().toISOString().split("T")[0];
    document.getElementById("rescue-fecha").value = today;

    // Mostrar el modal
    const modalElement = document.getElementById(
      "createRescueFromChickenModal"
    );
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  } catch (error) {
    console.error(
      `Error al obtener datos para salvamento ${chickenId}:`,
      error
    );
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos para el salvamento.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

// =======================
// MANEJAR ENVÍO DEL FORMULARIO DE SALVAMENTO
// =======================
async function handleRescueSubmit(event) {
  event.preventDefault();

  const chickenId = document.getElementById("rescue-chicken-id").value;
  const rescueData = {
    id_galpon: parseInt(document.getElementById("rescue-id-galpon").value),
    id_tipo_gallina: parseInt(
      document.getElementById("rescue-id-tipo-gallina").value
    ),
    cantidad_gallinas: parseInt(
      document.getElementById("rescue-cantidad-gallinas").value
    ),
    fecha: document.getElementById("rescue-fecha").value,
  };

  // Obtener datos para mostrar en el SweetAlert
  const galponNombre = document.getElementById("rescue-galpon-display").value;
  const tipoGallina = document.getElementById(
    "rescue-tipo-gallina-display"
  ).value;

  // Validaciones
  if (!rescueData.cantidad_gallinas || rescueData.cantidad_gallinas <= 0) {
    Swal.fire({
      icon: "warning",
      title: "Cantidad inválida",
      text: "Por favor ingrese una cantidad válida de gallinas.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    return;
  }

  try {
    // Crear el salvamento
    const createdRescue = await rescueService.createRescue(rescueData);

    // Cerrar el modal primero
    const modalElement = document.getElementById(
      "createRescueFromChickenModal"
    );
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();

    // Mostrar SweetAlert personalizado con la información
    const result = await Swal.fire({
      title: "¡Salvamento Creado Exitosamente!",
      html: `
                <div class="text-start">
                    <div class="alert alert-success border-success bg-success bg-opacity-10">
                        <div class="d-flex align-items-center">
                            <i class="fa-solid fa-circle-check text-success me-2"></i>
                            <strong>El salvamento se ha creado exitosamente</strong>
                        </div>
                    </div>
                    
                    <div class="border rounded p-3 bg-light mt-3">
                        <h6 class="text-success mb-3">
                            <i class="fa-solid fa-drumstick-bite me-2"></i>Detalles del Salvamento
                        </h6>
                        
                        <div class="row">
                            <div class="col-6">
                                <p class="mb-2"><strong><i class="fa-solid fa-warehouse me-1 text-muted"></i> Galpón:</strong></p>
                                <p class="mb-2"><strong><i class="fa-solid fa-kiwi-bird me-1 text-muted"></i> Tipo Gallina:</strong></p>
                                <p class="mb-2"><strong><i class="fa-solid fa-hashtag me-1 text-muted"></i> Cantidad:</strong></p>
                                <p class="mb-0"><strong><i class="fa-solid fa-calendar me-1 text-muted"></i> Fecha:</strong></p>
                            </div>
                            <div class="col-6">
                                <p class="mb-2">${galponNombre}</p>
                                <p class="mb-2">${tipoGallina}</p>
                                <p class="mb-2">${rescueData.cantidad_gallinas} gallinas</p>
                                <p class="mb-0">${rescueData.fecha}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p class="mt-4 text-center text-muted">
                        <i class="fa-solid fa-arrow-pointer me-1"></i>¿Qué deseas hacer ahora?
                    </p>
                </div>
            `,
      icon: "success",
      showCancelButton: true,
      confirmButtonColor: "#198754",
      cancelButtonColor: "#6c757d",
      confirmButtonText:
        '<i class="fa-solid fa-list me-2"></i> Ir a Salvamentos',
      cancelButtonText:
        '<i class="fa-solid fa-table me-2"></i> Seguir en Gallinas',
      reverseButtons: true,
      width: "600px",
      customClass: {
        popup: "border-success",
        confirmButton: "btn-success",
        cancelButton: "btn-secondary",
      },
    });

    if (result.isConfirmed) {
      // Usar loadContent en lugar de redirección directa
      if (typeof loadContent === "function") {
        loadContent("rescue");
      } else {
        // Fallback: intentar encontrar la función global
        if (window.loadContent) {
          window.loadContent("rescue");
        } else {
          // Redirección alternativa si no existe loadContent
          window.location.href = "../../pages/rescue.html";
        }
      }
    } else {
      // Recargar los datos actuales de chickens
      if (currentSelectedGalponId) {
        const select = document.getElementById("filter-galpon");
        if (select) select.dispatchEvent(new Event("change"));
      }
    }
  } catch (error) {
    console.error("Error al crear el salvamento:", error);
    Swal.fire({
      icon: "error",
      title: "Error al crear salvamento",
      html: `
                <div class="text-start">
                    <p>No se pudo crear el salvamento:</p>
                    <div class="alert alert-danger mt-2">
                        <strong>Error:</strong> ${
                          error.message || "Error desconocido"
                        }
                    </div>
                </div>
            `,
      confirmButtonColor: "success",
    });
  }
}

async function handleDeleteChicken(chickenId) {
  try {
    const result = await Swal.fire({
      title: "¿Eliminar registro?",
      text: "Esta acción no se puede deshacer.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar",
      customClass: {
        confirmButton: "btn btn-success",
        cancelButton: "btn btn-secondary",
      },
      buttonsStyling: false,
    });

    if (!result.isConfirmed) return;

    await chickenService.deleteChicken(chickenId);

    await Swal.fire({
      icon: "success",
      title: "Eliminado",
      text: "Registro eliminado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });

    // If we were viewing this galpon, reload recent view
    if (currentSelectedGalponId) {
      const select = document.getElementById("filter-galpon");
      if (select) {
        // trigger change to reload
        select.dispatchEvent(new Event("change"));
      }
    } else {
      init();
    }
  } catch (error) {
    console.error(`Error al eliminar el registro ${chickenId}:`, error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: error?.message || "No se pudo eliminar el registro.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function handleCreateSubmit(event) {
  event.preventDefault();

  const fechaLocal = new Date();
  const pad = (n) => n.toString().padStart(2, "0");
  const fechaPC = `${fechaLocal.getFullYear()}-${pad(
    fechaLocal.getMonth() + 1
  )}-${pad(fechaLocal.getDate())}`;

  const newChickenData = {
    id_galpon: parseInt(document.getElementById("create-id_galpon").value),
    fecha: fechaPC,
    id_tipo_gallina: parseInt(
      document.getElementById("create-id_tipo_gallina").value
    ),
    cantidad_gallinas: parseInt(
      document.getElementById("create-cantidad_gallinas").value
    ),
  };

  try {
    await chickenService.createChicken(newChickenData);

    const createModal = bootstrap.Modal.getInstance(
      document.getElementById("createChickenModal")
    );
    if (createModal) {
      createModal.hide();
    }

    document.getElementById("create-chicken-form").reset();
    await Swal.fire({
      icon: "success",
      title: "Creado",
      text: "Registro creado exitosamente.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    // After create, reload either recent view or full view based on mode
    if (currentSelectedGalponId && !isVerMasMode) {
      // reload recent for selected galpon
      const select = document.getElementById("filter-galpon");
      if (select) select.dispatchEvent(new Event("change"));
    } else if (currentSelectedGalponId && isVerMasMode) {
      cargarTodosRegistrosGalponPaginados(
        currentSelectedGalponId,
        1,
        document.getElementById("pageSize").value
      );
    } else {
      init();
    }
  } catch (error) {
    console.error("Error al crear el registro:", error);
    const msg = error?.message || error?.toString() || "";

    if (msg.includes("excede") || msg.includes("exced")) {
      Swal.fire({
        icon: "warning",
        title: "Capacidad excedida",
        text: "La cantidad de gallinas excede la capacidad del galpón.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    } else {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "No se pudo crear el registro.",
        confirmButtonText: "OK",
        customClass: {
          confirmButton: "btn btn-success",
        },
        buttonsStyling: false,
      });
    }
  }
}

// =======================
// PAGINACIÓN (ajustada para modos)
// =======================
function renderPagination(total_pages, currentPage = 1) {
  const container = document.querySelector("#pagination");
  if (!container) return;

  container.innerHTML = "";

  const prevItem = document.createElement("li");
  prevItem.classList.add("page-item");
  if (currentPage === 1) prevItem.classList.add("disabled");

  const prevLink = document.createElement("a");
  prevLink.classList.add("page-link", "text-success");
  prevLink.href = "#";
  prevLink.innerHTML = "&lt;";
  prevLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage > 1) {
      const prevPage = currentPage - 1;
      if (isVerMasMode && currentSelectedGalponId) {
        cargarTodosRegistrosGalponPaginados(
          currentSelectedGalponId,
          prevPage,
          document.getElementById("pageSize").value
        );
      } else if (isVerMasMode) {
        // **NUEVO: Manejar paginación en modo "Ver todos" sin galpón**
        cargarTodosRegistrosGalponPaginados(
          null,
          prevPage,
          document.getElementById("pageSize").value
        );
      } else {
        init(prevPage, document.getElementById("pageSize").value);
      }
    }
  });

  prevItem.appendChild(prevLink);
  container.appendChild(prevItem);

  for (let i = 1; i <= total_pages; i++) {
    const pageItem = document.createElement("li");
    pageItem.classList.add("page-item");

    const pageLink = document.createElement("a");

    if (i === currentPage) {
      pageLink.classList.add(
        "page-link",
        "bg-success",
        "border-success",
        "text-white"
      );
      pageItem.classList.add("active");
    } else {
      pageLink.classList.add("page-link", "text-success");
    }

    pageLink.href = "#";
    pageLink.textContent = i;
    pageLink.addEventListener("click", (e) => {
      e.preventDefault();
      if (isVerMasMode && currentSelectedGalponId) {
        cargarTodosRegistrosGalponPaginados(
          currentSelectedGalponId,
          i,
          document.getElementById("pageSize").value
        );
      } else if (isVerMasMode) {
        // **NUEVO: Manejar paginación en modo "Ver todos" sin galpón**
        cargarTodosRegistrosGalponPaginados(
          null,
          i,
          document.getElementById("pageSize").value
        );
      } else {
        init(i, document.getElementById("pageSize").value);
      }
    });

    pageItem.appendChild(pageLink);
    container.appendChild(pageItem);
  }

  const nextItem = document.createElement("li");
  nextItem.classList.add("page-item");
  if (currentPage === total_pages) nextItem.classList.add("disabled");

  const nextLink = document.createElement("a");
  nextLink.classList.add("page-link", "text-success");
  nextLink.href = "#";
  nextLink.innerHTML = "&gt;";
  nextLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage < total_pages) {
      const nextPage = currentPage + 1;
      if (isVerMasMode && currentSelectedGalponId) {
        cargarTodosRegistrosGalponPaginados(
          currentSelectedGalponId,
          nextPage,
          document.getElementById("pageSize").value
        );
      } else if (isVerMasMode) {
        // **NUEVO: Manejar paginación en modo "Ver todos" sin galpón**
        cargarTodosRegistrosGalponPaginados(
          null,
          nextPage,
          document.getElementById("pageSize").value
        );
      } else {
        init(nextPage, document.getElementById("pageSize").value);
      }
    }
  });

  nextItem.appendChild(nextLink);
  container.appendChild(nextItem);
}

// =======================
// FILTROS - COMPLETAMENTE CORREGIDOS
// =======================
async function filtrarChickens() {
  const galponId = document.getElementById("filter-galpon")?.value;
  let startDate = document.getElementById("filter-start-date")?.value;
  let endDate = document.getElementById("filter-end-date")?.value;

  const tableBody = document.getElementById("chicken-table-body");
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="5" class="text-center">Cargando registros...</td></tr>';

  if (!endDate) {
    const now = new Date();
    const pad = (n) => n.toString().padStart(2, "0");
    endDate = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }
  if (!startDate) startDate = "2000-01-01";

  const isDateFilter = startDate && endDate;

  try {
    let data = { record_chickens: [], total_pages: 1, page: 1 };

    if (!galponId && isDateFilter) {
      try {
        data = await chickenService.getChickensByRangeDate(
          startDate,
          endDate,
          1,
          document.getElementById("pageSize").value
        );
      } catch (err) {
        console.error("Error al filtrar por fechas:", err);
      }
    } 
    else if (galponId && isDateFilter) {
      try {
        const galponData = await chickenService.getChickensByGalpon(
          galponId,
          1,
          document.getElementById("pageSize").value
        );

        const filtered = galponData.record_chickens.filter(
          (c) => c.fecha >= startDate && c.fecha <= endDate
        );

        data.record_chickens = filtered;
      } catch (err) {
        console.error("Error al filtrar registros:", err);
      }
    } 
    else if (galponId) {
      data = await chickenService.getChickensByGalpon(
        galponId,
        1,
        document.getElementById("pageSize").value
      );
    } 
    else {
      data = await chickenService.getChickens(
        1,
        document.getElementById("pageSize").value
      );
    }

    const chickens = data.record_chickens || [];
    filteredChickens = chickens;

    if (chickens.length === 0 && isDateFilter) {
      tableBody.innerHTML = `
         <tr>
            <td colspan="7" class="text-center">
              <div class="alert alert-success mt-3">
                <i class="fas fa-info-circle me-2"></i>
                No hay registros en el rango de fechas seleccionado.
              </div>
            </td>
          </tr>`;
    } else if (chickens.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center">
            No se encontraron registros.
          </td>
        </tr>`;
    } else {
      tableBody.innerHTML = chickens.map(createChickenRow).join("");
    }

    renderPagination(data.total_pages || 1, 1);

  } catch (error) {
    tableBody.innerHTML =
      '<tr><td colspan="5" class="text-center text-danger">Error al cargar los datos.</td></tr>';
  }
}


// =======================
// LIMPIAR FILTROS - CORREGIDO
// =======================
function limpiarFiltros() {
  // Solo limpiar los filtros de fecha
  const startDate = document.getElementById("filter-start-date");
  const endDate = document.getElementById("filter-end-date");

  if (startDate) startDate.value = "";
  if (endDate) endDate.value = "";

  // Aplicar filtros actuales (solo sin fechas)
  if (isVerMasMode) {
    filtrarChickens();
  }
}

// =======================
// EXPORTACIÓN - CORREGIDA
// =======================
// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_ingreso" },
  { header: "Galpon", key: "nombre_galpon" },
  { header: "Fecha", key: "fecha" },
  { header: "Tipo Gallina", key: "raza" },
  { header: "Cantidad Gallinas", key: "cantidad_gallinas" },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Gallinas");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Gallinas");
}

function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;
  event.preventDefault();
  event.stopPropagation();

  // PREVENIR MÚLTIPLES DESCARGAS
  if (item.classList.contains("exporting")) return;
  item.classList.add("exporting");

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  // Usar filteredChickens si está disponible, sino allChickens
  let dataToExport = [];
  if (filteredChickens && filteredChickens.length > 0) {
    dataToExport = filteredChickens;
  } else if (allChickens && allChickens.length > 0) {
    dataToExport = allChickens;
  }

  if (!dataToExport || dataToExport.length === 0) {
    Swal.fire({
      title: "No hay datos para exportar.",
      icon: "info",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    item.classList.remove("exporting");
    return;
  }

  try {
    if (fmt === "csv") {
      exportToCSV(dataToExport, `Gallinas_${dateTag}.csv`);
    } else if (fmt === "excel") {
      exportToExcel(dataToExport, `Gallinas_${dateTag}.xlsx`);
    } else if (fmt === "pdf") {
      exportToPDF(dataToExport, `Gallinas_${dateTag}.pdf`);
    }

    item.classList.remove("exporting");
  } catch (error) {
    console.error("Error en exportación:", error);
    Swal.fire({
      title: "Error",
      text: "No se pudo generar el archivo de exportación.",
      icon: "error",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    item.classList.remove("exporting");
  }
}







// =======================
// INICIALIZACIÓN - COMPLETAMENTE CORREGIDA
// =======================
function setupEventListeners() {
  // Botón Filtrar
  const btnFilter = document.getElementById("btn-filter");
  if (btnFilter) {
    btnFilter.removeEventListener("click", filtrarChickens);
    btnFilter.addEventListener("click", filtrarChickens);
  }

  // Botón Limpiar Filtros
  const btnClear = document.getElementById("btn_clear_filters");
  if (btnClear) {
    btnClear.removeEventListener("click", limpiarFiltros);
    btnClear.addEventListener("click", limpiarFiltros);
  }

  // Select de página
  const selectPage = document.getElementById("pageSize");
  if (selectPage) {
    selectPage.removeEventListener("change", handlePageSizeChange);
    selectPage.addEventListener("change", handlePageSizeChange);
  }

  // Formularios de modales
  const editForm = document.getElementById("edit-chicken-form");
  if (editForm) {
    editForm.removeEventListener("submit", handleUpdateSubmit);
    editForm.addEventListener("submit", handleUpdateSubmit);
  }

  const createForm = document.getElementById("create-chicken-form");
  if (createForm) {
    createForm.removeEventListener("submit", handleCreateSubmit);
    createForm.addEventListener("submit", handleCreateSubmit);
  }

  // Evento para abrir modal de crear
  const createButton = document.querySelector(
    '[data-bs-target="#createChickenModal"]'
  );
  if (createButton) {
    createButton.removeEventListener("click", handleCreateModalOpen);
    createButton.addEventListener("click", handleCreateModalOpen);
  }

  // Exportación
  const exportItems = document.querySelectorAll(".export-format");
  exportItems.forEach((item) => {
    item.removeEventListener("click", handleExportClick);
    item.addEventListener("click", handleExportClick);
  });

  // Botón Ver Más
  setupVerMasButton();

  // Eventos de la tabla (delegados)
  const tableBody = document.getElementById("chicken-table-body");
  if (tableBody) {
    tableBody.removeEventListener("click", handleTableClick);
    tableBody.addEventListener("click", handleTableClick);
  }

  const rescueForm = document.getElementById("create-rescue-from-chicken-form");
  if (rescueForm) {
    rescueForm.removeEventListener("submit", handleRescueSubmit);
    rescueForm.addEventListener("submit", handleRescueSubmit);
  }
}

async function handleCreateModalOpen(e) {
  e.preventDefault();
  await cargarSelectGalponesModals(true);
  await cargarSelectTypeChickensModals(true);

  const selectCreate = document.getElementById("create-id_galpon");
  if (selectCreate) {
    if (currentSelectedGalponId && !isVerMasMode) {
      selectCreate.value = String(currentSelectedGalponId);
      selectCreate.disabled = true;
    } else {
      selectCreate.disabled = false;
    }
  }
}

function handlePageSizeChange() {
  const selectPage = document.getElementById("pageSize");
  if (isVerMasMode && currentSelectedGalponId) {
    cargarTodosRegistrosGalponPaginados(
      currentSelectedGalponId,
      1,
      selectPage.value
    );
  } else if (isVerMasMode) {
    // **NUEVO: Cargar todos los registros cuando estamos en modo "Ver todos" sin galpón seleccionado**
    cargarTodosRegistrosGalponPaginados(null, 1, selectPage.value);
  } else {
    init(1, selectPage.value);
  }
}

// =======================
// INIT
// =======================
async function init(page = 1, page_size = 10) {
  await cargarSelectFilterGalpones();

  // initial UI state: show table empty message asking to select a galpón
  entrarModoReciente();
  currentSelectedGalponId = null;
  isVerMasMode = false;

  const tbody = document.getElementById("chicken-table-body");
  if (!tbody) {
    return;
  }
  tbody.innerHTML =
    '<tr><td colspan="5" class="text-center">Seleccione un galpón para ver los registros.</td></tr>';

  // hide galpon info
  const galponInfo = document.getElementById("galpon-info");
  if (galponInfo) galponInfo.classList.add("d-none");

  // Configurar event listeners
  setupEventListeners();
}

export { init };
