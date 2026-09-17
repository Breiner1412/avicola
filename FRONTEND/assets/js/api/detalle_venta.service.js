import { request } from "./apiClient.js";

export const detalleVentaService = {
  /**
   * Obtener todos los productos de salvamento y huevos
   * @returns {Promise<object>} - Lista de productos de salvamento
   */
  getDettallesVenta: (id_venta) => {
    const endpoint = `/ventas/all-detalles-by-id?venta_id=${id_venta}`;
    return request(endpoint);
  },
  getProductosStock: () => {
    const endpoint = `/detalle_huevos/all-products-stock`;
    return request(endpoint);
  },

  getProductosSalvamento: () => {
    const endpoint = `/detalle_salvamento/all-products-salvamento`;
    return request(endpoint);
  },

  getDetalleVenta: (id_detalle, tipo) => {
    if (tipo == "Huevos") {
      const endpoint = `/detalle_huevos/by-id_detalle?id_detalle=${id_detalle}`;
      return request(endpoint);
    } else if (tipo == "Salvamento") {
      const endpoint = `/detalle_salvamento/by-id_detalle?id_detalle=${id_detalle}`;
      return request(endpoint);
    }
  },

  /**
   * Crear un detalles salvamento y huevos.
   * @param {object} detallesData - Los nuevos datos del usuario.
   * @returns {Promise<object>}
   */
  createDetalleHuevos: (detallesData) => {
    return request(`/detalle_huevos/crear`, {
      method: "POST",
      body: JSON.stringify(detallesData), // El body convierte los datos que le compartimos del form en formato JSON legible para el schema
    });
  },
  createDetalleSalvamento: (detallesData) => {
    return request(`/detalle_salvamento/crear`, {
      method: "POST",
      body: JSON.stringify(detallesData), // El body convierte los datos que le compartimos del form en formato JSON legible para el schema
    });
  },

  updateDetalle: (id_detalle, data, tipo) => {
    if (tipo == "Huevos") {
      return request(`/detalle_huevos/by-id/${id_detalle}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    }

    if (tipo == "Salvamento") {
      return request(`/detalle_salvamento/${id_detalle}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    }
  },

  deleteDetalle: (id_detalle, tipo) => {
    if (tipo == "Huevos") {
      return request(`/detalle_huevos/by-id/${id_detalle}`, {
        method: "DELETE",
      });
    } else if (tipo == "Salvamento") {
      return request(`/detalle_salvamento/${id_detalle}`, {
        method: "DELETE",
      });
    }
  },
};
