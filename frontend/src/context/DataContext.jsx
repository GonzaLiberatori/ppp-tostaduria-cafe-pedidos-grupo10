import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { mockCafes, mockOrdenesTueste, mockClientes, mockPedidos, mockGastos } from '../data/mockData'
import { kilosPorTipo } from '../utils/cafes'

const DataContext = createContext(null)

const STORAGE_KEYS = {
  CAFES: 'cafe-finca-cafes-v2',
  CLIENTES: 'cafe-finca-clientes',
  PEDIDOS: 'cafe-finca-pedidos',
  GASTOS: 'cafe-finca-gastos',
}

const LEGACY_STOCK_KEY = 'cafe-finca-stock'

function loadFromStorage(key, fallback) {
  try {
    const stored = localStorage.getItem(key)
    return stored ? JSON.parse(stored) : fallback
  } catch {
    return fallback
  }
}

function saveToStorage(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data))
  } catch (error) {
    console.error(`Error guardando ${key}:`, error)
  }
}

// Consumo FIFO: primero lotes abiertos, luego cerrados, ambos por antigüedad.
// Solo se descuentan lotes de café tostado (producto terminado).
function consumirLotesFIFO(lotes = [], kilosAConsumir) {
  const ordenados = lotes
    .filter(lote => lote.tipo === 'tostado')
    .sort((a, b) => {
      if (a.estado === 'abierto' && b.estado === 'cerrado') return -1
      if (a.estado === 'cerrado' && b.estado === 'abierto') return 1
      return new Date(a.fechaCreacion) - new Date(b.fechaCreacion)
    })

  let restantes = kilosAConsumir
  const consumo = []
  const nuevasLotes = lotes.map(l => ({ ...l }))

  for (const lote of ordenados) {
    if (restantes <= 0) break
    const idx = nuevasLotes.findIndex(l => l.id === lote.id)
    if (idx === -1) continue

    const disponible = nuevasLotes[idx].kilos || 0
    const consumir = Math.min(disponible, restantes)

    if (consumir > 0) {
      nuevasLotes[idx].kilos = disponible - consumir
      if (nuevasLotes[idx].estado === 'cerrado') {
        nuevasLotes[idx].estado = 'abierto'
      }
      consumo.push({ loteId: lote.id, consumido: consumir })
      restantes -= consumir
    }
  }

  const lotesFinales = nuevasLotes.filter(l => (l.kilos || 0) > 0.001)

  return { lotes: lotesFinales, consumo, faltante: Math.max(restantes, 0) }
}

