import { request } from "./apiClient.js";

export const landService = {
  /**
   * Obtener todas las fincas.
   * Devuelve la promesa que resuelve con el array devuelto por el servidor.
   */
  getLands: () => {
    return request("/lands/all");
  },

  /**
   * Obtener una finca por id.
   * @param {number} landId
   */
  getLandById: (landId) => {
    return request(`/lands/get/${landId}`);
  },

  /**
   * Crear una nueva finca.
   * @param {object} landData
   */
  createLand: (landData) => {
    return request(`/lands/crear`, {
      method: "POST",
      body: JSON.stringify(landData),
    });
  },

  /**
   * Actualizar una finca por id (PUT parcial aceptado por backend).
   * @param {number} landId
   * @param {object} landData
   */
  updateLand: (landId, landData) => {
    return request(`/lands/update/${landId}`, {
      method: "PUT",
      body: JSON.stringify(landData),
    });
  },

  /**
   * Cambiar estado de la finca (activar/desactivar).
   * @param {number} landId
   * @param {boolean} newStatus
   */
  changeLandStatus: (landId, newStatus) => {
    return request(`/lands/cambiar-estado/${landId}`, {
      method: "PUT",
      body: JSON.stringify({ estado: newStatus }),
    });
  },
};
