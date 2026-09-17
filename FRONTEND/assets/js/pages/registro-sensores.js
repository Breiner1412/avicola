import { registroSensoresService } from '../api/registro-sensores.service.js';
import { sensorService } from '../api/sensor.service.js';

let currentPage = 1;
const pageSize = 10;
let allRegistros = [];
let promediosChart = null;
let filteredRegistros = [];
let currentTipoPromedio = 'diario';
let currentSensorPromedio = null;
let currentGalponPromedio = null;
let sensoresList = [];

const rangosSeguridad = {
    'Temperatura': { min: 18, max: 28, unidad: '°C' },
    'Humedad': { min: 40, max: 70, unidad: '%' },
    'Luz': { min: 200, max: 800, unidad: 'lux' }
};

// Función para verificar si un registro está fuera de rango
function verificarRangoSeguridad(registro) {
    if (!registro.tipo_sensor || !rangosSeguridad[registro.tipo_sensor]) {
        return { fueraDeRango: false, mensaje: '' };
    }

    const valor = parseFloat(registro.dato_sensor);
    const rango = rangosSeguridad[registro.tipo_sensor];
    
    if (isNaN(valor)) return { fueraDeRango: false, mensaje: '' };

    if (valor < rango.min || valor > rango.max) {
        return {
            fueraDeRango: true,
            mensaje: `${registro.tipo_sensor} fuera de rango: ${valor.toFixed(2)}${registro.u_medida || ''} (Rango: ${rango.min}-${rango.max}${rango.unidad})`
        };
    }
    
    return { fueraDeRango: false, mensaje: '' };
}

// Contador de sensores activos únicos (por id)
function contarSensoresActivos(registros) {
    const sensoresSet = new Set();
    (registros || []).forEach(registro => {
        if (registro.id_sensor) sensoresSet.add(registro.id_sensor.toString());
    });
    return sensoresSet.size;
}

