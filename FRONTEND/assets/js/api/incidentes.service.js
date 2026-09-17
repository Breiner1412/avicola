import { request } from './apiClient.js';

export const incidentesService = {
    /**
     * Obtener todos los incidentes con paginación
     * @param {number} skip - Número de registros a saltar
     * @param {number} limit - Número máximo de registros
     * @returns {Promise<object>}
     */
    getIncidentes: (skip = 0, limit = 5) => {
        const endpoint = `/incidentes_generales/all?skip=${skip}&limit=${limit}`;
        return request(endpoint);
    },

    /**
     * Obtener incidentes filtrados por estado
     * @param {boolean} esta_resuelta - Estado del incidente (true/false)
     * @param {number} skip - Número de registros a saltar
     * @param {number} limit - Número máximo de registros
     * @returns {Promise<object>}
     */
    getIncidentesByEstado: (esta_resuelta, skip = 0, limit = 5) => {
        const endpoint = `/incidentes_generales/by-estado/${esta_resuelta}?skip=${skip}&limit=${limit}`;
        return request(endpoint);
    },

    /**
     * Obtener un incidente por su ID
     * @param {string|number} id_incidente - El ID del incidente
     * @returns {Promise<object>}
     */
    getIncidenteById: (id_incidente) => {
        const endpoint = `/incidentes_generales/by-id/${id_incidente}`;
        return request(endpoint);
    },

    /**
     * Obtener fincas activas
     * @returns {Promise<Array>}
     */
    getLandsActive: () => {
        const endpoint = `/incidentes_generales/fincas/activas`;
        return request(endpoint);
    },

    /**
     * Actualizar un incidente
     * @param {string|number} id_incidente - El ID del incidente
     * @param {object} incidenteData - Los nuevos datos del incidente
     * @returns {Promise<object>}
     */
    updateIncidente: (id_incidente, incidenteData) => {
        return request(`/incidentes_generales/by-id/${id_incidente}`, {
            method: 'PUT',
            body: JSON.stringify(incidenteData),
        });
    },

    /**
     * Cambiar estado del incidente (resuelto/pendiente)
     * @param {string|number} id_incidente - El ID del incidente
     * @returns {Promise<object>}
     */
    changeStatusIncidente: (id_incidente) => {
        return request(`/incidentes_generales/cambiar-estado/${id_incidente}`, {
            method: 'PUT',
        });
    },

    /**
     * Crear un nuevo incidente
     * @param {object} incidenteData - Datos del nuevo incidente
     * @returns {Promise<object>}
     */
    createIncidente: (incidenteData) => {
        return request(`/incidentes_generales/crear`, {
            method: 'POST',
            body: JSON.stringify(incidenteData),
        });
    },

    /**
     * Eliminar un incidente
     * @param {string|number} id_incidente - El ID del incidente
     * @returns {Promise<object>}
     */
    deleteIncidente: (id_incidente) => {
        return request(`/incidentes_generales/by-id/${id_incidente}`, {
            method: 'DELETE',
        });
    }
};