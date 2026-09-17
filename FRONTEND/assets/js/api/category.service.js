import { request } from './apiClient.js';

export const categoryService = {
    getCategories: () => {
    const endpoint = `/categories/all`;
    return request(endpoint);
    },

    /**
     * Obtener una categoria por su ID.
     * @param {string} id - El id de la categoria.
     * @returns {Promise<object>}
    */

    getCategoriesById: (id) => {
        // Construimos la URL con el parámetro ?id_categoria=
        const endpoint = `/categories/by-id/${id}`;
        return request(endpoint);
    },

    /**
     * Actualizar una categoria.
     * @param {string | number} catId - El ID del categoria a actualizar.
     * @param {object} catData - Los nuevos datos del categoria.
     * @returns {Promise<object>}
    */
    updateCategory: (catId, catData) => {
        return request(`/categories/by-id/${catId}`, {
        method: 'PUT',
        body: JSON.stringify(catData),
        });
    },

    /**
     * Crear un Categoria.
     * @param {object} catData - Los nuevos datos del categoria.
     * @returns {Promise<object>}
    */
    createCategory: (catData) => {
        return request(`/categories/crear`, {
        method: 'POST',
        body: JSON.stringify(catData),
        });
    },

    /**
     * Eliminar una categoria.
     * @param {string | number} catId - El ID del categoria a Eliminar.
     * @returns {Promise<object>}
    */
    deleteCategory: (catId, catData) => {
        return request(`/categories/by-id/${catId}`, {
        method: 'DELETE',
        body: JSON.stringify(catData),
        });
    },


};
