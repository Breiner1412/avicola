// Cliente central para todas las peticiones a la API:
// añade la URL base y el token, maneja sesión expirada / permisos y
// escapa el texto que llega del backend para evitar XSS al usar innerHTML.

import { authService } from './auth.service.js';
import { API_BASE_URL } from '../config.js';

export { API_BASE_URL };

// Mensajes del backend que indican que la sesión ya no es válida
const SESSION_ERRORS = [
    'token invalido',
    'not authenticated',
    'could not validate credentials',
    'usuario inactivo',
    'rol inactivo',
];

const HTML_ESCAPES = { '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/**
 * Escapa los caracteres peligrosos de un texto (< > " ').
 * No se escapa "&" a propósito para que el valor no cambie si se vuelve a guardar.
 */
export function escapeHtml(value) {
    return String(value).replace(/[<>"']/g, (c) => HTML_ESCAPES[c]);
}

/** Recorre la respuesta y escapa todos los textos. */
export function sanitizeData(data) {
    if (typeof data === 'string') return escapeHtml(data);
    if (Array.isArray(data)) return data.map(sanitizeData);
    if (data && typeof data === 'object') {
        const out = {};
        for (const [k, v] of Object.entries(data)) out[k] = sanitizeData(v);
        return out;
    }
    return data;
}

/** Convierte el "detail" de FastAPI (texto o lista de errores 422) en un mensaje legible. */
export function getErrorMessage(detail, fallback = 'Ocurrió un error en la petición.') {
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((d) => {
                const campo = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : '';
                return campo ? `${campo}: ${d.msg}` : d.msg;
            })
            .join('\n');
    }
    return fallback;
}

function isSessionError(status, detail) {
    const text = String(typeof detail === 'string' ? detail : '').toLowerCase();
    return SESSION_ERRORS.some((m) => text.includes(m)) || (status === 401 && !localStorage.getItem('access_token'));
}

let sessionAlertShown = false;

async function handleSessionExpired() {
    if (sessionAlertShown) return;
    sessionAlertShown = true;
    if (window.Swal) {
        await Swal.fire({
            icon: 'error',
            title: 'Sesión expirada',
            text: 'Tu sesión ha caducado. Por favor inicia sesión nuevamente.',
        });
    }
    authService.logout();
}

/**
 * Comprueba la respuesta de un fetch (sirve también para quien use fetch directo).
 * Lanza un Error con el mensaje del backend si la respuesta no es correcta.
 * @returns {Promise<any>} JSON ya sanitizado
 */
export async function handleResponse(response) {
    if (response.status === 401 || response.status === 403) {
        const errorData = await response.json().catch(() => ({ detail: '' }));

        if (isSessionError(response.status, errorData.detail)) {
            await handleSessionExpired();
            const err = new Error('Sesión expirada');
            err.status = response.status;
            throw err;
        }

        // El usuario está autenticado pero no tiene permiso para esta acción
        if (window.Swal) {
            await Swal.fire({
                icon: 'warning',
                title: 'Acceso denegado',
                text: 'No tiene permisos para realizar esta acción.',
                showConfirmButton: false,
                timer: 1200,
            });
        }
        const err = new Error(getErrorMessage(errorData.detail, 'Usuario no autorizado'));
        err.status = response.status;
        err.response = { status: response.status };
        throw err;
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const err = new Error(getErrorMessage(errorData.detail));
        err.status = response.status;
        err.response = { status: response.status };
        throw err;
    }

    if (response.status === 204) return {};
    const text = await response.text();
    return text ? sanitizeData(JSON.parse(text)) : {};
}

/** Cabeceras con el token actual. */
export function authHeaders(extra = {}) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        'accept': 'application/json',
        ...extra,
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

/**
 * Cliente central para realizar todas las peticiones a la API.
 * @param {string} endpoint - El endpoint al que se llamará (ej. '/users/by-email').
 * @param {object} [options={}] - Opciones para fetch (method, headers, body).
 * @returns {Promise<any>} - La respuesta de la API en formato JSON.
 */
export async function request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = authHeaders(options.headers);

    try {
        const response = await fetch(url, { ...options, headers });
        return await handleResponse(response);
    } catch (error) {
        if (error instanceof TypeError) {
            // Error de red / servidor caído / CORS
            const err = new Error('No se pudo conectar con el servidor. Revisa tu conexión.');
            err.cause = error;
            console.error(`Error de red en ${endpoint}:`, error);
            throw err;
        }
        console.error(`Error en la petición a ${endpoint}:`, error);
        throw error;
    }
}
