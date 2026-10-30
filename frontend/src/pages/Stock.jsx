import React, { useState, useMemo } from 'react'
import { useData } from '../context/DataContext'
import { useToast } from '../hooks/useToast.jsx'
import { TIPOS_STOCK } from '../data/constants'
import StockForm from '../components/forms/StockForm'
import BolsaCard from '../components/forms/BolsaCard'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import { formatearMoneda, formatearKilos, formatearFecha } from '../utils/formatters'
import { Package, Plus, Filter, Trash2, Edit, AlertTriangle, ChevronDown, ChevronUp, Coffee, Package2 } from 'lucide-react'

export default function Stock() {
  const { 
    stock, 
    addStock, 
    updateStock, 
    deleteStock, 
    getTotalKilosStock,
    getStockByTipo,
    addBolsa,
    updateBolsa,
    deleteBolsa,
  } = useData()
  const { success, error: toastError } = useToast()

  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [expandedRow, setExpandedRow] = useState(null)
  const [filters, setFilters] = useState({ tipo: '', search: '' })
  const [bolsaEditMode, setBolsaEditMode] = useState(null) // stockId para editar bolsas

  const totalVerde = getTotalKilosStock('verde')
  const totalTostado = getTotalKilosStock('tostado')
  const valorVerde = getStockByTipo('verde').reduce((sum, s) => sum + calcularKilosTotales(s) * s.precioKg, 0)
  const valorTostado = getStockByTipo('tostado').reduce((sum, s) => sum + calcularKilosTotales(s) * s.precioKg, 0)

  function calcularKilosTotales(item) {
    if (!item.bolsas || !Array.isArray(item.bolsas)) return 0
    return item.bolsas.reduce((sum, b) => sum + (b.kilos || 0), 0)
  }

  const filteredStock = useMemo(() => {
    return stock.filter(item => {
      const matchesTipo = !filters.tipo || item.tipo === filters.tipo
      const matchesSearch = !filters.search || 
        item.variedad.toLowerCase().includes(filters.search.toLowerCase()) ||
        item.origen.toLowerCase().includes(filters.search.toLowerCase()) ||
        item.lotePrincipal.toLowerCase().includes(filters.search.toLowerCase())
      return matchesTipo && matchesSearch
    })
  }, [stock, filters])

  const handleSubmit = async (data, id) => {
    try {
      if (id) {
        await updateStock(id, data)
        success('Café actualizado')
      } else {
        await addStock(data)
        success('Café creado')
      }
      setShowForm(false)
      setEditingItem(null)
    } catch (err) {
      toastError(err.message || 'No se pudo guardar el café')
    }
  }

  const handleEdit = (item) => {
    setEditingItem(item)
    setShowForm(true)
    setExpandedRow(null)
  }

  const handleDelete = (id) => {
    setDeleteConfirm(id)
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return

    try {
      await deleteStock(deleteConfirm)
      success('Café eliminado')
      setDeleteConfirm(null)
    } catch (err) {
      toastError(err.message || 'No se pudo eliminar el café')
    }
  }

  const toggleExpand = (id) => {
    setExpandedRow(prev => prev === id ? null : id)
  }

  const handleBolsaUpdateKilos = (stockId, bolsaId, kilos) => (
    updateBolsa(stockId, bolsaId, { kilos })
  )

  const handleBolsaToggleEstado = (stockId, bolsaId) => {
    const item = stock.find(s => s.id === stockId)
    const bolsa = item?.bolsas.find(b => b.id === bolsaId)
    if (!bolsa) return Promise.resolve()

    return updateBolsa(stockId, bolsaId, {
      estado: bolsa.estado === 'cerrada' ? 'abierta' : 'cerrada',
    })
  }

  const handleBolsaDelete = (stockId, bolsaId) => (
    deleteBolsa(stockId, bolsaId)
  )

  const handleAddBolsa = async (stockId) => {
    const item = stock.find(s => s.id === stockId)
    const nuevoNumero = (item?.bolsas?.length || 0) + 1
    const loteRef = `${item?.lotePrincipal || 'LOTE'}-${String(nuevoNumero).padStart(2, '0')}`

    try {
      await addBolsa(stockId, {
        estado: 'cerrada',
        kilos: item.tipo === 'verde' ? 60 : 1,
        loteRef,
      })
      success('Bolsa agregada')
    } catch (err) {
      toastError(err.message || 'No se pudo agregar la bolsa')
    }
  }

  const columns = [
    { key: 'lotePrincipal', header: 'Lote', width: '130px', render: (v) => <code className="text-sm bg-[var(--color-bg-tertiary)] px-2 py-0.5 rounded">{v}</code> },
    { key: 'tipo', header: 'Tipo', width: '100px', render: (v) => <Badge variant={v === 'verde' ? 'success' : 'coffee'}>{v === 'verde' ? 'Verde' : 'Tostado'}</Badge> },
    { key: 'variedad', header: 'Variedad', render: (_, row) => (
      <div>
        <p className="font-medium text-[var(--color-text-primary)]">{row.variedad}</p>
        <p className="text-xs text-[var(--color-text-muted)]">{row.origen}</p>
      </div>
    )},
    { key: 'bolsasCount', header: 'Bolsas', width: '90px', render: (_, row) => {
      const cerradas = row.bolsas?.filter(b => b.estado === 'cerrada').length || 0
      const abiertas = row.bolsas?.filter(b => b.estado === 'abierta').length || 0
      return (
        <div className="flex items-center gap-2">
          <Badge variant="success" className="text-xs">{cerradas} 🔒</Badge>
          <Badge variant="warning" className="text-xs">{abiertas} 🔓</Badge>
        </div>
      )
    }},
    { key: 'kilos', header: 'Total Kilos', width: '110px', render: (_, row) => <span className="font-mono tabular-nums font-medium">{formatearKilos(calcularKilosTotales(row))}</span> },
    { key: 'precioKg', header: 'Precio/Kg', width: '110px', render: (v) => formatearMoneda(v), className: 'font-mono tabular-nums' },
    { key: 'valor', header: 'Valor Total', render: (_, row) => formatearMoneda(calcularKilosTotales(row) * row.precioKg), className: 'font-mono tabular-nums font-medium text-right' },
    { key: 'fechaIngreso', header: 'Ingreso', width: '110px', render: (v) => formatearFecha(v) },
  ]

  const lowStockItems = stock.filter(s => calcularKilosTotales(s) < (s.tipo === 'tostado' ? 5 : 30))

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <Package2 className="w-6 h-6 text-coffee-500" />
            Stock de Café
          </h1>
          <p className="text-[var(--color-text-muted)]">Gestión de café verde y tostado por bolsas</p>
        </div>
        <Button onClick={() => { setEditingItem(null); setShowForm(true); }}>
          <Plus className="w-4 h-4" />
          Nuevo Café
        </Button>
      </div>

      {lowStockItems.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-amber-900 dark:text-amber-100">Stock Bajo</h3>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                {lowStockItems.length} variedad{lowStockItems.length !== 1 ? 'es' : ''} por debajo del mínimo:
                <ul className="mt-1 list-disc list-inside text-xs">
                  {lowStockItems.map(item => (
                    <li key={item.id}>{item.variedad} ({formatearKilos(calcularKilosTotales(item))}) - {item.tipo === 'verde' ? 'Verde' : 'Tostado'}</li>
                  ))}
                </ul>
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Café Verde Total</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearKilos(totalVerde)}</p>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">Valor: {formatearMoneda(valorVerde)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
              <Coffee className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Café Tostado Total</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearKilos(totalTostado)}</p>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">Valor: {formatearMoneda(valorTostado)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-coffee-500/10 flex items-center justify-center">
              <Package2 className="w-6 h-6 text-coffee-600 dark:text-coffee-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Valor Inventario</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearMoneda(valorVerde + valorTostado)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <Package className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Variedades</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{stock.length}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Package2 className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Catálogo de Cafés</h2>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
              <Input
                placeholder="Buscar variedad, origen, lote..."
                value={filters.search}
                onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            <Select
              value={filters.tipo}
              onChange={e => setFilters(prev => ({ ...prev, tipo: e.target.value }))}
              options={[{ value: '', label: 'Todos los tipos' }, ...TIPOS_STOCK]}
              className="w-full sm:w-40"
              label=""
            />
          </div>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  {columns.map((col, index) => (
                    <th key={col.key || index} scope="col" style={{ width: col.width }}>
                      {col.header}
                    </th>
                  ))}
                  <th scope="col" style={{ width: '48px' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredStock.map((row, rowIndex) => (
                  <React.Fragment key={row.id}>
                    <tr 
                      onClick={() => toggleExpand(row.id)}
                      className={`cursor-pointer transition-colors ${expandedRow === row.id ? 'bg-coffee-500/5' : ''}`}
                    >
                      {columns.map((col, colIndex) => (
                        <td key={col.key || colIndex} className={col.className}>
                          {col.render ? col.render(row[col.key], row) : row[col.key]}
                        </td>
                      ))}
                      <td className="text-center">
                        <button
                          onClick={e => { e.stopPropagation(); handleEdit(row); }}
                          className="btn-ghost btn-sm p-1.5 rounded-lg"
                          aria-label="Editar"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                    
                    {expandedRow === row.id && (
                      <tr>
                        <td colSpan={columns.length + 1} className="p-0">
                          <div className="bg-[var(--color-bg-tertiary)] border-t border-[var(--color-border)] animate-slide-in">
                            <div className="p-4 sm:p-6">
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                                <div className="flex items-center gap-3">
                                  <span className={`w-10 h-10 rounded-lg flex items-center justify-center ${row.tipo === 'verde' ? 'bg-green-500/10' : 'bg-coffee-500/10'}`}>
                                    {row.tipo === 'verde' ? <Coffee className="w-5 h-5 text-green-600" /> : <Package2 className="w-5 h-5 text-coffee-600" />}
                                  </span>
                                  <div>
                                    <h3 className="font-semibold text-lg text-[var(--color-text-primary)]">{row.variedad}</h3>
                                    <p className="text-sm text-[var(--color-text-muted)]">{row.origen} · Lote: {row.lotePrincipal}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Button variant="secondary" size="sm" onClick={() => setBolsaEditMode(row.id)}>
                                    {bolsaEditMode === row.id ? 'Ver' : 'Editar Bolsas'}
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => handleAddBolsa(row.id)}>
                                    <Plus className="w-4 h-4" />
                                    Agregar Bolsa
                                  </Button>
                                </div>
                              </div>

                              {bolsaEditMode === row.id ? (
                                <div className="space-y-4">
                                  <div className="flex items-center justify-between text-sm text-[var(--color-text-muted)]">
                                    <span>Click en 🔒/🔓 para cambiar estado · "Vaciar" para poner a 0 · Editar kilos directamente</span>
                                  </div>
                                  
                                  <div className="grid gap-4 lg:grid-cols-2">
                                    <div>
                                      <h4 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                        Bolsas Cerradas ({row.bolsas?.filter(b => b.estado === 'cerrada').length || 0})
                                      </h4>
                                      <div className="space-y-2 max-h-64 overflow-y-auto">
                                        {row.bolsas?.filter(b => b.estado === 'cerrada').map((bolsa, index) => (
                                          <BolsaCard
                                            key={bolsa.id}
                                            bolsa={bolsa}
                                            index={index}
                                            onUpdateKilos={(id, kilos) => handleBolsaUpdateKilos(row.id, id, kilos)}
                                            onToggleEstado={(id) => handleBolsaToggleEstado(row.id, id)}
                                            onDelete={(id) => handleBolsaDelete(row.id, id)}
                                            editable
                                          />
                                        ))}
                                        {row.bolsas?.filter(b => b.estado === 'cerrada').length === 0 && (
                                          <p className="text-center text-[var(--color-text-muted)] py-4 text-sm">Sin bolsas cerradas</p>
                                        )}
                                      </div>
                                    </div>
                                    <div>
                                      <h4 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                                        <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                        Bolsas Abiertas ({row.bolsas?.filter(b => b.estado === 'abierta').length || 0})
                                      </h4>
                                      <div className="space-y-2 max-h-64 overflow-y-auto">
                                        {row.bolsas?.filter(b => b.estado === 'abierta').map((bolsa, index) => (
                                          <BolsaCard
                                            key={bolsa.id}
                                            bolsa={bolsa}
                                            index={index}
                                            onUpdateKilos={(id, kilos) => handleBolsaUpdateKilos(row.id, id, kilos)}
                                            onToggleEstado={(id) => handleBolsaToggleEstado(row.id, id)}
                                            onDelete={(id) => handleBolsaDelete(row.id, id)}
                                            editable
                                          />
                                        ))}
                                        {row.bolsas?.filter(b => b.estado === 'abierta').length === 0 && (
                                          <p className="text-center text-[var(--color-text-muted)] py-4 text-sm">Sin bolsas abiertas</p>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="grid gap-4 lg:grid-cols-2">
                                  <div>
                                    <h4 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                                      <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                      Bolsas Cerradas
                                    </h4>
                                    <div className="grid gap-2 sm:grid-cols-2">
                                      {row.bolsas?.filter(b => b.estado === 'cerrada').map((bolsa, index) => (
                                        <BolsaCard key={bolsa.id} bolsa={bolsa} index={index} />
                                      ))}
                                      {row.bolsas?.filter(b => b.estado === 'cerrada').length === 0 && (
                                        <div className="col-span-full text-center text-[var(--color-text-muted)] py-4 text-sm">Sin bolsas cerradas</div>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                                      <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                      Bolsas Abiertas
                                    </h4>
                                    <div className="grid gap-2 sm:grid-cols-2">
                                      {row.bolsas?.filter(b => b.estado === 'abierta').map((bolsa, index) => (
                                        <BolsaCard key={bolsa.id} bolsa={bolsa} index={index} />
                                      ))}
                                      {row.bolsas?.filter(b => b.estado === 'abierta').length === 0 && (
                                        <div className="col-span-full text-center text-[var(--color-text-muted)] py-4 text-sm">Sin bolsas abiertas</div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          
          {filteredStock.length === 0 && (
            <div className="empty-state">
              <Package2 className="empty-state-icon w-12 h-12" />
              <p className="empty-state-title">Sin resultados</p>
              <p className="empty-state-description">No hay cafés que coincidan con los filtros</p>
            </div>
          )}
        </div>
      </div>

      <StockForm
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
              <p className="text-[var(--color-text-secondary)]">¿Está seguro de eliminar este café y todas sus bolsas? Esta acción no se puede deshacer.</p>
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