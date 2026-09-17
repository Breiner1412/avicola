import { alimentoService } from "../api/alimento.service.js";
import { consumoService } from "../api/consumo-alimento.service.js";

import { exportarCSV, exportarExcel, exportarPDF } from "../utils/exportar.js";
let modalInstance = null;
let activeFechaInicio = "";
let activeFechaFin = "";

//______________________boton consumo alimentos__________________________
// Navega con el cargador central (main.js)
document.addEventListener("click", (e) => {
  const btn = e.target.closest("#consumo_alimento");
  if (!btn) return;
  e.preventDefault();
  window.loadContent("consumo_alimento");
});

// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---

function createAlimentosRow(alimento) {
  const alimentoId = alimento.id_alimento;
  const [year, month, day] = alimento.fecha_ingreso.split("-");
  const fecha = new Date(year, month - 1, day);

  const fechaFormateada = new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(fecha);

  return `
    <tr>
      <td class="px-0">${alimento.nombre}</td>
      <td class="px-0">${alimento.cantidad}</td> 
      <td class="px-0">${fechaFormateada}</td>
      <td class="text-end justify-content-end gap-2">
          <button class="btn btn-sm btn-success btn-edit-alimento" data-alimento-id="${alimentoId}" aria-label="Editar"><i class="fa-regular fa-pen-to-square me-0"></i></button>
          ${
            alimento.cantidad > 0
              ? `
            <button class="btn btn-sm btn-success btn-consumo-alimento" data-alimento-id="${alimentoId}" data-alimento-nombre="${alimento.nombre}" data-alimento-cantidad="${alimento.cantidad}"><i class="fa-solid fa-utensils"></i></button>
          `
              : ""
          }
      </td>
    </tr>
  `;
}

//______________________________paginación para todos los datos y filtrados_____________

async function fetchAlimentos(
  page = 1,
  page_size = 10,
  fechaInicio = "",
  fechaFin = ""
) {
  try {
    let response;

    if (fechaInicio && fechaFin) {
      response = await alimentoService.getAlimentoAllDate(
        fechaInicio,
        fechaFin,
        page,
        page_size
      );
    } else {
      response = await alimentoService.getAlimentoAllPag(page, page_size);
    }

    // Validamos que la respuesta tenga datos
    if (!response || !response.alimento) {
      return {
        page: page,
        page_size: page_size,
        total_alimento: 0,
        total_pages: 1,
        alimento: [],
      };
    }

    return response;
  } catch (error) {
    console.error("Error en fetchAlimentos:", error);
    return {
      page: page,
      page_size: page_size,
      total_alimento: 0,
      total_pages: 1,
      alimento: [],
    };
  }
}

// Modificar la función init para que pase correctamente los filtros a la paginación
function renderPagination(total_pages, currentPage = 1) {
  const container = document.querySelector("#pagination");
  if (!container) return;

  container.innerHTML = "";

  // ---------- BOTÓN ANTERIOR ----------
  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage - 1
        }">
            <i class="fas fa-chevron-left"></i>
        </a>
    `;
  prevLi.addEventListener("click", () => {
    if (currentPage !== 1) {
      const prevPage = currentPage - 1;
      init(prevPage, 10, activeFechaInicio, activeFechaFin);
    }
  });
  container.appendChild(prevLi);

  const maxVisible = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  let endPage = Math.min(total_pages, startPage + maxVisible - 1);

  if (endPage - startPage + 1 < maxVisible) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  // ---------- PRIMERA PÁGINA + ... ----------
  if (startPage > 1) {
    container.appendChild(createPageLi(1, currentPage));
    if (startPage > 2) container.appendChild(createDotsLi());
  }

  // ---------- NÚMEROS DE PÁGINA ----------
  for (let i = startPage; i <= endPage; i++) {
    container.appendChild(createPageLi(i, currentPage));
  }

  // ---------- ... + ÚLTIMA PÁGINA ----------
  if (endPage < total_pages) {
    if (endPage < total_pages - 1) container.appendChild(createDotsLi());
    container.appendChild(createPageLi(total_pages, currentPage));
  }

  // ---------- BOTÓN SIGUIENTE ----------
  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${
    currentPage === total_pages ? "disabled" : ""
  }`;
  nextLi.innerHTML = `
        <a class="page-link text-success" href="#" data-page="${
          currentPage + 1
        }">
            <i class="fas fa-chevron-right"></i>
        </a>
    `;
  nextLi.addEventListener("click", () => {
    if (currentPage !== total_pages) {
      const nextPage = currentPage + 1;
      init(nextPage, 10, activeFechaInicio, activeFechaFin);
    }
  });
  container.appendChild(nextLi);
}

