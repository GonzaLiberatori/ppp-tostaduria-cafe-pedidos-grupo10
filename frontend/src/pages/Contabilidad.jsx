import { useState, useMemo } from 'react'
import { useData } from '../context/DataContext'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../hooks/useToast.jsx'
import { CATEGORIAS_GASTO } from '../data/constants'
import GastoForm from '../components/forms/GastoForm'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import { 
  formatearMoneda, 
  formatearFecha, 
  getMesNombre,
  truncate 
} from '../utils/formatters'
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  Plus, 
  Filter, 
  Trash2, 
  Edit, 
  Download,
  Calculator,
  CreditCard,
  Receipt,
  AlertTriangle,
  Ban,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line
} from 'recharts'

const ETIQUETAS_METODO = {
  EFECTIVO: 'Efectivo',
  CREDITO: 'Crédito',
  DEBITO: 'Débito',
  TRANSFERENCIA: 'Transferencia',
  MERCADO_PAGO: 'Mercado Pago',
  CHEQUE: 'Cheque',
  OTRO: 'Otro',
}

// Métodos con los que se puede cobrar un pagaré: crédito queda afuera porque
// representa la deuda original, no un medio real de cobro.
const METODOS_COBRO = [
  { value: 'EFECTIVO', label: 'Efectivo' },
  { value: 'TRANSFERENCIA', label: 'Transferencia' },
  { value: 'DEBITO', label: 'Débito' },
  { value: 'MERCADO_PAGO', label: 'Mercado Pago' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'OTRO', label: 'Otro' },
]

function diasHasta(fechaISO) {
  if (!fechaISO) return null
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const vence = new Date(fechaISO)
  vence.setHours(0, 0, 0, 0)
  return Math.round((vence - hoy) / 86400000)
}

function descripcionVencimiento(item) {
  const dias = diasHasta(item.fecha_vencimiento)
  if (dias === null) return 'Sin vencimiento'
  if (dias < 0) {
    const atraso = Math.abs(dias)
    return `${atraso} día${atraso === 1 ? '' : 's'} de atraso`
  }
  if (dias === 0) return 'Vence hoy'
  return `En ${dias} día${dias === 1 ? '' : 's'}`
}

