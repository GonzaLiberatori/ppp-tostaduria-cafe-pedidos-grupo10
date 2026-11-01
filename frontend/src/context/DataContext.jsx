import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useAuth } from './AuthContext'
import { api } from '../services/api'

const DataContext = createContext(null)

// Estado inicial de "Por cobrar" mientras la API no responde o falla.
const POR_COBRAR_VACIO = {
  items: [],
  total_por_cobrar: 0,
  cantidad_vencidas: 0,
}

function kilosDeStock(stockItem) {
  if (!stockItem?.bolsas || !Array.isArray(stockItem.bolsas)) return 0
  return stockItem.bolsas.reduce((sum, bolsa) => sum + (bolsa.kilos || 0), 0)
}

export function DataProvider({ children }) {
  const { user } = useAuth()
  const [stock, setStock] = useState([])
  const [clientes, setClientes] = useState([])
  const [pedidos, setPedidos] = useState([])
  const [gastos, setGastos] = useState([])
  const [ventas, setVentas] = useState([])
  const [resumenVentasMensual, setResumenVentasMensual] = useState([])
  const [cobranzaMensual, setCobranzaMensual] = useState([])
  const [porCobrar, setPorCobrar] = useState(POR_COBRAR_VACIO)
  const [isLoaded, setIsLoaded] = useState(false)
  const [loading, setLoading] = useState({})
  const [errors, setErrors] = useState({})

  // Carga inicial: solo con una sesión activa y sin datos de ejemplo.
  useEffect(() => {
    let activo = true

    if (!user) {
      setStock([])
      setClientes([])
      setPedidos([])
      setGastos([])
      setVentas([])
      setResumenVentasMensual([])
      setCobranzaMensual([])
      setPorCobrar(POR_COBRAR_VACIO)
      setErrors({})
      setIsLoaded(false)
      return () => {
        activo = false
      }
    }

    async function cargarTodo() {
      setIsLoaded(false)
      setLoading(prev => ({ ...prev, initial: true }))
      setErrors({})

      // El portal del cliente no necesita el padrón completo ni los gastos:
      // se limita a su propio perfil y a sus pedidos.
      const esCliente = user.role === 'cliente'
      const tieneCliente = Boolean(user.clienteId)

      const pedidosPromise = esCliente
        ? (tieneCliente ? api.getPedidosByCliente(user.clienteId) : Promise.resolve([]))
        : api.getPedidos()
      const clientesPromise = esCliente
        ? (tieneCliente
          ? api.getCliente(user.clienteId).then(cliente => [cliente])
          : Promise.resolve([]))
        : api.getClientes()
      const gastosPromise = esCliente ? Promise.resolve([]) : api.getGastos()

      // Las ventas alimentan Contabilidad. Si la base no tiene la migración
      // 003_ventas, el endpoint falla: se aísla para que el resto del panel
      // siga cargando y Contabilidad muestre un aviso.
      let errorContabilidad = null
      const ventasPromise = esCliente
        ? Promise.resolve([])
        : api.getVentas({ limit: 100 }).catch(error => {
          errorContabilidad = error.message
          return []
        })
      const resumenVentasPromise = esCliente
        ? Promise.resolve([])
        : api.getResumenMensualVentas().catch(error => {
          errorContabilidad = errorContabilidad || error.message
          return []
        })
      const cobranzaPromise = esCliente
        ? Promise.resolve([])
        : api.getCobranzaMensualVentas().catch(error => {
          errorContabilidad = errorContabilidad || error.message
          return []
        })
      const porCobrarPromise = esCliente
        ? Promise.resolve(POR_COBRAR_VACIO)
        : api.getPorCobrarVentas().catch(error => {
          errorContabilidad = errorContabilidad || error.message
          return POR_COBRAR_VACIO
        })

      try {
        const [
          stockRes,
          clientesRes,
          pedidosRes,
          gastosRes,
          ventasRes,
          resumenVentasRes,
          cobranzaRes,
          porCobrarRes,
        ] = await Promise.all([
          api.getStock(),
          clientesPromise,
          pedidosPromise,
          gastosPromise,
          ventasPromise,
          resumenVentasPromise,
          cobranzaPromise,
          porCobrarPromise,
        ])

        if (!activo) return
        setStock(stockRes || [])
        setClientes(clientesRes || [])
        setPedidos(pedidosRes || [])
        setGastos(gastosRes || [])
        setVentas(ventasRes || [])
        setResumenVentasMensual(resumenVentasRes || [])
        setCobranzaMensual(cobranzaRes || [])
        setPorCobrar(porCobrarRes || POR_COBRAR_VACIO)
        if (errorContabilidad) {
          setErrors(prev => ({ ...prev, contabilidad: errorContabilidad }))
        }
      } catch (error) {
        if (!activo) return
        console.error('Error cargando datos del panel:', error)
        setErrors(prev => ({ ...prev, initial: error.message }))
      } finally {
        if (activo) {
          setIsLoaded(true)
          setLoading(prev => ({ ...prev, initial: false }))
        }
      }
    }

    cargarTodo()
    return () => {
      activo = false
    }
  }, [user?.id])

  // --- Helpers ---
  const withLoading = useCallback((key, fn) => async (...args) => {
    setLoading(prev => ({ ...prev, [key]: true }))
    setErrors(prev => ({ ...prev, [key]: null }))
    try {
      return await fn(...args)
    } catch (error) {
      setErrors(prev => ({ ...prev, [key]: error.message }))
      throw error
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }))
    }
  }, [])

  const refrescarStockSilencioso = useCallback(async () => {
    try {
      const respuesta = await api.getStock()
      setStock(respuesta || [])
    } catch (error) {
      console.warn('No se pudo refrescar el stock:', error)
    }
  }, [])

  const refrescarClientesSilencioso = useCallback(async () => {
    // Los clientes solo ven su propio perfil; no se recarga el padrón completo.
    if (user?.role === 'cliente') return
    try {
      const respuesta = await api.getClientes()
      setClientes(respuesta || [])
    } catch (error) {
      console.warn('No se pudo refrescar los clientes:', error)
    }
  }, [user?.role])

  const refrescarStockYClientes = useCallback(async () => {
    await Promise.all([refrescarStockSilencioso(), refrescarClientesSilencioso()])
  }, [refrescarStockSilencioso, refrescarClientesSilencioso])

  // --- Ventas (contabilidad) ---
  const refrescarVentas = useCallback(async () => {
    if (user?.role === 'cliente') return
    try {
      const [ventasRes, resumenRes, cobranzaRes, porCobrarRes] = await Promise.all([
        api.getVentas({ limit: 100 }),
        api.getResumenMensualVentas(),
        api.getCobranzaMensualVentas(),
        api.getPorCobrarVentas(),
      ])
      setVentas(ventasRes || [])
      setResumenVentasMensual(resumenRes || [])
      setCobranzaMensual(cobranzaRes || [])
      setPorCobrar(porCobrarRes || POR_COBRAR_VACIO)
      setErrors(prev => ({ ...prev, contabilidad: null }))
    } catch (error) {
      setErrors(prev => ({ ...prev, contabilidad: error.message }))
      throw error
    }
  }, [user?.role])

  // --- Stock ---
  const addStock = withLoading('stock', async (item) => {
    const nuevo = await api.createStock(item)
    setStock(prev => [nuevo, ...prev.filter(stockItem => stockItem.id !== nuevo.id)])
    return nuevo
  })

  const updateStock = withLoading('stock', async (id, cambios) => {
    const actualizado = await api.updateStock(id, cambios)
    setStock(prev => prev.map(item => item.id === id ? actualizado : item))
    return actualizado
  })

  const deleteStock = withLoading('stock', async (id) => {
    await api.deleteStock(id)
    setStock(prev => prev.filter(item => item.id !== id))
  })

  // --- Bolsas ---
  const addBolsa = withLoading('stock', async (stockId, bolsa) => {
    try {
      const nueva = await api.addBolsa(stockId, bolsa)
      setStock(prev => prev.map(item => (
        item.id === stockId
          ? { ...item, bolsas: [...(item.bolsas || []), nueva] }
          : item
      )))
      return nueva
    } catch (error) {
      await refrescarStockSilencioso()
      throw error
    }
  })

  const updateBolsa = withLoading('stock', async (stockId, bolsaId, cambios) => {
    try {
      const actualizada = await api.updateBolsa(stockId, bolsaId, cambios)
      setStock(prev => prev.map(item => (
        item.id === stockId
          ? {
            ...item,
            bolsas: (item.bolsas || []).map(bolsa => (
              bolsa.id === bolsaId ? actualizada : bolsa
            )),
          }
          : item
      )))
      return actualizada
    } catch (error) {
      await refrescarStockSilencioso()
      throw error
    }
  })

  const deleteBolsa = withLoading('stock', async (stockId, bolsaId) => {
    try {
      await api.deleteBolsa(stockId, bolsaId)
      setStock(prev => prev.map(item => (
        item.id === stockId
          ? { ...item, bolsas: (item.bolsas || []).filter(bolsa => bolsa.id !== bolsaId) }
          : item
      )))
    } catch (error) {
      await refrescarStockSilencioso()
      throw error
    }
  })

  // --- Clientes ---
  const addCliente = withLoading('clientes', async (cliente) => {
    const nuevo = await api.createCliente(cliente)
    setClientes(prev => [nuevo, ...prev.filter(item => item.id !== nuevo.id)])
    return nuevo
  })

  const updateCliente = withLoading('clientes', async (id, cambios) => {
    const actualizado = await api.updateCliente(id, cambios)
    setClientes(prev => prev.map(item => item.id === id ? actualizado : item))
    return actualizado
  })

  const deleteCliente = withLoading('clientes', async (id) => {
    await api.deleteCliente(id)
    setClientes(prev => prev.filter(item => item.id !== id))
  })

  // --- Pedidos ---
  const addPedido = withLoading('pedidos', async (pedido) => {
    const nuevo = await api.createPedido(pedido)
    setPedidos(prev => [nuevo, ...prev.filter(item => item.id !== nuevo.id)])
    await refrescarStockYClientes()
    return nuevo
  })

  const updatePedido = withLoading('pedidos', async (id, cambios) => {
    const actualizado = await api.updatePedido(id, cambios)
    setPedidos(prev => prev.map(item => item.id === id ? actualizado : item))
    await refrescarStockYClientes()
    if (cambios?.estado === 'Entregado') {
      // La entrega crea la venta: se refresca para mostrar condición y vencimiento.
      await refrescarVentas().catch(() => {})
    }
    return actualizado
  })

  const deletePedido = withLoading('pedidos', async (id) => {
    await api.deletePedido(id)
    setPedidos(prev => prev.filter(item => item.id !== id))
    await refrescarStockYClientes()
  })

  const changeEstado = withLoading('pedidos', async (id, nuevoEstado) => {
    const actualizado = await api.updatePedido(id, { estado: nuevoEstado })
    setPedidos(prev => prev.map(item => item.id === id ? actualizado : item))
    await refrescarClientesSilencioso()
    if (nuevoEstado === 'Entregado') {
      await refrescarVentas().catch(() => {})
    }
    return actualizado
  })

  // --- Gastos ---
  const addGasto = withLoading('gastos', async (gasto) => {
    const nuevo = await api.createGasto(gasto)
    setGastos(prev => [nuevo, ...prev.filter(item => item.id !== nuevo.id)])
    return nuevo
  })

  const updateGasto = withLoading('gastos', async (id, cambios) => {
    const actualizado = await api.updateGasto(id, cambios)
    setGastos(prev => prev.map(item => item.id === id ? actualizado : item))
    return actualizado
  })

  const deleteGasto = withLoading('gastos', async (id) => {
    await api.deleteGasto(id)
    setGastos(prev => prev.filter(item => item.id !== id))
  })

  // --- Ventas (contabilidad) ---
  const cobrarVenta = withLoading('ventas', async (id, datos) => {
    const venta = await api.cobrarVenta(id, datos)
    await refrescarVentas()
    await refrescarClientesSilencioso()
    return venta
  })

  const anularVenta = withLoading('ventas', async (id, motivo) => {
    const anulada = await api.anularVenta(id, motivo)
    await refrescarVentas()
    await refrescarClientesSilencioso()
    return anulada
  })

  // --- Consultas derivadas ---
  const getClienteById = useCallback((id) => (
    clientes.find(cliente => String(cliente.id) === String(id))
  ), [clientes])

  const getStockById = useCallback((id) => (
    stock.find(item => item.id === id)
  ), [stock])

  const getPedidosByCliente = useCallback((clienteId) => (
    pedidos.filter(pedido => String(pedido.clienteId) === String(clienteId))
  ), [pedidos])

  const getStockByTipo = useCallback((tipo) => (
    stock.filter(item => item.tipo === tipo)
  ), [stock])

  const getTotalKilosStock = useCallback((tipo) => (
    stock
      .filter(item => item.tipo === tipo)
      .reduce((sum, item) => sum + kilosDeStock(item), 0)
  ), [stock])

  const getBolsasByEstado = useCallback((stockId, estado) => {
    const item = stock.find(stockItem => stockItem.id === stockId)
    if (!item) return []
    return (item.bolsas || []).filter(bolsa => bolsa.estado === estado)
  }, [stock])

  const getClientesConDeuda = useCallback(() => (
    clientes.filter(cliente => cliente.tieneDeuda && cliente.montoDeuda > 0)
  ), [clientes])

  const getPedidosByEstado = useCallback((estado) => (
    pedidos.filter(pedido => pedido.estado === estado)
  ), [pedidos])

  const getContabilidadMensual = useCallback(() => {
    const ventasPorMes = {}
    const gastosPorMes = {}

    resumenVentasMensual.forEach(fila => {
      ventasPorMes[fila.mes] = Number(fila.total_facturado) || 0
    })

    gastos.forEach(gasto => {
      const mes = String(gasto.fecha).substring(0, 7)
      gastosPorMes[mes] = (gastosPorMes[mes] || 0) + (gasto.monto || 0)
    })

    const todosLosMeses = new Set([
      ...Object.keys(ventasPorMes),
      ...Object.keys(gastosPorMes),
    ])

    return Array.from(todosLosMeses)
      .sort()
      .reverse()
      .map(mes => ({
        mes,
        ventasTotales: ventasPorMes[mes] || 0,
        gastosTotales: gastosPorMes[mes] || 0,
        gananciaNeta: (ventasPorMes[mes] || 0) - (gastosPorMes[mes] || 0),
      }))
  }, [resumenVentasMensual, gastos])

  const getTotalesGenerales = useCallback(() => {
    const contabilidad = getContabilidadMensual()
    return {
      ventasTotales: contabilidad.reduce((sum, mes) => sum + mes.ventasTotales, 0),
      gastosTotales: contabilidad.reduce((sum, mes) => sum + mes.gastosTotales, 0),
      gananciaNeta: contabilidad.reduce((sum, mes) => sum + mes.gananciaNeta, 0),
      totalKilosVerdes: getTotalKilosStock('verde'),
      totalKilosTostados: getTotalKilosStock('tostado'),
      clientesConDeuda: getClientesConDeuda().length,
      pedidosPendientes: getPedidosByEstado('Pendiente').length,
    }
  }, [getContabilidadMensual, getTotalKilosStock, getClientesConDeuda, getPedidosByEstado])

  const value = {
    // Estado
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
    kilosDeStock,

    // Bolsas
    addBolsa,
    updateBolsa,
    deleteBolsa,
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

    // Ventas
    ventas,
    resumenVentasMensual,
    cobranzaMensual,
    porCobrar,
    refrescarVentas,
    cobrarVenta,
    anularVenta,

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
    throw new Error('useData debe usarse dentro de un DataProvider')
  }
  return context
}
