import { request } from './apiClient.js';

export const produccionHuevosService = {

  CreateProduccionHuevos: (data) => {
    return request('/produccion-huevos/crear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  GetProduccionHuevosById: (produccion_id) => {
    return request(`/produccion-huevos/by-id/${produccion_id}`);
  },

  UpdateProduccionHuevos: (id, data) => {
    return request(`/produccion-huevos/by-id/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  GetProduccionHuevosAll: ({ page = 1, limit = 10, fecha_inicio = null, fecha_fin = null } = {}) => {

    // Si solo viene una fecha → usar la misma para ambas
    if (fecha_inicio && !fecha_fin) fecha_fin = fecha_inicio;
    if (!fecha_inicio && fecha_fin) fecha_inicio = fecha_fin;

    const offset = (page - 1) * limit;

    const qs = `limit=${limit}&offset=${offset}&fecha_inicio=${fecha_inicio || ""}&fecha_fin=${fecha_fin || ""}`;

    return request(`/produccion-huevos/all?${qs}`);
  },

  DeleteProduccionHuevos: (produccion_id) => {
    return request(`/produccion-huevos/by-id/${produccion_id}`, {
      method: 'DELETE'
    });
  }

};
