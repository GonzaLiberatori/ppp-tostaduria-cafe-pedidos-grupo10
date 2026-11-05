import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useAuth } from './AuthContext'
import { api } from '../services/api'
import { mockOrdenesTueste, mockClientes, mockPedidos, mockGastos } from '../data/mockData'
import { kilosPorTipo } from '../utils/cafes'
import {
  listarTiposDeCafe,
  listarBlends,
  listarTodosLosLotes,
  crearTipoDeCafe,
  actualizarTipoDeCafe,
  eliminarTipoDeCafe,
  crearBlend,
  actualizarBlend,
  eliminarBlend,
  crearLote,
  actualizarLote,
  eliminarLote,
} from '../api/inventario'
import {
  ensamblarCafes,
  cafeSimpleToBackend,
  cafeBlendToBackend,
  loteToBackendCreate,
  loteToBackendUpdate,
} from '../api/mappers'

const DataContext = createContext(null)

const STORAGE_KEYS = {
  CLIENTES: 'cafe-finca-clientes',
  PEDIDOS: 'cafe-finca-pedidos',
  GASTOS: 'cafe-finca-gastos',
}

// Estado inicial de "Por cobrar" mientras la API no responde o falla.
const POR_COBRAR_VACIO = {
  items: [],
  total_por_cobrar: 0,
  cantidad_vencidas: 0,
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

    const disponible = nuevasLotes[idx].kgDisponibles ?? nuevasLotes[idx].kilos ?? 0
    const consumir = Math.min(disponible, restantes)

    if (consumir > 0) {
      nuevasLotes[idx].kgDisponibles = disponible - consumir
      if (nuevasLotes[idx].estado === 'cerrado') {
        nuevasLotes[idx].estado = 'abierto'
      }
      consumo.push({ loteId: lote.id, consumido: consumir })
      restantes -= consumir
    }
  }

  const lotesFinales = nuevasLotes.filter(
    l => (l.kgDisponibles ?? l.kilos ?? 0) > 0.001,
  )

  return { lotes: lotesFinales, consumo, faltante: Math.max(restantes, 0) }
}

