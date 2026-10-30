import { useState, useMemo } from 'react'
import { useData } from '../context/DataContext'
import { useToast } from '../hooks/useToast.jsx'
import { ESTADOS_PEDIDO, MEDIOS_CONTACTO } from '../data/constants'
import PedidoForm from '../components/forms/PedidoForm'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import { formatearMoneda, formatearFecha, formatearKilos } from '../utils/formatters'
import { ShoppingCart, Plus, Filter, Trash2, Edit, Eye, Truck, CheckCircle, Clock } from 'lucide-react'

export default function Pedidos() {
  const { 
    pedidos, 
    clientes, 
    addPedido, 
    updatePedido, 
    deletePedido,
    getPedidosByEstado 
  } = useData()
  const { success, error: toastError } = useToast()

  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [viewDetail, setViewDetail] = useState(null)
  const [filters, setFilters] = useState({ estado: '', search: '', clienteId: '' })
  const [kanbanView, setKanbanView] = useState(false)

  const pedidosPendientes = getPedidosByEstado('Pendiente')
  const pedidosListos = getPedidosByEstado('Listo')
  const pedidosEntregados = getPedidosByEstado('Entregado')

  const filteredPedidos = useMemo(() => {
    return pedidos.filter(pedido => {
      const matchesEstado = !filters.estado || pedido.estado === filters.estado
      const matchesCliente = !filters.clienteId || pedido.clienteId === filters.clienteId
      const cliente = clientes.find(c => c.id === pedido.clienteId)
      const matchesSearch = !filters.search || 
        (cliente && cliente.nombre.toLowerCase().includes(filters.search.toLowerCase())) ||
        pedido.medioContacto.toLowerCase().includes(filters.search.toLowerCase()) ||
        pedido.observaciones.toLowerCase().includes(filters.search.toLowerCase())
      return matchesEstado && matchesCliente && matchesSearch
    })
  }, [pedidos, clientes, filters])

  const handleSubmit = async (data, id) => {
    try {
      if (id) {
        await updatePedido(id, data)
        success('Pedido actualizado')
      } else {
        await addPedido(data)
        success('Pedido creado')
      }
      setShowForm(false)
      setEditingItem(null)
    } catch (err) {
      toastError(err.message || 'No se pudo guardar el pedido')
    }
  }

  const handleEdit = (item) => {
    setEditingItem(item)
    setShowForm(true)
  }

  const handleViewDetail = (item) => {
    setViewDetail(item)
  }

  const handleDelete = (id) => {
    setDeleteConfirm(id)
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return

    try {
      await deletePedido(deleteConfirm)
      success('Pedido eliminado')
      setDeleteConfirm(null)
    } catch (err) {
      toastError(err.message || 'No se pudo eliminar el pedido')
    }
  }

  const changeEstado = async (pedido, nuevoEstado) => {
    try {
      await updatePedido(pedido.id, { estado: nuevoEstado })
      success(`Pedido actualizado a ${nuevoEstado}`)
    } catch (err) {
      toastError(err.message || 'No se pudo cambiar el estado')
    }
  }

  const estadoIcon = {
    Pendiente: Clock,
    Listo: CheckCircle,
    Entregado: Truck,
  }

  const estadoColor = {
    Pendiente: 'warning',
    Listo: 'info',
    Entregado: 'success',
  }

  const columns = [
    { key: 'fecha', header: 'Fecha', width: '100px', render: (v) => formatearFecha(v) },
    { key: 'cliente', header: 'Cliente', render: (_, row) => {
      const cliente = clientes.find(c => c.id === row.clienteId)
      return cliente?.nombre || 'Desconocido'
    }},
    { key: 'estado', header: 'Estado', width: '110px', render: (v) => <Badge variant={estadoColor[v]}>{v}</Badge> },
    { key: 'items', header: 'Items', render: (v) => `${v.length} producto${v.length !== 1 ? 's' : ''}` },
    { key: 'kilos', header: 'Kilos', render: (_, row) => formatearKilos(row.items.reduce((sum, i) => sum + i.kilos, 0)), className: 'font-mono tabular-nums' },
    { key: 'total', header: 'Total', render: (v) => formatearMoneda(v), className: 'font-mono tabular-nums font-medium text-right' },
    { key: 'medioContacto', header: 'Contacto', width: '120px' },
  ]

  const kanbanColumns = ESTADOS_PEDIDO.map(estado => ({
    estado: estado.value,
    label: estado.label,
    color: estado.color,
    items: filteredPedidos.filter(p => p.estado === estado.value)
      .sort((a, b) => new Date(a.fecha) - new Date(b.fecha)),
  }))

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Pedidos</h1>
          <p className="text-[var(--color-text-muted)]">Gestión de pedidos y estados</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setKanbanView(!kanbanView)}>
            {kanbanView ? 'Vista Tabla' : 'Vista Kanban'}
          </Button>
          <Button onClick={() => { setEditingItem(null); setShowForm(true); }}>
            <Plus className="w-4 h-4" />
            Nuevo Pedido
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-5 border-l-4 border-amber-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Pendientes</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{pedidosPendientes.length}</p>
            </div>
            <Clock className="w-8 h-8 text-amber-500" />
          </div>
        </div>
        <div className="card p-5 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Listos</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{pedidosListos.length}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        <div className="card p-5 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Entregados</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">{pedidosEntregados.length}</p>
            </div>
            <Truck className="w-8 h-8 text-green-500" />
          </div>
        </div>
      </div>

      {kanbanView ? (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Tablero Kanban</h2>
            <div className="flex gap-2">
              <Select
                value={filters.estado}
                onChange={e => setFilters(prev => ({ ...prev, estado: e.target.value }))}
                options={[{ value: '', label: 'Todos los estados' }, ...ESTADOS_PEDIDO]}
                className="w-40"
                label=""
              />
              <Select
                value={filters.clienteId}
                onChange={e => setFilters(prev => ({ ...prev, clienteId: e.target.value }))}
                options={[{ value: '', label: 'Todos los clientes' }, ...clientes.map(c => ({ value: c.id, label: c.nombre }))]}
                className="w-48"
                label=""
              />
            </div>
          </div>
          <div className="card-body p-0">
            <div className="flex gap-4 p-4 overflow-x-auto min-h-[500px]">
              {kanbanColumns.map(col => (
                <div key={col.estado} className="flex-1 min-w-[300px] max-w-[350px]">
                  <div className="flex items-center justify-between mb-3">
                    <Badge variant={col.color} className="text-xs font-medium px-3 py-1">
                      {col.label} <span className="ml-2 px-2 py-0.5 bg-white/20 rounded-full text-xs">{col.items.length}</span>
                    </Badge>
                  </div>
                  <div className="space-y-3 min-h-[400px] bg-[var(--color-bg-tertiary)]/50 rounded-lg p-2" 
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => {
                      e.preventDefault()
                      const pedidoId = e.dataTransfer.getData('pedidoId')
                      if (pedidoId) {
                        const pedido = pedidos.find(p => p.id === pedidoId)
                        if (pedido && pedido.estado !== col.estado) {
                          changeEstado(pedido, col.estado)
                        }
                      }
                    }}>
                    {col.items.map(pedido => {
                      const cliente = clientes.find(c => c.id === pedido.clienteId)
                      return (
                        <div 
                          key={pedido.id}
                          draggable
                          onDragStart={e => e.dataTransfer.setData('pedidoId', pedido.id)}
                          className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3 hover:shadow-soft transition-shadow cursor-grab active:cursor-grabbing"
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-[var(--color-text-primary)] truncate">{cliente?.nombre || 'Cliente desconocido'}</p>
                              <p className="text-xs text-[var(--color-text-muted)]">{formatearFecha(pedido.fecha)}</p>
                            </div>
                            <button onClick={() => handleViewDetail(pedido)} className="btn-ghost btn-sm p-1 opacity-0 hover:opacity-100 transition-opacity" aria-label="Ver detalle">
                              <Eye className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
                            <span>{pedido.items.length} items · {formatearKilos(pedido.items.reduce((s, i) => s + i.kilos, 0))}</span>
                            <span className="font-medium text-[var(--color-text-primary)]">{formatearMoneda(pedido.total)}</span>
                          </div>
                          <div className="flex gap-1 mt-2">
                            {ESTADOS_PEDIDO.filter(e => e.value !== pedido.estado).map(e => (
                              <button
                                key={e.value}
                                onClick={() => changeEstado(pedido, e.value)}
                                className={`flex-1 text-xs py-1 rounded ${pedido.estado === e.value ? 'bg-coffee-500 text-white' : 'bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)]'}`}
                              >
                                {e.value === 'Pendiente' ? '⏳' : e.value === 'Listo' ? '✓' : '🚚'}
                              </button>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                    {col.items.length === 0 && (
                      <div className="text-center py-8 text-[var(--color-text-muted)] text-sm">
                        Arrastrar pedidos aquí
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Listado de Pedidos</h2>
            <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
                <Input
                  placeholder="Buscar cliente, contacto..."
                  value={filters.search}
                  onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  className="pl-10"
                />
              </div>
              <Select
                value={filters.estado}
                onChange={e => setFilters(prev => ({ ...prev, estado: e.target.value }))}
                options={[{ value: '', label: 'Todos los estados' }, ...ESTADOS_PEDIDO]}
                className="w-full sm:w-40"
                label=""
              />
              <Select
                value={filters.clienteId}
                onChange={e => setFilters(prev => ({ ...prev, clienteId: e.target.value }))}
                options={[{ value: '', label: 'Todos los clientes' }, ...clientes.map(c => ({ value: c.id, label: c.nombre }))]}
                className="w-full sm:w-48"
                label=""
              />
            </div>
          </div>
          <div className="card-body p-0">
            <Table
              columns={columns}
              data={filteredPedidos}
              onRowClick={handleViewDetail}
              emptyMessage="No hay pedidos que coincidan con los filtros"
            />
          </div>
        </div>
      )}

      <PedidoForm
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditingItem(null); }}
        initialData={editingItem}
        onSubmit={handleSubmit}
      />

      {viewDetail && (
        <div className="modal-overlay" onClick={() => setViewDetail(null)}>
          <div className="modal-content max-w-2xl" onClick={e => e.stopPropagation()}>
            <div className="modal-header flex flex-wrap items-center gap-4">
              <div>
                <h2 className="text-lg font-semibold">Pedido #{viewDetail.id.slice(0, 8)}</h2>
                <Badge variant={estadoColor[viewDetail.estado]}>{viewDetail.estado}</Badge>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => { setEditingItem(viewDetail); setViewDetail(null); setShowForm(true); }}>
                  <Edit className="w-4 h-4" />
                  Editar
                </Button>
              </div>
            </div>
            <div className="modal-body">
              <div className="grid gap-4 sm:grid-cols-2 mb-6">
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Cliente</p>
                  <p className="font-medium">{clientes.find(c => c.id === viewDetail.clienteId)?.nombre || 'Desconocido'}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Fecha</p>
                  <p className="font-medium">{formatearFecha(viewDetail.fecha)}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Medio de contacto</p>
                  <p className="font-medium">{viewDetail.medioContacto}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Estado</p>
                  <p className="font-medium"><Badge variant={estadoColor[viewDetail.estado]}>{viewDetail.estado}</Badge></p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-sm text-[var(--color-text-muted)]">Observaciones</p>
                  <p className="font-medium">{viewDetail.observaciones || 'Sin observaciones'}</p>
                </div>
              </div>

              <div className="border-t border-[var(--color-border)] pt-4 mb-4">
                <h3 className="font-medium text-[var(--color-text-primary)] mb-3">Items del Pedido</h3>
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th className="text-right">Kilos</th>
                        <th className="text-right">Precio/Kg</th>
                        <th className="text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {viewDetail.items.map((item, index) => (
                        <tr key={index}>
                          <td>{item.variedad}</td>
                          <td className="text-right font-mono tabular-nums">{formatearKilos(item.kilos)}</td>
                          <td className="text-right font-mono tabular-nums">{formatearMoneda(item.precioKg)}</td>
                          <td className="text-right font-mono tabular-nums font-medium">{formatearMoneda(item.kilos * item.precioKg)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="w-64 bg-[var(--color-bg-tertiary)] rounded-lg p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[var(--color-text-secondary)]">Subtotal</span>
                    <span className="font-medium">{formatearMoneda(viewDetail.total)}</span>
                  </div>
                  <div className="flex justify-between border-t border-[var(--color-border)] pt-2">
                    <span className="font-medium text-[var(--color-text-primary)]">Total</span>
                    <span className="font-bold text-lg text-coffee-600 dark:text-coffee-400">{formatearMoneda(viewDetail.total)}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setViewDetail(null)}>Cerrar</Button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal-content max-w-md" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="text-lg font-semibold">Confirmar eliminación</h2>
            </div>
            <div className="modal-body">
              <p className="text-[var(--color-text-secondary)]">¿Está seguro de eliminar este pedido? Esta acción no se puede deshacer.</p>
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