export default function Contabilidad() {
  const { 
    gastos, 
    ventas,
    cobranzaMensual,
    porCobrar,
    addGasto, 
    updateGasto, 
    deleteGasto,
    cobrarVenta,
    anularVenta,
    getContabilidadMensual,
    getTotalesGenerales,
    errors,
  } = useData()
  const { user } = useAuth()
  const { success, error: toastError } = useToast()

  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [filters, setFilters] = useState({ categoria: '', mes: '', search: '' })
  const [filtrosVentas, setFiltrosVentas] = useState({ estado: '', search: '' })
  const [ventaAnular, setVentaAnular] = useState(null)
  const [motivoAnulacion, setMotivoAnulacion] = useState('')
  const [anulando, setAnulando] = useState(false)
  const [ventaCobrar, setVentaCobrar] = useState(null)
  const [metodoCobro, setMetodoCobro] = useState('TRANSFERENCIA')
  const [aclaracionCobro, setAclaracionCobro] = useState('')
  const [cobrando, setCobrando] = useState(false)
  const [exportData, setExportData] = useState(null)

  const esAdmin = user?.role === 'admin'
  // El backend habilita el cobro a Administrador y Cajero (rol "vendedor" en
  // el frontend). La pantalla Contabilidad sigue siendo solo para admin.
  const puedeCobrar = esAdmin || user?.role === 'vendedor'

  const totales = getTotalesGenerales()
  const contabilidadMensual = getContabilidadMensual()
  const currentMonth = new Date().toISOString().substring(0, 7)
  const currentMonthData = contabilidadMensual.find(m => m.mes === currentMonth) || { ventasTotales: 0, gastosTotales: 0, gananciaNeta: 0 }
  const cobranzaMes = cobranzaMensual.find(c => c.mes === currentMonth)
  const cobranzaDelMes = Number(cobranzaMes?.total_cobrado || 0)
  const totalPorCobrar = Number(porCobrar?.total_por_cobrar || 0)
  const vencidas = porCobrar?.cantidad_vencidas || 0

  const filteredGastos = useMemo(() => {
    return gastos.filter(gasto => {
      const matchesCategoria = !filters.categoria || gasto.categoria === filters.categoria
      const matchesMes = !filters.mes || gasto.fecha.substring(0, 7) === filters.mes
      const matchesSearch = !filters.search || 
        gasto.descripcion.toLowerCase().includes(filters.search.toLowerCase())
      return matchesCategoria && matchesMes && matchesSearch
    })
  }, [gastos, filters])

  const gastosPorCategoria = useMemo(() => {
    const categorias = {}
    gastos.forEach(g => {
      if (!categorias[g.categoria]) categorias[g.categoria] = 0
      categorias[g.categoria] += g.monto
    })
    return Object.entries(categorias).map(([categoria, monto]) => ({ categoria, monto }))
  }, [gastos])

  const filteredVentas = useMemo(() => {
    const texto = filtrosVentas.search.trim().toLowerCase()

    return ventas.filter(venta => {
      const matchesEstado = !filtrosVentas.estado || venta.estado === filtrosVentas.estado
      const matchesTexto = !texto
        || String(venta.numero_comprobante || '').toLowerCase().includes(texto)
        || String(venta.cliente_nombre || '').toLowerCase().includes(texto)
      return matchesEstado && matchesTexto
    })
  }, [ventas, filtrosVentas])

  const abrirAnulacion = (venta) => {
    setVentaAnular(venta)
    setMotivoAnulacion('')
  }

  const cerrarAnulacion = () => {
    if (anulando) return
    setVentaAnular(null)
    setMotivoAnulacion('')
  }

  const confirmarAnulacion = async () => {
    if (!ventaAnular) return
    if (!motivoAnulacion.trim()) {
      toastError('Indicá el motivo de la anulación')
      return
    }

    setAnulando(true)
    try {
      await anularVenta(ventaAnular.id, motivoAnulacion.trim())
      success('Venta anulada')
      setVentaAnular(null)
      setMotivoAnulacion('')
    } catch (err) {
      toastError(err.message || 'No se pudo anular la venta')
    } finally {
      setAnulando(false)
    }
  }

  const abrirCobro = (item) => {
    setVentaCobrar(item)
    setMetodoCobro('TRANSFERENCIA')
    setAclaracionCobro('')
  }

  const cerrarCobro = () => {
    if (cobrando) return
    setVentaCobrar(null)
    setAclaracionCobro('')
  }

  const confirmarCobro = async () => {
    if (!ventaCobrar) return

    setCobrando(true)
    try {
      await cobrarVenta(ventaCobrar.venta_id, {
        metodo_de_pago: metodoCobro,
        ...(aclaracionCobro.trim() ? { aclaracion: aclaracionCobro.trim() } : {}),
      })
      success('Venta marcada como cobrada')
      setVentaCobrar(null)
      setAclaracionCobro('')
    } catch (err) {
      toastError(err.message || 'No se pudo cobrar la venta')
    } finally {
      setCobrando(false)
    }
  }

  const handleSubmit = async (data, id) => {
    try {
      if (id) {
        await updateGasto(id, data)
        success('Gasto actualizado')
      } else {
        await addGasto(data)
        success('Gasto registrado')
      }
      setShowForm(false)
      setEditingItem(null)
    } catch (err) {
      toastError(err.message || 'No se pudo guardar el gasto')
    }
  }

  const handleDelete = (id) => {
    setDeleteConfirm(id)
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return

    try {
      await deleteGasto(deleteConfirm)
      success('Gasto eliminado')
      setDeleteConfirm(null)
    } catch (err) {
      toastError(err.message || 'No se pudo eliminar el gasto')
    }
  }

  const handleExportCSV = () => {
    const headers = ['Fecha', 'Categoría', 'Descripción', 'Monto']
    const rows = gastos.map(g => [
      formatearFecha(g.fecha),
      g.categoria,
      `"${g.descripcion.replace(/"/g, '""')}"`,
      g.monto
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `gastos_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const handleExportContabilidadCSV = () => {
    const headers = ['Mes', 'Ventas', 'Gastos', 'Ganancia Neta', 'Margen %']
    const rows = contabilidadMensual.map(m => [
      getMesNombre(m.mes),
      m.ventasTotales,
      m.gastosTotales,
      m.gananciaNeta,
      m.ventasTotales > 0 ? ((m.gananciaNeta / m.ventasTotales) * 100).toFixed(2) : '0'
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `contabilidad_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const chartData = contabilidadMensual.slice(0, 12).reverse().map(m => ({
    mes: getMesNombre(m.mes).split(' ')[0],
    ventas: m.ventasTotales,
    gastos: m.gastosTotales,
    ganancia: m.gananciaNeta,
  }))

  const categoriaColors = {
    Producción: '#8B6F47',
    Operativo: '#3B82F6',
    Marketing: '#F59E0B',
    Otro: '#10B981',
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Contabilidad</h1>
          <p className="text-[var(--color-text-muted)]">Ganancias, gastos y análisis financiero</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleExportContabilidadCSV}>
            <Download className="w-4 h-4" />
            Exportar Contabilidad
          </Button>
          <Button variant="secondary" onClick={handleExportCSV}>
            <Download className="w-4 h-4" />
            Exportar Gastos
          </Button>
          <Button onClick={() => { setEditingItem(null); setShowForm(true); }}>
            <Plus className="w-4 h-4" />
            Nuevo Gasto
          </Button>
        </div>
      </div>

      {errors.contabilidad && (
        <div className="card p-4 border border-amber-400/40 bg-amber-500/5 flex items-start gap-3" role="alert">
          <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-[var(--color-text-primary)]">
              No se pudo cargar la información de ventas
            </p>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">
              {errors.contabilidad}. Verificá que la base tenga aplicada la migración `004_ventas_cobranza`.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Ventas Totales</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearMoneda(totales.ventasTotales)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Gastos Totales</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{formatearMoneda(totales.gastosTotales)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Ganancia Neta Total</p>
              <p className={`text-2xl font-bold mt-1 ${totales.gananciaNeta >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatearMoneda(totales.gananciaNeta)}
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Mes Actual ({getMesNombre(currentMonth).split(' ')[0]})</p>
              <p className={`text-2xl font-bold mt-1 ${currentMonthData.gananciaNeta >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatearMoneda(currentMonthData.gananciaNeta)}
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Calculator className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Cobranza del mes</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearMoneda(cobranzaDelMes)}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {cobranzaMes?.cantidad_cobros || 0} cobro{(cobranzaMes?.cantidad_cobros || 0) === 1 ? '' : 's'} en {getMesNombre(currentMonth)}
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <Receipt className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Por cobrar</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{formatearMoneda(totalPorCobrar)}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {porCobrar?.items?.length || 0} pendiente{(porCobrar?.items?.length || 0) === 1 ? '' : 's'}
                {vencidas > 0 && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {' '}· {vencidas} vencida{vencidas === 1 ? '' : 's'}
                  </span>
                )}
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Evolución Mensual</h2>
          </div>
          <div className="card-body">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-[var(--color-border)]" />
                  <XAxis dataKey="mes" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} tickFormatter={v => formatearMoneda(v).replace('ARS', '').trim()} />
                  <Tooltip 
                    formatter={(value) => [formatearMoneda(value), '']}
                    labelFormatter={v => v}
                    contentStyle={{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="ventas" name="Ventas" fill="#8B6F47" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="gastos" name="Gastos" fill="#EF4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Ganancia Neta por Mes</h2>
          </div>
          <div className="card-body">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-[var(--color-border)]" />
                  <XAxis dataKey="mes" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} tickFormatter={v => formatearMoneda(v).replace('ARS', '').trim()} />
                  <Tooltip 
                    formatter={(value) => [formatearMoneda(value), '']}
                    labelFormatter={v => v}
                    contentStyle={{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: '8px' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="ganancia" 
                    name="Ganancia Neta" 
                    stroke="#8B6F47" 
                    strokeWidth={3}
                    dot={{ fill: '#8B6F47', strokeWidth: 2, r: 5 }}
                    activeDot={{ r: 7 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Gastos por Categoría</h2>
            <Badge variant="info">{gastos.length} gastos</Badge>
          </div>
          <div className="card-body">
            <div className="h-64 flex items-end justify-around px-4">
              {gastosPorCategoria.map((item, index) => (
                <div key={item.categoria} className="flex flex-col items-center w-full">
                  <div 
                    className="w-full bg-[var(--color-border)] rounded-t transition-all duration-300 hover:opacity-80 cursor-pointer"
                    style={{ 
                      height: `${gastosPorCategoria.length > 0 ? (item.monto / Math.max(...gastosPorCategoria.map(c => c.monto)) * 100) : 0}%`,
                      backgroundColor: categoriaColors[item.categoria],
                      minHeight: '8px'
                    }}
                    title={`${item.categoria}: ${formatearMoneda(item.monto)}`}
                  />
                  <span className="text-xs text-[var(--color-text-muted)] mt-2 text-center">{item.categoria}</span>
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">{formatearMoneda(item.monto)}</span>
                </div>
              ))}
              {gastosPorCategoria.length === 0 && (
                <div className="w-full text-center text-[var(--color-text-muted)] py-8">Sin datos de gastos</div>
              )}
            </div>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {CATEGORIAS_GASTO.map(cat => (
                <Badge key={cat.value} variant={cat.value === 'Producción' ? 'coffee' : cat.value === 'Operativo' ? 'info' : cat.value === 'Marketing' ? 'warning' : 'success'} className="text-xs">
                  {cat.label}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Resumen Contable Mensual</h2>
          </div>
          <div className="card-body p-0">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Mes</th>
                    <th className="text-right">Ventas</th>
                    <th className="text-right">Gastos</th>
                    <th className="text-right">Ganancia Neta</th>
                    <th className="text-right">Margen</th>
                  </tr>
                </thead>
                <tbody>
                  {contabilidadMensual.map(item => (
                    <tr key={item.mes}>
                      <td className="font-medium">{getMesNombre(item.mes)}</td>
                      <td className="text-right">{formatearMoneda(item.ventasTotales)}</td>
                      <td className="text-right">{formatearMoneda(item.gastosTotales)}</td>
                      <td className={`text-right font-medium ${item.gananciaNeta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatearMoneda(item.gananciaNeta)}
                      </td>
                      <td className="text-right">
                        {item.ventasTotales > 0 ? (
                          <Badge variant={item.gananciaNeta >= 0 ? 'success' : 'danger'}>
                            {(item.gananciaNeta / item.ventasTotales * 100).toFixed(1)}%
                          </Badge>
                        ) : (
                          <span className="text-[var(--color-text-muted)]">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Por cobrar</h2>
            <Badge variant="warning">{porCobrar?.items?.length || 0} pendientes</Badge>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Total por cobrar: <span className="font-medium font-mono tabular-nums">{formatearMoneda(totalPorCobrar)}</span>
            {vencidas > 0 && (
              <span className="text-amber-600 dark:text-amber-400 ml-2">
                ({vencidas} vencida{vencidas === 1 ? '' : 's'})
              </span>
            )}
          </p>
        </div>
        <div className="card-body p-0">
          <Table
            keyField="venta_id"
            columns={[
              { key: 'numero_comprobante', header: 'Comprobante', width: '150px', render: (v) => v || '-' },
              { key: 'cliente_nombre', header: 'Cliente', render: (v) => v || 'Sin cliente' },
              {
                key: 'total',
                header: 'Total',
                render: (v) => formatearMoneda(v),
                className: 'font-mono tabular-nums font-medium text-right',
              },
              {
                key: 'fecha_vencimiento',
                header: 'Vencimiento',
                width: '120px',
                render: (v) => v ? formatearFecha(v) : '-',
              },
              {
                key: 'vencimiento',
                header: 'Estado',
                width: '150px',
                render: (_, item) => (
                  <Badge variant={item.vencida ? 'danger' : 'warning'}>
                    {descripcionVencimiento(item)}
                  </Badge>
                ),
              },
              ...(puedeCobrar ? [{
                key: 'acciones',
                header: '',
                width: '160px',
                render: (_, item) => (
                  <Button size="sm" onClick={() => abrirCobro(item)}>
                    <Receipt className="w-4 h-4" />
                    Marcar cobrado
                  </Button>
                ),
              }] : []),
            ]}
            data={porCobrar?.items || []}
            emptyMessage="No hay ventas pendientes de cobro"
          />
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Ventas registradas</h2>
            <Badge variant="info">{filteredVentas.length} ventas</Badge>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
              <Input
                placeholder="Buscar comprobante o cliente..."
                value={filtrosVentas.search}
                onChange={e => setFiltrosVentas(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            <Select
              value={filtrosVentas.estado}
              onChange={e => setFiltrosVentas(prev => ({ ...prev, estado: e.target.value }))}
              options={[
                { value: '', label: 'Todos los estados' },
                { value: 'CONFIRMADA', label: 'Confirmada' },
                { value: 'PENDIENTE_COBRO', label: 'Pendiente de cobro' },
                { value: 'ANULADA', label: 'Anulada' },
              ]}
              className="w-full sm:w-44"
              label=""
            />
          </div>
        </div>
        <div className="card-body p-0">
          <Table
            columns={[
              { key: 'numero_comprobante', header: 'Comprobante', width: '150px', render: (v) => v || '-' },
              { key: 'fecha', header: 'Fecha', width: '110px', render: (v) => formatearFecha(v) },
              { key: 'cliente_nombre', header: 'Cliente', render: (v) => v || 'Sin cliente' },
              {
                key: 'metodos_de_pago',
                header: 'Métodos',
                render: (metodos) => (
                  metodos?.length
                    ? metodos.map(m => ETIQUETAS_METODO[m] || m).join(', ')
                    : '-'
                ),
              },
              {
                key: 'total',
                header: 'Total',
                render: (v) => formatearMoneda(v),
                className: 'font-mono tabular-nums font-medium text-right',
              },
              {
                key: 'fecha_vencimiento',
                header: 'Vencimiento',
                width: '120px',
                render: (v) => v ? formatearFecha(v) : '-',
              },
              {
                key: 'estado',
                header: 'Estado',
                width: '140px',
                render: (v) => (
                  <Badge
                    variant={
                      v === 'ANULADA'
                        ? 'danger'
                        : v === 'PENDIENTE_COBRO'
                          ? 'warning'
                          : 'success'
                    }
                  >
                    {v === 'ANULADA'
                      ? 'Anulada'
                      : v === 'PENDIENTE_COBRO'
                        ? 'Pendiente de cobro'
                        : 'Confirmada'}
                  </Badge>
                ),
              },
              ...(esAdmin ? [{
                key: 'acciones',
                header: '',
                width: '96px',
                render: (_, venta) => (
                  venta.estado !== 'ANULADA' ? (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => abrirAnulacion(venta)}
                    >
                      <Ban className="w-4 h-4" />
                      Anular
                    </Button>
                  ) : null
                ),
              }] : []),
            ]}
            data={filteredVentas}
            emptyMessage="No hay ventas que coincidan con los filtros"
          />
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Detalle de Gastos</h2>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
              <Input
                placeholder="Buscar descripción..."
                value={filters.search}
                onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            <Select
              value={filters.categoria}
              onChange={e => setFilters(prev => ({ ...prev, categoria: e.target.value }))}
              options={[{ value: '', label: 'Todas' }, ...CATEGORIAS_GASTO]}
              className="w-full sm:w-40"
              label=""
            />
            <Select
              value={filters.mes}
              onChange={e => setFilters(prev => ({ ...prev, mes: e.target.value }))}
              options={[{ value: '', label: 'Todos los meses' }, ...contabilidadMensual.map(m => ({ value: m.mes, label: getMesNombre(m.mes) }))]}
              className="w-full sm:w-40"
              label=""
            />
          </div>
        </div>
        <div className="card-body p-0">
          <Table
            columns={[
              { key: 'fecha', header: 'Fecha', width: '110px', render: (v) => formatearFecha(v) },
              { key: 'categoria', header: 'Categoría', width: '120px', render: (v) => <Badge variant={v === 'Producción' ? 'coffee' : v === 'Operativo' ? 'info' : v === 'Marketing' ? 'warning' : 'success'}>{v}</Badge> },
              { key: 'descripcion', header: 'Descripción', render: (v) => truncate(v, 40) },
              { key: 'monto', header: 'Monto', render: (v) => formatearMoneda(v), className: 'font-mono tabular-nums font-medium text-right' },
            ]}
            data={filteredGastos.sort((a, b) => new Date(b.fecha) - new Date(a.fecha))}
            onRowClick={(gasto) => { setEditingItem(gasto); setShowForm(true); }}
            emptyMessage="No hay gastos que coincidan con los filtros"
          />
        </div>
      </div>

      <GastoForm
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditingItem(null); }}
        initialData={editingItem}
        onSubmit={handleSubmit}
      />

      <Modal
        isOpen={Boolean(ventaAnular)}
        onClose={cerrarAnulacion}
        title="Anular venta"
        size="sm"
        confirmAction={confirmarAnulacion}
        confirmText="Anular venta"
        loading={anulando}
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            La venta <span className="font-medium">{ventaAnular?.numero_comprobante || ventaAnular?.id}</span>
            {' '}por {formatearMoneda(ventaAnular?.total || 0)} quedará <strong>ANULADA</strong> y
            dejará de sumar en Contabilidad. No se borran los pagos ni el comprobante.
          </p>
          <Input
            label="Motivo de la anulación"
            placeholder="Ej.: cobro cargado dos veces"
            value={motivoAnulacion}
            onChange={e => setMotivoAnulacion(e.target.value)}
          />
        </div>
      </Modal>

      <Modal
        isOpen={Boolean(ventaCobrar)}
        onClose={cerrarCobro}
        title="Marcar venta como cobrada"
        size="sm"
        confirmAction={confirmarCobro}
        confirmText="Confirmar cobro"
        loading={cobrando}
      >
        {ventaCobrar && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              La venta <span className="font-medium">{ventaCobrar.numero_comprobante || ventaCobrar.venta_id}</span>
              {' '}por {formatearMoneda(ventaCobrar.total)} de {ventaCobrar.cliente_nombre || 'cliente'} pasará a <strong>CONFIRMADA</strong>.
              La deuda se descontará de su cuenta corriente.
            </p>
            <Select
              label="Método de pago"
              value={metodoCobro}
              onChange={e => setMetodoCobro(e.target.value)}
              options={METODOS_COBRO}
            />
            <Input
              label="Aclaración (opcional)"
              placeholder="Ej.: transferencia Banco Nación"
              value={aclaracionCobro}
              onChange={e => setAclaracionCobro(e.target.value)}
            />
          </div>
        )}
      </Modal>

      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal-content max-w-md" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="text-lg font-semibold">Confirmar eliminación</h2>
            </div>
            <div className="modal-body">
              <p className="text-[var(--color-text-secondary)]">¿Está seguro de eliminar este gasto? Esta acción no se puede deshacer.</p>
            </div>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancelar</Button>
              <Button variant="danger" onClick={confirmDelete}>Eliminar</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}