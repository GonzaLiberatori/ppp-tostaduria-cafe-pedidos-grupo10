/**
 * API Service - Wrapper around fetch for backend communication
 * Handles auth, baseURL, error handling, and request/response formatting
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// snake_case <-> camelCase transformers
function toCamelCase(str) {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function toSnakeCase(str) {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

// WeakMap cache para evitar transformar el mismo objeto múltiples veces
const transformCache = new WeakMap();

function transformKeys(obj, transformer) {
  // Solo transformar plain objects y arrays
  if (obj === null || obj === undefined || typeof obj !== 'object') return obj;
  
  // No transformar: Date, RegExp, Error, File, Blob, etc.
  if (obj instanceof Date || obj instanceof RegExp || obj instanceof Error) return obj;
  
  // Cache por identidad del objeto
  const cacheKey = transformer === toCamelCase ? 'camel' : 'snake';
  if (!transformCache.has(obj)) {
    transformCache.set(obj, new Map());
  }
  const objCache = transformCache.get(obj);
  if (objCache.has(cacheKey)) {
    return objCache.get(cacheKey);
  }
  
  let result;
  if (Array.isArray(obj)) {
    result = obj.map(item => transformKeys(item, transformer));
  } else {
    result = {};
    for (const [key, value] of Object.entries(obj)) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        result[transformer(key)] = transformKeys(value, transformer);
      }
    }
  }
  
  objCache.set(cacheKey, result);
  return result;
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const token = localStorage.getItem('auth_token');
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
    ...options,
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(transformKeys(options.body, toSnakeCase));
  }

  try {
    const response = await fetch(url, config);
    
    // Handle 401 - token expired or invalid
    if (response.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      throw new ApiError('Sesión expirada', 401);
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new ApiError(
        data.detail || data.message || `Error ${response.status}`,
        response.status,
        data
      );
    }

    // Transform snake_case response to camelCase for frontend
    return transformKeys(data, toCamelCase);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    
    // Network error
    throw new ApiError(
      'Error de conexión. Verifique que el backend esté corriendo.',
      0,
      { originalError: error.message }
    );
  }
}

export const api = {
  // Auth
  login: (credentials) => request('/auth/login', {
    method: 'POST',
    body: credentials,
  }),

  // Pedidos
  getPedidos: (params = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, value);
      }
    });
    return request(`/pedidos/?${searchParams.toString()}`);
  },

  getPedido: (id) => request(`/pedidos/${id}`),

  getPedidosByCliente: (clienteId) => request(`/pedidos/cliente/${clienteId}`),

  createPedido: (data) => request('/pedidos/', {
    method: 'POST',
    body: data,
  }),

  updatePedido: (id, data) => request(`/pedidos/${id}`, {
    method: 'PATCH',
    body: data,
  }),

  changeEstado: (id, estado) => request(`/pedidos/${id}/estado`, {
    method: 'PATCH',
    body: estado, // enviar string directamente
  }),

  deletePedido: (id) => request(`/pedidos/${id}`, {
    method: 'DELETE',
  }),

  // Clientes
  getClientes: () => request('/clientes/'),
  getCliente: (id) => request(`/clientes/${id}`),
  createCliente: (data) => request('/clientes/', { method: 'POST', body: data }),
  updateCliente: (id, data) => request(`/clientes/${id}`, { method: 'PATCH', body: data }),
  deleteCliente: (id) => request(`/clientes/${id}`, { method: 'DELETE' }),

  // Stock/Inventario
  getStock: (params = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, value);
      }
    });
    return request(`/inventario/?${searchParams.toString()}`);
  },
  getStockItem: (id) => request(`/inventario/${id}`),
  createStock: (data) => request('/inventario/', { method: 'POST', body: data }),
  updateStock: (id, data) => request(`/inventario/${id}`, { method: 'PATCH', body: data }),
  deleteStock: (id) => request(`/inventario/${id}`, { method: 'DELETE' }),
  addBolsa: (stockId, bolsa) => request(`/inventario/${stockId}/bolsas`, { method: 'POST', body: bolsa }),

  // Producción
  getOrdenesTueste: () => request('/produccion/ordenes'),
  createOrdenTueste: (data) => request('/produccion/ordenes', { method: 'POST', body: data }),

  // Gastos/Contabilidad
  getGastos: () => request('/gastos/'),
  createGasto: (data) => request('/gastos/', { method: 'POST', body: data }),
  updateGasto: (id, data) => request(`/gastos/${id}`, { method: 'PATCH', body: data }),
  deleteGasto: (id) => request(`/gastos/${id}`, { method: 'DELETE' }),

  // Health
  health: () => request('/health', { method: 'GET' }).catch(() => ({ status: 'error' })),
};

export { ApiError };
export default api;