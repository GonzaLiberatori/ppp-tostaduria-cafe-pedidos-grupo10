export const TIPOS_STOCK = [
  { value: 'verde', label: 'Café Verde' },
  { value: 'tostado', label: 'Café Tostado' },
]

export const ESTADOS_PEDIDO = [
  { value: 'Pendiente', label: 'Pendiente', color: 'warning' },
  { value: 'Listo', label: 'Listo', color: 'info' },
  { value: 'Entregado', label: 'Entregado', color: 'success' },
]

export const TIPOS_CLIENTE = [
  { value: 'B2B', label: 'Mayorista (B2B)' },
  { value: 'B2C', label: 'Minorista (B2C)' },
]

export const MEDIOS_CONTACTO = [
  { value: 'WhatsApp', label: 'WhatsApp' },
  { value: 'Email', label: 'Email' },
  { value: 'Teléfono', label: 'Teléfono' },
  { value: 'Presencial', label: 'Presencial' },
]

export const CATEGORIAS_GASTO = [
  { value: 'Producción', label: 'Producción' },
  { value: 'Operativo', label: 'Operativo' },
  { value: 'Marketing', label: 'Marketing' },
  { value: 'Otro', label: 'Otro' },
]

export const ESTADOS_BOLSA = [
  { value: 'cerrada', label: 'Cerrada', color: 'success' },
  { value: 'abierta', label: 'Abierta', color: 'warning' },
]

export const ESTADO_COLORS = {
  Pendiente: 'badge-warning',
  Listo: 'badge-info',
  Entregado: 'badge-success',
}

export const TIPO_CLIENTE_COLORS = {
  B2B: 'badge-coffee',
  B2C: 'badge-info',
}

export const CATEGORIA_GASTO_COLORS = {
  Producción: 'badge-coffee',
  Operativo: 'badge-info',
  Marketing: 'badge-warning',
  Otro: 'badge-success',
}

export const ESTADO_BOLSA_COLORS = {
  cerrada: 'badge-success',
  abierta: 'badge-warning',
}

export const MEDIOS_PAGO = [
  { value: 'transferencia', label: 'Transferencia bancaria' },
  { value: 'tarjeta', label: 'Tarjeta de crédito/débito' },
  { value: 'efectivo', label: 'Efectivo' },
]

export const FRECUENCIA_SUSCRIPCION = [
  { value: 'semanal', label: 'Semanal' },
  { value: 'mensual', label: 'Mensual' },
]

export const ESTADO_PEDIDO_CLIENTE = [
  { value: 'Pendiente', label: 'Pendiente', color: 'warning' },
  { value: 'Listo', label: 'Listo para retirar', color: 'info' },
  { value: 'Entregado', label: 'Entregado', color: 'success' },
]

export const MESES_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

export function formatearMoneda(valor) {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(valor)
}

export function formatearKilos(kilos) {
  return new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(kilos) + ' kg'
}

export function formatearFecha(fechaISO, opciones = {}) {
  const defaultOptions = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...opciones,
  }
  return new Date(fechaISO).toLocaleDateString('es-AR', defaultOptions)
}

export function formatearFechaHora(fechaISO) {
  return new Date(fechaISO).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getMesNombre(mesISO) {
  const [year, month] = mesISO.split('-')
  return `${MESES_ES[parseInt(month) - 1]} ${year}`
}

export function generarId() {
  return crypto.randomUUID()
}