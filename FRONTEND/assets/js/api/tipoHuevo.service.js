import { request } from './apiClient.js';

export const TipoHuevosService = {

  CreateTipoHuevos: (data) => {
    return request('/tipo-huevos/crear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  GetTipoHuevosById: (produccion_id) => {
    return request(`/tipo-huevos/by-id/${produccion_id}`);
  },

  UpdateTipoHuevos: (id, data) => {
    return request(`/tipo-huevos/by-id/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  GetTipoHuevosAll: () => {
    return request(`/tipo-huevos/all`);
  },

};