// ========== BOTÓN DE NÚMERO DE PÁGINA ==========
function createPageLi(page, currentPage) {
  const li = document.createElement("li");

  const isActive = page === currentPage;

  li.className = `page-item ${isActive ? "active" : ""}`;
  li.innerHTML = `
        <a class="page-link ${
          isActive ? "bg-success border-success text-white" : "text-success"
        }"
           href="#" data-page="${page}">
           ${page}
        </a>
    `;

  li.addEventListener("click", () => {
    if (!isActive) {
      init(page, 10, activeFechaInicio, activeFechaFin);
    }
  });

  return li;
}

// ========== PUNTOS SUSPENSIVOS ==========
function createDotsLi() {
  const li = document.createElement("li");
  li.className = "page-item disabled";
  li.innerHTML = `<a class="page-link text-success">...</a>`;
  return li;
}

//______________________ para filtrar por fechas_______________________________________
function inicializarFiltroFechas() {
  const btnApplyFilter = document.getElementById("btn-apply-date-filter");
  const btnClear = document.getElementById("btn_clear_filters");

  if (btnApplyFilter) {
    // Remover listeners anteriores
    btnApplyFilter.replaceWith(btnApplyFilter.cloneNode(true));
    const nuevoBtn = document.getElementById("btn-apply-date-filter");

    nuevoBtn.addEventListener("click", () => {
      const fechaInicio = document.getElementById("fecha-inicio").value;
      const fechaFin = document.getElementById("fecha-fin").value;
      filtrarAlimentos(fechaInicio, fechaFin);
    });
  }

  if (btnClear) {
    btnClear.replaceWith(btnClear.cloneNode(true));
    const nuevoBtnClear = document.getElementById("btn_clear_filters");

    nuevoBtnClear.addEventListener("click", limpiarFiltros);
  }
}

function filtrarAlimentos(fechaInicio, fechaFin) {
  if (!fechaInicio || !fechaFin) {
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "Debe seleccionar ambas fechas",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    return;
  }

  // Guardar fechas para usar en fetchAlimentos
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  // Recargar la tabla desde la página 1 con el filtro
  init(1, 10);
}

