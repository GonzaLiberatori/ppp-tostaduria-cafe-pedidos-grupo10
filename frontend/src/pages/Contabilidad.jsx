import { useState, useMemo } from 'react'
import { useData } from '../context/DataContext'
import { CATEGORIAS_GASTO } from '../data/constants'
import GastoForm from '../components/forms/GastoForm'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
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
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line
} from 'recharts'

export default function Contabilidad() {
  const { 
    gastos, 
    pedidos, 
    addGasto, 
    updateGasto, 
    deleteGasto,
    getContabilidadMensual,
    getTotalesGenerales 
  } = useData()

  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [filters, setFilters] = useState({ categoria: '', mes: '', search: '' })
  const [exportData, setExportData] = useState(null)

  const totales = getTotalesGenerales()
  const contabilidadMensual = getContabilidadMensual()
  const currentMonth = new Date().toISOString().substring(0, 7)
  const currentMonthData = contabilidadMensual.find(m => m.mes === currentMonth) || { ventasTotales: 0, gastosTotales: 0, gananciaNeta: 0 }

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

  const handleSubmit = (data, id) => {
    if (id) {
      updateGasto(id, data)
    } else {
      addGasto(data)
    }
    setShowForm(false)
    setEditingItem(null)
  }

  const handleDelete = (id) => {
    setDeleteConfirm(id)
  }

  const confirmDelete = () => {
    if (deleteConfirm) {
      deleteGasto(deleteConfirm)
      setDeleteConfirm(null)
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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