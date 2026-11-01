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
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);
    
    // Handle 401 - token expired or invalid
    if (response.status === 401) {
      // Sin token no hay una sesión real que expirar: el frontend de demo usa
      // autenticación mock y algunos endpoints protegidos responden 401. En ese
      // caso se propaga el error para que el consumidor haga su fallback, sin
      // redirigir (redirigir acá provoca un bucle de recargas con el login mock).
      if (token) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
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

    return data;
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

  // Inventario (endpoints canónicos)
  getTiposDeCafe: () => request('/inventario/tipos-de-cafe'),
  getLotes: (params = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, value);
      }
    });
    return request(`/inventario/lotes?${searchParams.toString()}`);
  },
  getLote: (id) => request(`/inventario/lotes/${id}`),

  // Producción
  getTuestes: () => request('/produccion/tuestes'),
  createTueste: (data) => request('/produccion/tuestes', { method: 'POST', body: data }),

  // Stock/Inventario (endpoints heredados)
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