//___________para abrir el modal de edit_________________________________________
async function openEditModal(id_alimento) {
  const modalElement = document.getElementById("edit-alimento-modal");
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const alimento = await alimentoService.getAlimentoById(id_alimento);

    // Guardar el ID oculto
    document.getElementById("edit-alimento-id").value = alimento.id_alimento;

    // Poner los valores en los inputs
    document.getElementById("edit-nombre_alimento").value = alimento.nombre;
    document.getElementById("edit-cantidad_alimento").value = alimento.cantidad;

    modalInstance.show();
  } catch (error) {
    console.error("Error en openEditModal:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos del alimento.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function handleTableClick(event) {
  // Manejador para el botón de editar
  const editButton = event.target.closest(".btn-edit-alimento");
  if (editButton) {
    const idAlimento = editButton.dataset.alimentoId;
    openEditModal(idAlimento);
    return;
  }
  //  Manejador de eventos para el boton consumo
  const consumoButton = event.target.closest(".btn-consumo-alimento");
  if (consumoButton) {
    const alimentoId = consumoButton.dataset.alimentoId;
    const alimentoNombre = consumoButton.dataset.alimentoNombre;
    const alimentoCantidad = consumoButton.dataset.alimentoCantidad;

    await openConsumoModal(alimentoId, alimentoNombre, alimentoCantidad);
    return;
  }
}

// --- MANEJADORES DE EVENTOS ---
async function handleUpdateSubmit(event) {
  event.preventDefault();

  const alimentosId = document.getElementById("edit-alimento-id").value;
  const updatedData = {
    nombre: document.getElementById("edit-nombre_alimento").value.trim(), // texto del input
    cantidad: parseFloat(
      document.getElementById("edit-cantidad_alimento").value
    ), // número
  };

  try {
    await alimentoService.updateAlimento(alimentosId, updatedData);
    modalInstance.hide();
    init(); // recarga la tabla
    Swal.fire({
      icon: "success",
      title: "Actualizado",
      text: "El alimento se actualizó correctamente",
      timer: 2000,
      showConfirmButton: false,
    });
  } catch (error) {
    console.error("Error actualizando alimento:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudo actualizar el alimento.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

// ----- FUNCIONES DE CONSUMOS -----

async function openConsumoModal(alimentoId, alimentoNombre, alimentoCantidad) {
  try {
    // Llenar los campos del modal
    document.getElementById("consumo-id-alimento").value = alimentoId;
    document.getElementById("consumo-alimento-display").value = alimentoNombre;
    document.getElementById("consumo-cantidad-alimento").value = "";
    document.getElementById("consumo-cantidad-alimento").max = alimentoCantidad;

    // Mostrar cantidad disponible
    const maxText = document.getElementById("consumo-cantidad-max-text");
    if (maxText) {
      maxText.textContent = `Cantidad disponible: ${alimentoCantidad} Kg`;
    }

    // Llenar select de galpones (necesitarás cargarlos)
    await cargarGalponesParaConsumo();

    // Establecer fecha actual por defecto
    const today = new Date().toLocaleDateString("en-CA");
    document.getElementById("consumo-fecha").value = today;

    // Mostrar el modal
    const modalElement = document.getElementById(
      "createConsumoFromAlimentoModal"
    );
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  } catch (error) {
    console.error(
      `Error al abrir modal de consumo para alimento ${alimentoId}:`,
      error
    );
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "No se pudieron cargar los datos para el consumo.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}

async function cargarGalponesParaConsumo() {
  try {
    // Necesitarás importar o tener acceso al servicio de galpones
    const shedsService = await import("../api/shed.service.js");
    const galpones = await shedsService.shedsService.getSheds();

    const galponesActivos = galpones.filter((g) => g.estado === true);
    const selectGalpon = document.getElementById("consumo-id-galpon");

    if (selectGalpon) {
      selectGalpon.innerHTML =
        `<option value="" disabled selected>Seleccione un galpón</option>` +
        galponesActivos
          .map((g) => `<option value="${g.id_galpon}">${g.nombre}</option>`)
          .join("");
    }
  } catch (error) {
    console.error("Error cargando galpones:", error);
    const selectGalpon = document.getElementById("consumo-id-galpon");
    if (selectGalpon) {
      selectGalpon.innerHTML = `<option value="">Error al cargar galpones</option>`;
    }
  }
}

async function handleConsumoSubmit(event) {
  event.preventDefault();

  const consumoData = {
    id_alimento: parseInt(document.getElementById("consumo-id-alimento").value),
    id_galpon: parseInt(document.getElementById("consumo-id-galpon").value),
    cantidad_alimento: parseFloat(
      document.getElementById("consumo-cantidad-alimento").value
    ),
    fecha_registro: document.getElementById("consumo-fecha").value,
  };

  const alimentoNombre = document.getElementById(
    "consumo-alimento-display"
  ).value;
  const galponSelect = document.getElementById("consumo-id-galpon");
  const galponNombre = galponSelect.options[galponSelect.selectedIndex].text;

  // Validaciones
  if (!consumoData.cantidad_alimento || consumoData.cantidad_alimento <= 0) {
    Swal.fire({
      icon: "warning",
      title: "Cantidad inválida",
      text: "Por favor ingrese una cantidad válida.",
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
    return;
  }

  try {
    const createdConsumo = await consumoService.createConsumo(consumoData);

    const modalElement = document.getElementById(
      "createConsumoFromAlimentoModal"
    );
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();

    const result = await Swal.fire({
      title: "¡Consumo Registrado Exitosamente!",
      html: `
                <div class="text-start">
                    <div class="alert alert-success border-success bg-success bg-opacity-10">
                        <div class="d-flex align-items-center">
                            <i class="fa-solid fa-circle-check text-success me-2"></i>
                            <strong>El consumo se ha registrado exitosamente</strong>
                        </div>
                    </div>
                    
                    <div class="border rounded p-3 bg-light mt-3">
                        <h6 class="text-success mb-3">
                            <i class="fa-solid fa-utensils me-2"></i>Detalles del Consumo
                        </h6>
                        
                        <div class="row">
                            <div class="col-6">
                                <p class="mb-2"><strong><i class="fa-solid fa-wheat-awn me-1 text-muted"></i> Alimento:</strong></p>
                                <p class="mb-2"><strong><i class="fa-solid fa-warehouse me-1 text-muted"></i> Galpón:</strong></p>
                                <p class="mb-2"><strong><i class="fa-solid fa-weight me-1 text-muted"></i> Cantidad:</strong></p>
                                <p class="mb-0"><strong><i class="fa-solid fa-calendar me-1 text-muted"></i> Fecha:</strong></p>
                            </div>
                            <div class="col-6">
                                <p class="mb-2">${alimentoNombre}</p>
                                <p class="mb-2">${galponNombre}</p>
                                <p class="mb-2">${consumoData.cantidad_alimento} Kg</p>
                                <p class="mb-0">${consumoData.fecha_registro}</p>
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
      confirmButtonText: '<i class="fa-solid fa-list me-2"></i> Ir a Consumos',
      cancelButtonText:
        '<i class="fa-solid fa-wheat-awn me-2"></i> Seguir en Alimentos',
      reverseButtons: true,
      width: "600px",
      customClass: {
        popup: "border-success",
        confirmButton: "btn-success",
        cancelButton: "btn-secondary",
      },
    });

    if (result.isConfirmed) {
      // Cargar la página de consumos
      const btnConsumo = document.getElementById("consumo_alimento");
      if (btnConsumo) {
        btnConsumo.click();
      }
    } else {
      // Recargar la página de alimentos
      init(1, 10, activeFechaInicio, activeFechaFin);
    }
  } catch (error) {
    console.error("Error al crear el consumo:", error);
    Swal.fire({
      icon: "error",
      title: "Error al registrar consumo",
      html: `
                <div class="text-start">
                    <p>No se pudo registrar el consumo:</p>
                    <div class="alert alert-danger mt-2">
                        <strong>Error:</strong> ${
                          error.message || "Error desconocido"
                        }
                    </div>
                </div>
            `,
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

  const newAlimentoData = {
    nombre: document.getElementById("create-nombre_alimento").value,
    cantidad: parseInt(
      document.getElementById("create-cantidad_alimento").value
    ),
    fecha_ingreso: fechaPC,
  };

  try {
    await alimentoService.createAlimento(newAlimentoData);

    const createAlimento_modal = document.getElementById(
      "create-alimento-modal"
    );
    let createAlimentoModalInstance =
      bootstrap.Modal.getInstance(createAlimento_modal);
    if (!createAlimentoModalInstance) {
      createAlimentoModalInstance = new bootstrap.Modal(createAlimento_modal);
    }
    createAlimentoModalInstance.hide();

    createAlimento_modal.addEventListener(
      "hidden.bs.modal",
      function handler() {
        createAlimento_modal.removeEventListener("hidden.bs.modal", handler);
        document.getElementById("create-alimento-form").reset();

        Swal.fire({
          icon: "success",
          title: "¡Guardado!",
          text: "Alimento creado correctamente.",
          confirmButtonText: "OK",
          customClass: {
            confirmButton: "btn btn-success",
          },
          buttonsStyling: false,
        });

        // 🔹 Recargar la tabla para que aparezca el nuevo alimento
        init(1, 10, activeFechaInicio, activeFechaFin);
      }
    );
  } catch (error) {
    console.error("Error al crear alimento:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text:
        "Error al crear el alimento: " + (error.message || "Error desconocido"),
      confirmButtonText: "OK",
      customClass: {
        confirmButton: "btn btn-success",
      },
      buttonsStyling: false,
    });
  }
}
//____________________________________buscador inteligente____________________________________
function inicializarBuscador() {
  const BuscarAimento = document.getElementById("search-alimentos");

  if (BuscarAimento) {
    // Remover event listener anterior si existe
    BuscarAimento.replaceWith(BuscarAimento.cloneNode(true));
    const nuevoInput = document.getElementById("search-alimentos");

    nuevoInput.addEventListener("input", () => {
      const filter = nuevoInput.value.toLowerCase();
      const tableBody = document.getElementById("alimentos-table-body");
      if (!tableBody) return;

      const rows = tableBody.querySelectorAll("tr");
      rows.forEach((row) => {
        const idCell = row.cells[0]?.textContent.toLowerCase() || "";
        const fechaCell = row.cells[1]?.textContent.toLowerCase() || "";
        const galponCell = row.cells[2]?.textContent.toLowerCase() || "";
        row.style.display =
          idCell.includes(filter) ||
          fechaCell.includes(filter) ||
          galponCell.includes(filter)
            ? ""
            : "none";
      });
    });
  }
}

//_______________________________ limpiador de filtros__________________________________________
function limpiarFiltros() {
  activeFechaInicio = "";
  activeFechaFin = "";
  document.getElementById("fecha-inicio").value = "";
  document.getElementById("fecha-fin").value = "";
  const searchInput = document.getElementById("search-alimentos");
  if (searchInput) searchInput.value = "";
  init(1, 10);
}
//_____________________________________________________________________________________________

async function init(
  page = 1,
  page_size = 10,
  fechaInicio = activeFechaInicio,
  fechaFin = activeFechaFin
) {
  activeFechaInicio = fechaInicio;
  activeFechaFin = fechaFin;

  const tableBody = document.getElementById("alimentos-table-body");
  if (!tableBody) {
    return;
  }

  tableBody.innerHTML =
    '<tr><td colspan="7" class="text-center">Cargando alimentos...</td></tr>';

  try {
    const data = await fetchAlimentos(
      page,
      page_size,
      activeFechaInicio,
      activeFechaFin
    );
    const alimentos = data.alimento || [];

    if (alimentos.length > 0) {
      tableBody.innerHTML = alimentos.map(createAlimentosRow).join("");
    } else {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="text-center">No se encontraron alimentos.</td></tr>';

      if (activeFechaInicio && activeFechaFin) {
        tableBody.innerHTML = `
              <tr>
                <td colspan="7" class="text-center">
                  <div class="alert alert-info mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No se encontraron alimentos en el rango de fechas:<br>
                    <strong>${activeFechaInicio} a ${activeFechaFin}</strong>
                  </div>
                </td>
              </tr>
            `;
      } else {
        tableBody.innerHTML =
          '<tr><td colspan="7" class="text-center">No se encontraron alimentos.</td></tr>';
      }
    }

    renderPagination(data.total_pages || 1, page);

    // Inicializar event listeners de la tabla
    const editForm = document.getElementById("edit-alimento-form");
    const createForm = document.getElementById("create-alimento-form");
    tableBody.removeEventListener("click", handleTableClick);
    tableBody.addEventListener("click", handleTableClick);
    editForm.removeEventListener("submit", handleUpdateSubmit);
    editForm.addEventListener("submit", handleUpdateSubmit);
    tableBody.addEventListener("click", handleTableClick);
    createForm.removeEventListener("submit", handleCreateSubmit);
    createForm.addEventListener("submit", handleCreateSubmit);
    // Event listener de consumo
    const consumoForm = document.getElementById(
      "create-consumo-from-alimento-form"
    );
    if (consumoForm) {
      consumoForm.removeEventListener("submit", handleConsumoSubmit);
      consumoForm.addEventListener("submit", handleConsumoSubmit);
    }

    inicializarBuscador();
    inicializarFiltroFechas();
  } catch (error) {
    console.error("Error al cargar alimentos:", error);
    tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error al cargar los datos.</td></tr>`;
  }
}

//____________________formato_para_exportar_por_fechas______________________________

function formatDateForAPI(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}







// Descarga todas las páginas para exportar el listado completo
async function fetchTodosAlimentos(fechaInicio = "", fechaFin = "") {
  let page = 1;
  let totalPages = 1;
  let todos = [];
  do {
    const r = await fetchAlimentos(page, 100, fechaInicio, fechaFin);
    todos = todos.concat(r?.alimento || []);
    totalPages = r?.total_pages || 1;
    page++;
  } while (page <= totalPages && page <= 200);
  return todos;
}

// =======================
// EXPORTACIÓN (utilidades compartidas en ../utils/exportar.js)
// =======================
const COLUMNAS_EXPORTACION = [
  { header: "Id", key: "id_alimento" },
  { header: "Nombre alimento", key: "nombre" },
  { header: "Cantidad (Kg)", key: "cantidad" },
  { header: "Fecha ingreso", key: "fecha_ingreso" },
];

function exportToCSV(data, filename) {
  exportarCSV(data, COLUMNAS_EXPORTACION, filename);
}

async function exportToExcel(data, filename) {
  await exportarExcel(data, COLUMNAS_EXPORTACION, filename, "Alimentos");
}

async function exportToPDF(data, filename) {
  await exportarPDF(data, COLUMNAS_EXPORTACION, filename, "Reporte de Alimentos");
}

async function handleExportClick(event) {
  const item = event.target.closest(".export-format");
  if (!item) return;
  // Solo responder si la página visible es la de alimentos
  if (window.currentPage !== "alimentos") return;

  event.preventDefault();

  const fmt = item.dataset.format;
  const dateTag = new Date().toISOString().slice(0, 10);

  let data;

  if (!activeFechaInicio || !activeFechaFin) {
    data = await fetchTodosAlimentos();
  } else {
    const fechaInicio = formatDateForAPI(activeFechaInicio);
    const fechaFin = formatDateForAPI(activeFechaFin);
    data = await fetchTodosAlimentos(fechaInicio, fechaFin);
  }

  if (data.length === 0) {
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
    exportToCSV(data, `alimentos_${dateTag}.csv`);
  } else if (fmt === "excel") {
    exportToExcel(data, `alimentos_${dateTag}.xlsx`);
  } else if (fmt === "pdf") {
    exportToPDF(data, `alimentos_${dateTag}.pdf`);
  }
}

function inicializarExportacion() {
  document.addEventListener("click", (e) => {
    const item = e.target.closest(".export-format");
    if (!item) return;
    handleExportClick(e);
  });
}

inicializarExportacion();

export { init };
