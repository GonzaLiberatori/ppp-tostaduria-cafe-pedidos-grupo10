export function calcularTotalPedido(items) {
  return items.reduce((sum, item) => sum + (item.kilos || 0) * (item.precioKg || 0), 0)
}

export function calcularKilosTotales(items) {
  return items.reduce((sum, item) => sum + (item.kilos || 0), 0)
}

export function calcularMerma(kilosVerdes, kilosTostados) {
  if (kilosVerdes <= 0) return 0
  return ((kilosVerdes - kilosTostados) / kilosVerdes) * 100
}

export function calcularRendimiento(kilosVerdes, kilosTostados) {
  if (kilosVerdes <= 0) return 0
  return (kilosTostados / kilosVerdes) * 100
}

export function agruparPorMes(datos, campoFecha) {
  const grupos = {}
  datos.forEach(item => {
    const mes = item[campoFecha].substring(0, 7)
    if (!grupos[mes]) grupos[mes] = []
    grupos[mes].push(item)
  })
  return grupos
}

export function sumarPorCampo(datos, campo) {
  return datos.reduce((sum, item) => sum + (item[campo] || 0), 0)
}

export function filtrarPorRangoFechas(datos, campoFecha, fechaInicio, fechaFin) {
  const inicio = new Date(fechaInicio).getTime()
  const fin = new Date(fechaFin).getTime()
  return datos.filter(item => {
    const fecha = new Date(item[campoFecha]).getTime()
    return fecha >= inicio && fecha <= fin
  })
}