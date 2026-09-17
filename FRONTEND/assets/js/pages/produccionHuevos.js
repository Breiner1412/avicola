import { produccionHuevosService } from '../api/produccionHuevos.service.js';

let modalInstance = null; // Guardará la instancia del modal
let originalFecha = null;



// --- VARIABLES DE PAGINACIÓN ---
let currentPage = 1;
let limit = 10;
let fechaInicioGlobal = null;
let fechaFinGlobal = null;

// --- FUNCIONES AUXILIARES ---

function createProduccionRow(produccion) {
  const idRol = JSON.parse(localStorage.getItem('user'))?.id_rol;
  
  const tabla = `
    <tr>
      <td>${produccion.nombre_galpon}</td>
      <td>${produccion.cantidad || 'Sin Cantidad'}</td>
      <td>${produccion.fecha}</td>
      <td>${produccion.tamaño}</td>
      <td class="text-end">
        <button class="btn btn-sm btn-success btn-edit-produccion text-black" data-produccion-id="${produccion.id_produccion}">
          <i class="fa-regular fa-pen-to-square"></i>
        </button>
        ${idRol === 1 || idRol === 2 ? `
          <button class="btn btn-sm btn-secondary btn-eliminar-produccion" data-produccion-id="${produccion.id_produccion}">
            <i class="fa-regular fa-trash-can"></i>
          </button>
        ` : ''}
      </td>
    </tr>
  `;
  
  return tabla;
}

// --- MODAL DE EDICIÓN ---

async function openEditModal(produccionId) {
  const modalElement = document.getElementById('edit-produccion-modal');
  if (!modalInstance) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  try {
    const produccion = await produccionHuevosService.GetProduccionHuevosById(produccionId);

    originalFecha = produccion.fecha; // Guardamos la fecha original

    const inputFecha = document.getElementById('edit-fecha');

    document.getElementById('edit-produccion-id').value = produccion.id_produccion;
    // document.querySelector('.optionAnteriorG').textContent = produccion.nombre_galpon;

    document.getElementById('edit-cantidad').value = produccion.cantidad;
    document.getElementById('edit-tamaño').value = produccion.id_tipo_huevo;
    document.getElementById('edit-produccion-nombre').value = produccion.id_galpon;
    // document.querySelector('.optionAnteriorT').textContent = produccion.tamaño;

    // --- VALIDACIÓN DE FECHA ---
    inputFecha.value = produccion.fecha;
    inputFecha.max = produccion.fecha; // No permite fechas anteriores

    // Opcional: mostrar alerta si se intenta cambiar por debajo del mínimo
    inputFecha.addEventListener('input', () => {
      if (inputFecha.value > inputFecha.max) {
        inputFecha.value = inputFecha.max;
      }
    });

    modalInstance.show();
  } catch (error) {
    console.error("Error:", error);

    Swal.fire({
      icon: "error",
      title: "Error al cargar datos",
      text: "No se pudieron cargar los datos de la producción.",
      confirmButtonText: "Aceptar",
      customClass: {
        confirmButton: "btn btn-danger"
      },
      buttonsStyling: false
    }).then(() => {
      // 🔵 CERRAR MODAL DESPUÉS DEL SWEETALERT
      const modal = bootstrap.Modal.getInstance(modalElement);
      if (modal) modal.hide();
    });
  }
}


// --- ENVÍO DEL FORMULARIO DE ACTUALIZACIÓN ---

