/**
 * Mappers para traducir entre el modelo del frontend (cafés unificados)
 * y el modelo del backend (TipoDeCafe, Blend, Lote separados).
 */

// ============================================================================
// Backend → Frontend
// ============================================================================

/**
 * Convierte un TipoDeCafe del backend en un café simple del frontend.
 */
export function tipoDeCafeToFrontend(tipo) {
  return {
    id: tipo.id,
    tipoProducto: 'simple',
    variedad: tipo.variedad,
    region: tipo.region,
    pais: tipo.pais,
    organico: tipo.organico,
    precioKg: Number(tipo.precio_por_kg_verde),
    nombre: '',
    descripcion: '',
    mezcla: [],
    lotes: [],
  }
}

/**
 * Convierte un Blend del backend en un café blend del frontend.
 */
export function blendToFrontend(blend) {
  return {
    id: blend.id,
    tipoProducto: 'blend',
    nombre: blend.nombre,
    descripcion: blend.descripcion,
    precioKg: Number(blend.precio_por_kg_verde),
    variedad: '',
    region: '',
    pais: '',
    organico: false,
    mezcla: blend.tipos_de_cafe.map(item => ({
      cafeId: item.tipo_de_cafe_id,
      porcentaje: Number(item.porcentaje),
    })),
    lotes: [],
  }
}

/**
 * Convierte un Lote del backend en un lote del frontend.
 */
export function loteToFrontend(lote) {
  return {
    id: lote.id,
    tipo: lote.tipo.toLowerCase(),
    estado: lote.estado.toLowerCase(),
    vencimiento: lote.fecha_vencimiento,
    humedad: Number(lote.humedad),
    kilos: Number(lote.kg_reales),
    kgDisponibles: Number(lote.kg_disponibles),
    ubicacion: lote.ubicacion_fisica,
    observaciones: lote.observaciones || '',
    ordenTuesteId: lote.orden_tueste_id,
    cafeId: lote.tipo_de_cafe_id || lote.blend_id,
  }
}

/**
 * Ensambla los cafés unificados del frontend a partir de las 3 respuestas del backend.
 */
export function ensamblarCafes(tiposDeCafe, blends, lotes) {
  // Crear mapa de cafés por ID
  const cafesMap = new Map()

  // Agregar tipos de café
  tiposDeCafe.forEach(tipo => {
    cafesMap.set(tipo.id, tipoDeCafeToFrontend(tipo))
  })

  // Agregar blends
  blends.forEach(blend => {
    cafesMap.set(blend.id, blendToFrontend(blend))
  })

  // Asignar lotes a sus cafés padre
  lotes.forEach(lote => {
    const loteFrontend = loteToFrontend(lote)
    const cafeId = lote.tipo_de_cafe_id || lote.blend_id
    
    if (cafeId && cafesMap.has(cafeId)) {
      cafesMap.get(cafeId).lotes.push(loteFrontend)
    }
  })

  // Convertir mapa a array
  return Array.from(cafesMap.values())
}

// ============================================================================
// Frontend → Backend
// ============================================================================

/**
 * Convierte un café simple del frontend en el payload para crear/actualizar TipoDeCafe.
 */
export function cafeSimpleToBackend(cafe) {
  return {
    variedad: cafe.variedad,
    region: cafe.region,
    pais: cafe.pais,
    organico: cafe.organico,
    precio_por_kg_verde: cafe.precioKg,
  }
}

/**
 * Convierte un café blend del frontend en el payload para crear/actualizar Blend.
 */
export function cafeBlendToBackend(cafe) {
  return {
    nombre: cafe.nombre,
    descripcion: cafe.descripcion,
    precio_por_kg_verde: cafe.precioKg,
    tipos_de_cafe: cafe.mezcla.map(item => ({
      tipo_de_cafe_id: item.cafeId,
      porcentaje: item.porcentaje,
    })),
  }
}

/**
 * Convierte un lote del frontend en el payload para crear Lote.
 * Necesita el café padre para determinar si es tipo_de_cafe_id o blend_id.
 */
export function loteToBackendCreate(lote, cafePadre) {
  const payload = {
    tipo: lote.tipo.toUpperCase(),
    estado: lote.estado.toUpperCase(),
    fecha_vencimiento: lote.vencimiento,
    humedad: lote.humedad,
    kg_reales: lote.kilos,
    ubicacion_fisica: lote.ubicacion,
    observaciones: lote.observaciones,
    orden_tueste_id: lote.ordenTuesteId,
  }

  // Determinar si el café padre es simple o blend
  if (cafePadre.tipoProducto === 'simple') {
    payload.tipo_de_cafe_id = cafePadre.id
  } else {
    payload.blend_id = cafePadre.id
  }

  return payload
}

/**
 * Convierte un lote del frontend en el payload para actualizar Lote.
 * El backend solo permite actualizar ciertos campos (no tipo ni FKs).
 */
export function loteToBackendUpdate(lote) {
  return {
    estado: lote.estado.toUpperCase(),
    fecha_vencimiento: lote.vencimiento,
    humedad: lote.humedad,
    kg_reales: lote.kilos,
    ubicacion_fisica: lote.ubicacion,
    observaciones: lote.observaciones,
  }
}