export function DataProvider({ children }) {
  const [cafes, setCafes] = useState(() => loadFromStorage(STORAGE_KEYS.CAFES, mockCafes))
  const [clientes, setClientes] = useState(() => loadFromStorage(STORAGE_KEYS.CLIENTES, mockClientes))
  const [pedidos, setPedidos] = useState(() => loadFromStorage(STORAGE_KEYS.PEDIDOS, mockPedidos))
  const [gastos, setGastos] = useState(() => loadFromStorage(STORAGE_KEYS.GASTOS, mockGastos))
  const [ordenesTueste] = useState(mockOrdenesTueste)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // El modelo anterior de stock (cafés con bolsas) queda descartado.
    localStorage.removeItem(LEGACY_STOCK_KEY)
    setIsLoaded(true)
  }, [])

  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.CAFES, cafes) }, [cafes, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.CLIENTES, clientes) }, [clientes, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.PEDIDOS, pedidos) }, [pedidos, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.GASTOS, gastos) }, [gastos, isLoaded])

  // --- Café Actions ---
  const addCafe = useCallback((cafe) => {
    const nuevoCafe = {
      ...cafe,
      id: crypto.randomUUID(),
      fechaIngreso: new Date().toISOString(),
      lotes: [],
    }
    setCafes(prev => [...prev, nuevoCafe])
    return nuevoCafe
  }, [])

  const updateCafe = useCallback((id, updates) => {
    setCafes(prev => prev.map(cafe => (cafe.id === id ? { ...cafe, ...updates } : cafe)))
  }, [])

  const deleteCafe = useCallback((id) => {
    setCafes(prev => prev.filter(cafe => cafe.id !== id))
  }, [])

  // --- Lote Actions ---
  const addLote = useCallback((cafeId, lote) => {
    const nuevoLote = {
      ...lote,
      id: crypto.randomUUID(),
      fechaCreacion: new Date().toISOString(),
    }
    setCafes(prev => prev.map(cafe => (
      cafe.id === cafeId ? { ...cafe, lotes: [...(cafe.lotes || []), nuevoLote] } : cafe
    )))
    return nuevoLote
  }, [])

  const updateLote = useCallback((cafeId, loteId, updates) => {
    setCafes(prev => {
      const origen = prev.find(cafe => cafe.id === cafeId)
      const lote = origen?.lotes?.find(l => l.id === loteId)
      if (!origen || !lote) return prev

      const { cafeId: cafeDestinoId, ...resto } = updates
      const loteActualizado = { ...lote, ...resto }

      if (cafeDestinoId && cafeDestinoId !== cafeId) {
        return prev.map(cafe => {
          if (cafe.id === cafeId) {
            return { ...cafe, lotes: cafe.lotes.filter(l => l.id !== loteId) }
          }
          if (cafe.id === cafeDestinoId) {
            return { ...cafe, lotes: [...(cafe.lotes || []), loteActualizado] }
          }
          return cafe
        })
      }

      return prev.map(cafe => (
        cafe.id === cafeId
          ? { ...cafe, lotes: cafe.lotes.map(l => (l.id === loteId ? loteActualizado : l)) }
          : cafe
      ))
    })
  }, [])

  const deleteLote = useCallback((cafeId, loteId) => {
    setCafes(prev => prev.map(cafe => (
      cafe.id === cafeId
        ? { ...cafe, lotes: (cafe.lotes || []).filter(l => l.id !== loteId) }
        : cafe
    )))
  }, [])

  // --- Consumo de stock (ventas) ---
  const previewConsumoFIFO = useCallback((cafeId, kilos) => {
    const cafe = cafes.find(c => c.id === cafeId)
    if (!cafe) return { consumo: [], faltante: kilos }
    const { consumo, faltante } = consumirLotesFIFO(cafe.lotes || [], kilos)
    return { consumo, faltante }
  }, [cafes])

  const consumirStockFIFO = useCallback((cafeId, kilos) => {
    const cafe = cafes.find(c => c.id === cafeId)
    if (!cafe) return { consumo: [], faltante: kilos }
    const { lotes, consumo, faltante } = consumirLotesFIFO(cafe.lotes || [], kilos)
    setCafes(prev => prev.map(c => (c.id === cafeId ? { ...c, lotes } : c)))
    return { consumo, faltante }
  }, [cafes])

  // --- Cliente Actions ---
  const addCliente = useCallback((cliente) => {
    const newCliente = { ...cliente, id: cliente.id || crypto.randomUUID(), creadoEn: new Date().toISOString() }
    setClientes(prev => [...prev, newCliente])
    return newCliente
  }, [])

  const updateCliente = useCallback((id, updates) => {
    setClientes(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c))
  }, [])

  const deleteCliente = useCallback((id) => {
    setClientes(prev => prev.filter(c => c.id !== id))
  }, [])

  // --- Pedido Actions ---
  const addPedido = useCallback((pedido) => {
    const newPedido = { ...pedido, id: crypto.randomUUID(), fecha: new Date().toISOString() }
    setPedidos(prev => [...prev, newPedido])
    return newPedido
  }, [])

  const updatePedido = useCallback((id, updates) => {
    setPedidos(prev => prev.map(p => p.id === id ? { ...p, ...updates } : p))
  }, [])

  const deletePedido = useCallback((id) => {
    setPedidos(prev => prev.filter(p => p.id !== id))
  }, [])

  // --- Gasto Actions ---
  const addGasto = useCallback((gasto) => {
    const newGasto = { ...gasto, id: crypto.randomUUID(), fecha: new Date().toISOString() }
    setGastos(prev => [...prev, newGasto])
    return newGasto
  }, [])

  const updateGasto = useCallback((id, updates) => {
    setGastos(prev => prev.map(g => g.id === id ? { ...g, ...updates } : g))
  }, [])

  const deleteGasto = useCallback((id) => {
    setGastos(prev => prev.filter(g => g.id !== id))
  }, [])

  // --- Computed / Helpers ---
  const getClienteById = useCallback((id) => {
    return clientes.find(c => c.id === id)
  }, [clientes])

  const getCafeById = useCallback((id) => {
    return cafes.find(c => c.id === id)
  }, [cafes])

  const getCafesByTipoProducto = useCallback((tipoProducto) => {
    return cafes.filter(c => c.tipoProducto === tipoProducto)
  }, [cafes])

  const getKilosPorTipo = useCallback((cafe, tipo) => {
    return kilosPorTipo(cafe?.lotes || [], tipo)
  }, [])

  const getTotalKilosPorTipo = useCallback((tipo) => {
    return cafes.reduce((sum, cafe) => sum + kilosPorTipo(cafe.lotes || [], tipo), 0)
  }, [cafes])

  const getCafesConTostado = useCallback(() => {
    return cafes.filter(cafe => kilosPorTipo(cafe.lotes || [], 'tostado') > 0)
  }, [cafes])

  const getLotesByEstado = useCallback((cafeId, estado) => {
    const cafe = cafes.find(c => c.id === cafeId)
    if (!cafe) return []
    return (cafe.lotes || []).filter(lote => lote.estado === estado)
  }, [cafes])

  const getOrdenTuesteById = useCallback((id) => {
    return ordenesTueste.find(orden => orden.id === id)
  }, [ordenesTueste])

  const getPedidosByCliente = useCallback((clienteId) => {
    return pedidos.filter(p => p.clienteId === clienteId)
  }, [pedidos])

  const getClientesConDeuda = useCallback(() => {
    return clientes.filter(c => c.tieneDeuda && c.montoDeuda > 0)
  }, [clientes])

  const getPedidosByEstado = useCallback((estado) => {
    return pedidos.filter(p => p.estado === estado)
  }, [pedidos])

  // Contabilidad computada
  const getContabilidadMensual = useCallback(() => {
    const ventasPorMes = {}
    const gastosPorMes = {}

    pedidos
      .filter(p => p.estado === 'Entregado')
      .forEach(p => {
        const mes = p.fecha.substring(0, 7)
        if (!ventasPorMes[mes]) ventasPorMes[mes] = 0
        ventasPorMes[mes] += p.total || 0
      })

    gastos.forEach(g => {
      const mes = g.fecha.substring(0, 7)
      if (!gastosPorMes[mes]) gastosPorMes[mes] = 0
      gastosPorMes[mes] += g.monto || 0
    })

    const allMeses = new Set([...Object.keys(ventasPorMes), ...Object.keys(gastosPorMes)])
    return Array.from(allMeses)
      .sort()
      .reverse()
      .map(mes => ({
        mes,
        ventasTotales: ventasPorMes[mes] || 0,
        gastosTotales: gastosPorMes[mes] || 0,
        gananciaNeta: (ventasPorMes[mes] || 0) - (gastosPorMes[mes] || 0),
      }))
  }, [pedidos, gastos])

  const getTotalesGenerales = useCallback(() => {
    const contabilidad = getContabilidadMensual()
    return {
      ventasTotales: contabilidad.reduce((sum, m) => sum + m.ventasTotales, 0),
      gastosTotales: contabilidad.reduce((sum, m) => sum + m.gastosTotales, 0),
      gananciaNeta: contabilidad.reduce((sum, m) => sum + m.gananciaNeta, 0),
      totalKilosVerdes: getTotalKilosPorTipo('verde'),
      totalKilosTostados: getTotalKilosPorTipo('tostado'),
      clientesConDeuda: getClientesConDeuda().length,
      pedidosPendientes: getPedidosByEstado('Pendiente').length,
    }
  }, [getContabilidadMensual, getTotalKilosPorTipo, getClientesConDeuda, getPedidosByEstado])

  const value = {
    // State
    cafes,
    ordenesTueste,
    clientes,
    pedidos,
    gastos,
    isLoaded,
    // Cafés
    addCafe,
    updateCafe,
    deleteCafe,
    getCafeById,
    getCafesByTipoProducto,
    getKilosPorTipo,
    getTotalKilosPorTipo,
    getCafesConTostado,
    // Lotes
    addLote,
    updateLote,
    deleteLote,
    getLotesByEstado,
    getOrdenTuesteById,
    previewConsumoFIFO,
    consumirStockFIFO,
    // Clientes
    addCliente,
    updateCliente,
    deleteCliente,
    getClienteById,
    getClientesConDeuda,
    getPedidosByCliente,
    // Pedidos
    addPedido,
    updatePedido,
    deletePedido,
    getPedidosByEstado,
    // Gastos
    addGasto,
    updateGasto,
    deleteGasto,
    // Contabilidad
    getContabilidadMensual,
    getTotalesGenerales,
  }

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (!context) {
    throw new Error('useData must be used within a DataProvider')
  }
  return context
}