async function handleUpdateSubmit(event) {
  event.preventDefault();

  const produccionId = document.getElementById('edit-produccion-id').value;
  const updatedData = {
    fecha: document.getElementById('edit-fecha').value,
    cantidad: parseInt(document.getElementById('edit-cantidad').value),
    id_tipo_huevo: parseInt(document.getElementById('edit-tamaño').value),
    id_galpon: parseInt(document.getElementById('edit-produccion-nombre').value)
  };

  try {
    await produccionHuevosService.UpdateProduccionHuevos(produccionId, updatedData);
    modalInstance.hide();
    init();
    
      Swal.fire({
      icon: "success",
      title: "¡Actualizado!",
      text: "La producción se actualizó correctamente.",
      confirmButtonText: "Aceptar",
      customClass: {
        confirmButton: "btn btn-success"
      },
      buttonsStyling: false
    });// recarga la tabla
  } catch (error) {
    console.error("Error:", error);

    // 🔴 SWEETALERT DE ERROR
    Swal.fire({
      icon: "error",
      title: "Error al actualizar",
      text: "No se pudo actualizar la producción.",
      confirmButtonText: "Aceptar",
      customClass: {
        confirmButton: "btn btn-danger"
      },
      buttonsStyling: false
    });
  }
}

// --- CREAR NUEVA PRODUCCIÓN ---
async function handleCreateSubmit(event) {
  event.preventDefault();

  const newData = {
    id_galpon: parseInt(document.getElementById('create-id-galpon').value),
    cantidad: parseInt(document.getElementById('create-cantidad').value),
    fecha: document.getElementById('create-fecha').value,
    id_tipo_huevo: parseInt(document.getElementById('create-id-tipo-huevo').value)
  };
try {
    await produccionHuevosService.CreateProduccionHuevos(newData);

    // 🔵 SWEETALERT DE ÉXITO
    await Swal.fire({
      icon: "success",
      title: "Producción registrada!",
      text: "La nueva producción fue guardada correctamente.",
      timer: 1500,
      showConfirmButton: false
    });

    // ✅ CERRAR EL MODAL LUEGO DEL SWEETALERT
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("create-produccion-modal")
    );
    modal.hide();

    // Limpiar el formulario y recargar
    event.target.reset();
    init();

  } catch (error) {
    console.error("Error:", error);

    // 🔴 SWEETALERT DE ERROR
    Swal.fire({
      icon: "error",
      title: "Error al registrar",
      text: "No se pudo crear la producción.",
      confirmButtonText: "Aceptar",
      customClass: {
        confirmButton: "btn btn-danger"
      },
      buttonsStyling: false
    });
  }
}

// --- CLICK EN LA TABLA (para editar) ---

async function handleTableClick(event) {
  const editButton = event.target.closest('.btn-edit-produccion');
  if (editButton) {
    const produccionId = editButton.dataset.produccionId;
    openEditModal(produccionId);
  }

   const deleteButton = event.target.closest('.btn-eliminar-produccion');
  if (deleteButton) {
    const produccionId = deleteButton.dataset.produccionId;
    eliminarProduccion(produccionId); // ← AQUÍ SE CONECTA
    return;
  }
}

// --- FUNCIÓN PRINCIPAL DE INICIALIZACIÓN ---

