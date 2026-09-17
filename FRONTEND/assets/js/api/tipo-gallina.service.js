
import { request } from './apiClient.js';

export const typeChickenService = {
    /**
     * Obtener todos los tipos
     * @returns {Promise<object>}
     */

    getTypeChicken: () => {
        const endpoint = `/type_chicken/all-type-chickens`;
        return request(endpoint);
    },

    /**
     * Obtener un rescate por su ID
     * @param {number} id - El ID del rescate a buscar
     * @returns {Promise<object>}
     */

    getTypeChickenById: (id) => {
        return request(`/type_chicken/by-id?id=${id}`);
    },

    /**
     * Actualizar un tipo
     * @param {string | number} id - El ID del tipo a actualizar.
     * @param {object} typeChickenData - Los nuevos datos del tipo.
     * @returns {Promise<object>}
     */
    updateTypeChicken: (id, typeChickenData) => {
        return request(`/type_chicken/by-id/${id}`, {
        method: 'PUT',
        body: JSON.stringify(typeChickenData),
        });
    },

    /**
     * Crear un tipo.
     * @param {object} typeChickenData - Los nuevos datos del tipo.
     * @returns {Promise<object>}
    */
    createTypeChicken: (typeChickenData) => {
        return request(`/type_chicken/crear`, {
        method: 'POST',
        body: JSON.stringify(typeChickenData),
        });
    },

    // Aquí podrías añadir más servicios
};
