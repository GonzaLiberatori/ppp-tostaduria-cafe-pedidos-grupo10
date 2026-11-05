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
import Modal from '../components/ui/Modal'
import { formatearMoneda, formatearFecha, formatearKilos } from '../utils/formatters'
import { ShoppingCart, Plus, Filter, Trash2, Edit, Eye, Truck, CheckCircle, Clock } from 'lucide-react'

// Métodos admitidos al cobrar una entrega al contado. Crédito queda afuera
// porque en el panel representa un pagaré, no un medio de cobro.
const METODOS_PAGO_CONTADO = [
  { value: 'EFECTIVO', label: 'Efectivo' },
  { value: 'TRANSFERENCIA', label: 'Transferencia' },
  { value: 'DEBITO', label: 'Débito' },
  { value: 'MERCADO_PAGO', label: 'Mercado Pago' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'OTRO', label: 'Otro' },
]

const PLAZOS_PAGARE = [
  { value: '30', label: '30 días' },
  { value: '60', label: '60 días' },
  { value: '90', label: '90 días' },
]

export default function Pedidos() {
  const { 
    pedidos, 
    clientes, 
    ventas,
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
  const [entrega, setEntrega] = useState(null)
  const [condicionPago, setCondicionPago] = useState('CONTADO')
  const [metodoPago, setMetodoPago] = useState('EFECTIVO')
  const [plazoDias, setPlazoDias] = useState('30')
  const [entregando, setEntregando] = useState(false)

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

  const clienteDePedido = (pedido) => (
    clientes.find(c => String(c.id) === String(pedido?.clienteId))
  )

  const esClienteB2B = (cliente) => cliente?.tipo === 'B2B'

  // Devuelve la venta vigente del pedido; si solo hay una anulada, la devuelve
  // igual para poder informar que la entrega quedó sin venta.
  const ventaDePedido = (pedidoId) => {
    const delPedido = ventas.filter(v => String(v.pedido_id) === String(pedidoId))
    return delPedido.find(v => v.estado !== 'ANULADA') || delPedido[0] || null
  }

  const abrirEntrega = (pedido) => {
    setEntrega(pedido)
    setCondicionPago('CONTADO')
    setMetodoPago('EFECTIVO')
    setPlazoDias('30')
  }

  const cerrarEntrega = () => {
    if (entregando) return
    setEntrega(null)
  }

  const changeEstado = async (pedido, nuevoEstado) => {
    // La entrega crea la venta y necesita la condición de pago: se pide en un
    // modal en lugar de mandar el estado a ciegas.
    if (nuevoEstado === 'Entregado') {
      abrirEntrega(pedido)
      return
    }

    try {
      await updatePedido(pedido.id, { estado: nuevoEstado })
      success(`Pedido actualizado a ${nuevoEstado}`)
    } catch (err) {
      toastError(err.message || 'No se pudo cambiar el estado')
    }
  }

  const confirmarEntrega = async () => {
    if (!entrega) return

    const esB2B = esClienteB2B(clienteDePedido(entrega))
    const condicion = esB2B ? condicionPago : 'CONTADO'
    const cambios = { estado: 'Entregado', condicionPago: condicion }

    if (condicion === 'CONTADO') {
      cambios.metodoPago = metodoPago
    } else {
      cambios.plazoDias = Number(plazoDias)
    }

    setEntregando(true)
    try {
      await updatePedido(entrega.id, cambios)
      success(
        condicion === 'CONTADO'
          ? 'Pedido entregado con venta al contado'
          : `Pedido entregado con pagaré a ${plazoDias} días`,
      )
      setEntrega(null)
    } catch (err) {
      toastError(err.message || 'No se pudo confirmar la entrega')
    } finally {
      setEntregando(false)
    }
  }

  const ventaDetalle = viewDetail ? ventaDePedido(viewDetail.id) : null

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

  const cobroDeVenta = (venta) => {
    if (!venta) return null
    if (venta.estado === 'ANULADA') {
      return { variant: 'danger', label: 'Venta anulada' }
    }
    if (venta.estado === 'PENDIENTE_COBRO') {
      return {
        variant: 'warning',
        label: `Pagaré · vence ${formatearFecha(venta.fecha_vencimiento)}`,
      }
    }
    return {
      variant: 'success',
      label: venta.fecha_vencimiento ? 'Pagaré cobrado' : 'Contado',
    }
  }

  const columns = [
    { key: 'fecha', header: 'Fecha', width: '100px', render: (v) => formatearFecha(v) },
    { key: 'cliente', header: 'Cliente', render: (_, row) => {
      const cliente = clientes.find(c => c.id === row.clienteId)
      return cliente?.nombre || 'Desconocido'
    }},
    { key: 'estado', header: 'Estado', width: '110px', render: (v) => <Badge variant={estadoColor[v]}>{v}</Badge> },
    { key: 'cobro', header: 'Cobro', width: '170px', render: (_, row) => {
      const cobro = cobroDeVenta(ventaDePedido(row.id))
      return cobro
        ? <Badge variant={cobro.variant}>{cobro.label}</Badge>
        : <span className="text-[var(--color-text-muted)]">-</span>
    }},
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
                          {(() => {
                            const cobro = cobroDeVenta(ventaDePedido(pedido.id))
                            if (!cobro) return null
                            return (
                              <div className="mt-2">
                                <Badge variant={cobro.variant} className="text-[10px]">{cobro.label}</Badge>
                              </div>
                            )
                          })()}
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

      <Modal
        isOpen={Boolean(entrega)}
        onClose={cerrarEntrega}
        title="Confirmar entrega"
        size="md"
        confirmAction={confirmarEntrega}
        confirmText="Confirmar entrega"
        loading={entregando}
      >
        {entrega && (() => {
          const cliente = clienteDePedido(entrega)
          const esB2B = esClienteB2B(cliente)
          const condicion = esB2B ? condicionPago : 'CONTADO'
          const vencimiento = condicion === 'PAGARE'
            ? new Date(Date.now() + Number(plazoDias) * 24 * 60 * 60 * 1000)
            : null

          return (
            <div className="space-y-4">
              <div className="grid gap-2 sm:grid-cols-2 text-sm">
                <div>
                  <p className="text-[var(--color-text-muted)]">Cliente</p>
                  <p className="font-medium">{cliente?.nombre || 'Desconocido'}</p>
                </div>
                <div>
                  <p className="text-[var(--color-text-muted)]">Total del pedido</p>
                  <p className="font-medium font-mono tabular-nums">{formatearMoneda(entrega.total)}</p>
                </div>
              </div>

              <Select
                label="Condición de pago"
                value={condicion}
                onChange={e => setCondicionPago(e.target.value)}
                options={[
                  { value: 'CONTADO', label: 'Contado' },
                  {
                    value: 'PAGARE',
                    label: esB2B
                      ? 'Pagaré (cuenta corriente)'
                      : 'Pagaré (solo mayoristas)',
                    disabled: !esB2B,
                  },
                ]}
              />

              {condicion === 'CONTADO' ? (
                <Select
                  label="Método de pago"
                  value={metodoPago}
                  onChange={e => setMetodoPago(e.target.value)}
                  options={METODOS_PAGO_CONTADO}
                />
              ) : (
                <Select
                  label="Plazo del pagaré"
                  value={plazoDias}
                  onChange={e => setPlazoDias(e.target.value)}
                  options={PLAZOS_PAGARE}
                />
              )}

              {!esB2B && (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  {cliente?.nombre || 'El cliente'} es minorista: no tiene cuenta
                  corriente, así que la entrega solo puede registrarse al contado.
                </p>
              )}

              <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-lg p-4 text-sm">
                {condicion === 'CONTADO' ? (
                  <p>
                    Se registrará una venta <strong>al contado</strong> por{' '}
                    <strong>{formatearMoneda(entrega.total)}</strong> con el método{' '}
                    <strong>
                      {METODOS_PAGO_CONTADO.find(m => m.value === metodoPago)?.label || metodoPago}
                    </strong>.
                  </p>
                ) : (
                  <p>
                    Se registrará una venta <strong>a pagaré</strong> por{' '}
                    <strong>{formatearMoneda(entrega.total)}</strong>, con vencimiento
                    el <strong>{formatearFecha(vencimiento)}</strong>. La deuda se
                    sumará a la cuenta corriente del cliente.
                  </p>
                )}
              </div>
            </div>
          )
        })()}
      </Modal>

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
                  <p className="text-sm text-[var(--color-text-muted)]">Cobro</p>
                  {ventaDetalle ? (
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <Badge
                        variant={
                          ventaDetalle.estado === 'PENDIENTE_COBRO'
                            ? 'warning'
                            : ventaDetalle.estado === 'ANULADA'
                              ? 'danger'
                              : 'success'
                        }
                      >
                        {ventaDetalle.estado === 'ANULADA'
                          ? 'Venta anulada'
                          : ventaDetalle.fecha_vencimiento
                            ? 'Pagaré'
                            : 'Contado'}
                      </Badge>
                      <span className="text-sm text-[var(--color-text-secondary)]">
                        {ventaDetalle.numero_comprobante || 'Sin comprobante'}
                      </span>
                      {ventaDetalle.estado === 'PENDIENTE_COBRO' && (
                        <span className="text-sm text-amber-600 dark:text-amber-400">
                          Pendiente de cobro · vence {formatearFecha(ventaDetalle.fecha_vencimiento)}
                        </span>
                      )}
                      {ventaDetalle.estado === 'CONFIRMADA' && (
                        <span className="text-sm text-[var(--color-text-muted)]">
                          Cobrado{ventaDetalle.cobrada_en ? ` el ${formatearFecha(ventaDetalle.cobrada_en)}` : ''}
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="font-medium text-[var(--color-text-muted)]">
                      {viewDetail.estado === 'Entregado'
                        ? 'Sin venta registrada (pedido heredado)'
                        : 'Se registra al confirmar la entrega'}
                    </p>
                  )}
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
                          <td>
                            {item.nombre || item.variedad || 'Café'}
                            {item.stockId?.endsWith('-VERDE') && (
                              <span className="ml-2 inline-flex items-center rounded bg-green-500/10 px-1.5 py-0.5 text-xs font-medium text-green-700">
                                Verde
                              </span>
                            )}
                          </td>
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