import { request } from './apiClient.js';

export const inventoryService = {
    getInventory: () => {
    const endpoint = `/inventory/all`;
    return request(endpoint);
    },

    /**
     * Obtener una inventario por su ID.
     * @param {string} id - El id de la inventario.
     * @returns {Promise<object>}
    */

    getInventoryById: (id) => {
        // Construimos la URL con el parámetro ?id_inventario=
        const endpoint = `/inventory/by-id/${id}`;
        return request(endpoint);
    },

    /**
     * Obtener inventario por finca/land id.
     * @param {number|string} landId
     */
    getInventoryByLand: (landId) => {
        return request(`/inventory/by-land/${landId}`);
    },

    /**
     * Actualizar una inventario.
     * @param {string | number} invId - El ID del inventario a actualizar.
     * @param {object} invData - Los nuevos datos del inventario.
     * @returns {Promise<object>}
    */
    updateInventory: (invId, invData) => {
        // Usar el endpoint de inventory para actualizar (no categories)
        return request(`/inventory/by-id/${invId}`, {
        method: 'PUT',
        body: JSON.stringify(invData),
        });
    },

    /**
     * Crear un item inventario.
     * @param {object} invData - Los nuevos datos del item inventario.
     * @returns {Promise<object>}
    */
    createInventory: (invData) => {
        return request(`/inventory/crear`, {
        method: 'POST',
        body: JSON.stringify(invData),
        });
    },

    /**
     * Eliminar una item inventario.
     * @param {string | number} invId - El ID del item inventario a Eliminar.
     * @returns {Promise<object>}
    */
    deleteInventory: (invId) => {
        // Eliminar usando el endpoint de inventory
        return request(`/inventory/by-id/${invId}`, {
        method: 'DELETE'
        });
    },


};
