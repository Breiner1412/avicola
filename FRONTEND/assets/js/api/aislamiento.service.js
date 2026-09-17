
import { request } from './apiClient.js';

export const isolationService = {
    getIsolations: () => {
        const userString = localStorage.getItem('user');
        if (!userString) {
            return Promise.reject(new Error('Información de usuario no encontrada.'));
        }
        const user = JSON.parse(userString);

        const endpoint = `/isolations/all-isolation`;
        
        // La lógica es mucho más simple ahora, solo llamamos a nuestro cliente central.
        return request(endpoint);
    },
    
    /**
     * Obtener un usuario por su ID.
     * @param { number } id_aislamiento - El id_aislamiento del usuario a buscar.
     * @returns {Promise<object>}
    */
    getIsolationById: (id_aislamiento) => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/isolations/by-id?id=${id_aislamiento}`;
        return request(endpoint);
    },

     getGalponesAll: () => {
        // Construimos la URL con el parámetro ?id_usuario=
        const endpoint = `/sheds/all`;
        return request(endpoint);
    },
    /**
     * Actualizar un usuario.
     * @param {string | number} aislamientoId - El ID del usuario a actualizar.
     * @param {object} isolationData - Los nuevos datos del usuario.
     * @returns {Promise<object>}
    */
    updateIsolation: (aislamientoId, isolationData) => {
        return request(`/isolations/by-id/${aislamientoId}`, {
        method: 'PUT',
        body: JSON.stringify(isolationData),
        });
    },

    getIsolationAllDate: (fechaInicio, fechaFin, page = 1, page_size = 10) => {
        const endpoint = `/isolations/rango-fechas?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },

    getIsolationAll: (page = 1, page_size = 10) => {
        const endpoint = `/isolations/all_isolations-pag?page=${page}&page_size=${page_size}`;
        return request(endpoint);
    },
    
    /**
     * Crear un usuario.
     * @param {object} isolationData - Los nuevos datos del usuario.
     * @returns {Promise<object>}
    */
    createIsolation: (isolationData) => {
        return request(`/isolations/crear`, {
        method: 'POST',
        body: JSON.stringify(isolationData),
        });
    },

    // /**
    // * @param {object} isolationData - Los nuevos datos del usuario.
    //  * @returns {Promise<object>}
    // */
    // paginationIsolation: (isolationData) => {
    //     return request(`/isolations/crear`, {
    //     method: 'POST',
    //     body: JSON.stringify(isolationData),
    //     });
    // },

    // Aquí podrías añadir más servicios
};
