// Helpers de presentación y cálculo para cafés y lotes.

export function nombreCafe(cafe) {
  if (!cafe) return ''
  return cafe.tipoProducto === 'blend' ? cafe.nombre : cafe.variedad
}

export function origenCafe(cafe) {
  if (!cafe) return ''
  if (cafe.tipoProducto === 'blend') {
    const componentes = cafe.mezcla?.length || 0
    return `Blend · ${componentes} variedad${componentes !== 1 ? 'es' : ''}`
  }
  return [cafe.pais, cafe.region].filter(Boolean).join(' - ')
}

export function kilosPorTipo(lotes = [], tipo) {
  return lotes
    .filter(lote => lote.tipo === tipo)
    // Se usa el stock disponible (no los kg reales de alta): los lotes ya
    // vendidos conservan su peso original, pero solo cuentan los kg que quedan.
    .reduce((sum, lote) => {
      const disponible = lote.kgDisponibles ?? lote.kilos
      return sum + (Number(disponible) || 0)
    }, 0)
}

export function kilosCafe(cafe, tipo) {
  return kilosPorTipo(cafe?.lotes || [], tipo)
}

// El backend identifica cada producto vendible con un `stockId` del tipo
// `tc-<id>-TOSTADO` (tipo de café) o `bl-<id>-TOSTADO` (blend). El sufijo
// cambia a `VERDE` cuando se compra materia prima.
export function stockIdDeCafe(cafe, tipo = 'tostado') {
  if (!cafe) return ''
  const entidadId = cafe.entidadId ?? cafe.id
  if (!entidadId) return ''
  const prefijo = cafe.tipoProducto === 'blend' ? 'bl' : 'tc'
  const sufijoTipo = tipo === 'verde' ? 'VERDE' : 'TOSTADO'
  return `${prefijo}-${entidadId}-${sufijoTipo}`
}

// Un blend se considera orgánico cuando todos sus componentes simples lo son.
export function esOrganico(cafe, cafesPorId) {
  if (!cafe) return false
  if (cafe.tipoProducto !== 'blend') return !!cafe.organico
  const componentes = (cafe.mezcla || []).map(m => cafesPorId?.[m.cafeId]).filter(Boolean)
  if (componentes.length === 0) return false
  return componentes.every(c => !!c.organico)
}

export function lotesPorEstado(cafe, estado) {
  return (cafe?.lotes || []).filter(lote => lote.estado === estado)
}

// Sugiere porcentajes de mezcla proporcionales a los kilos verdes disponibles.
export function sugerirPorcentajes(cafesSeleccionados) {
  if (cafesSeleccionados.length === 0) return []
  const pesos = cafesSeleccionados.map(c => Math.max(kilosCafe(c, 'verde'), 0))
  const totalPeso = pesos.reduce((a, b) => a + b, 0)

  if (totalPeso <= 0) {
    const base = Math.floor(100 / cafesSeleccionados.length)
    return cafesSeleccionados.map((c, i) => ({
      cafeId: c.entidadId ?? c.id,
      porcentaje: i === 0 ? base + (100 - base * cafesSeleccionados.length) : base,
    }))
  }

  const resultado = cafesSeleccionados.map((c, i) => ({
    cafeId: c.entidadId ?? c.id,
    porcentaje: Math.round((pesos[i] / totalPeso) * 100),
  }))

  const suma = resultado.reduce((sum, m) => sum + m.porcentaje, 0)
  if (resultado.length > 0 && suma !== 100) {
    const mayor = resultado.reduce((maxIdx, m, i) => (m.porcentaje > resultado[maxIdx].porcentaje ? i : maxIdx), 0)
    resultado[mayor].porcentaje += 100 - suma
  }
  return resultado
}
