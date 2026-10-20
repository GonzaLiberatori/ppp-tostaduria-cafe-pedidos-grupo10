import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { mockStock, mockClientes, mockPedidos, mockGastos } from '../data/mockData'

const DataContext = createContext(null)

const STORAGE_KEYS = {
  STOCK: 'cafe-finca-stock',
  CLIENTES: 'cafe-finca-clientes',
  PEDIDOS: 'cafe-finca-pedidos',
  GASTOS: 'cafe-finca-gastos',
}

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

// Helper para calcular kilos totales de un item de stock
function calcularKilosTotales(stockItem) {
  if (!stockItem.bolsas || !Array.isArray(stockItem.bolsas)) return 0
  return stockItem.bolsas.reduce((sum, bolsa) => sum + (bolsa.kilos || 0), 0)
}

// Helper para consumir kilos usando FIFO (primero abiertas, luego cerradas)
function consumirKilosFIFO(bolsas, kilosAConsumir) {
  const bolsasOrdenadas = [...bolsas].sort((a, b) => {
    // Primero abiertas (por fecha creacion ascendente), luego cerradas
    if (a.estado === 'abierta' && b.estado === 'cerrada') return -1
    if (a.estado === 'cerrada' && b.estado === 'abierta') return 1
    return new Date(a.fechaCreacion) - new Date(b.fechaCreacion)
  })

  let restantes = kilosAConsumir
  const consumo = []
  const nuevasBolsas = bolsas.map(b => ({ ...b }))

  for (const bolsa of bolsasOrdenadas) {
    if (restantes <= 0) break
    const idx = nuevasBolsas.findIndex(b => b.id === bolsa.id)
    if (idx === -1) continue

    const disponible = nuevasBolsas[idx].kilos
    const consumir = Math.min(disponible, restantes)
    
    if (consumir > 0) {
      nuevasBolsas[idx].kilos = disponible - consumir
      // Si era cerrada y se consumió algo, se vuelve abierta
      if (nuevasBolsas[idx].estado === 'cerrada' && consumir > 0) {
        nuevasBolsas[idx].estado = 'abierta'
      }
      consumo.push({ bolsaId: bolsa.id, consumido: consumir })
      restantes -= consumir
    }
  }

  // Eliminar bolsas vacías (kilos <= 0)
  const bolsasFinales = nuevasBolsas.filter(b => b.kilos > 0.001)

  return { bolsas: bolsasFinales, consumo, faltante: restantes }
}

export function DataProvider({ children }) {
  const [stock, setStock] = useState(() => loadFromStorage(STORAGE_KEYS.STOCK, mockStock))
  const [clientes, setClientes] = useState(() => loadFromStorage(STORAGE_KEYS.CLIENTES, mockClientes))
  const [pedidos, setPedidos] = useState(() => loadFromStorage(STORAGE_KEYS.PEDIDOS, mockPedidos))
  const [gastos, setGastos] = useState(() => loadFromStorage(STORAGE_KEYS.GASTOS, mockGastos))
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => { setIsLoaded(true) }, [])

  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.STOCK, stock) }, [stock, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.CLIENTES, clientes) }, [clientes, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.PEDIDOS, pedidos) }, [pedidos, isLoaded])
  useEffect(() => { if (isLoaded) saveToStorage(STORAGE_KEYS.GASTOS, gastos) }, [gastos, isLoaded])

  // --- Stock Actions ---
  const addStock = useCallback((item) => {
    const newItem = { 
      ...item, 
      id: crypto.randomUUID(), 
      fechaIngreso: new Date().toISOString(),
      bolsas: item.bolsas || []
    }
    setStock(prev => [...prev, newItem])
    return newItem
  }, [])

  const updateStock = useCallback((id, updates) => {
    setStock(prev => prev.map(item => item.id === id ? { ...item, ...updates } : item))
  }, [])

  const deleteStock = useCallback((id) => {
    setStock(prev => prev.filter(item => item.id !== id))
  }, [])

  // --- Bolsa Actions ---
  const addBolsa = useCallback((stockId, bolsa) => {
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      const nuevaBolsa = { ...bolsa, id: crypto.randomUUID(), fechaCreacion: new Date().toISOString() }
      return { ...item, bolsas: [...(item.bolsas || []), nuevaBolsa] }
    }))
  }, [])

  const updateBolsa = useCallback((stockId, bolsaId, updates) => {
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      return {
        ...item,
        bolsas: item.bolsas.map(b => b.id === bolsaId ? { ...b, ...updates } : b)
      }
    }))
  }, [])

  const deleteBolsa = useCallback((stockId, bolsaId) => {
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      return { ...item, bolsas: item.bolsas.filter(b => b.id !== bolsaId) }
    }))
  }, [])

  // Consumo FIFO para pedidos
  const consumirStockFIFO = useCallback((stockId, kilos) => {
    let consumoRealizado = []
    let faltante = 0
    
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      const resultado = consumirKilosFIFO(item.bolsas, kilos)
      consumoRealizado = resultado.consumo
      faltante = resultado.faltante
      return { ...item, bolsas: resultado.bolsas }
    }))
    
    return { consumo: consumoRealizado, faltante }
  }, [])

  // --- Cliente Actions ---
  const addCliente = useCallback((cliente) => {
    const newCliente = { ...cliente, id: crypto.randomUUID(), creadoEn: new Date().toISOString() }
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

  const getStockById = useCallback((id) => {
    return stock.find(s => s.id === id)
  }, [stock])

  const getPedidosByCliente = useCallback((clienteId) => {
    return pedidos.filter(p => p.clienteId === clienteId)
  }, [pedidos])

  const getStockByTipo = useCallback((tipo) => {
    return stock.filter(s => s.tipo === tipo)
  }, [stock])

  const getTotalKilosStock = useCallback((tipo) => {
    return stock
      .filter(s => s.tipo === tipo)
      .reduce((sum, s) => sum + calcularKilosTotales(s), 0)
  }, [stock])

  const getBolsasByEstado = useCallback((stockId, estado) => {
    const item = stock.find(s => s.id === stockId)
    if (!item) return []
    return item.bolsas.filter(b => b.estado === estado)
  }, [stock])

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
      totalKilosVerdes: getTotalKilosStock('verde'),
      totalKilosTostados: getTotalKilosStock('tostado'),
      clientesConDeuda: getClientesConDeuda().length,
      pedidosPendientes: getPedidosByEstado('Pendiente').length,
    }
  }, [getContabilidadMensual, getTotalKilosStock, getClientesConDeuda, getPedidosByEstado])

  const value = {
    // State
    stock,
    clientes,
    pedidos,
    gastos,
    isLoaded,
    // Stock
    addStock,
    updateStock,
    deleteStock,
    getStockById,
    getStockByTipo,
    getTotalKilosStock,
    // Bolsas
    addBolsa,
    updateBolsa,
    deleteBolsa,
    consumirStockFIFO,
    getBolsasByEstado,
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