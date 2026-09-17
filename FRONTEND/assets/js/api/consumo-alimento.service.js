import { request } from './apiClient.js';

export const consumoService = {
    /**
     * Obtener todos los salvamentos
     * @returns {Promise<object>}
     */
    getConsumo: (page = 1, page_size = 10) => {
        const endpoint = `/consumo_gallinas/all-consumos-pag?page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },
    
    /**
     * Obtener un salvamento por su ID
     * @param {number} consumoId - El ID del rescate a buscar
     * @returns {Promise<object>}
     */
    getConsumoById: (consumoId) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/consumo_gallinas/by-id/${consumoId}`;
        return request(endpoint);
    },

    getConsumoByGalpon: (galponId, page = 1, page_size = 10) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/consumo_gallinas/by-galpon?page=${page}&page_size=${page_size}&id_galpon=${galponId}`;
        return request(endpoint);
    },

    getConsumoByRangeDate: (date_start, date_end, page = 1, page_size = 10) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/consumo_gallinas/rango-fechas?fecha_inicio=${date_start}&fecha_fin=${date_end}&page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },
    getAllConsumos: () => {
        const endpoint = `/consumo_gallinas/all-consumos`;
        return request(endpoint);
    },
    getAlimentos: (page = 1, page_size = 10) => {
        // CORRECCIÓN: Nombre de función y parámetro
        const endpoint = `/alimento/all-type-alimentos_pag?page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },

    /**
     * Actualizar un rescate
     * @param {string | number} consumoId - El ID del rescate a actualizar
     * @param {object} consumoData - Los nuevos datos del rescate
     * @returns {Promise<object>}
     */
    updateConsumo: (consumoId, consumoData) => {
        // CORRECCIÓN: Nombre de función
        return request(`/consumo_gallinas/by-id/${consumoId}`, {
            method: 'PUT',
            body: JSON.stringify(consumoData),
        });
    },

    /**
     * @param {object} consumoData - Los datos del nuevo rescate
     * @returns {Promise<object>}
     */
    createConsumo: (consumoData) => {
        // CORRECCIÓN: Nombre de función
        return request(`/consumo_gallinas/crear`, {
            method: 'POST',
            body: JSON.stringify(consumoData),
        });
    },

};

