import { request } from "./apiClient.js";

export const sensorTypeService = {

  /**
   * Create a new sensor type
   * @param {object} sensorTypeData
   * @returns {Promise<object>}
   */
  createSensorType: (sensorTypeData) => {
    return request(`/sensor-types/crear`, {
      method: "POST",
      body: JSON.stringify(sensorTypeData),
    });
  },

  /**
   * Get all sensor types
   * @returns {Promise<object>}
   */
  getSensorTypes: () => {
    return request(`/sensor-types/all`);
  },

  /**
   * Get active sensor types
   * @returns {Promise<object>}
   */
  getActiveSensorTypes: () => {
    return request(`/sensor-types/activos`);
  },

  /**
   * Get sensor type by ID
   * @param {number} sensorTypeId
   * @returns {Promise<object>}
   */
  getSensorTypeById: (sensorTypeId) => {
    return request(`/sensor-types/by-id/${sensorTypeId}`);
  },

  /**
   * Update a sensor type
   * @param {number} sensorTypeId
   * @param {object} sensorTypeData
   * @returns {Promise<object>}
   */
  updateSensorType: (sensorTypeId, sensorTypeData) => {
    return request(`/sensor-types/by-id/${sensorTypeId}`, {
      method: "PUT",
      body: JSON.stringify(sensorTypeData),
    });
  },

  /**
   * Change sensor type active/inactive status
   * @param {number} sensorTypeId
   * @param {boolean} newStatus
   * @returns {Promise<object>}
   */
  changeSensorTypeStatus: (sensorTypeId, newStatus) => {
    return request(
      `/sensor-types/cambiar-estado/${sensorTypeId}?nuevo_estado=${newStatus}`,
      {
        method: "PUT",
      }
    );
  },
};