async function init(page = 1) {
  currentPage = page;

  const tableBody = document.getElementById('produccion-table-body');
  if (!tableBody) return;

  tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando producciones...</td></tr>';

  try {
    const producciones = await produccionHuevosService.GetProduccionHuevosAll({
      page: currentPage,
      limit,
      fecha_inicio: fechaInicioGlobal,
      fecha_fin: fechaFinGlobal
    });

    if (producciones && producciones.length > 0) {
      tableBody.innerHTML = producciones.map(createProduccionRow).join('');
    } else {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No se encontraron registros.</td></tr>';
    }

    renderPaginationControls();

  } catch (error) {
    console.error('Error al obtener producciones:', error);
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error al cargar datos.</td></tr>`;
  }

  // Listeners
  const editForm = document.getElementById('edit-produccion-form');
  tableBody.removeEventListener('click', handleTableClick);
  tableBody.addEventListener('click', handleTableClick);
  editForm.removeEventListener('submit', handleUpdateSubmit);
  editForm.addEventListener('submit', handleUpdateSubmit);
  const createForm = document.getElementById('create-produccion-form');
  if(createForm){
    createForm.removeEventListener('submit', handleCreateSubmit);
    createForm.addEventListener('submit', handleCreateSubmit);
  
  }
}

function renderPaginationControls() {
  const paginationDiv = document.getElementById("pagination-controls");
  if (!paginationDiv) return;


  paginationDiv.innerHTML = `
    <button id="btn-prev" class="btn btn-light text-success"><svg class="svg-inline--fa fa-chevron-left" aria-hidden="true" focusable="false" data-prefix="fas" data-icon="chevron-left" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512" data-fa-i2svg=""><path fill="currentColor" d="M9.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l192 192c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L77.3 256 246.6 86.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-192 192z"></path></svg></button>
    <span class='px-3 bg-success align-content-center text-white'>${currentPage}</span>
    <button id="btn-next" class="btn btn-light text-success"><svg class="svg-inline--fa fa-chevron-right" aria-hidden="true" focusable="false" data-prefix="fas" data-icon="chevron-right" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512" data-fa-i2svg=""><path fill="currentColor" d="M310.6 233.4c12.5 12.5 12.5 32.8 0 45.3l-192 192c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3L242.7 256 73.4 86.6c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l192 192z"></path></svg></button>
  `;
  const botonPrev = document.getElementById("btn-prev").style.backgroundColor = '#f2f2f2'
  const botonSig = document.getElementById("btn-next").style.backgroundColor = '#f2f2f2'
  document.getElementById("btn-prev").onclick = () => {
    if (currentPage > 1) init(currentPage - 1);
  };

  document.getElementById("btn-next").onclick = () => {
    init(currentPage + 1);
  };
}

// --- FILTRADO POR FECHA ---

function setupFilterListeners() {
  const btnFiltrar = document.getElementById('btn-filtrar');
  const btnLimpiar = document.getElementById('btn-limpiar');
  const inputFechaInicio = document.getElementById('filtro-fecha-inicio');
  const inputFechaFin = document.getElementById('filtro-fecha-fin');

  if (!btnFiltrar || !inputFechaInicio || !inputFechaFin) return;

  btnFiltrar.addEventListener('click', () => {
    // Tomar valores o null si están vacíos
    fechaInicioGlobal = inputFechaInicio.value || null;
    fechaFinGlobal = inputFechaFin.value || null;

    // Reiniciar a la primera página al filtrar
    init(1);
  });

  btnLimpiar.addEventListener('click', () => {
    // Limpiar variables globales
    fechaInicioGlobal = null;
    fechaFinGlobal = null;

    // Limpiar inputs visuales
    inputFechaInicio.value = "";
    inputFechaFin.value = "";

    // Recargar la tabla sin filtros
    init(1);
});
}


async function eliminarProduccion(produccionId) {
 try {
    // 🔵 SWEETALERT DE CONFIRMACIÓN
    const result = await Swal.fire({
      title: "¿Estás seguro?",
      text: "Esta producción será eliminada permanentemente.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "No, cancelar",
      reverseButtons: true,
      customClass: {
        confirmButton: "btn btn-success",
        cancelButton: "btn btn-secondary"
      },
      buttonsStyling: false
    });

    // ❌ Si cancela, no eliminamos
    if (!result.isConfirmed) return;

    // 🗑️ Ejecutar eliminación
    await produccionHuevosService.DeleteProduccionHuevos(produccionId);

    // 🟢 SWEETALERT DE ÉXITO
    Swal.fire({
      icon: "success",
      title: "Producción eliminada",
      text: "La producción fue eliminada correctamente.",
      timer: 1500,
      showConfirmButton: false
    }).then(() => {

      // ✅ CERRAR MODAL SI ESTÁ ABIERTO
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("edit-produccion-modal")
      );
      if (modal) modal.hide();

      // ♻️ Recargar tabla
      init(currentPage);
    });

  } catch (error) {
    console.error("Error:", error);

    // 🔴 SWEETALERT DE ERROR
    Swal.fire({
      icon: "error",
      title: "Error al eliminar",
      text: "No se pudo eliminar la producción.",
      confirmButtonText: "Aceptar",
      customClass: {
        confirmButton: "btn btn-danger"
      },
      buttonsStyling: false
    });
  }
}

setupFilterListeners();

export { init };

