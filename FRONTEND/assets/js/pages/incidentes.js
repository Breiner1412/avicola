import { incidentesService } from '../api/incidentes.service.js';

let modalInstance = null;
let fincas = [];

// Función auxiliar para verificar permisos
function tienePermiso(accion) {
    return window.tienePermiso ? window.tienePermiso('incidentes', accion) : true;
}

function createIncidenteRow(incidente, filtroEstado) {
    const puedeEditar = tienePermiso('editar');
    const puedeEliminar = tienePermiso('eliminar');
    
    // Determinar si debe mostrar la columna de acciones
    let mostrarAcciones = false;
    let accionesHTML = '';
    
    if (incidente.esta_resuelta) {
        // Incidente resuelto
        if (puedeEliminar) {
            mostrarAcciones = true;
            accionesHTML = `
                <button class="btn btn-sm btn-secondary btn-delete-incidente" 
                        data-incidente-id="${incidente.id_incidente}"
                        data-required-module="incidentes" 
                        data-required-action="eliminar">
                    <i class="fa-regular fa-trash-can"></i>
                </button>
            `;
        }
    } else {
        // Incidente pendiente
        if (puedeEditar) {
            mostrarAcciones = true;
            accionesHTML = `
                <button class="btn btn-sm btn-success btn-edit-incidente" 
                        data-incidente-id="${incidente.id_incidente}"
                        data-required-module="incidentes" 
                        data-required-action="editar">
                    <i class="fa-regular fa-pen-to-square"></i>
                </button>
            `;
        }
    }
    
    // Si el filtro está en "Resueltos" y el usuario no puede eliminar, ocultar la columna
    const esFiltroResueltos = filtroEstado === 'true';
    if (esFiltroResueltos && !puedeEliminar) {
        mostrarAcciones = false;
    }
    
    // Si el filtro está en "Pendientes" y el usuario no puede editar, ocultar la columna
    const esFiltroPendientes = filtroEstado === 'false';
    if (esFiltroPendientes && !puedeEditar) {
        mostrarAcciones = false;
    }
    
    const accionesCell = mostrarAcciones ? `
        <td class="px-0 text-end">
            <div class="btn-group">
                ${accionesHTML}
            </div>
        </td>
    ` : '<td></td>';
    
    return `
    <tr>
      <td class="px-0">${incidente.descripcion}</td>
      <td class="px-0">
        <small>${new Date(incidente.fecha_hora).toLocaleString('es-ES')}</small>
      </td>
      <td class="px-0">
        <span class="">${incidente.nombre_finca || `Finca ${incidente.id_finca}`}</span>
      </td>
      <td class="px-0">
        <div class="form-check form-switch d-inline-block">
          <input class="form-check-input switch-status" type="checkbox" 
                 data-incidente-id="${incidente.id_incidente}"
                 ${incidente.esta_resuelta ? 'checked' : ''}
                 ${!puedeEditar || incidente.esta_resuelta ? 'disabled' : ''}>
          <label class="form-check-label small ms-2">
            ${incidente.esta_resuelta ? 'Resuelto' : 'Pendiente'}
          </label>
        </div>
      </td>
      ${accionesCell}
    </tr>
  `;
}

// --- LÓGICA DE MODALES ---

async function openEditModal(id_incidente) {
    // Verificar permiso antes de abrir
    if (!tienePermiso('editar')) {
        Swal.fire({
            icon: 'warning',
            title: 'Acceso denegado',
            text: 'No tienes permiso para editar incidentes',
            confirmButtonText: 'Aceptar'
        });
        return;
    }
    
    const modalElement = document.getElementById('edit-incidente-modal');
    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalElement);
    }

    try {
        const incidente = await incidentesService.getIncidenteById(id_incidente);

        document.getElementById('edit-incidente-id').value = incidente.id_incidente;
        document.getElementById('edit-descripcion').value = incidente.descripcion;
        
        // Convertir fecha del servidor a hora local del cliente para edición
        const fechaServidor = new Date(incidente.fecha_hora);
        const fechaLocal = formatDateForInput(fechaServidor);
        document.getElementById('edit-fecha_hora').value = fechaLocal;

        // Cargar y seleccionar finca
        await loadLandsSelect('edit-id_finca', incidente.id_finca);

        modalInstance.show();
    } catch (error) {
        console.error('Error al obtener datos del incidente:', error);
        alert('No se pudieron cargar los datos del incidente.');
    }
}