// Función para generar el panel de alertas con Bootstrap
function generarPanelAlertas() {
    const container = document.getElementById('alertas-container');
    if (!container) return;

    // Configuración para análisis por promedio de últimas lecturas por sensor
    const ALERT_CONFIG = {
        lookbackCount: 5,
        lookbackMinutes: 60 * 24,
        margenAdvertencia: 0.05,
        margenCritica: 0.10
    };

    const ahora = Date.now();
    const cutoff = ALERT_CONFIG.lookbackMinutes > 0 ? (ahora - ALERT_CONFIG.lookbackMinutes * 60 * 1000) : 0;

    // Agrupar por sensor y ordenar por fecha
    const mapaSensores = new Map();
    (allRegistros || []).forEach(r => {
        if (!r || !r.id_sensor) return;
        if (!['Temperatura', 'Humedad', 'Luz'].includes(r.tipo_sensor)) return;
        
        const ts = r.fecha_hora ? new Date(r.fecha_hora).getTime() : 0;
        if (cutoff && ts && ts < cutoff) return;
        const sid = r.id_sensor.toString();
        if (!mapaSensores.has(sid)) mapaSensores.set(sid, []);
        mapaSensores.get(sid).push(Object.assign({}, r, { _ts: ts }));
    });

    let criticas = 0, advertencias = 0;
    const alertasDetalles = [];

    for (const [sensorId, lecturas] of mapaSensores.entries()) {
        if (lecturas.length === 0) continue;
        
        lecturas.sort((a, b) => (b._ts || 0) - (a._ts || 0));
        const seleccion = lecturas.slice(0, ALERT_CONFIG.lookbackCount);
        if (!seleccion || seleccion.length === 0) continue;

        const valores = seleccion.map(x => parseFloat(x.dato_sensor)).filter(v => !isNaN(v));
        if (valores.length === 0) continue;
        const suma = valores.reduce((s, v) => s + v, 0);
        const promedio = suma / valores.length;

        const tipo = seleccion[0].tipo_sensor;
        const rango = rangosSeguridad[tipo];
        if (!rango) continue;

        let nivel = 0;
        if (promedio > rango.max) {
            const exceso = promedio - rango.max;
            const pct = exceso / Math.max(1, rango.max);
            if (pct >= ALERT_CONFIG.margenCritica) nivel = 2;
            else if (pct >= ALERT_CONFIG.margenAdvertencia) nivel = 1;
        } else if (promedio < rango.min) {
            const deficit = rango.min - promedio;
            const pct = deficit / Math.max(1, rango.min);
            if (pct >= ALERT_CONFIG.margenCritica) nivel = 2;
            else if (pct >= ALERT_CONFIG.margenAdvertencia) nivel = 1;
        }

        if (nivel === 2) criticas++;
        else if (nivel === 1) advertencias++;

        if (nivel > 0) {
            const rec = seleccion[0];
            alertasDetalles.push({
                tipo: nivel === 2 ? 'critica' : 'advertencia',
                mensaje: `${tipo} promedio (${promedio.toFixed(2)}${rec.u_medida || ''}) fuera de rango (Rango: ${rango.min}-${rango.max}${rango.unidad})`,
                sensor: rec.nombre_sensor || `Sensor ${sensorId}`,
                galpon: rec.nombre_galpon || 'Sin galpón',
                fecha: formatDateTime(rec.fecha_hora),
                promedio: parseFloat(promedio.toFixed(2)),
                muestras: seleccion.length
            });
        }
    }

    let alertasHTML = '';
    if (criticas === 0 && advertencias === 0) {
        alertasHTML = `
            <div class="alert alert-success mb-0">
                <div class="d-flex align-items-center">
                    <div class="flex-shrink-0">
                        <i class="fa-solid fa-check-circle fs-4 me-3"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1">Estado Normal</h6>
                        <p class="mb-0 small">Todos los sensores dentro de rangos seguros.</p>
                    </div>
                </div>
            </div>
        `;
    } else {
        // Diseño limpio para alertas críticas
        if (criticas > 0) {
            alertasHTML += `
                <div class="alert alert-danger mb-3">
                    <div class="d-flex align-items-start">
                        <div class="flex-shrink-0">
                            <div class="bg-white rounded-circle p-2 me-3">
                                <i class="fa-solid fa-triangle-exclamation text-danger fs-5"></i>
                            </div>
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="mb-1 fw-bold">Alertas Críticas</h6>
                                    <p class="mb-0 small text-white-75">${criticas} sensor(es) requieren atención inmediata</p>
                                </div>
                                <div class="d-flex align-items-center">
                                    <button class="btn btn-sm btn-outline-light" id="btn-ver-detalles-criticas">
                                        <i class="fa-solid fa-chevron-right"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Diseño limpio para advertencias
        if (advertencias > 0) {
            alertasHTML += `
                <div class="alert alert-warning">
                    <div class="d-flex align-items-start">
                        <div class="flex-shrink-0">
                            <div class="bg-white rounded-circle p-2 me-3">
                                <i class="fa-solid fa-exclamation-triangle text-warning fs-5"></i>
                            </div>
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="mb-1 fw-bold">Advertencias</h6>
                                    <p class="mb-0 small text-dark">${advertencias} sensor(es) necesitan monitorización</p>
                                </div>
                                <div class="d-flex align-items-center">
                                    <span class="badge bg-white text-warning fw-bold fs-6 me-2">${advertencias}</span>
                                    <button class="btn btn-sm btn-outline-dark" id="btn-ver-detalles-advertencias">
                                        <i class="fa-solid fa-chevron-right"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    container.innerHTML = alertasHTML;

    // Event listeners para botones
    document.getElementById('btn-ver-detalles-criticas')?.addEventListener('click', () => {
        const lista = alertasDetalles.filter(a => a.tipo === 'critica');
        mostrarTodasAlertas(lista);
    });
    document.getElementById('btn-ver-detalles-advertencias')?.addEventListener('click', () => {
        const lista = alertasDetalles.filter(a => a.tipo === 'advertencia');
        mostrarTodasAlertas(lista);
    });
}
// Función auxiliar para obtener descripción de alertas
function obtenerDescripcionAlertas(alertasDetalles, tipo) {
    const alertasFiltradas = alertasDetalles.filter(a => a.tipo === tipo);
    if (alertasFiltradas.length === 0) return '';
    
    // Agrupar por tipo de sensor
    const tipos = {};
    alertasFiltradas.forEach(alerta => {
        const match = alerta.mensaje.match(/(.+?) fuera de rango/);
        const tipoSensor = match ? match[1] : 'Desconocido';
        tipos[tipoSensor] = (tipos[tipoSensor] || 0) + 1;
    });
    
    return Object.entries(tipos)
        .map(([tipo, count]) => `${count} ${tipo.toLowerCase()}(s) fuera de rango`)
        .join(', ');
}

function mostrarTodasAlertas(alertas) {
    let mensaje = '<div class="text-start">';
    
    if (alertas.length === 0) {
        mensaje += `
            <div class="text-center py-4">
                <i class="fa-solid fa-check-circle fs-1 text-success mb-3"></i>
                <h6 class="text-success mb-2">No hay alertas activas</h6>
                <p class="text-muted small">Todos los sensores están dentro de los rangos normales.</p>
            </div>
        `;
    } else {
        // Agrupar alertas por tipo
        const alertasCriticas = alertas.filter(a => a.tipo === 'critica');
        const alertasAdvertencias = alertas.filter(a => a.tipo === 'advertencia');
        
        // Mostrar alertas críticas primero
        if (alertasCriticas.length > 0) {
            mensaje += `
                <div class="mb-4">
                    <h6 class="text-danger mb-3 border-bottom pb-2">
                        <i class="fa-solid fa-triangle-exclamation me-2"></i>
                        Alertas Críticas (${alertasCriticas.length})
                    </h6>
            `;
            
            alertasCriticas.forEach((alerta, index) => {
                mensaje += crearTarjetaAlerta(alerta, index, alertasCriticas.length);
            });
            
            mensaje += `</div>`;
        }
        
        // Mostrar advertencias después
        if (alertasAdvertencias.length > 0) {
            mensaje += `
                <div class="mt-4">
                    <h6 class="text-warning mb-3 border-bottom pb-2">
                        <i class="fa-solid fa-exclamation-triangle me-2"></i>
                        Advertencias (${alertasAdvertencias.length})
                    </h6>
            `;
            
            alertasAdvertencias.forEach((alerta, index) => {
                mensaje += crearTarjetaAlerta(alerta, index, alertasAdvertencias.length);
            });
            
            mensaje += `</div>`;
        }
        
       
    }
    
    mensaje += '</div>';

    Swal.fire({
        title: 'Detalles de Alertas',
        html: mensaje,
        width: '600px',
        showCloseButton: true,
        showConfirmButton: false,
        customClass: {
            popup: 'rounded-3'
        }
    });
}
function crearTarjetaAlerta(alerta, index, total) {
    const esUltima = index === total - 1;
    const bordeClase = esUltima ? '' : 'border-bottom pb-3 mb-3';
    
    // Extraer información del mensaje
    const tipoSensor = alerta.mensaje.match(/(Temperatura|Humedad|Luz)/)?.[0] || 'Sensor';
    const valorMatch = alerta.mensaje.match(/promedio \((\d+\.?\d*)/);
    const valor = valorMatch ? valorMatch[1] : alerta.promedio.toFixed(2);
    const unidad = alerta.mensaje.includes('°C') ? '°C' : 
                   alerta.mensaje.includes('%') ? '%' : 
                   alerta.mensaje.includes('lux') ? 'lux' : '';
    
    // Determinar si está por encima o por debajo
    const rangoMatch = alerta.mensaje.match(/Rango: (\d+)-(\d+)/);
    const esAlto = rangoMatch && parseFloat(valor) > parseFloat(rangoMatch[2]);
    const iconoDireccion = esAlto ? 'fa-arrow-up' : 'fa-arrow-down';
    
    return `
        <div class="alert-detail ${bordeClase}">
            <div class="d-flex align-items-start">
                <div class="flex-shrink-0 me-3">
                    <div class="rounded-circle ${alerta.tipo === 'critica' ? 'bg-danger' : 'bg-warning'} p-2">
                        <i class="fa-solid ${alerta.tipo === 'critica' ? 'fa-triangle-exclamation' : 'fa-exclamation-triangle'} text-white"></i>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="mb-1 fw-bold">${alerta.sensor}</h6>
                            <div class="small text-muted">
                                <i class="fa-solid fa-house me-1"></i>
                                ${alerta.galpon}
                            </div>
                        </div>
                        <span class="badge ${alerta.tipo === 'critica' ? 'bg-danger' : 'bg-warning'}">
                            ${alerta.tipo === 'critica' ? 'CRÍTICA' : 'ADVERTENCIA'}
                        </span>
                    </div>
                    
                    <div class="alert-values card border-0 bg-light mb-3">
                        <div class="card-body p-3">
                            <div class="row g-2">
                                <div class="col-12 mb-2">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span class="text-muted small">${tipoSensor}:</span>
                                        <div class="d-flex align-items-center">
                                            <i class="fa-solid ${iconoDireccion} ${alerta.tipo === 'critica' ? 'text-danger' : 'text-warning'} me-2"></i>
                                            <span class="fw-bold ${alerta.tipo === 'critica' ? 'text-danger' : 'text-warning'} fs-5">
                                                ${valor}${unidad}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert-meta">
                        <div class="row g-2">
                            <div class="col-12 col-md-6">
                                <div class="small text-muted">
                                    <i class="fa-regular fa-calendar me-1"></i>
                                    ${alerta.fecha}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Función para actualizar el resumen
function actualizarResumen() {
    if (filteredRegistros.length === 0) {
        document.getElementById('total-registros').textContent = '0';
        document.getElementById('sensores-activos').textContent = '0';
        document.getElementById('valor-maximo').textContent = '0.00';
        document.getElementById('valor-minimo').textContent = '0.00';
        document.getElementById('sensor-maximo').textContent = '';
        document.getElementById('sensor-minimo').textContent = '';
        return;
    }

    document.getElementById('total-registros').textContent = 
        filteredRegistros.length.toLocaleString();

    document.getElementById('sensores-activos').textContent = 
        contarSensoresActivos(filteredRegistros);

    let maxValor = -Infinity;
    let minValor = Infinity;
    let sensorMax = '';
    let sensorMin = '';

    filteredRegistros.forEach(registro => {
        const valor = parseFloat(registro.dato_sensor);
        if (valor > maxValor) {
            maxValor = valor;
            sensorMax = registro.nombre_sensor;
        }
        if (valor < minValor) {
            minValor = valor;
            sensorMin = registro.nombre_sensor;
        }
    });

    document.getElementById('valor-maximo').textContent = 
        maxValor.toFixed(2);
    document.getElementById('sensor-maximo').textContent = 
        `(${sensorMax})`;

    document.getElementById('valor-minimo').textContent = 
        minValor.toFixed(2);
    document.getElementById('sensor-minimo').textContent = 
        `(${sensorMin})`;
}

function createRegistroRow(registro) {
  return `
    <tr>
      <td class="cell">${registro.nombre_sensor || `Sensor ${registro.id_sensor}`} </td>
      <td class="cell">${registro.nombre_galpon || 'Sin galpón'} </td>
      <td class="cell">${parseFloat(registro.dato_sensor).toFixed(2)} </td>
      <td class="cell">
        <span class="badge bg-secondary">${registro.u_medida}</span> </td>
      <td class="cell">
        <small>${formatDateTime(registro.fecha_hora)}</small> </td>
      <td class="cell text-end">
        <button class="btn btn-sm btn-outline-success btn-view-registro" data-registro-id="${registro.id_registro}">
          <i class="fa-regular fa-eye"></i>
        </button>
      </td>
    </tr>
  `;
}

function formatDateTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toLocaleString('es-ES');
}

function formatWeekLabel(year, week) {
    const simple = new Date(year, 0, 1 + (week - 1) * 7);
    const dayOfWeek = simple.getDay();
    const ISOweekStart = simple;
    if (dayOfWeek <= 4) {
        ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
    } else {
        ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
    }

    const day = ISOweekStart.getDate();
    const month = ISOweekStart.toLocaleString('es-ES', { month: 'short' });

    return `Sem ${week} (${day} ${month})`;
}

function renderPagination(total_pages, currentPageNum = 1) {
    const container = document.querySelector("#pagination");
    if (!container) return;

    container.innerHTML = "";

    const prevItem = document.createElement("li");
    prevItem.classList.add('page-item');
    if (currentPageNum === 1) prevItem.classList.add('disabled');

    const prevLink = document.createElement("a");
    prevLink.classList.add('page-link', 'text-success');
    prevLink.href = "#";
    prevLink.innerHTML = "&lt;";
    prevLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPageNum > 1) {
            loadRegistrosPage(currentPageNum - 1);
        }
    });

    prevItem.appendChild(prevLink);
    container.appendChild(prevItem);

    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPageNum - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(total_pages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        const firstPageItem = document.createElement("li");
        firstPageItem.classList.add('page-item');
        const firstPageLink = document.createElement("a");
        firstPageLink.classList.add('page-link', 'text-success');
        firstPageLink.href = "#";
        firstPageLink.textContent = "1";
        firstPageLink.addEventListener("click", (e) => {
            e.preventDefault();
            loadRegistrosPage(1);
        });
        firstPageItem.appendChild(firstPageLink);
        container.appendChild(firstPageItem);

        if (startPage > 2) {
            const dotsItem = document.createElement("li");
            dotsItem.classList.add('page-item', 'disabled');
            const dotsLink = document.createElement("a");
            dotsLink.classList.add('page-link');
            dotsLink.textContent = "...";
            dotsItem.appendChild(dotsLink);
            container.appendChild(dotsItem);
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageItem = document.createElement("li");
        pageItem.classList.add('page-item');

        const pageLink = document.createElement("a");

        if (i === currentPageNum) {
            pageLink.classList.add('page-link', 'bg-success', 'border-success', 'text-white');
            pageItem.classList.add('active');
        } else {
            pageLink.classList.add('page-link', 'text-success');
        }

        pageLink.href = "#";
        pageLink.textContent = i;
        pageLink.addEventListener("click", (e) => {
            e.preventDefault();
            loadRegistrosPage(i);
        });

        pageItem.appendChild(pageLink);
        container.appendChild(pageItem);
    }

    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            const dotsItem = document.createElement("li");
            dotsItem.classList.add('page-item', 'disabled');
            const dotsLink = document.createElement("a");
            dotsLink.classList.add('page-link');
            dotsLink.textContent = "...";
            dotsItem.appendChild(dotsLink);
            container.appendChild(dotsItem);
        }

        const lastPageItem = document.createElement("li");
        lastPageItem.classList.add('page-item');
        const lastPageLink = document.createElement("a");
        lastPageLink.classList.add('page-link', 'text-success');
        lastPageLink.href = "#";
        lastPageLink.textContent = total_pages;
        lastPageLink.addEventListener("click", (e) => {
            e.preventDefault();
            loadRegistrosPage(total_pages);
        });
        lastPageItem.appendChild(lastPageLink);
        container.appendChild(lastPageItem);
    }

    const nextItem = document.createElement("li");
    nextItem.classList.add('page-item');
    if (currentPageNum === total_pages) nextItem.classList.add('disabled');

    const nextLink = document.createElement("a");
    nextLink.classList.add('page-link', 'text-success');
    nextLink.href = "#";
    nextLink.innerHTML = "&gt;";
    nextLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPageNum < total_pages) {
            loadRegistrosPage(currentPageNum + 1);
        }
    });

    nextItem.appendChild(nextLink);
    container.appendChild(nextItem);
}

function loadRegistrosPage(page) {
    currentPage = page;
    updateTable();
}

async function loadAllRegistros() {
    try {
        const tbody = document.getElementById("registros-table-body");
        tbody.innerHTML = `<tr><td colspan="7" class="text-center">Cargando registros...</td></tr>`;

        const response = await registroSensoresService.getRegistros(0, 1000);

        if (response && Array.isArray(response)) {
            allRegistros = response;
        } else if (response && response.registros && Array.isArray(response.registros)) {
            allRegistros = response.registros;
        } else if (response && response.data && Array.isArray(response.data)) {
            allRegistros = response.data;
        } else {
            allRegistros = [];
        }

        if (allRegistros.length > 0) {
            await enriquecerDatosSensores();
        }

        filteredRegistros = [...allRegistros];

        await loadSensorsForFilter();
        await loadGalponesForFilter();

        updateTable();
        
        // Actualizar panel de alertas y resumen
        generarPanelAlertas();
        actualizarResumen();
        
        calcularPromediosFrontend(currentTipoPromedio, currentSensorPromedio, currentGalponPromedio);

        return true;
    } catch (error) {
        console.error('Error al cargar registros:', error);
        const tableBody = document.getElementById('registros-table-body');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error al cargar los registros.</td></tr>';
        }
        return false;
    }
}

async function enriquecerDatosSensores() {
    try {
        const sensoresResponse = await sensorService.getSensors();

        const sensoresMap = new Map();

        let sensores = [];
        if (Array.isArray(sensoresResponse)) {
            sensores = sensoresResponse;
        } else if (sensoresResponse && sensoresResponse.sensores) {
            sensores = sensoresResponse.sensores;
        } else if (sensoresResponse && sensoresResponse.data) {
            sensores = sensoresResponse.data;
        } else if (sensoresResponse && typeof sensoresResponse === 'object') {
            sensores = Object.values(sensoresResponse).find(val => Array.isArray(val)) || [];
        }

        // Mapeo de nombres de tipo de sensor a las claves de rangosSeguridad
        const mapaTipoSensor = {
            'Sensor de Temperatura': 'Temperatura',
            'Sensor de Humedad': 'Humedad',
            'Sensor de Iluminación': 'Luz',
            'Sensor de Luz': 'Luz',
            'Temperatura': 'Temperatura',
            'Humedad': 'Humedad',
            'Luz': 'Luz'
        };

        sensores.forEach(sensor => {
            if (sensor && sensor.id_sensor) {
                const nombreTipo = sensor.nombre_tipo || sensor.tipo_sensor || '';
                const tipoMapeado = mapaTipoSensor[nombreTipo] || nombreTipo;
                
                if (['Temperatura', 'Humedad', 'Luz'].includes(tipoMapeado)) {
                    sensoresMap.set(sensor.id_sensor.toString(), {
                        nombre: sensor.nombre || `Sensor ${sensor.id_sensor}`,
                        id_galpon: sensor.id_galpon,
                        nombre_galpon: sensor.nombre_galpon || `Galpón ${sensor.id_galpon || 'Desconocido'}`,
                        tipo_sensor: tipoMapeado,
                        u_medida: sensor.u_medida
                    });
                }
            }
        });

        allRegistros.forEach(registro => {
            const infoSensor = sensoresMap.get(registro.id_sensor?.toString());
            if (infoSensor) {
                registro.nombre_sensor = infoSensor.nombre;
                registro.id_galpon = infoSensor.id_galpon;
                registro.nombre_galpon = infoSensor.nombre_galpon;
                registro.tipo_sensor = infoSensor.tipo_sensor;
                if (!registro.u_medida) registro.u_medida = infoSensor.u_medida;
            } else {
                registro.nombre_sensor = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;
                registro.nombre_galpon = registro.nombre_galpon || 'Sin galpón';
                if (!registro.tipo_sensor) {
                    registro.tipo_sensor = 'Desconocido';
                }
            }
        });

    } catch (error) {
        console.error('Error al enriquecer datos de sensores:', error);
        allRegistros.forEach(registro => {
            registro.nombre_sensor = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;
            registro.nombre_galpon = registro.nombre_galpon || 'Sin galpón';
            registro.tipo_sensor = registro.tipo_sensor || 'Desconocido';
            registro.u_medida = registro.u_medida || 'Unidad';
        });
    }
}

async function loadSensorsForFilter() {
    try {
        const filterSelect = document.getElementById('filter-sensor');
        const filterPromedios = document.getElementById('filter-sensor-promedios');

        if (!filterSelect || !filterPromedios) return;

        filterSelect.innerHTML = '<option value="all">Seleccione un sensor</option>';
        filterPromedios.innerHTML = '<option value="todos">Seleccione un sensor</option>';

        const uniqueSensors = [];
        const sensorMap = new Map();

        allRegistros.forEach(registro => {
            const sensorId = registro.id_sensor;
            const sensorName = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;

            if (sensorId && !sensorMap.has(sensorId.toString())) {
                sensorMap.set(sensorId.toString(), {
                    id: sensorId,
                    nombre: sensorName,
                    nombre_galpon: registro.nombre_galpon
                });
                uniqueSensors.push({
                    id: sensorId,
                    nombre: sensorName,
                    nombre_galpon: registro.nombre_galpon
                });
            }
        });

        sensoresList = uniqueSensors;

        uniqueSensors.forEach(sensor => {
            filterSelect.innerHTML += `<option value="${sensor.nombre}">${sensor.nombre}</option>`;
            filterPromedios.innerHTML += `<option value="${sensor.id}">${sensor.nombre}</option>`;
        });

        const galponFilter = document.getElementById('filter-galpon');
        if (galponFilter) {
            galponFilter.addEventListener('change', (e) => {
                filterSensorsByGalpon(e.target.value, 'main');
            });
        }

        const galponPromFilter = document.getElementById('filter-galpon-promedios');
        if (galponPromFilter) {
            galponPromFilter.addEventListener('change', (e) => {
                filterSensorsByGalpon(e.target.value, 'promedios');
            });
        }

    } catch (error) {
        console.error('Error al cargar sensores para filtro:', error);
    }
}

function filterSensorsByGalpon(galponNombre, scope = 'main') {
    const targetSelectId = scope === 'promedios' ? 'filter-sensor-promedios' : 'filter-sensor';
    const selectEl = document.getElementById(targetSelectId);
    if (!selectEl) return;

    const defaultValue = scope === 'promedios' ? 'todos' : 'all';
    const defaultText = scope === 'promedios' ? 'Seleccione un sensor' : 'Seleccione un sensor';

    selectEl.innerHTML = `<option value="${defaultValue}">${defaultText}</option>`;

    if (!galponNombre || galponNombre === 'all' || galponNombre === 'todos') {
        sensoresList.forEach(sensor => {
            if (scope === 'promedios') selectEl.innerHTML += `<option value="${sensor.id}">${sensor.nombre}</option>`;
            else selectEl.innerHTML += `<option value="${sensor.nombre}">${sensor.nombre}</option>`;
        });
        return;
    }

    const filtrados = sensoresList.filter(s => (s.nombre_galpon || '').toString() === galponNombre);

    filtrados.forEach(sensor => {
        if (scope === 'promedios') selectEl.innerHTML += `<option value="${sensor.id}">${sensor.nombre}</option>`;
        else selectEl.innerHTML += `<option value="${sensor.nombre}">${sensor.nombre}</option>`;
    });

    if (scope === 'main') {
        const current = document.getElementById('filter-sensor')?.value;
        if (current && current !== 'all') {
            const found = filtrados.find(s => s.nombre === current);
            if (!found) document.getElementById('filter-sensor').value = 'all';
        }
    } else {
        const current = document.getElementById('filter-sensor-promedios')?.value;
        if (current && current !== 'todos') {
            const found = filtrados.find(s => s.id == current);
            if (!found) document.getElementById('filter-sensor-promedios').value = 'todos';
        }
    }
}

async function loadGalponesForFilter() {
    try {
        const filterSelect = document.getElementById('filter-galpon');
        const filterPromedios = document.getElementById('filter-galpon-promedios');

        if (!filterSelect || !filterPromedios) return;

        filterSelect.innerHTML = '<option value="all">Seleccione un galpón</option>';
        filterPromedios.innerHTML = '<option value="todos">Seleccione un galpón</option>';

        const uniqueGalpones = [...new Set(allRegistros
            .map(r => r.nombre_galpon)
            .filter(nombre => nombre && nombre.trim() !== ''))];

        uniqueGalpones.forEach(galpon => {
            if (galpon) {
                const nombre = galpon.trim();
                filterSelect.innerHTML += `<option value="${nombre}">${nombre}</option>`;
                filterPromedios.innerHTML += `<option value="${nombre}">${nombre}</option>`;
            }
        });

    } catch (error) {
        console.error('Error al cargar galpones:', error);
    }
}

function updateTable() {
    const tableBody = document.getElementById('registros-table-body');
    if (!tableBody) return;

    if (filteredRegistros.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No se encontraron registros.</td></tr>';

        const paginationContainer = document.getElementById('pagination-container');
        if (paginationContainer) {
            paginationContainer.classList.add('d-none');
        }
        return;
    }

    const total = filteredRegistros.length;
    const totalPages = Math.ceil(total / pageSize);
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, total);
    const pageRegistros = filteredRegistros.slice(startIndex, endIndex);

    tableBody.innerHTML = pageRegistros.map(createRegistroRow).join('');

    const paginationContainer = document.getElementById('pagination-container');
    if (paginationContainer) {
        if (totalPages > 1) {
            paginationContainer.classList.remove('d-none');
            renderPagination(totalPages, currentPage);
        } else {
            paginationContainer.classList.add('d-none');
        }
    }
}

async function applyFilters() {
    const dateFrom = document.getElementById('filter-date-from')?.value;
    const dateTo = document.getElementById('filter-date-to')?.value;
    const sensorFilter = document.getElementById('filter-sensor')?.value;
    const galponFilter = document.getElementById('filter-galpon')?.value;

    currentPage = 1;
    filteredRegistros = [...allRegistros];

    if (dateFrom && dateTo) {
        const fromDate = new Date(dateFrom);
        const toDate = new Date(dateTo);
        
        fromDate.setHours(0, 0, 0, 0);
        toDate.setHours(23, 59, 59, 999);
        
        filteredRegistros = filteredRegistros.filter(reg => {
            const regDate = new Date(reg.fecha_hora);
            return regDate >= fromDate && regDate <= toDate;
        });
    } else if (dateFrom) {
        const fromDate = new Date(dateFrom);
        fromDate.setHours(0, 0, 0, 0);
        const toDate = new Date(dateFrom);
        toDate.setHours(23, 59, 59, 999);
        
        filteredRegistros = filteredRegistros.filter(reg => {
            const regDate = new Date(reg.fecha_hora);
            return regDate >= fromDate && regDate <= toDate;
        });
    } else if (dateTo) {
        const fromDate = new Date(dateTo);
        fromDate.setHours(0, 0, 0, 0);
        const toDate = new Date(dateTo);
        toDate.setHours(23, 59, 59, 999);
        
        filteredRegistros = filteredRegistros.filter(reg => {
            const regDate = new Date(reg.fecha_hora);
            return regDate >= fromDate && regDate <= toDate;
        });
    }

    if (sensorFilter && sensorFilter !== 'all') {
        filteredRegistros = filteredRegistros.filter(reg =>
            reg.nombre_sensor === sensorFilter
        );
    }

    if (galponFilter && galponFilter !== 'all') {
        filteredRegistros = filteredRegistros.filter(reg =>
            reg.nombre_galpon === galponFilter
        );
    }

    updateTable();
    // Actualizar panel de alertas y resumen
    generarPanelAlertas();
    actualizarResumen();
    
    calcularPromediosFrontend(currentTipoPromedio, currentSensorPromedio, currentGalponPromedio);
}

function clearFilters() {
    const filters = [
        'filter-date-from',
        'filter-date-to',
        'filter-sensor',
        'filter-galpon'
    ];

    filters.forEach(filterId => {
        const element = document.getElementById(filterId);
        if (element) {
            element.value = filterId === 'filter-sensor' ||
                filterId === 'filter-galpon' ? 'all' : '';
        }
    });

    const filterSensorPromedios = document.getElementById('filter-sensor-promedios');
    if (filterSensorPromedios) filterSensorPromedios.value = 'todos';

    const filterGalponPromedios = document.getElementById('filter-galpon-promedios');
    if (filterGalponPromedios) filterGalponPromedios.value = 'todos';

    currentSensorPromedio = null;
    currentGalponPromedio = null;

    applyFilters();

    document.querySelectorAll('.btn-tipo-promedio').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tipo === 'diario') {
            btn.classList.add('active');
        }
    });
    currentTipoPromedio = 'diario';

    calcularPromediosFrontend('diario', null, null);
}

async function refreshFromServer() {
    try {
        const loading = Swal.fire({
            title: 'Actualizando...',
            text: 'Cargando los últimos datos',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        await loadAllRegistros();

        await loading.close();

        Swal.fire({
            icon: 'success',
            title: 'Actualizado',
            text: 'Datos actualizados correctamente',
            timer: 1500,
            showConfirmButton: false
        });
    } catch (error) {
        console.error('Error al refrescar:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudieron actualizar los datos'
        });
    }
}

function calcularPromediosFrontend(tipo = 'diario', sensorId = null, galpon = null) {
    try {
        const filtroSensorSeleccionado = sensorId && sensorId !== 'todos';
        const filtroGalponSeleccionado = galpon && galpon !== 'todos';

        if (!filtroSensorSeleccionado) {
            if (promediosChart) {
                try { promediosChart.destroy(); } catch (e) { }
                promediosChart = null;
            }

            const emptyOverlay = document.getElementById('promedios-empty');
            const canvas = document.getElementById('promediosChart');
            
            let mensaje = '<div class="text-center w-100 px-3">';
            mensaje += '<i class="fa-solid fa-chart-line fs-1 text-muted mb-3"></i><br>';
            mensaje += '<h6 class="text-muted mb-2">Seleccione un sensor para visualizar datos</h6>';
            mensaje += '<p class="small text-muted mb-0">Puede filtrar por galpón primero para ver solo los sensores de ese galpón</p>';
            mensaje += '</div>';

            if (emptyOverlay) {
                emptyOverlay.style.display = 'flex';
                emptyOverlay.innerHTML = mensaje;
            }
            if (canvas) {
                const ctx = canvas.getContext('2d');
                try { ctx.clearRect(0, 0, canvas.width, canvas.height); } catch (e) { }
            }

            const estadisticasVacias = calcularEstadisticasPromedios([]);
            actualizarPanelEstadisticas([], [], estadisticasVacias);

            return;
        }

        let registrosParaPromedios = [...allRegistros];

        if (sensorId && sensorId !== 'todos') {
            registrosParaPromedios = registrosParaPromedios.filter(r => r.id_sensor == sensorId);
        }

        if (galpon && galpon !== 'todos') {
            registrosParaPromedios = registrosParaPromedios.filter(r => r.nombre_galpon === galpon);
        }

        let promediosData = [];
        let estadisticas = {
            promedio_global: 0,
            valor_maximo: 0,
            valor_minimo: 0,
            sensor_maximo: '',
            galpon_maximo: '',
            sensor_minimo: '',
            galpon_minimo: '',
            total_lecturas: 0
        };

        if (registrosParaPromedios.length === 0) {
            if (promediosChart) {
                try { promediosChart.destroy(); } catch (e) { }
                promediosChart = null;
            }

            const emptyOverlay = document.getElementById('promedios-empty');
            const canvas = document.getElementById('promediosChart');
            
            let mensaje = '<div class="text-center w-100 px-3">';
            mensaje += '<i class="fa-solid fa-circle-exclamation fs-1 text-warning mb-3"></i><br>';
            mensaje += '<h6 class="text-muted mb-2">No hay datos disponibles</h6>';
            mensaje += '<p class="small text-muted mb-0">El sensor seleccionado no tiene registros en el período actual</p>';
            mensaje += '</div>';

            if (emptyOverlay) {
                emptyOverlay.style.display = 'flex';
                emptyOverlay.innerHTML = mensaje;
            }
            if (canvas) {
                const ctx = canvas.getContext('2d');
                try { ctx.clearRect(0, 0, canvas.width, canvas.height); } catch (e) { }
            }

            actualizarPanelEstadisticas(registrosParaPromedios, [], estadisticas);
            return;
        }

        if (tipo === 'diario') {
            promediosData = calcularPromediosDiarios(registrosParaPromedios);
        } else if (tipo === 'semanal') {
            promediosData = calcularPromediosSemanales(registrosParaPromedios);
        } else {
            promediosData = calcularPromediosMensuales(registrosParaPromedios);
        }

        estadisticas = calcularEstadisticasPromedios(promediosData);
        actualizarPanelEstadisticas(registrosParaPromedios, promediosData, estadisticas);
        generarGraficoPromedios(promediosData);

    } catch (error) {
        console.error('Error calculando promedios:', error);
    }
}

function calcularPromediosDiarios(registros) {
    const promediosPorDia = {};

    registros.forEach(registro => {
        const fecha = new Date(registro.fecha_hora);
        const fechaStr = fecha.toLocaleDateString('es-ES');
        const sensorNombre = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;
        const galpon = registro.nombre_galpon || 'Sin galpón';

        const key = `${fechaStr}_${sensorNombre}_${galpon}`;

        if (!promediosPorDia[key]) {
            promediosPorDia[key] = {
                sensor: sensorNombre,
                galpon: galpon,
                fecha: fechaStr,
                fechaISO: fecha.toISOString().split('T')[0],
                sum: 0,
                count: 0,
                unidad: registro.u_medida || 'Unidad'
            };
        }

        promediosPorDia[key].sum += parseFloat(registro.dato_sensor);
        promediosPorDia[key].count++;
    });

    const resultado = Object.values(promediosPorDia).map(item => ({
        sensor: item.sensor,
        galpon: item.galpon,
        fecha: item.fecha,
        promedio: item.sum / item.count,
        unidad: item.unidad,
        fechaOrden: item.fechaISO
    }));

    return resultado.sort((a, b) => a.fechaOrden.localeCompare(b.fechaOrden));
}

function calcularPromediosSemanales(registros) {
    const promediosPorSemana = {};

    registros.forEach(registro => {
        const fecha = new Date(registro.fecha_hora);
        const año = fecha.getFullYear();
        const semana = getWeekNumber(fecha);
        const sensorNombre = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;
        const galpon = registro.nombre_galpon || 'Sin galpón';

        const semanaLabel = formatWeekLabel(año, semana);
        const semanaKey = `${año}-W${String(semana).padStart(2, '0')}`;

        const key = `${semanaKey}_${sensorNombre}_${galpon}`;

        if (!promediosPorSemana[key]) {
            promediosPorSemana[key] = {
                sensor: sensorNombre,
                galpon: galpon,
                semana: semanaLabel,
                semanaKey: semanaKey,
                semana_numero: semana,
                año: año,
                sum: 0,
                count: 0,
                unidad: registro.u_medida || 'Unidad'
            };
        }

        promediosPorSemana[key].sum += parseFloat(registro.dato_sensor);
        promediosPorSemana[key].count++;
    });

    const resultado = Object.values(promediosPorSemana).map(item => ({
        sensor: item.sensor,
        galpon: item.galpon,
        semana: item.semana,
        semanaKey: item.semanaKey,
        semana_numero: item.semana_numero,
        año: item.año,
        promedio: item.sum / item.count,
        unidad: item.unidad
    }));

    return resultado.sort((a, b) => {
        if (a.año !== b.año) return a.año - b.año;
        return a.semana_numero - b.semana_numero;
    });
}

function calcularPromediosMensuales(registros) {
    const promediosPorMes = {};

    registros.forEach(registro => {
        const fecha = new Date(registro.fecha_hora);
        const año = fecha.getFullYear();
        const mes = fecha.getMonth() + 1;
        const sensorNombre = registro.nombre_sensor || `Sensor ${registro.id_sensor}`;
        const galpon = registro.nombre_galpon || 'Sin galpón';

        const mesNombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const mesLabel = `${mesNombres[mes - 1]} ${año}`;
        const mesKey = `${año}-${String(mes).padStart(2, '0')}`;

        const key = `${mesKey}_${sensorNombre}_${galpon}`;

        if (!promediosPorMes[key]) {
            promediosPorMes[key] = {
                sensor: sensorNombre,
                galpon: galpon,
                mes: mesLabel,
                mesKey: mesKey,
                año: año,
                mesNumero: mes,
                sum: 0,
                count: 0,
                unidad: registro.u_medida || 'Unidad'
            };
        }

        promediosPorMes[key].sum += parseFloat(registro.dato_sensor);
        promediosPorMes[key].count++;
    });

    const resultado = Object.values(promediosPorMes).map(item => ({
        sensor: item.sensor,
        galpon: item.galpon,
        mes: item.mes,
        mesKey: item.mesKey,
        promedio: item.sum / item.count,
        unidad: item.unidad,
        año: item.año,
        mesNumero: item.mesNumero
    }));

    return resultado.sort((a, b) => {
        if (a.año !== b.año) return a.año - b.año;
        return a.mesNumero - b.mesNumero;
    });
}

function getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

function calcularEstadisticasPromedios(promediosList) {
    if (!promediosList || promediosList.length === 0) {
        return {
            promedio_global: 0,
            valor_maximo: 0,
            valor_minimo: 0,
            sensor_maximo: '',
            galpon_maximo: '',
            sensor_minimo: '',
            galpon_minimo: '',
            total_lecturas: 0
        };
    }

    const promediosValores = promediosList.map(p => p.promedio);
    const promedioGlobal = promediosValores.reduce((a, b) => a + b, 0) / promediosValores.length;

    const maxValor = Math.max(...promediosValores);
    const minValor = Math.min(...promediosValores);

    const sensorMaximo = promediosList.find(p => p.promedio === maxValor);
    const sensorMinimo = promediosList.find(p => p.promedio === minValor);

    return {
        promedio_global: parseFloat(promedioGlobal.toFixed(2)),
        valor_maximo: parseFloat(maxValor.toFixed(2)),
        valor_minimo: parseFloat(minValor.toFixed(2)),
        sensor_maximo: sensorMaximo?.sensor || '',
        galpon_maximo: sensorMaximo?.galpon || '',
        sensor_minimo: sensorMinimo?.sensor || '',
        galpon_minimo: sensorMinimo?.galpon || '',
        total_lecturas: promediosList.length
    };
}

function actualizarPanelEstadisticas(registros, promediosData, estadisticas) {
    try {
        const totalRecordsEl = document.getElementById('total-registros');
        const activeSensorsEl = document.getElementById('sensores-activos');
        const maxValueEl = document.getElementById('valor-maximo');
        const minValueEl = document.getElementById('valor-minimo');
        const sensorMaxEl = document.getElementById('sensor-maximo');
        const sensorMinEl = document.getElementById('sensor-minimo');

        if (totalRecordsEl) totalRecordsEl.textContent = (registros || []).length.toLocaleString();

        if (activeSensorsEl) {
            const uniqueSensors = new Set((registros || []).map(r => r.nombre_sensor || `Sensor ${r.id_sensor}`));
            activeSensorsEl.textContent = uniqueSensors.size.toString();
        }

        const unidad = (Array.isArray(promediosData) && promediosData[0]?.unidad) ? ` ${promediosData[0].unidad}` : '';

        if (maxValueEl) maxValueEl.textContent = (estadisticas?.valor_maximo ?? 0).toFixed(2) + unidad;
        if (minValueEl) minValueEl.textContent = (estadisticas?.valor_minimo ?? 0).toFixed(2) + unidad;

        if (sensorMaxEl) sensorMaxEl.textContent = estadisticas?.sensor_maximo ? `${estadisticas.sensor_maximo} ${estadisticas.galpon_maximo ? '(' + estadisticas.galpon_maximo + ')' : ''}` : '';
        if (sensorMinEl) sensorMinEl.textContent = estadisticas?.sensor_minimo ? `${estadisticas.sensor_minimo} ${estadisticas.galpon_minimo ? '(' + estadisticas.galpon_minimo + ')' : ''}` : '';

    } catch (error) {
        console.error('Error actualizando panel de estadísticas:', error);
    }
}

function generarGraficoPromedios(promediosData) {
    const ctx = document.getElementById('promediosChart');
    if (!ctx) return;
    const emptyOverlay = document.getElementById('promedios-empty');

    if (promediosChart) {
        promediosChart.destroy();
        promediosChart = null;
    }

    let dataToPlot = Array.isArray(promediosData) ? [...promediosData] : [];

    if (!dataToPlot || dataToPlot.length === 0) {
        if (emptyOverlay) emptyOverlay.style.display = 'flex';
        const canvas = document.getElementById('promediosChart');
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    if (currentTipoPromedio === 'diario') {
        const cutoff = new Date();
        cutoff.setHours(0, 0, 0, 0);
        cutoff.setDate(cutoff.getDate() - 6);
        const cutoffISO = cutoff.toISOString().split('T')[0];

        dataToPlot = dataToPlot.filter(item => {
            if (item.fechaOrden) return item.fechaOrden >= cutoffISO;
            if (item.fecha) {
                const d = new Date(item.fecha);
                return d.toISOString().split('T')[0] >= cutoffISO;
            }
            return true;
        });
    } else {
        dataToPlot = dataToPlot.slice(-10);
    }

    if (!dataToPlot || dataToPlot.length === 0) {
        if (emptyOverlay) {
            emptyOverlay.style.display = 'flex';
            let mensaje = '<div class="text-center w-100 px-3">';
            mensaje += '<i class="fa-solid fa-calendar-xmark fs-1 text-muted mb-3"></i><br>';
            mensaje += '<h6 class="text-muted mb-2">Sin datos en el período seleccionado</h6>';
            mensaje += '<p class="small text-muted mb-0">No hay registros para el rango de fechas actual</p>';
            mensaje += '</div>';
            emptyOverlay.innerHTML = mensaje;
        }
        const canvas = document.getElementById('promediosChart');
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    if (emptyOverlay) emptyOverlay.style.display = 'none';

    const labels = dataToPlot.map(item => {
        if (item.fecha) return item.fecha;
        if (item.semana) return item.semana;
        if (item.mes) return item.mes;
        return `${item.sensor}`;
    });

    const promedios = dataToPlot.map(item => item.promedio);
    const sensorNombres = dataToPlot.map(item => item.sensor || 'Sensor');
    const galpones = dataToPlot.map(item => item.galpon || 'Sin galpón');
    const unidad = dataToPlot[0]?.unidad || 'Unidad';

    const tipoGrafico = dataToPlot.length > 10 ? 'line' : 'bar';

    promediosChart = new Chart(ctx, {
        type: tipoGrafico,
        data: {
            labels: labels,
            datasets: [{
                label: `Promedio (${unidad})`,
                data: promedios,
                backgroundColor: currentTipoPromedio === 'diario'
                    ? 'rgba(25, 135, 84, 0.7)'
                    : currentTipoPromedio === 'semanal'
                        ? 'rgba(41, 128, 185, 0.7)'
                        : 'rgba(243, 156, 18, 0.7)',
                borderColor: currentTipoPromedio === 'diario'
                    ? 'rgba(25, 135, 84, 1)'
                    : currentTipoPromedio === 'semanal'
                        ? 'rgba(41, 128, 185, 1)'
                        : 'rgba(243, 156, 18, 1)',
                borderWidth: 2,
                fill: tipoGrafico === 'line',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function (tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            return `${sensorNombres[index]}\n${galpones[index]}`;
                        },
                        label: function (context) {
                            const value = context.parsed && (context.parsed.y ?? context.parsed);
                            const num = (typeof value === 'number') ? value.toFixed(2) : value;
                            return `Promedio: ${num} ${unidad}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: `Valor (${unidad})`
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: currentTipoPromedio === 'diario' ? 'Días' :
                            currentTipoPromedio === 'semanal' ? 'Semanas' : 'Meses'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function cambiarTipoPromedio(tipo) {
    currentTipoPromedio = tipo;
    calcularPromediosFrontend(tipo, currentSensorPromedio, currentGalponPromedio);

    document.querySelectorAll('.btn-tipo-promedio').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tipo === tipo) {
            btn.classList.add('active');
        }
    });
}

function cambiarSensorPromedio(sensorId) {
    currentSensorPromedio = sensorId;
    calcularPromediosFrontend(currentTipoPromedio, sensorId, currentGalponPromedio);
}

function cambiarGalponPromedio(galpon) {
    currentGalponPromedio = galpon;
    calcularPromediosFrontend(currentTipoPromedio, currentSensorPromedio, galpon);
}

function initializeDateFilters() {
    const today = new Date().toISOString().split('T')[0];
    const dateTo = document.getElementById('filter-date-to');
    if (dateTo && !dateTo.value) {
        dateTo.value = today;
    }

    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const dateFrom = document.getElementById('filter-date-from');
    if (dateFrom && !dateFrom.value) {
        dateFrom.value = weekAgo.toISOString().split('T')[0];
    }

    if (dateFrom?.value || dateTo?.value) {
        setTimeout(() => {
            applyFilters();
        }, 500);
    }
}

function handleTableClick(event) {
    const viewButton = event.target.closest('.btn-view-registro');
    if (viewButton) {
        const registroId = viewButton.dataset.registroId;
        viewRegistroDetails(registroId);
    }
}

async function viewRegistroDetails(registroId) {
    try {
        const registro = allRegistros.find(r => r.id_registro == registroId);
        if (!registro) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Registro no encontrado'
            });
            return;
        }

        const fecha = formatDateTime(registro.fecha_hora);
        const unidad = registro.u_medida || 'Unidad';
        const tipoSensor = registro.tipo_sensor || 'Sensor';

       

        Swal.fire({
            title: `Detalles del Registro #${registroId}`,
            html: `
                <div class="text-start">
                    <p><strong>Sensor:</strong> ${registro.nombre_sensor || `Sensor ${registro.id_sensor}`}</p>
                    <p><strong>Galpón:</strong> ${registro.nombre_galpon || 'Sin galpón'}</p>
                    <p><strong>Tipo:</strong> ${tipoSensor}</p>
                    <p><strong>Valor:</strong> ${registro.dato_sensor} ${unidad}</p>
                    <p><strong>Fecha y Hora:</strong> ${fecha}</p>
                   
                </div>
            `,
            icon: 'info',
            confirmButtonText: 'Cerrar',
            width: '500px',
            customClass: {
                confirmButton: 'btn btn-secondary'
            }
        });
    } catch (error) {
        console.error('Error al ver detalles:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudieron cargar los detalles'
        });
    }
}

