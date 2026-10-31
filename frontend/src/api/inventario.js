/**
 * Servicio de inventario - mapea 1:1 a los endpoints del backend.
 */

import { api } from './client'

// ============================================================================
// Tipos de Café
// ============================================================================

export async function listarTiposDeCafe() {
  return api.get('/tipos-de-cafe')
}

export async function crearTipoDeCafe(datos) {
  return api.post('/tipos-de-cafe', datos)
}

export async function actualizarTipoDeCafe(id, datos) {
  return api.patch(`/tipos-de-cafe/${id}`, datos)
}

export async function eliminarTipoDeCafe(id) {
  return api.delete(`/tipos-de-cafe/${id}`)
}

// ============================================================================
// Blends
// ============================================================================

export async function listarBlends() {
  return api.get('/blends')
}

export async function crearBlend(datos) {
  return api.post('/blends', datos)
}

export async function actualizarBlend(id, datos) {
  return api.patch(`/blends/${id}`, datos)
}

export async function eliminarBlend(id) {
  return api.delete(`/blends/${id}`)
}

// ============================================================================
// Lotes
// ============================================================================

/**
 * Lista lotes filtrados por tipo_de_cafe_id o blend_id (XOR).
 * El backend requiere exactamente uno de los dos parámetros.
 */
export async function listarLotes({ tipoDeCafeId = null, blendId = null } = {}) {
  const params = new URLSearchParams()
  
  if (tipoDeCafeId && !blendId) {
    params.append('tipo_de_cafe_id', tipoDeCafeId)
  } else if (blendId && !tipoDeCafeId) {
    params.append('blend_id', blendId)
  } else {
    // Si no hay filtro o hay ambos, listar todos sin filtro
    // El backend exige XOR, así que necesitamos hacer múltiples llamadas
    // Por ahora, devolvemos array vacío si no hay filtro válido
    return []
  }
  
  return api.get(`/lotes?${params.toString()}`)
}

/**
 * Lista todos los lotes sin filtro.
 * Hace múltiples llamadas al backend para obtener todos los lotes.
 */
export async function listarTodosLosLotes(tiposDeCafe, blends) {
  const todosLosLotes = []
  
  // Obtener lotes por cada tipo de café
  for (const tipo of tiposDeCafe) {
    try {
      const lotes = await listarLotes({ tipoDeCafeId: tipo.id })
      todosLosLotes.push(...lotes)
    } catch (error) {
      console.error(`Error obteniendo lotes para tipo ${tipo.id}:`, error)
    }
  }
  
  // Obtener lotes por cada blend
  for (const blend of blends) {
    try {
      const lotes = await listarLotes({ blendId: blend.id })
      todosLosLotes.push(...lotes)
    } catch (error) {
      console.error(`Error obteniendo lotes para blend ${blend.id}:`, error)
    }
  }
  
  return todosLosLotes
}

export async function crearLote(datos) {
  return api.post('/lotes', datos)
}

export async function actualizarLote(id, datos) {
  return api.patch(`/lotes/${id}`, datos)
}

export async function eliminarLote(id) {
  return api.delete(`/lotes/${id}`)
}