// --- MANEJADORES DE EVENTOS ---

async function handleUpdateSubmit(event) {
    event.preventDefault();
    
    // Verificar permiso antes de actualizar
    if (!tienePermiso('editar')) {
        Swal.fire({
            icon: 'error',
            title: 'Acceso denegado',
            text: 'No tienes permiso para editar incidentes',
            confirmButtonText: 'Aceptar'
        });
        return;
    }
    
    const incidenteId = document.getElementById('edit-incidente-id').value;
    const updatedData = {
        descripcion: document.getElementById('edit-descripcion').value,
        fecha_hora: document.getElementById('edit-fecha_hora').value,
        id_finca: document.getElementById('edit-id_finca').value,
    };

    try {
        await incidentesService.updateIncidente(incidenteId, updatedData);
        modalInstance.hide();
        init();
        Swal.fire({
            position: "top-center",
            icon: "success",
            title: "Incidente actualizado correctamente",
            showConfirmButton: false,
            timer: 1500
        });
    } catch (error) {
        console.error('Error al actualizar el incidente:', error);
        alert('No se pudo actualizar el incidente.');
    }
}

async function handleTableClick(event) {
    // Verificar permiso de editar antes de abrir modal
    const editButton = event.target.closest('.btn-edit-incidente');
    if (editButton) {
        if (!tienePermiso('editar')) {
            Swal.fire({
                icon: 'warning',
                title: 'Acceso denegado',
                text: 'No tienes permiso para editar incidentes',
                confirmButtonText: 'Aceptar'
            });
            return;
        }
        const id_incidente = editButton.dataset.incidenteId;
        openEditModal(id_incidente);
        return;
    }

    // Verificar permiso antes de cambiar estado
    const switchButton = event.target.closest('.switch-status');
    if (switchButton && !switchButton.disabled) {
        if (!tienePermiso('editar')) {
            Swal.fire({
                icon: 'warning',
                title: 'Acceso denegado',
                text: 'No tienes permiso para cambiar el estado de incidentes',
                confirmButtonText: 'Aceptar'
            });
            return;
        }
        const id_incidente = switchButton.dataset.incidenteId;
        await handleStatusChange(id_incidente);
        return;
    }

    // Verificar permiso antes de eliminar
    const deleteButton = event.target.closest('.btn-delete-incidente');
    if (deleteButton) {
        if (!tienePermiso('eliminar')) {
            Swal.fire({
                icon: 'warning',
                title: 'Acceso denegado',
                text: 'No tienes permiso para eliminar incidentes',
                confirmButtonText: 'Aceptar'
            });
            return;
        }
        const id_incidente = deleteButton.dataset.incidenteId;
        await handleDeleteIncidente(id_incidente);
        return;
    }
}

async function handleStatusChange(incidenteId) {
    if (!tienePermiso('editar')) {
        Swal.fire({
            icon: 'error',
            title: 'Acceso denegado',
            text: 'No tienes permiso para cambiar el estado de incidentes',
            confirmButtonText: 'Aceptar'
        });
        return;
    }

    const confirmacion = await Swal.fire({
        title: '¿Estás seguro?',
        text: '¿Deseas marcar este incidente como resuelto?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, cambiarlo',
        cancelButtonText: 'Cancelar',
        customClass: {
            confirmButton: 'btn btn-success',
            cancelButton: 'btn btn-secondary'
        }
    });

    if (confirmacion.isConfirmed) {
        try {
            await incidentesService.changeStatusIncidente(incidenteId);
            Swal.fire({
                position: "top-center",
                icon: "success",
                title: "Estado del incidente cambiado correctamente",
                showConfirmButton: false,
                timer: 1500
            });
            init();
        } catch (error) {
            console.error('Error al cambiar estado del incidente:', error);
            Swal.fire({
                position: "top-center",
                icon: "warning",
                title: "No se pudo cambiar el estado del incidente",
                showConfirmButton: false,
                timer: 1500
            });
        }
    }
}

