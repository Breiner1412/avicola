
import { request } from './apiClient.js';

export const alimentoService = {    
    /**
     * Obtener un usuario por su ID.
     * @param { number } id_alimento - El id_aislamiento del usuario a buscar.
     * @returns {Promise<object>}
    */
    getAlimentoById: (id_alimentos) => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/alimento/by-id?id_alimento=${id_alimentos}`;
        return request(endpoint);
    },

    /**
     * Actualizar un usuario.
     * @param {string | number} alimentoId - El ID del usuario a actualizar.
     * @param {object} alimentoData - Los nuevos datos del usuario.
     * @returns {Promise<object>}
    */
   
   updateAlimento: (alimentoId, alimentoData) => {
    return request(`/alimento/by-id/${alimentoId}`, {
        method: 'PUT',
        body: JSON.stringify(alimentoData),
        });
    },

   getAlimentoAll: () => {
        const endpoint = `/alimento/all-alimentos`;
        return request(endpoint);
    },

    getAlimentoAllPag: (page = 1, page_size = 10) => {
    const endpoint = `/alimento/all-type-alimentos_pag?page=${page}&page_size=${page_size}`;
    return request(endpoint);
    },

    getAlimentoAllDate: (fechaInicio, fechaFin, page = 1, page_size = 10) => {
        const endpoint = `/alimento/rango-fechas?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },

    
    /**
     * Crear un usuario.
     * @param {object} alimentoData - Los nuevos datos del usuario.
     * @returns {Promise<object>}
    */
    createAlimento: (alimentoData) => {
        return request(`/alimento/crear`, {
        method: 'POST',
        body: JSON.stringify(alimentoData),
        });
    },

    // Aquí podrías añadir más servicios
};
