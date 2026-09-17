// api/tarea.service.js
import { request } from "./apiClient.js";

export const tareaService = {
  // paginado con filtros (fecha_inicio, fecha_fin, page, page_size)
  getPaginated: ({ page = 1, page_size = 10, fecha_inicio, fecha_fin } = {}) => {

    let url = `/tareas/pag?page=${page}&page_size=${page_size}`;

    if (fecha_inicio) {
        url += `&fecha_inicio=${fecha_inicio.split('T')[0]}`;
    }

    if (fecha_fin) {
        url += `&fecha_fin=${fecha_fin.split('T')[0]}`;
    }

    return request(url);
},


  // obtener tareas de un usuario (GET /usuario/{id_usuario})
  getByUser: (id_usuario) => {
    return request(`/tareas/usuario/${id_usuario}`);
  },

  // crear
  create: (data) => {
    return request(`/tareas/crear`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // actualizar por id
  updateById: (id_tarea, data) => {
    return request(`/tareas/${id_tarea}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};
