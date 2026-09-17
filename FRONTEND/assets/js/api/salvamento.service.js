import { request } from './apiClient.js';

export const rescueService = {
    /**
     * Obtener todos los rescates
     * @returns {Promise<object>}
     */
    getRescues: () => {
        const endpoint = `/rescue/all`;
        return request(endpoint);
    },
    
    /**
     * Obtener un rescate por su ID
     * @param {number} rescueId - El ID del rescate a buscar
     * @returns {Promise<object>}
     */
    getRescueById: (rescueId) => {
        const endpoint = `/rescue/by-id/${rescueId}`;
        return request(endpoint);
    },

     getRescuesAll: (page = 1, size = 10) => {
        const endpoint = `/rescue/all-pag?page=${page}&page_size=${size}`;  
        return request(endpoint);
    },
    
    getRescuesAllDate: (fechaInicio, fechaFin, page = 1, size = 10) => {
        const endpoint = `/rescue/all-pag-by-date?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&page=${page}&page_size=${size}`;
        return request(endpoint);
    },
    /**
     * Actualizar un rescate
     * @param {string | number} rescueId - El ID del rescate a actualizar
     * @param {object} rescueData - Los nuevos datos del rescate
     * @returns {Promise<object>}
     */
    updateRescue: (rescueId, rescueData) => {
        return request(`/rescue/by-id/${rescueId}`, {
            method: 'PUT',
            body: JSON.stringify(rescueData),
        });
    },

    /**
     * Crear un rescate
     * @param {object} rescueData - Los datos del nuevo rescate
     * @returns {Promise<object>}
     */
    createRescue: (rescueData) => {
        return request(`/rescue/crear`, {
            method: 'POST',
            body: JSON.stringify(rescueData),
        });
    },

    /**
     * Eliminar un rescate
     * @param {string | number} rescueId - El ID del rescate a eliminar
     * @returns {Promise<object>}
     */
    deleteRescue: (rescueId) => {
        return request(`/rescue/by-id/${rescueId}`, {
            method: 'DELETE',
        });
    },

    getChickenTypes: () => {
        const endpoint = `/type_chicken/all-type-chickens`;  
        return request(endpoint);
    },

    getSheds: () => {
        const endpoint = `/sheds/all`;
        return request(endpoint);
    },

    clearCache() {
        this.sheds = [];
        this.chickenTypes = [];
        this.isLoaded = false;
    }
};
