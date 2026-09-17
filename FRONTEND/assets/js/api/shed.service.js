import { request } from './apiClient.js';

export const shedService = {
    getSheds: () => {
        const endpoint = `/sheds/all`;

        // La lógica es mucho más simple ahora, solo llamamos a nuestro cliente central.
        return request(endpoint);
    },

    /**
     * Obtener un galpón por id.
     * @param {string} shed_id - El id del galpón a buscar.
     * @returns {Promise<object>}
    */
    getShedById: (shed_id) => {
        // Construimos la URL con el parámetro ?id_galpon=
        const endpoint = `/sheds/by-id/${shed_id}`;
        return request(endpoint);
    },

    /**
     * Obtener galpones filtrados por finca
     * @param {string|number} landId - id de la finca
     * @returns {Promise<Array>} lista de galpones
     */
    getShedsByLand: (landId) => {
        const endpoint = `/sheds/galpones/por-finca?id_finca=${landId}`;
        return request(endpoint);
    },

    getLandsActive: () => {
        const endpoint = `/sheds/fincas/activas`;

        return request(endpoint);
    },
    /**
     * Actualizar un usuario.
     * @param {string | number} shed_id - El ID del galpon a actualizar.
     * @param {object} shedData - Los nuevos datos del galpón.
     * @returns {Promise<object>}
    */
    updateShed: (shed_id, shedData) => {
        return request(`/sheds/by-id/${shed_id}`, {
            method: 'PUT',
            body: JSON.stringify(shedData),
        });
    },

    // Desactivar / Activar un usuario
    /**
     * Modifica el estado de un usuario (generalmente para desactivarlo).
     * @param {string | number} shedId - El ID del usuario a modificar.
     * @returns {Promise<object>}
     */
    deleteShed: (shedId, newStatus) => {
        // Nuestro apiClient se encargará de añadir el token de autorización.
        return request(`/sheds/cambiar-estado/${shedId}?nuevo_estado=${newStatus}`, {
            method: 'PUT'
        });

    },

    /**
     * Crear un usuario.
     * @param {object} shedData - Los nuevos datos del usuario.
     * @returns {Promise<object>}
    */
    createShed: (shedData) => {
        return request(`/sheds/crear-galpon`, {
            method: 'POST',
            body: JSON.stringify(shedData),
        });
    },
    getActiveSheds: () => {
        const endpoint = `/sheds/activos`;
        return request(endpoint);
    },
};

// Alias usado por algunas páginas
shedService.deleteShed = shedService.changeShedStatus;
export const shedsService = shedService;
