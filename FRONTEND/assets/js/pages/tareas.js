// pages/tareas.js
// Importamos lo que se comunica con la API de tareas
import { tareaService } from "../api/tareas.service.js";
import { userService } from "../api/user.service.js";

import { exportarCSV } from "../utils/exportar.js";
// Instancias de modales
let createModalInst = null;
let editModalInst = null;

// Caché de tareas
let cachedTareas = [];
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;

// Obtener usuario desde localStorage
function getCurrentUser() {
  const s = localStorage.getItem("user");
  if (!s) return null;
  try {
    return JSON.parse(s);
  } catch (err) {
    console.error("Error parseando user desde localStorage:", err);
    return null;
  }
}

// Convierte fecha a formato aceptado por datetime-local
function formatDateInputToLocalDatetime(value) {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d)) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

// Convierte fecha a formato bonito con toLocaleString
function formatDateDisplay(value) {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d)) return value;
  return d.toLocaleString("es-CO");
}

/* ---------------------------------------------------
   FILA DE TABLA (AQUÍ SE HICIERON LOS CAMBIOS DE ESTILOS)
--------------------------------------------------- */
function createTareaRow(t) {
  return `
    <tr data-id_tarea="${t.id_tarea}">
      <td class="cell desaparecer">${t.id_tarea}</td>
      <td class="cell desaparecer">${t.documento}</td>
      <td class="cell desaparecer">${t.nombre_usuario}</td>
      <td class="cell">${t.descripcion}</td>
      <td class="cell">${formatDateDisplay(t.fecha_hora_init)}</td>
      <td class="cell">${
        t.fecha_hora_fin ? formatDateDisplay(t.fecha_hora_fin) : "-"
      }</td>
      <td class="cell">
        <span class="app-badge app-badge-secondary">${t.estado}</span>
      </td>
      <td class="cell text-end">
        <button 
          class="btn btn-success btn-sm btn-edit"
          data-id="${t.id_tarea}"
          title="Editar">
          <i class="fa-regular fa-pen-to-square"></i>
        </button>
      </td>
    </tr>
  `;
}
// selects tareas

async function loadUsuariosSelects() {
  const user = getCurrentUser();
  if (!user || user.id_rol === 4) return;

  try {
    const usuarios = await userService.getUsers();
    if (!Array.isArray(usuarios)) return;

    const createSelect = document.getElementById("create-id_usuario");
    const editSelect = document.getElementById("edit-id_usuario");

    const optionsHtml = usuarios
      .map(
        (u) => `
      <option value="${u.id_usuario}">
        ${u.nombre} - ${u.documento}
      </option>
    `
      )
      .join("");

    if (createSelect) {
      createSelect.innerHTML = `
        <option value="">Seleccione un usuario</option>
        ${optionsHtml}
      `;
    }

    if (editSelect) {
      editSelect.innerHTML = `
        <option value="">Seleccione un usuario</option>
        ${optionsHtml}
      `;
    }
  } catch (error) {
    console.error("Error cargando usuarios:", error);
  }
}

