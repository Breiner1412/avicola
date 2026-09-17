
import { request } from './apiClient.js';

export const incident_chickenService = {

    // Obtener todos los incidentes
    getChickenIncidents: () => {
        const Incident_chickenString = localStorage.getItem('user');
        if (!Incident_chickenString) {
            return Promise.reject(new Error('Información de incidente no encontrada.'));
        }
        const user = JSON.parse(Incident_chickenString);

        const endpoint = `/incident/all-chicken_incidents`;
        return request(endpoint);
    },

    /**
     * Obtener incidente por su ID.
     * @param { number } id_inc_gallina - El ID del incidente a buscar.
     * @returns {Promise<object>}
    */
    getChickenIncidentById: (id_inc_gallina) => {
        const endpoint = `/incident/by-id?id=${id_inc_gallina}`;
        return request(endpoint);
    },

     getGalponesAll: () => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/sheds/all`;
        return request(endpoint);
    },

     getIsolationAllDate: (fechaInicio, fechaFin, page = 1, page_size = 10) => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/incident/rango-fechas?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },

    getIsolationAll: (page = 1, page_size = 10) => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/incident/all_incidentes-gallinas-pag?page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },
    
    /**
     * Actualizar un incidente.
     * @param {string | number} incidenteId - El ID del incidente a actualizar.
     * @param {object} incidentData - Los nuevos datos del incidente.
     * @returns {Promise<object>}
    */
    updateChickenIncident: (incidenteId, incidentData) => {
        return request(`/incident/by-id/${incidenteId}`, {
            method: 'PUT',
            body: JSON.stringify(incidentData),
        });
    },

    /**
     * Crear un incidente gallina.
     * @param {object} incidentData - Datos del nuevo incidente.
     * @returns {Promise<object>}
    */
    createChickenIncident: (incidentData) => {
        return request(`/incident/crear`, {
            method: 'POST',
            body: JSON.stringify(incidentData),
        });
    },

    /**
     * Cambiar estado (resuelto / no resuelto)
     * @param {string | number} user_id - ID del incidente
     * @param {boolean} nuevo_estado - Estado nuevo
     * @returns {Promise<object>}
    */
    changeChickenStatus: (user_id, nuevo_estado) => {
        
        return request(`/incident/cambiar-estado/${user_id}?nuevo_estado=${nuevo_estado}`, {
            method: 'PUT'
        });
    },

    /**
     * Obtener incidentes con paginación
     * @param {number} skip
     * @param {number} limit
     * @returns {Promise<object>}
    */
    getChickenIncidentPaginated: (skip = 0, limit = 10) => {
        return request(`/incident/all_incidentes-gallinas-pag?page=${Math.floor(skip / limit) + 1}&page_size=${limit}`);
    },

    /**
     * Obtener incidentes por rango de fechas
     * @param {string} fecha_inicio
     * @param {string} fecha_fin
     * @returns {Promise<object>}
    */
    getChickenIncidentByDateRange: (fecha_inicio, fecha_fin) => {
        return request(`/incident/rango-fechas?fecha_inicio=${fecha_inicio}&fecha_fin=${fecha_fin}`);
    }


};
