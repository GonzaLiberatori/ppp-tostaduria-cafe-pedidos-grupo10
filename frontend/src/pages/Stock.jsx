import { Fragment, useMemo, useState } from 'react'
import { useData } from '../context/DataContext'
import CafeForm from '../components/forms/CafeForm'
import LoteForm from '../components/forms/LoteForm'
import LoteCard from '../components/forms/LoteCard'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import { formatearMoneda, formatearKilos, formatearFecha } from '../utils/formatters'
import { nombreCafe, origenCafe, esOrganico, kilosCafe } from '../utils/cafes'
import { TIPOS_CAFE, TIPOS_LOTE } from '../data/constants'
import { Package, Plus, Filter, Trash2, Pencil, AlertTriangle, ChevronDown, ChevronUp, Coffee, Package2 } from 'lucide-react'

export default function Stock() {
  const {
    cafes,
    ordenesTueste,
    loading,
    error,
    cargarInventario,
    addCafe,
    updateCafe,
    deleteCafe,
    addLote,
    updateLote,
    deleteLote,
    getOrdenTuesteById,
  } = useData()

  const [showCafeForm, setShowCafeForm] = useState(false)
  const [editingCafe, setEditingCafe] = useState(null)
  const [showLoteForm, setShowLoteForm] = useState(false)
  const [loteCafeId, setLoteCafeId] = useState(null)
  const [editingLote, setEditingLote] = useState(null)
  const [expandedRow, setExpandedRow] = useState(null)
  const [filters, setFilters] = useState({ tipoProducto: '', tipoLote: '', search: '' })
  const [deleteCafeConfirm, setDeleteCafeConfirm] = useState(null)
  const [deleteLoteConfirm, setDeleteLoteConfirm] = useState(null)
  const [formError, setFormError] = useState(null)

  const cafesPorId = useMemo(
    () => Object.fromEntries(cafes.map(cafe => [cafe.id, cafe])),
    [cafes]
  )

  const totalVerde = cafes.reduce((sum, cafe) => sum + kilosCafe(cafe, 'verde'), 0)
  const totalTostado = cafes.reduce((sum, cafe) => sum + kilosCafe(cafe, 'tostado'), 0)
  const valorVerde = cafes.reduce((sum, cafe) => sum + kilosCafe(cafe, 'verde') * (cafe.precioKg || 0), 0)
  const valorTostado = cafes.reduce((sum, cafe) => sum + kilosCafe(cafe, 'tostado') * (cafe.precioKg || 0), 0)

  const filteredCafes = useMemo(() => {
    return cafes.filter(cafe => {
      const texto = [nombreCafe(cafe), cafe.variedad, cafe.pais, cafe.region, cafe.descripcion]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      const matchesSearch = !filters.search || texto.includes(filters.search.toLowerCase())
      const matchesTipo = !filters.tipoProducto || cafe.tipoProducto === filters.tipoProducto
      const matchesLote = !filters.tipoLote || kilosCafe(cafe, filters.tipoLote) > 0
      return matchesSearch && matchesTipo && matchesLote
    })
  }, [cafes, filters])

  const alertasStock = useMemo(() => {
    return cafes.flatMap(cafe => {
      const lotes = cafe.lotes || []
      const alertas = []
      if (lotes.some(l => l.tipo === 'verde') && kilosCafe(cafe, 'verde') < 30) {
        alertas.push({ cafe, tipo: 'verde' })
      }
      if (lotes.some(l => l.tipo === 'tostado') && kilosCafe(cafe, 'tostado') < 5) {
        alertas.push({ cafe, tipo: 'tostado' })
      }
      return alertas
    })
  }, [cafes])

  const handleCafeSubmit = async (data, id) => {
    try {
      setFormError(null)
      if (id) {
        await updateCafe(id, data)
      } else {
        await addCafe(data)
      }
      setShowCafeForm(false)
      setEditingCafe(null)
    } catch (err) {
      setFormError(err.message || 'Error al guardar el café')
    }
  }

  const handleEditCafe = (cafe) => {
    setEditingCafe(cafe)
    setShowCafeForm(true)
    setExpandedRow(null)
  }

  const abrirNuevoLote = (cafeId) => {
    setEditingLote(null)
    setLoteCafeId(cafeId)
    setShowLoteForm(true)
  }

  const abrirEditarLote = (cafeId, lote) => {
    setEditingLote(lote)
    setLoteCafeId(cafeId)
    setShowLoteForm(true)
  }

  const handleLoteSubmit = async (data, loteId, cafeOrigenId) => {
    try {
      setFormError(null)
      if (loteId) {
        await updateLote(cafeOrigenId, loteId, data)
      } else {
        await addLote(data.cafeId, data)
      }
      setShowLoteForm(false)
      setEditingLote(null)
      setLoteCafeId(null)
    } catch (err) {
      setFormError(err.message || 'Error al guardar el lote')
    }
  }

  const confirmDeleteCafe = async () => {
    if (deleteCafeConfirm) {
      try {
        setFormError(null)
        await deleteCafe(deleteCafeConfirm)
        setDeleteCafeConfirm(null)
      } catch (err) {
        setFormError(err.message || 'Error al eliminar el café')
      }
    }
  }

  const confirmDeleteLote = async () => {
    if (deleteLoteConfirm) {
      try {
        setFormError(null)
        await deleteLote(deleteLoteConfirm.cafeId, deleteLoteConfirm.loteId)
        setDeleteLoteConfirm(null)
      } catch (err) {
        setFormError(err.message || 'Error al eliminar el lote')
      }
    }
  }

  const renderLotes = (cafe, estado) => {
    const lotes = (cafe.lotes || []).filter(lote => lote.estado === estado)
    if (lotes.length === 0) return null
    return (
      <div>
        <h4 className="mb-3 flex items-center gap-2 font-medium text-[var(--color-text-primary)]">
          <span className={`h-2 w-2 rounded-full ${estado === 'cerrado' ? 'bg-green-500' : 'bg-amber-500'}`}></span>
          Lotes {estado === 'cerrado' ? 'cerrados' : 'abiertos'} ({lotes.length})
        </h4>
        <div className="grid gap-2 sm:grid-cols-2">
          {lotes.map(lote => (
            <LoteCard
              key={lote.id}
              lote={lote}
              ordenTuesteId={getOrdenTuesteById(lote.ordenTuesteId)?.id}
              onEdit={() => abrirEditarLote(cafe.id, lote)}
              onDelete={() => setDeleteLoteConfirm({ cafeId: cafe.id, loteId: lote.id })}
            />
          ))}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-coffee-500 border-t-transparent"></div>
          <p className="text-[var(--color-text-secondary)]">Cargando inventario...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center">
        <p className="mb-2 font-medium text-red-600 dark:text-red-400">Error al cargar el inventario</p>
        <p className="text-sm text-red-500 dark:text-red-300">{error}</p>
        <button
          onClick={cargarInventario}
          className="mt-4 rounded-lg bg-red-500 px-4 py-2 text-white hover:bg-red-600"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {formError && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
            <div className="flex-1">
              <p className="text-sm text-red-700 dark:text-red-300">{formError}</p>
            </div>
            <button
              onClick={() => setFormError(null)}
              className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
            >
              ×
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-[var(--color-text-primary)]">
            <Package2 className="h-6 w-6 text-coffee-500" />
            Stock de Café
          </h1>
          <p className="text-[var(--color-text-muted)]">Catálogo de cafés simples y blends, con lotes de café verde y tostado</p>
        </div>
        <Button onClick={() => { setEditingCafe(null); setShowCafeForm(true) }}>
          <Plus className="h-4 w-4" />
          Nuevo Café
        </Button>
      </div>

      {alertasStock.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600 dark:text-amber-400" />
            <div className="flex-1">
              <h3 className="font-medium text-amber-900 dark:text-amber-100">Stock Bajo</h3>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                {alertasStock.length} alerta{alertasStock.length !== 1 ? 's' : ''} por debajo del mínimo (verde &lt; 30 kg, tostado &lt; 5 kg):
                <ul className="mt-1 list-inside list-disc text-xs">
                  {alertasStock.map(({ cafe, tipo }) => (
                    <li key={`${cafe.id}-${tipo}`}>
                      {nombreCafe(cafe)} ({formatearKilos(kilosCafe(cafe, tipo))}) - {tipo === 'verde' ? 'Verde' : 'Tostado'}
                    </li>
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
              <p className="mt-1 text-2xl font-bold text-[var(--color-text-primary)]">{formatearKilos(totalVerde)}</p>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">Valor: {formatearMoneda(valorVerde)}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/10">
              <Coffee className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Café Tostado Total</p>
              <p className="mt-1 text-2xl font-bold text-[var(--color-text-primary)]">{formatearKilos(totalTostado)}</p>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">Valor: {formatearMoneda(valorTostado)}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-coffee-500/10">
              <Package2 className="h-6 w-6 text-coffee-600 dark:text-coffee-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Valor Inventario</p>
              <p className="mt-1 text-2xl font-bold text-[var(--color-text-primary)]">{formatearMoneda(valorVerde + valorTostado)}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10">
              <Package className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Cafés</p>
              <p className="mt-1 text-2xl font-bold text-[var(--color-text-primary)]">{cafes.length}</p>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                {cafes.filter(c => c.tipoProducto === 'simple').length} simples · {cafes.filter(c => c.tipoProducto === 'blend').length} blends
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10">
              <Package2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Catálogo de Cafés</h2>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            <div className="relative flex-1 sm:w-64">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <Input
                placeholder="Buscar variedad, origen, blend..."
                value={filters.search}
                onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            <Select
              value={filters.tipoProducto}
              onChange={e => setFilters(prev => ({ ...prev, tipoProducto: e.target.value }))}
              options={[{ value: '', label: 'Simple y Blend' }, ...TIPOS_CAFE]}
              className="w-full sm:w-40"
              label=""
            />
            <Select
              value={filters.tipoLote}
              onChange={e => setFilters(prev => ({ ...prev, tipoLote: e.target.value }))}
              options={[{ value: '', label: 'Todos los lotes' }, ...TIPOS_LOTE]}
              className="w-full sm:w-44"
              label=""
            />
          </div>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Variedad y origen</th>
                  <th scope="col" className="text-right">Café verde</th>
                  <th scope="col" className="text-right">Café tostado</th>
                  <th scope="col" className="text-right">Precio / kg</th>
                  <th scope="col">Orgánico</th>
                  <th scope="col" style={{ width: '96px' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredCafes.map(cafe => {
                  const expandido = expandedRow === cafe.id
                  const verde = kilosCafe(cafe, 'verde')
                  const tostado = kilosCafe(cafe, 'tostado')
                  const organico = esOrganico(cafe, cafesPorId)

                  return (
                    <Fragment key={cafe.id}>
                      <tr
                        onClick={() => setExpandedRow(prev => (prev === cafe.id ? null : cafe.id))}
                        className={`cursor-pointer transition-colors ${expandido ? 'bg-coffee-500/5' : ''}`}
                      >
                        <td>
                          <div className="flex items-start gap-2">
                            <span className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${cafe.tipoProducto === 'blend' ? 'bg-coffee-500/10' : 'bg-green-500/10'}`}>
                              {cafe.tipoProducto === 'blend'
                                ? <Package2 className="h-4 w-4 text-coffee-600 dark:text-coffee-400" />
                                : <Coffee className="h-4 w-4 text-green-600 dark:text-green-400" />}
                            </span>
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-medium text-[var(--color-text-primary)]">{nombreCafe(cafe)}</p>
                                <Badge variant={cafe.tipoProducto === 'blend' ? 'coffee' : 'info'} className="text-xs">
                                  {cafe.tipoProducto === 'blend' ? 'Blend' : 'Simple'}
                                </Badge>
                              </div>
                              <p className="text-xs text-[var(--color-text-muted)]">{origenCafe(cafe)}</p>
                            </div>
                          </div>
                        </td>
                        <td className="text-right font-mono tabular-nums">{formatearKilos(verde)}</td>
                        <td className="text-right font-mono tabular-nums">{formatearKilos(tostado)}</td>
                        <td className="text-right font-mono tabular-nums">{formatearMoneda(cafe.precioKg || 0)}</td>
                        <td>
                          <Badge variant={organico ? 'success' : 'default'} className="text-xs">
                            {organico ? 'Sí' : 'No'}
                          </Badge>
                        </td>
                        <td>
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={e => { e.stopPropagation(); handleEditCafe(cafe) }}
                              className="btn-ghost btn-sm rounded-lg p-1.5"
                              aria-label={`Editar ${nombreCafe(cafe)}`}
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={e => { e.stopPropagation(); setDeleteCafeConfirm(cafe.id) }}
                              className="btn-ghost btn-sm rounded-lg p-1.5"
                              aria-label={`Eliminar ${nombreCafe(cafe)}`}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </button>
                            {expandido ? <ChevronUp className="h-4 w-4 text-[var(--color-text-muted)]" /> : <ChevronDown className="h-4 w-4 text-[var(--color-text-muted)]" />}
                          </div>
                        </td>
                      </tr>

                      {expandido && (
                        <tr>
                          <td colSpan={6} className="p-0">
                            <div className="animate-slide-in border-t border-[var(--color-border)] bg-[var(--color-bg-tertiary)]">
                              <div className="space-y-4 p-4 sm:p-6">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                  <div>
                                    <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">{nombreCafe(cafe)}</h3>
                                    <p className="text-sm text-[var(--color-text-muted)]">
                                      {origenCafe(cafe)} · Alta: {formatearFecha(cafe.fechaIngreso)}
                                    </p>
                                    {cafe.tipoProducto === 'blend' && cafe.descripcion && (
                                      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{cafe.descripcion}</p>
                                    )}
                                  </div>
                                  <Button variant="secondary" size="sm" onClick={() => handleEditCafe(cafe)}>
                                    <Pencil className="h-3.5 w-3.5" />
                                    Editar café
                                  </Button>
                                </div>

                                {cafe.tipoProducto === 'blend' && (
                                  <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
                                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">Composición de la mezcla</p>
                                    <div className="flex flex-wrap gap-2">
                                      {(cafe.mezcla || []).map(({ cafeId, porcentaje }) => {
                                        const componente = cafesPorId[cafeId]
                                        return (
                                          <Badge key={cafeId} variant="coffee" className="text-xs">
                                            {componente ? nombreCafe(componente) : 'Café eliminado'} · {porcentaje}%
                                          </Badge>
                                        )
                                      })}
                                      {(cafe.mezcla || []).length === 0 && (
                                        <span className="text-sm text-[var(--color-text-muted)]">Sin componentes definidos</span>
                                      )}
                                    </div>
                                  </div>
                                )}

                                <div className="grid gap-4 lg:grid-cols-2">
                                  {renderLotes(cafe, 'cerrado')}
                                  {renderLotes(cafe, 'abierto')}
                                </div>

                                {(cafe.lotes || []).length === 0 && (
                                  <p className="py-2 text-center text-sm text-[var(--color-text-muted)]">Este café todavía no tiene lotes cargados</p>
                                )}

                                <button
                                  type="button"
                                  onClick={() => abrirNuevoLote(cafe.id)}
                                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--color-border)] px-4 py-3 text-sm font-medium text-[var(--color-text-muted)] transition-colors hover:border-coffee-500/40 hover:text-[var(--color-text-primary)]"
                                >
                                  <Plus className="h-4 w-4" />
                                  Crear lote
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>

          {filteredCafes.length === 0 && (
            <div className="empty-state">
              <Package2 className="empty-state-icon h-12 w-12" />
              <p className="empty-state-title">Sin resultados</p>
              <p className="empty-state-description">No hay cafés que coincidan con los filtros</p>
            </div>
          )}
        </div>
      </div>

      <CafeForm
        isOpen={showCafeForm}
        onClose={() => { setShowCafeForm(false); setEditingCafe(null) }}
        initialData={editingCafe}
        onSubmit={handleCafeSubmit}
        cafes={cafes}
      />

      <LoteForm
        isOpen={showLoteForm}
        onClose={() => { setShowLoteForm(false); setEditingLote(null); setLoteCafeId(null) }}
        initialData={editingLote}
        cafeIdInicial={loteCafeId}
        onSubmit={handleLoteSubmit}
        cafes={cafes}
        ordenesTueste={ordenesTueste}
      />

      {deleteCafeConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteCafeConfirm(null)}>
          <div className="modal-content max-w-md" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="text-lg font-semibold">Confirmar eliminación</h2>
            </div>
            <div className="modal-body">
              <p className="text-[var(--color-text-secondary)]">¿Seguro que querés eliminar este café y todos sus lotes? Esta acción no se puede deshacer.</p>
            </div>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setDeleteCafeConfirm(null)}>Cancelar</Button>
              <Button variant="danger" onClick={confirmDeleteCafe}>Eliminar</Button>
            </div>
          </div>
        </div>
      )}

      {deleteLoteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteLoteConfirm(null)}>
          <div className="modal-content max-w-md" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="text-lg font-semibold">Eliminar lote</h2>
            </div>
            <div className="modal-body">
              <p className="text-[var(--color-text-secondary)]">¿Seguro que querés eliminar este lote? El stock de kilos se descontará del café.</p>
            </div>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setDeleteLoteConfirm(null)}>Cancelar</Button>
              <Button variant="danger" onClick={confirmDeleteLote}>Eliminar lote</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
