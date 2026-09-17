import { request } from './apiClient.js';

export const sensorService = {

    /**
     * Create a new sensor
     * @param {object} sensorData
     * @returns {Promise<object>}
     */
    createSensor: (sensorData) => {
        return request(`/sensors/crear`, {
            method: 'POST',
            body: JSON.stringify(sensorData),
        });
    },

    /**
     * Get all sensors
     * @returns {Promise<object>}
     */
    getSensors: () => {
        return request(`/sensors/all`);
    },

    /**
     * Get sensor by ID
     * @param {number} sensorId
     * @returns {Promise<object>}
     */
    getSensorById: (sensorId) => {
        return request(`/sensors/by-id/${sensorId}`);
    },

    /**
     * Get sensors by shed (galpón)
     * @param {number} galponId
     * @returns {Promise<object>}
     */
    getSensorsByShed: (galponId) => {
        return request(`/sensors/by-galpon/${galponId}`);
    },

    /**
     * Get active sheds (galpones)
     * @returns {Promise<object>}
     */
    getActiveSheds: () => {
        return request(`/sheds/activos`);
    },

    /**
     * Update a sensor
     * @param {number} sensorId
     * @param {object} sensorData
     * @returns {Promise<object>}
     */
    updateSensor: (sensorId, sensorData) => {
        return request(`/sensors/by-id/${sensorId}`, {
            method: 'PUT',
            body: JSON.stringify(sensorData),
        });
    },

    /**
     * Change sensor active/inactive status
     * @param {number} sensorId
     * @param {boolean} newStatus
     * @returns {Promise<object>}
     */
    changeSensorStatus: (sensorId, newStatus) => {
        return request(`/sensors/cambiar-estado/${sensorId}?nuevo_estado=${newStatus}`, {
            method: 'PUT',
        });
    },
};
