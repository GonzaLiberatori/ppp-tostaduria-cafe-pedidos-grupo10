import { formatearMoneda, formatearKilos, formatearFecha, formatearFechaHora, getMesNombre } from '../data/constants'

export { formatearMoneda, formatearKilos, formatearFecha, formatearFechaHora, getMesNombre }

export function truncate(text, maxLength = 30) {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - 3) + '...'
}

export function classNames(...classes) {
  return classes.filter(Boolean).join(' ')
}