async function handleDeleteIncidente(incidenteId) {
    if (!tienePermiso('eliminar')) {
        Swal.fire({
            icon: 'error',
            title: 'Acceso denegado',
            text: 'No tienes permiso para eliminar incidentes',
            confirmButtonText: 'Aceptar'
        });
        return;
    }

    const confirmacion = await Swal.fire({
        title: '¿Estás seguro?',
        text: 'Esta acción no se puede deshacer',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        customClass: {
            confirmButton: 'btn btn-success',
            cancelButton: 'btn btn-secondary'
        }
    });

    if (confirmacion.isConfirmed) {
        try {
            await incidentesService.deleteIncidente(incidenteId);
            Swal.fire({
                position: "top-center",
                icon: "success",
                title: "Incidente eliminado correctamente",
                showConfirmButton: false,
                timer: 1500
            });
            init();
        } catch (error) {
            console.error('Error al eliminar el incidente:', error);
            Swal.fire({
                position: "top-center",
                icon: "warning",
                title: "No se pudo eliminar el incidente",
                showConfirmButton: false,
                timer: 1500
            });
        }
    }
}

async function handleCreateSubmit(event) {
    event.preventDefault();
    
    // Verificar permiso antes de crear
    if (!tienePermiso('crear')) {
        Swal.fire({
            icon: 'error',
            title: 'Acceso denegado',
            text: 'No tienes permiso para crear incidentes',
            confirmButtonText: 'Aceptar'
        });
        return;
    }

    const newIncidenteData = {
        descripcion: document.getElementById('create-descripcion').value,
        fecha_hora: document.getElementById('create-fecha_hora').value,
        id_finca: document.getElementById('create-id_finca').value,
        esta_resuelta: false
    };

    try {
        await incidentesService.createIncidente(newIncidenteData);
        const modal = bootstrap.Modal.getInstance(document.getElementById('create-incidente-modal'));
        if (modal) modal.hide();
        document.getElementById('create-incidente-form').reset();
        document.getElementById('create-fecha_hora').value = getCurrentDateTimeLocal();

        Swal.fire({
            position: "top-center",
            icon: "success",
            title: "Incidente creado correctamente",
            showConfirmButton: false,
            timer: 1500
        });
        init();
    } catch (error) {
        console.error('Error al crear el incidente:', error);
        alert('No se pudo crear el incidente.');
    }
}

async function loadLandsSelect(selectId, selectedValue = '') {
    const select = document.getElementById(selectId);
    if (!select) return;

    select.innerHTML = '<option value="">Cargando fincas...</option>';

    try {
        const lands = await incidentesService.getLandsActive();

        select.innerHTML = '<option value="">Seleccione una finca</option>';

        lands.forEach(land => {
            const option = document.createElement('option');
            option.value = land.id_finca;
            option.textContent = land.nombre;

            if (String(land.id_finca) === String(selectedValue)) {
                option.selected = true;
            }

            select.appendChild(option);
        });

        // Si solo hay una finca, seleccionarla automáticamente
        if (lands.length === 1 && !selectedValue) {
            select.value = lands[0].id_finca;
        }

    } catch (error) {
        console.error('Error al cargar las fincas activas:', error);
        select.innerHTML = '<option value="">Error al cargar fincas</option>';
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'No se pudieron cargar las fincas.',
                confirmButtonText: 'Aceptar'
            });
        }
    }
}

async function loadLandsFilter() {
    const select = document.getElementById('filtro-finca');
    if (!select) return;
    select.innerHTML = '<option value="all">Todas las fincas</option>';
    try {
        const lands = await incidentesService.getLandsActive();
        lands.forEach(land => {
            const option = document.createElement('option');
            option.value = land.id_finca;
            option.textContent = land.nombre;
            select.appendChild(option);
        });
        
        // Si solo hay una finca, seleccionarla automáticamente
        if (lands.length === 1) {
            select.value = lands[0].id_finca;
        }
    } catch (error) {
        console.error('Error al cargar fincas en filtro:', error);
        select.innerHTML = '<option value="all">Todas las fincas</option>';
    }
}

