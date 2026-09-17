import { request } from './apiClient.js';

export const chickenService = {
    /**
     * Obtener todos los rescates
     * @returns {Promise<object>}
     */
    getChickens: (page = 1, page_size = 10) => {
        const endpoint = `/chickens/all-chickens-pag?page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },
    
    /**
     * Obtener un rescate por su ID
     * @param {number} chickenId - El ID del rescate a buscar
     * @returns {Promise<object>}
     */
    getChickenById: (chickenId) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/chickens/by-id/${chickenId}`;
        return request(endpoint);
    },

    getChickensByGalpon: (galponId, page = 1, page_size = 10) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/chickens/by-galpon?page=${page}&page_size=${page_size}&id_galpon=${galponId}`;
        return request(endpoint);
    },

    getChickensByRangeDate: (date_start, date_end, page = 1, page_size = 10) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/chickens/by-fechas?page=${page}&page_size=${page_size}&fecha_inicio=${date_start}&fecha_fin=${date_end}`;
        return request(endpoint);
    },

    /**
     * Actualizar un rescate
     * @param {string | number} chickenId - El ID del rescate a actualizar
     * @param {object} chickenData - Los nuevos datos del rescate
     * @returns {Promise<object>}
     */
    updateChicken: (chickenId, chickenData) => {
        // CORRECCIÓN: Nombre de función
        return request(`/chickens/by-id/${chickenId}`, {
            method: 'PUT',
            body: JSON.stringify(chickenData),
        });
    },

    /**
     * Crear un rescate
     * @param {object} chickenData - Los datos del nuevo rescate
     * @returns {Promise<object>}
     */
    createChicken: (chickenData) => {
        // CORRECCIÓN: Nombre de función
        return request(`/chickens/crear`, {
            method: 'POST',
            body: JSON.stringify(chickenData),
        });
    },

    /**
     * Eliminar un rescate
     * @param {string | number} chickenId - El ID del rescate a eliminar
     * @returns {Promise<object>}
     */
    deleteChicken: (chickenId) => {
        return request(`/chickens/eliminar/${chickenId}`, {
            method: 'DELETE',
        });
    },


    getGalpones: () => {
        const endpoint = `/sheds/all`;  // usa el nombre REAL
        return request(endpoint);
    },

    getTypeChickens: () => {
        const endpoint = `/type_chicken/all-type-chickens`;  // usa el nombre REAL
        return request(endpoint);
    },

    // Aquí podrías añadir más servicios
};
