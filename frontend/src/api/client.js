/**
 * Cliente HTTP para la API del backend.
 * 
 * Wrapper de fetch con métodos get/post/patch/delete.
 * Base URL desde variable de entorno VITE_API_BASE_URL.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/inventario'

/**
 * Error personalizado para respuestas HTTP con error.
 */
export class ApiError extends Error {
  constructor(status, detail, data = null) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.data = data
  }
}

/**
 * Realiza una petición HTTP y maneja la respuesta.
 */
async function request(method, path, body = null) {
  const url = `${BASE_URL}${path}`
  const config = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }

  if (body) {
    config.body = JSON.stringify(body)
  }

  try {
    const response = await fetch(url, config)

    // 204 No Content (DELETE exitoso)
    if (response.status === 204) {
      return null
    }

    const data = await response.json()

    if (!response.ok) {
      // FastAPI devuelve { detail: "..." } o { detail: [{ msg, loc, type }] }
      const detail = typeof data.detail === 'string'
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map(e => e.msg).join(', ')
          : 'Error desconocido'
      
      throw new ApiError(response.status, detail, data)
    }

    return data
  } catch (error) {
    // Si es un error de red (sin conexión)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new ApiError(0, 'No se pudo conectar con el servidor. Verificá que el backend esté corriendo.')
    }
    // Si ya es un ApiError, lo relanzo
    if (error instanceof ApiError) {
      throw error
    }
    // Cualquier otro error
    throw new ApiError(0, error.message || 'Error inesperado')
  }
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),
}