async function applyFilters() {
    const landFilter = document.getElementById('filtro-finca');
    const statusFilter = document.getElementById('filtro-estado');
    const tableBody = document.getElementById('incidentes-table-body');
    
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando incidentes...</td></tr>';

    try {
        let incidentes;
        const landValue = landFilter ? landFilter.value : 'all';
        const statusValue = statusFilter ? statusFilter.value : 'all';

        if (statusValue !== 'all') {
            const response = await incidentesService.getIncidentesByEstado(statusValue === 'true', 0, 1000);
            incidentes = response.incidentes;
        } else {
            const response = await incidentesService.getIncidentes(0, 1000);
            incidentes = response.incidentes;
        }

        if (landValue !== 'all') {
            incidentes = incidentes.filter(incidente => incidente.id_finca == landValue);
        }

        // Ordenar por fecha de creación (más reciente primero)
        incidentes.sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora));

        if (incidentes && incidentes.length > 0) {
            tableBody.innerHTML = incidentes.map(inc => createIncidenteRow(inc, statusValue)).join('');
            
            // Aplicar permisos a los botones dinámicamente generados
            if (window.aplicarPermisos) {
                window.aplicarPermisos('incidentes');
            }
            
            // Ocultar o mostrar el encabezado de la columna de acciones según sea necesario
            let tieneAcciones = incidentes.some(inc => {
                if (inc.esta_resuelta) {
                    return tienePermiso('eliminar');
                } else {
                    return tienePermiso('editar');
                }
            });
            
            // También considerar el filtro actual
            if ((statusValue === 'true' && !tienePermiso('eliminar')) ||
                (statusValue === 'false' && !tienePermiso('editar'))) {
                tieneAcciones = false;
            }
            
            // Ocultar la columna de acciones en el encabezado si no hay acciones
            const encabezadoAcciones = document.querySelector('th[scope="col"]:nth-child(5)');
            if (encabezadoAcciones) {
                encabezadoAcciones.style.display = tieneAcciones ? '' : 'none';
            }
            
            // Ocultar las celdas vacías en la columna de acciones
            document.querySelectorAll('tr td:nth-child(5)').forEach(celda => {
                if (!celda.querySelector('.btn-group') || (celda.querySelector('.btn-group') && celda.querySelector('.btn-group').children.length === 0)) {
                    celda.style.display = tieneAcciones ? '' : 'none';
                }
            });
            
        } else {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No se encontraron incidentes.</td></tr>';
        }
    } catch (error) {
        console.error('Error al filtrar incidentes:', error);
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error al cargar incidentes.</td></tr>`;
    }
}

// Obtener la fecha y hora actual en formato local (PC del usuario)
function getCurrentDateTimeLocal() {
    const now = new Date();
    
    // Obtener la fecha y hora en la zona horaria local
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Convertir fecha del servidor a formato local para input datetime-local
function formatDateForInput(date) {
    if (!date) return '';
    
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

async function init() {
    // Aplicar permisos al cargar el módulo
    if (window.aplicarPermisos) {
        window.aplicarPermisos('incidentes');
    }
    
    await loadLandsFilter();

    const landFilter = document.getElementById('filtro-finca');
    const statusFilter = document.getElementById('filtro-estado');

    if (landFilter) {
        landFilter.removeEventListener('change', applyFilters);
        landFilter.addEventListener('change', applyFilters);
    }

    if (statusFilter) {
        statusFilter.removeEventListener('change', applyFilters);
        statusFilter.addEventListener('change', applyFilters);
    }

    await applyFilters();

    const createModal = document.getElementById('create-incidente-modal');
    if (createModal) {
        createModal.addEventListener('show.bs.modal', () => {
            loadLandsSelect('create-id_finca');
            // Usar la fecha/hora local del PC del usuario
            document.getElementById('create-fecha_hora').value = getCurrentDateTimeLocal();
        });
    }

    const editModal = document.getElementById('edit-incidente-modal');
    if (editModal) {
        editModal.addEventListener('show.bs.modal', () => {
            // La finca se carga cuando se abre el modal de edición específico
        });
    }

    const editForm = document.getElementById('edit-incidente-form');
    const createForm = document.getElementById('create-incidente-form');
    const tableBody = document.getElementById('incidentes-table-body');

    if (tableBody) {
        tableBody.removeEventListener('click', handleTableClick);
        tableBody.addEventListener('click', handleTableClick);
    }

    if (editForm) {
        editForm.removeEventListener('submit', handleUpdateSubmit);
        editForm.addEventListener('submit', handleUpdateSubmit);
    }

    if (createForm) {
        createForm.removeEventListener('submit', handleCreateSubmit);
        createForm.addEventListener('submit', handleCreateSubmit);
    }
}

export { init };
