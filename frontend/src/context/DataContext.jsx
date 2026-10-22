import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { mockStock, mockClientes, mockPedidos, mockGastos } from '../data/mockData'
import { api, ApiError } from '../services/api'

const DataContext = createContext(null)

export function DataProvider({ children }) {
  const [stock, setStock] = useState([])
  const [clientes, setClientes] = useState([])
  const [pedidos, setPedidos] = useState([])
  const [gastos, setGastos] = useState([])
  const [isLoaded, setIsLoaded] = useState(false)
  const [loading, setLoading] = useState({})
  const [errors, setErrors] = useState({})

  // --- Carga inicial desde API ---
  useEffect(() => {
    async function loadAll() {
      setLoading(prev => ({ ...prev, initial: true }))
      setErrors({})
      try {
        const [stockRes, clientesRes, pedidosRes, gastosRes] = await Promise.all([
          api.getStock(),
          api.getClientes(),
          api.getPedidos(),
          api.getGastos(),
        ])
        setStock(stockRes || [])
        setClientes(clientesRes || [])
        setPedidos(pedidosRes || [])
        setGastos(gastosRes || [])
      } catch (err) {
        console.error('Error cargando datos iniciales:', err)
        setErrors(prev => ({ ...prev, initial: err.message }))
        // Fallback a mock data si falla la API
        setStock(mockStock)
        setClientes(mockClientes)
        setPedidos(mockPedidos)
        setGastos(mockGastos)
      } finally {
        setIsLoaded(true)
        setLoading(prev => ({ ...prev, initial: false }))
      }
    }
    loadAll()
  }, [])

  // --- Helpers ---
  const withLoading = useCallback((key, fn) => async (...args) => {
    setLoading(prev => ({ ...prev, [key]: true }))
    setErrors(prev => ({ ...prev, [key]: null }))
    try {
      return await fn(...args)
    } catch (err) {
      setErrors(prev => ({ ...prev, [key]: err.message }))
      throw err
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }))
    }
  }, [])

  // --- Stock Actions (API) ---
  const addStock = withLoading('stock', async (item) => {
    const newItem = await api.createStock({ ...item, bolsas: item.bolsas || [] })
    setStock(prev => [...prev, newItem])
    return newItem
  })

  const updateStock = withLoading('stock', async (id, updates) => {
    await api.updateStock(id, updates)
    setStock(prev => prev.map(item => item.id === id ? { ...item, ...updates } : item))
  })

  const deleteStock = withLoading('stock', async (id) => {
    await api.deleteStock(id)
    setStock(prev => prev.filter(item => item.id !== id))
  })

  // --- Bolsa Actions (API) ---
  const addBolsa = withLoading('stock', async (stockId, bolsa) => {
    const newBolsa = await api.addBolsa(stockId, bolsa)
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      return { ...item, bolsas: [...(item.bolsas || []), newBolsa] }
    }))
    return newBolsa
  })

  const updateBolsa = withLoading('stock', async (stockId, bolsaId, updates) => {
    // Backend doesn't have separate bolsa update yet, update stock
    await api.updateStock(stockId, {})  // trigger refresh
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      return { ...item, bolsas: item.bolsas.map(b => b.id === bolsaId ? { ...b, ...updates } : b) }
    }))
  })

  const deleteBolsa = withLoading('stock', async (stockId, bolsaId) => {
    await api.updateStock(stockId, {})
    setStock(prev => prev.map(item => {
      if (item.id !== stockId) return item
      return { ...item, bolsas: item.bolsas.filter(b => b.id !== bolsaId) }
    }))
  })

  // Consumo FIFO - ahora delega al backend via crear_pedido
  const consumirStockFIFO = useCallback(async (stockId, kilos) => {
    // El consumo real ocurre en el backend al crear pedido
    // Este método se mantiene para compatibilidad con preview en frontend
    const item = stock.find(s => s.id === stockId)
    if (!item) return { consumo: [], faltante: kilos }
    
    // Simular preview local (igual que antes)
    const bolsasOrdenadas = [...(item.bolsas || [])].sort((a, b) => {
      if (a.estado === 'abierta' && b.estado === 'cerrada') return -1
      if (a.estado === 'cerrada' && b.estado === 'abierta') return 1
      return new Date(a.fechaCreacion) - new Date(b.fechaCreacion)
    })
    
    let restantes = kilos
    const consumo = []
    const nuevasBolsas = bolsasOrdenadas.map(b => ({ ...b }))

    for (const bolsa of bolsasOrdenadas) {
      if (restantes <= 0) break
      const idx = nuevasBolsas.findIndex(b => b.id === bolsa.id)
      if (idx === -1) continue

      const disponible = nuevasBolsas[idx].kilos
      const consumir = Math.min(disponible, restantes)
      
      if (consumir > 0) {
        nuevasBolsas[idx].kilos = disponible - consumir
        if (nuevasBolsas[idx].estado === 'cerrada' && consumir > 0) {
          nuevasBolsas[idx].estado = 'abierta'
        }
        consumo.push({ bolsaId: bolsa.id, consumido: consumir })
        restantes -= consumir
      }
    }

    const bolsasFinales = nuevasBolsas.filter(b => b.kilos > 0.001)
    return { consumo, faltante: restantes }
  }, [stock])

  // --- Cliente Actions (API) ---
  const addCliente = withLoading('clientes', async (cliente) => {
    const newCliente = await api.createCliente(cliente)
    setClientes(prev => [...prev, newCliente])
    return newCliente
  })

  const updateCliente = withLoading('clientes', async (id, updates) => {
    await api.updateCliente(id, updates)
    setClientes(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c))
  })

  const deleteCliente = withLoading('clientes', async (id) => {
    await api.deleteCliente(id)
    setClientes(prev => prev.filter(c => c.id !== id))
  })

  // --- Pedido Actions (API) ---
  const addPedido = withLoading('pedidos', async (pedido) => {
    const newPedido = await api.createPedido(pedido)
    setPedidos(prev => [...prev, newPedido])
    
    // Refrescar stock y clientes (cuenta corriente) después de crear pedido
    try {
      const [stockRes, clientesRes] = await Promise.all([
        api.getStock(),
        api.getClientes(),
      ])
      setStock(stockRes || [])
      setClientes(clientesRes || [])
    } catch (err) {
      console.warn('No se pudo refrescar stock/clientes tras crear pedido:', err)
    }
    
    return newPedido
  })

  const updatePedido = withLoading('pedidos', async (id, updates) => {
    await api.updatePedido(id, updates)
    setPedidos(prev => prev.map(p => p.id === id ? { ...p, ...updates } : p))
  })

  const deletePedido = withLoading('pedidos', async (id) => {
    await api.deletePedido(id)
    setPedidos(prev => prev.filter(p => p.id !== id))
    
    // Refrescar stock y clientes tras eliminar
    try {
      const [stockRes, clientesRes] = await Promise.all([
        api.getStock(),
        api.getClientes(),
      ])
      setStock(stockRes || [])
      setClientes(clientesRes || [])
    } catch (err) {
      console.warn('No se pudo refrescar stock/clientes tras eliminar pedido:', err)
    }
  })

  const changeEstado = withLoading('pedidos', async (id, nuevoEstado) => {
    const updated = await api.changeEstado(id, nuevoEstado)
    setPedidos(prev => prev.map(p => p.id === id ? updated : p))
    
    // Refrescar cliente (cuenta corriente) si B2B
    try {
      const clientesRes = await api.getClientes()
      setClientes(clientesRes || [])
    } catch (err) {
      console.warn('No se pudo refrescar clientes tras cambio estado:', err)
    }
    
    return updated
  })

  // --- Gasto Actions (API) ---
  const addGasto = withLoading('gastos', async (gasto) => {
    const newGasto = await api.createGasto(gasto)
    setGastos(prev => [...prev, newGasto])
    return newGasto
  })

  const updateGasto = withLoading('gastos', async (id, updates) => {
    await api.updateGasto(id, updates)
    setGastos(prev => prev.map(g => g.id === id ? { ...g, ...updates } : g))
  })

  const deleteGasto = withLoading('gastos', async (id) => {
    await api.deleteGasto(id)
    setGastos(prev => prev.filter(g => g.id !== id))
  })

  // --- Computed / Helpers (sin cambios, usan state local) ---
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

  // Helpers internos (mantenidos del original)
  function calcularKilosTotales(stockItem) {
    if (!stockItem.bolsas || !Array.isArray(stockItem.bolsas)) return 0
    return stockItem.bolsas.reduce((sum, bolsa) => sum + (bolsa.kilos || 0), 0)
  }

  const value = {
    // State
    stock,
    clientes,
    pedidos,
    gastos,
    isLoaded,
    loading,
    errors,
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
    changeEstado,
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