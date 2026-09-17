import { request } from './apiClient.js';

export const metodoPagoService = {

    getMetodosPago: () => {

        const endpoint = `/metodo_pago/all-metodosPago`;

        // La lógica es mucho más simple ahora, solo llamamos a nuestro cliente central.
        return request(endpoint);
    },

    /**
     * Obtener un método de pago por su ID.
     * @param {number} metodoPagoId - El ID del método de pago a buscar.
     * @returns {Promise<object>}
     */
/*     getMetodoPagoById: (metodoPagoId) => {
        const endpoint = `/metodo_pago/by-id?metodoPago_id=${metodoPagoId}`;
        return request(endpoint);
    }, */

    getMetodoPagoById: (metodoPagoId) => {
    return request(`/metodo_pago/by-id?metodoPago_id=${metodoPagoId}`, {
    });
},


    /**
     * Crear un método de pago.
     * @param {object} metodoPagoData - Los datos del nuevo método de pago.
     * @returns {Promise<object>}
     */
    createMetodoPago: (metodoPagoData) => {
        return request(`/metodo_pago/crear`, {
            method: 'POST',
            body: JSON.stringify(metodoPagoData),
        });
    },

    /**
     * Actualizar un método de pago existente.
     * @param {number} metodoPagoId - El ID del método de pago a actualizar.
     * @param {object} metodoPagoData - Los nuevos datos del método de pago.
     * @returns {Promise<object>}
     */

updateMetodoPago: (metodoPagoId, metodoPagoData) => {
    return request(`/metodo_pago/by-id/${metodoPagoId}`, {
        method: 'PUT',
        body: JSON.stringify(metodoPagoData),
    });
},


    /**
     * Cambiar el estado de un método de pago (activar/desactivar).
     * @param {number} metodoPagoId
     * @returns {Promise<object>}
     */

changeMetodoPagoStatus: (metodoPagoId, nuevoEstado) => {
    return request(`/metodo_pago/change-status/${metodoPagoId}?nuevo_estado=${nuevoEstado}`, {
         method: 'PUT'
    });
}

    // Aquí podrías añadir más servicios
};
