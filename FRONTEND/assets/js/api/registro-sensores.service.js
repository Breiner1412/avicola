import { request } from './apiClient.js';

export const registroSensoresService = {
    /**
     * Obtener todos los registros de sensores con paginación
     * @param {number} skip - Número de registros a saltar
     * @param {number} limit - Número máximo de registros
     * @returns {Promise<object>}
     */
    getRegistros: (skip = 0, limit = 10) => {
        const endpoint = `/registro-sensores/all?skip=${skip}&limit=${limit}`;
        return request(endpoint);
    },

    /**
     * Crear un nuevo registro de sensor
     * @param {object} registroData - Datos del nuevo registro
     * @returns {Promise<object>}
     */
    createRegistro: (registroData) => {
        return request(`/registro-sensores/crear`, {
            method: 'POST',
            body: JSON.stringify(registroData),
        });
    },
};