/* ---------------------------------------------------
   CARGAR LISTADO DE TAREAS
--------------------------------------------------- */
async function loadPage(page = 1) {
  currentPage = page;

  const tbody = document.getElementById("tareas-table-body");
  if (!tbody) {
    console.error("No se encontró #tareas-table-body en el DOM.");
    return;
  }

  tbody.innerHTML = `<tr><td colspan="7" class="text-center">Cargando...</td></tr>`;

  const user = getCurrentUser();
  if (!user) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Usuario no autenticado.</td></tr>`;
    return;
  }

  // Filtros
  const estadoEl = document.getElementById("filter-estado");
  const fechaIniEl = document.getElementById("filter-fecha-inicio");
  const fechaFinEl = document.getElementById("filter-fecha-fin");
  const searchEl = document.getElementById("search-input");

  const estadoFilter = estadoEl ? estadoEl.value : "all";
  const fechaInicio = fechaIniEl ? fechaIniEl.value || null : null;
  const fechaFin = fechaFinEl ? fechaFinEl.value || null : null;
  const search = searchEl ? (searchEl.value || "").toLowerCase() : "";

  try {
    let responseData = null;

    // Si es operario (rol 4), solo ver sus tareas
    if (user.id_rol === 4) {
      const tareas = await tareaService.getByUser(user.id_usuario);
      const arr = Array.isArray(tareas) ? tareas : [];
      responseData = {
        page,
        page_size: arr.length,
        total_tareas: arr.length,
        total_pages: 1,
        tareas: arr,
      };
    } else {
      // Si no es operario → paginación normal y filtro desde backend
      const pagResp = await tareaService.getPaginated({
        page,
        page_size: pageSize,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin: fechaFin || undefined,
      });

      responseData = pagResp || { tareas: [], total_tareas: 0, total_pages: 1 };
    }

    const tareasList = responseData.tareas || [];
    cachedTareas = tareasList;

    /* FILTROS EN CLIENTE */
    let filtered = tareasList;

    if (estadoFilter && estadoFilter !== "all") {
      filtered = filtered.filter(
        (t) => String(t.estado) === String(estadoFilter)
      );
    }

    if (search) {
      filtered = filtered.filter(
        (t) => t.descripcion && t.descripcion.toLowerCase().includes(search)
      );
    }

    /* PAGINACIÓN CLIENTE SI ES OPERARIO */
    let displayed = filtered;

    if (user.id_rol === 4) {
      totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      const start = (page - 1) * pageSize;
      displayed = filtered.slice(start, start + pageSize);
    } else {
      totalPages = responseData.total_pages || 1;
    }

    /* LISTA FINAL */
    if (!displayed || displayed.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">No se encontraron tareas.</td></tr>`;
    } else {
      tbody.innerHTML = displayed.map(createTareaRow).join("");
    }

    renderPagination(currentPage, totalPages);
    applyUiPermissions(user);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error al cargar tareas.</td></tr>`;
  }
}

/* ---------------------------------------------------
   PAGINACIÓN (clases ya son las correctas)
--------------------------------------------------- */
function renderPagination(currentPage, totalPages) {
  const list = document.getElementById("pagination-list");
  if (!list) return;

  list.innerHTML = "";

  // Crear <li>
  const createLi = (content, disabled = false) => {
    const li = document.createElement("li");
    li.className = `page-item ${disabled ? "disabled" : ""}`;
    li.innerHTML = content;
    return li;
  };

  // Botón ANTERIOR
  const prevDisabled = currentPage === 1;
  const prevLi = createLi(
    `
        <a class="page-link text-success" href="#" data-page="${
          currentPage - 1
        }">
            <i class="fas fa-chevron-left"></i>
        </a>
    `,
    prevDisabled
  );

  list.appendChild(prevLi);

  // Botones numéricos
  for (let i = 1; i <= totalPages; i++) {
    const isActive = i === currentPage;

    const pageLi = createLi(`
            <a class="page-link ${
              isActive ? "bg-success border-success text-white" : "text-success"
            }" 
            href="#" data-page="${i}">
                ${i}
            </a>
        `);

    list.appendChild(pageLi);
  }

  // Botón SIGUIENTE
  const nextDisabled = currentPage === totalPages;
  const nextLi = createLi(
    `
        <a class="page-link text-success" href="#" data-page="${
          currentPage + 1
        }">
            <i class="fas fa-chevron-right"></i>
        </a>
    `,
    nextDisabled
  );

  list.appendChild(nextLi);
}

/* ---------------------------------------------------
   PERMISOS UI
--------------------------------------------------- */
function applyUiPermissions(user) {
  const btnCreate = document.getElementById("btn-open-create-user");

  if (!btnCreate) return;
  // if (!desaparecerElements) return;

  if (user.id_rol === 4) {
    btnCreate.style.display = "none";
    // desaparecerElements.style.display = "none";
  } else {
    btnCreate.style.display = "inline-block";
    // desaparecerElements.style.display = "table-cell";
  }
  const desaparecerElements =
    user.id_rol === 4 ? document.querySelectorAll(".desaparecer") : [];
  desaparecerElements.forEach((el) => {
    el.style.display = user.id_rol === 4 ? "none" : "table-cell";
  });

  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.style.display = "inline-block";
  });
}

/* ---------------------------------------------------
   EVENTOS
--------------------------------------------------- */
function handleTableClick(e) {
  const btn = e.target.closest ? e.target.closest(".btn-edit") : null;
  if (!btn) return;
  const id = btn.dataset.id;
  openEditModalFromCache(parseInt(id, 10));
}

function handlePaginationClick(e) {
  e.preventDefault();
  const a = e.target.closest ? e.target.closest("a[data-page]") : null;
  if (!a) return;
  const p = parseInt(a.dataset.page, 10);
  if (!isNaN(p)) loadPage(p);
}

function handleFilterChange() {
  loadPage(1);
}

function handleSearchInput() {
  loadPage(1);
}

/* ---------------------------------------------------
   MODALES (sin cambios de estilos)
--------------------------------------------------- */
function initModals() {
  try {
    const createEl = document.getElementById("create-tarea-modal");
    const editEl = document.getElementById("edit-tarea-modal");

    if (createEl) createModalInst = new bootstrap.Modal(createEl);
    if (editEl) editModalInst = new bootstrap.Modal(editEl);

    const btnOpen = document.getElementById("btn-open-create");
    if (btnOpen) {
      btnOpen.addEventListener("click", () => {
        if (createModalInst) createModalInst.show();
      });
    }

    const createForm = document.getElementById("create-tarea-form");
    if (createForm) {
      createForm.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          const newData = {
            id_usuario: parseInt(
              document.getElementById("create-id_usuario").value,
              10
            ),
            descripcion: document.getElementById("create-descripcion").value,
            fecha_hora_init: document.getElementById("create-fecha_hora_init").value,
            fecha_hora_fin: document.getElementById("create-fecha_hora_fin").value,
            estado: document.getElementById("create-estado").value,
          };
          await tareaService.create(newData);
          if (createModalInst) createModalInst.hide();
          createForm.reset();
          loadPage(1);
          Swal.fire({
            position: "top-end",
            icon: "success",
            title: "Tarea creada exitosamente",
            showConfirmButton: false,
            timer: 1500,
          });
        } catch (err) {
          Swal.fire({
            icon: "error",
            title: "Oops...",
            text: "Error al crear la tarea!",
          });
        }
      });
    }

    const editForm = document.getElementById("edit-tarea-form");
    if (editForm) {
      editForm.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          const id = document.getElementById("edit-id_tarea").value;

          const data = {
            fecha_hora_fin: document.getElementById("edit-fecha_hora_fin").value, 
            estado: document.getElementById("edit-estado").value,
          };

          if (getCurrentUser().id_rol !== 4) {
            data.id_usuario = parseInt(document.getElementById("edit-id_usuario").value, 10)
            data.descripcion = document.getElementById("edit-descripcion").value,
            data.fecha_hora_init = document.getElementById("edit-fecha_hora_init").value;
          }
          await tareaService.updateById(id, data);
          if (editModalInst) editModalInst.hide();
          loadPage(currentPage);
          Swal.fire({
            title: "Tarea actualizada exitosamente!",
            icon: "success",
            confirmButtonColor: "#28A745",
          });
        } catch (err) {
          Swal.fire({
            icon: "error",
            title: "Oops...",
            text: "No se pudo actualizar la tarea!",
          });
        }
      });
    }
  } catch (err) {}
}

/* ---------------------------------------------------
   EDITAR DESDE CACHÉ
--------------------------------------------------- */
function openEditModalFromCache(id_tarea) {
  const t = cachedTareas.find((x) => x.id_tarea === id_tarea);
  if (!t) return Swal.fire("No se encontró la tarea.");

  const user = getCurrentUser();
  const eliminarCabeceraIdUsuario = document.getElementById('id_usuario_modal'); 


  document.getElementById("edit-id_tarea").value = t.id_tarea;
  document.getElementById("edit-id_usuario").style.display = "inline-block"; // ya está disabled
  document.getElementById("edit-descripcion").value = t.descripcion;
  document.getElementById("edit-fecha_hora_init").value =
    formatDateInputToLocalDatetime(t.fecha_hora_init);
  document.getElementById("edit-fecha_hora_fin").value = t.fecha_hora_fin
    ? formatDateInputToLocalDatetime(t.fecha_hora_fin)
    : "";

  document.getElementById("edit-estado").value = t.estado;

  if (user.id_rol === 4) {
    eliminarCabeceraIdUsuario.classList.add('d-none'); 
    document.getElementById("edit-id_usuario").style.display = "none";
    document.getElementById("edit-descripcion").disabled = true;
    document.getElementById("edit-fecha_hora_init").disabled = true;
    document.getElementById("edit-fecha_hora_fin").disabled = false;
    document.getElementById("edit-estado").disabled = false;
  } else {
    document.getElementById("edit-id_usuario").disabled = false;
    document.getElementById("edit-descripcion").disabled = false;
    document.getElementById("edit-fecha_hora_init").disabled = false;
    document.getElementById("edit-fecha_hora_fin").disabled = false;
    document.getElementById("edit-estado").disabled = false;
  }

  if (editModalInst) editModalInst.show();
}

/* ---------------------------------------------------
  EXPORTAR CSV
--------------------------------------------------- */
const COLUMNAS_EXPORTACION = [
  { header: "ID", key: "id_tarea" },
  { header: "Usuario", key: (r) => r.nombre_usuario || r.id_usuario },
  { header: "Descripción", key: "descripcion" },
  { header: "Inicio", key: "fecha_hora_init" },
  { header: "Fin", key: "fecha_hora_fin" },
  { header: "Estado", key: "estado" },
];

function exportToCsv(rows, filename = "tareas.csv") {
  if (!rows || rows.length === 0)
    return Swal.fire({ title: "No hay datos para exportar.", icon: "info" });
  exportarCSV(rows, COLUMNAS_EXPORTACION, filename);
}


/* ---------------------------------------------------
  INIT
--------------------------------------------------- */
function attachEvents() {
  const pagList = document.getElementById("pagination-list");
  if (pagList) pagList.addEventListener("click", handlePaginationClick);

  const estadoEl = document.getElementById("filter-estado");
  if (estadoEl) estadoEl.addEventListener("change", handleFilterChange);

  const fi = document.getElementById("filter-fecha-inicio");
  if (fi) fi.addEventListener("change", handleFilterChange);

  const ff = document.getElementById("filter-fecha-fin");
  if (ff) ff.addEventListener("change", handleFilterChange);

  const search = document.getElementById("search-input");
  if (search)
    search.addEventListener("input", debounce(handleSearchInput, 300));

  const tbody = document.getElementById("tareas-table-body");
  if (tbody) tbody.addEventListener("click", handleTableClick);

  const exportBtn = document.getElementById("export-csv-btn");
  if (exportBtn)
    exportBtn.addEventListener("click", () => {
      exportToCsv(cachedTareas, `tareas_page${currentPage}.csv`);
    });
}

export function init() {
  initModals();
  attachEvents();
  const user = getCurrentUser();
  if (user && user.id_rol !== 4) {
    loadUsuariosSelects();
  }
  // <-- Nuevo
  loadPage(1);
}

/* ---------------------------------------------------
 UTIL
--------------------------------------------------- */
function debounce(fn, ms = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
