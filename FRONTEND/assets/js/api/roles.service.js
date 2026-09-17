import { request } from './apiClient.js';

export const rolesService = {

  // Crear rol
  CreateRol: (data) => {
    return request('/roles/crear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  // Obtener rol por ID (usa query param)
  GetRolById: (id_rol) => {
    return request(`/roles/by-id?rol_id=${id_rol}`);
  },

  // Obtener rol por nombre (también query param)
  GetRolByNombre: (nombre_rol) => {
    return request(`/roles/by-nombre?nombre_rol=${encodeURIComponent(nombre_rol)}`);
  },

  // Obtener roles paginados
  GetRoles: () => {
    return request('/roles/all-roles-pag');
  },

  // Actualizar rol por ID (usa path param)
  UpdateRolById: (id_rol, data) => {
    return request(`/roles/by-id/${id_rol}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  // Cambiar estado del rol por user_id (path param)
  CambiarRolEstado: (user_id, nuevo_estado) => {
    return request(`/roles/cambiar-estado/${user_id}?nuevo_estado=${nuevo_estado}`,
   {method:'PUT'}
   );
  }

};