export function DataProvider({ children }) {
  const { user } = useAuth()
  const [cafes, setCafes] = useState([])
  const [clientes, setClientes] = useState(() => loadFromStorage(STORAGE_KEYS.CLIENTES, mockClientes))
  const [pedidos, setPedidos] = useState(() => loadFromStorage(STORAGE_KEYS.PEDIDOS, mockPedidos))
  const [gastos, setGastos] = useState(() => loadFromStorage(STORAGE_KEYS.GASTOS, mockGastos))
  const [ordenesTueste] = useState(mockOrdenesTueste)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cargandoPorClave, setCargandoPorClave] = useState({})
  const [ventas, setVentas] = useState([])
  const [resumenVentasMensual, setResumenVentasMensual] = useState([])
  const [cobranzaMensual, setCobranzaMensual] = useState([])
  const [porCobrar, setPorCobrar] = useState(POR_COBRAR_VACIO)
  const [isLoaded, setIsLoaded] = useState(false)
  const [errors, setErrors] = useState({})

  // Envuelve una acción async marcando/desmarcando el estado de carga por clave
  // y capturando errores en el contexto. Devuelve una función lista para invocar.
  const withLoading = useCallback((clave, asyncFn) => {
    return async (...args) => {
      setCargandoPorClave(prev => ({ ...prev, [clave]: true }))
      setError(null)
      try {
        const resultado = await asyncFn(...args)
        setCargandoPorClave(prev => ({ ...prev, [clave]: false }))
        return resultado
      } catch (err) {
        setCargandoPorClave(prev => ({ ...prev, [clave]: false }))
        setError(err)
        throw err
      }
    }
  }, [])

  // Cargar inventario desde la API al montar
  const cargarInventario = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      // 1. Cargar tipos de café y blends en paralelo
      const [tiposDeCafe, blends] = await Promise.all([
        listarTiposDeCafe(),
        listarBlends(),
      ])

      // 2. Cargar lotes para cada tipo de café y blend
      // El backend requiere XOR: tipo_de_cafe_id o blend_id, no ambos ni ninguno
      const todosLosLotes = []
      
      for (const tipo of tiposDeCafe) {
        try {
          const lotesDelTipo = await listarTodosLosLotes([tipo], [])
          todosLosLotes.push(...lotesDelTipo)
        } catch (err) {
          console.error(`Error cargando lotes para tipo ${tipo.id}:`, err)
        }
      }

      for (const blend of blends) {
        try {
          const lotesDelBlend = await listarTodosLosLotes([], [blend])
          todosLosLotes.push(...lotesDelBlend)
        } catch (err) {
          console.error(`Error cargando lotes para blend ${blend.id}:`, err)
        }
      }

      // 3. Ensamblar cafés unificados
      const cafesUnificados = ensamblarCafes(tiposDeCafe, blends, todosLosLotes)
      setCafes(cafesUnificados)
    } catch (err) {
      console.error('Error cargando inventario:', err)
      setError(err.message || 'Error al cargar el inventario')
    } finally {
      setLoading(false)
      setIsLoaded(true)
    }
  }, [])

  const refrescarClientesSilencioso = useCallback(async () => {
    try {
      if (user?.role === 'cliente' && user?.clienteId) {
        // El portal solo puede consultar su propio cliente.
        const propio = await api.getCliente(user.clienteId)
        setClientes(propio ? [propio] : [])
        return
      }
      const respuesta = await api.getClientes()
      setClientes(respuesta || [])
    } catch (err) {
      console.warn('No se pudo refrescar los clientes:', err)
    }
  }, [user])

  const refrescarPedidos = useCallback(async () => {
    try {
      const respuesta = user?.role === 'cliente' && user?.clienteId
        ? await api.getPedidosByCliente(user.clienteId)
        : await api.getPedidos()
      setPedidos(respuesta || [])
    } catch (err) {
      console.warn('No se pudo refrescar los pedidos:', err)
    }
  }, [user])

  const refrescarGastos = useCallback(async () => {
    try {
      const respuesta = await api.getGastos()
      setGastos(respuesta || [])
    } catch (err) {
      console.warn('No se pudo refrescar los gastos:', err)
    }
  }, [])

  // El "stock" del panel son los cafés unificados (con sus lotes) que arma
  // cargarInventario; por eso se refresca el inventario completo.
  const refrescarStockYClientes = useCallback(async () => {
    await Promise.all([cargarInventario(), refrescarClientesSilencioso()])
  }, [cargarInventario, refrescarClientesSilencioso])

  const refrescarVentas = useCallback(async () => {
    if (!user || user.role === 'cliente') return
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
    } catch (err) {
      setErrors(prev => ({ ...prev, contabilidad: err.message }))
      throw err
    }
  }, [user])

  useEffect(() => {
    if (!user) {
      // Sin sesión no hay datos que cargar (el login se muestra igual).
      setIsLoaded(true)
      return
    }

    cargarInventario()
    refrescarClientesSilencioso()
    refrescarPedidos()
    refrescarGastos()
    refrescarVentas().catch(() => {})
  }, [
    user?.id,
    cargarInventario,
    refrescarClientesSilencioso,
    refrescarPedidos,
    refrescarGastos,
    refrescarVentas,
  ])

  // Guardar en localStorage solo clientes, pedidos, gastos
  useEffect(() => { saveToStorage(STORAGE_KEYS.CLIENTES, clientes) }, [clientes])
  useEffect(() => { saveToStorage(STORAGE_KEYS.PEDIDOS, pedidos) }, [pedidos])
  useEffect(() => { saveToStorage(STORAGE_KEYS.GASTOS, gastos) }, [gastos])

  // --- Café Actions ---
  const addCafe = useCallback(async (cafe) => {
    try {
      let response
      if (cafe.tipoProducto === 'simple') {
        const payload = cafeSimpleToBackend(cafe)
        response = await crearTipoDeCafe(payload)
      } else {
        const payload = cafeBlendToBackend(cafe)
        response = await crearBlend(payload)
      }

      // Recargar inventario para obtener los datos actualizados
      await cargarInventario()
      
      return response
    } catch (err) {
      throw err
    }
  }, [cargarInventario])

  const updateCafe = useCallback(async (id, updates) => {
    try {
      const cafe = cafes.find(c => c.id === id)
      if (!cafe) throw new Error('Café no encontrado')

      let response
      if (cafe.tipoProducto === 'simple') {
        const payload = cafeSimpleToBackend({ ...cafe, ...updates })
        response = await actualizarTipoDeCafe(cafe.entidadId, payload)
      } else {
        const payload = cafeBlendToBackend({ ...cafe, ...updates })
        response = await actualizarBlend(cafe.entidadId, payload)
      }

      await cargarInventario()
      return response
    } catch (err) {
      throw err
    }
  }, [cafes, cargarInventario])

  const deleteCafe = useCallback(async (id) => {
    try {
      const cafe = cafes.find(c => c.id === id)
      if (!cafe) throw new Error('Café no encontrado')

      if (cafe.tipoProducto === 'simple') {
        await eliminarTipoDeCafe(cafe.entidadId)
      } else {
        await eliminarBlend(cafe.entidadId)
      }

      await cargarInventario()
    } catch (err) {
      throw err
    }
  }, [cafes, cargarInventario])

  // --- Lote Actions ---
  const addLote = useCallback(async (cafeId, lote) => {
    try {
      const cafePadre = cafes.find(c => c.id === cafeId)
      if (!cafePadre) throw new Error('Café padre no encontrado')

      const payload = loteToBackendCreate(lote, cafePadre)
      const response = await crearLote(payload)

      await cargarInventario()
      return response
    } catch (err) {
      throw err
    }
  }, [cafes, cargarInventario])

  const updateLote = useCallback(async (cafeId, loteId, updates) => {
    try {
      const payload = loteToBackendUpdate(updates)
      const response = await actualizarLote(loteId, payload)

      await cargarInventario()
      return response
    } catch (err) {
      throw err
    }
  }, [cargarInventario])

  const deleteLote = useCallback(async (cafeId, loteId) => {
    try {
      await eliminarLote(loteId)
      await cargarInventario()
    } catch (err) {
      throw err
    }
  }, [cargarInventario])

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
  }, [])

  // --- Cliente Actions ---
  const addCliente = useCallback((cliente) => {
    const newCliente = { ...cliente, id: cliente.id || crypto.randomUUID(), creadoEn: new Date().toISOString() }
    setClientes(prev => [...prev, newCliente])
    return newCliente
  }, [])

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
    await refrescarStockYClientes()
    return anulada
  })

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

  // --- Consultas derivadas ---
  const getClienteById = useCallback((id) => (
    clientes.find(cliente => String(cliente.id) === String(id))
  ), [clientes])

  const getPedidosByCliente = useCallback((clienteId) => (
    pedidos.filter(pedido => String(pedido.clienteId) === String(clienteId))
  ), [pedidos])

  const getClientesConDeuda = useCallback(() => {
    return clientes.filter(c => c.tieneDeuda && c.montoDeuda > 0)
  }, [clientes])

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
    loading,
    error,
    errors,
    cargandoPorClave,
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
    // Refresh
    cargarInventario,
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
