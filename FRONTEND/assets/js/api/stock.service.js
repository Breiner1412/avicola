import { request } from './apiClient.js';

// El stock es de solo lectura desde el frontend: se actualiza automáticamente
// con la producción de huevos y las ventas (no hay endpoints para crear/editar).
export const stockService = {

  // Obtener stock por ID de producto
  GetStockById: (id_producto) => {
    return request(`/stock/by-id/${id_producto}`);
  },

  // Obtener TODO el stock
  GetStockAll: (skip = 0, limit = 500) => {
    return request(`/stock/stock/all?skip=${skip}&limit=${limit}`);
  },
};