function configurarEventosPromedios() {
    document.querySelectorAll('.btn-tipo-promedio').forEach(btn => {
        btn.addEventListener('change', () => {
            cambiarTipoPromedio(btn.dataset.tipo);
        });
    });

    const sensorFilter = document.getElementById('filter-sensor-promedios');
    if (sensorFilter) {
        sensorFilter.addEventListener('change', (e) => {
            cambiarSensorPromedio(e.target.value);
        });
    }

    const galponFilter = document.getElementById('filter-galpon-promedios');
    if (galponFilter) {
        galponFilter.addEventListener('change', (e) => {
            cambiarGalponPromedio(e.target.value);
        });
    }
}

async function init() {
    try {
        const dateFrom = document.getElementById('filter-date-from');
        const dateTo = document.getElementById('filter-date-to');
        if (dateFrom) dateFrom.value = '';
        if (dateTo) dateTo.value = '';

        await loadAllRegistros();

        initializeDateFilters();

        const tableBody = document.getElementById('registros-table-body');
        if (tableBody) {
            tableBody.removeEventListener('click', handleTableClick);
            tableBody.addEventListener('click', handleTableClick);
        }

        configurarEventosPromedios();

    } catch (error) {
        console.error('Error en inicialización:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudo cargar la información. Por favor, recarga la página.'
        });
    }
}

window.loadRegistrosPage = loadRegistrosPage;
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;
window.refreshRegistros = refreshFromServer;
window.cambiarTipoPromedio = cambiarTipoPromedio;

export { init };
