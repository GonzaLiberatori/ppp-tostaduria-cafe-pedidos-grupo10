/**
 * Cliente HTTP del panel.
 *
 * Centraliza la URL base, el token JWT y la traducción de errores de FastAPI
 * al formato que consumen los contextos y formularios.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const CLAVE_TOKEN = 'auth_token';
const CLAVE_USUARIO = 'user';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function extraerMensaje(data, status) {
  const detalle = data?.detail;

  if (Array.isArray(detalle)) {
    return detalle
      .map((item) => item?.msg || item?.message || String(item))
      .join('. ');
  }

  if (detalle && typeof detalle === 'object') {
    return detalle.msg || detalle.message || JSON.stringify(detalle);
  }

  return detalle || data?.message || `Error ${status}`;
}

function limpiarSesion() {
  localStorage.removeItem(CLAVE_TOKEN);
  localStorage.removeItem(CLAVE_USUARIO);
  localStorage.removeItem('cafe-finca-auth');
}

async function request(endpoint, options = {}) {
  const {
    method = 'GET',
    body,
    headers,
    manejar401 = true,
    autenticado = true,
  } = options;

  const token = autenticado ? localStorage.getItem(CLAVE_TOKEN) : null;
  const config = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  } catch (error) {
    throw new ApiError(
      'Error de conexión. Verifique que el backend esté corriendo.',
      0,
      { originalError: error.message },
    );
  }

  if (response.status === 401) {
    if (manejar401) {
      const teniaToken = Boolean(localStorage.getItem(CLAVE_TOKEN));
      limpiarSesion();
      if (teniaToken) {
        window.dispatchEvent(new Event('auth:expirada'));
      }
    }
    throw new ApiError('Sesión expirada o credenciales inválidas.', 401);
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(extraerMensaje(data, response.status), response.status, data);
  }

  return data;
}

function conQuery(endpoint, params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') {
      searchParams.append(clave, valor);
    }
  });

  const query = searchParams.toString();
  return query ? `${endpoint}?${query}` : endpoint;
}

export const api = {
  // Autenticación
  login: (credenciales) => request('/auth/login', {
    method: 'POST',
    body: credenciales,
    autenticado: false,
    manejar401: false,
  }),
  me: () => request('/auth/me'),

  // Pedidos del panel
  getPedidos: () => request('/pedidos/panel'),
  getPedidosByCliente: (clienteId) => request(`/pedidos/panel/cliente/${clienteId}`),
  createPedido: (data) => request('/pedidos/panel', { method: 'POST', body: data }),
  updatePedido: (id, data) => request(`/pedidos/panel/${id}`, { method: 'PATCH', body: data }),
  deletePedido: (id) => request(`/pedidos/panel/${id}`, { method: 'DELETE' }),

  // Clientes
  getClientes: () => request(conQuery('/clientes/')),
  getCliente: (id) => request(`/clientes/${id}`),
  createCliente: (data) => request('/clientes/', { method: 'POST', body: data }),
  updateCliente: (id, data) => request(`/clientes/${id}`, { method: 'PATCH', body: data }),
  deleteCliente: (id) => request(`/clientes/${id}`, { method: 'DELETE' }),

  // Inventario (contrato plano del panel)
  getStock: () => request('/inventario/stock'),
  getStockItem: (id) => request(`/inventario/stock/${id}`),
  createStock: (data) => request('/inventario/stock', { method: 'POST', body: data }),
  updateStock: (id, data) => request(`/inventario/stock/${id}`, { method: 'PATCH', body: data }),
  deleteStock: (id) => request(`/inventario/stock/${id}`, { method: 'DELETE' }),
  addBolsa: (stockId, bolsa) => request(
    `/inventario/stock/${stockId}/bolsas`,
    { method: 'POST', body: bolsa },
  ),
  updateBolsa: (stockId, bolsaId, data) => request(
    `/inventario/stock/${stockId}/bolsas/${bolsaId}`,
    { method: 'PATCH', body: data },
  ),
  deleteBolsa: (stockId, bolsaId) => request(
    `/inventario/stock/${stockId}/bolsas/${bolsaId}`,
    { method: 'DELETE' },
  ),

  // Gastos
  getGastos: () => request(conQuery('/gastos/')),
  createGasto: (data) => request('/gastos/', { method: 'POST', body: data }),
  updateGasto: (id, data) => request(`/gastos/${id}`, { method: 'PATCH', body: data }),
  deleteGasto: (id) => request(`/gastos/${id}`, { method: 'DELETE' }),
};

export { ApiError };
export default api;
