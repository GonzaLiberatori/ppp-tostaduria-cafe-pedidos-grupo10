import { useState, useMemo } from 'react'
import { useData } from '../context/DataContext'
import { useToast } from '../hooks/useToast.jsx'
import { TIPOS_CLIENTE } from '../data/constants'
import ClienteForm from '../components/forms/ClienteForm'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import { formatearMoneda, formatearKilos, formatearFecha } from '../utils/formatters'
import { Users, Plus, Filter, Trash2, Edit, CreditCard, DollarSign, Package } from 'lucide-react'

export default function Clientes() {
  const { 
    clientes, 
    addCliente, 
    updateCliente, 
    deleteCliente, 
    getPedidosByCliente,
    getClientesConDeuda 
  } = useData()
  const { success, error: toastError } = useToast()

  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [viewDetail, setViewDetail] = useState(null)
  const [filters, setFilters] = useState({ tipo: '', search: '', deuda: '' })

  const clientesConDeuda = getClientesConDeuda()
  const totalDeuda = clientesConDeuda.reduce((sum, c) => sum + c.montoDeuda, 0)
  const totalKilos = clientes.reduce((sum, c) => sum + c.kilosComprados, 0)

  const filteredClientes = useMemo(() => {
    return clientes.filter(cliente => {
      const matchesTipo = !filters.tipo || cliente.tipo === filters.tipo
      const matchesDeuda = filters.deuda === '' || 
        (filters.deuda === 'con' && cliente.tieneDeuda && cliente.montoDeuda > 0) ||
        (filters.deuda === 'sin' && (!cliente.tieneDeuda || cliente.montoDeuda === 0))
      const matchesSearch = !filters.search || 
        cliente.nombre.toLowerCase().includes(filters.search.toLowerCase()) ||
        cliente.email.toLowerCase().includes(filters.search.toLowerCase()) ||
        cliente.telefono.includes(filters.search)
      return matchesTipo && matchesDeuda && matchesSearch
    })
  }, [clientes, filters])

  const handleSubmit = async (data, id) => {
    try {
      if (id) {
        await updateCliente(id, data)
        success('Cliente actualizado')
      } else {
        await addCliente(data)
        success('Cliente creado')
      }
      setShowForm(false)
      setEditingItem(null)
    } catch (err) {
      toastError(err.message || 'No se pudo guardar el cliente')
    }
  }

  const handleEdit = (item) => {
    setEditingItem(item)
    setShowForm(true)
  }

  const handleViewDetail = (cliente) => {
    setViewDetail(cliente)
  }

  const handleDelete = (id) => {
    setDeleteConfirm(id)
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return

    try {
      await deleteCliente(deleteConfirm)
      success('Cliente eliminado')
      setDeleteConfirm(null)
    } catch (err) {
      toastError(err.message || 'No se pudo eliminar el cliente')
    }
  }

  const columns = [
    { key: 'nombre', header: 'Cliente' },
    { key: 'tipo', header: 'Tipo', width: '100px', render: (v) => <Badge variant={v === 'B2B' ? 'coffee' : 'info'}>{v === 'B2B' ? 'Mayorista' : 'Minorista'}</Badge> },
    { key: 'kilosComprados', header: 'Kilos Comprados', render: (v) => formatearKilos(v), className: 'font-mono tabular-nums' },
    { key: 'deuda', header: 'Deuda', render: (_, row) => row.tieneDeuda && row.montoDeuda > 0 ? (
      <span className="text-red-600 dark:text-red-400 font-medium">{formatearMoneda(row.montoDeuda)}</span>
    ) : <span className="text-green-600 dark:text-green-400">Al día</span> },
    { key: 'telefono', header: 'Teléfono', width: '140px' },
    { key: 'email', header: 'Email' },
    { key: 'creadoEn', header: 'Desde', render: (v) => formatearFecha(v) },
  ]

  const pedidosDelCliente = viewDetail ? getPedidosByCliente(viewDetail.id) : []

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Clientes</h1>
          <p className="text-[var(--color-text-muted)]">Gestión de clientes B2B y B2C</p>
        </div>
        <Button onClick={() => { setEditingItem(null); setShowForm(true); }}>
          <Plus className="w-4 h-4" />
          Nuevo Cliente
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total Clientes</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{clientes.length}</p>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                {clientes.filter(c => c.tipo === 'B2B').length} B2B · {clientes.filter(c => c.tipo === 'B2C').length} B2C
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Kilos Totales Vendidos</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearKilos(totalKilos)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
              <Package className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Clientes con Deuda</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{clientesConDeuda.length}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total Deuda Pendiente</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{formatearMoneda(totalDeuda)}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Listado de Clientes</h2>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
              <Input
                placeholder="Buscar nombre, email, teléfono..."
                value={filters.search}
                onChange={e => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            <Select
              value={filters.tipo}
              onChange={e => setFilters(prev => ({ ...prev, tipo: e.target.value }))}
              options={[{ value: '', label: 'Todos' }, ...TIPOS_CLIENTE]}
              className="w-full sm:w-40"
              label=""
            />
            <Select
              value={filters.deuda}
              onChange={e => setFilters(prev => ({ ...prev, deuda: e.target.value }))}
              options={[
                { value: '', label: 'Todas' },
                { value: 'con', label: 'Con deuda' },
                { value: 'sin', label: 'Sin deuda' },
              ]}
              className="w-full sm:w-40"
              label=""
            />
          </div>
        </div>
        <div className="card-body p-0">
          <Table
            columns={columns}
            data={filteredClientes}
            onRowClick={handleViewDetail}
            emptyMessage="No hay clientes que coincidan con los filtros"
          />
        </div>
      </div>

      <ClienteForm
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditingItem(null); }}
        initialData={editingItem}
        onSubmit={handleSubmit}
      />

      {viewDetail && (
        <div className="modal-overlay" onClick={() => setViewDetail(null)}>
          <div className="modal-content max-w-3xl" onClick={e => e.stopPropagation()}>
            <div className="modal-header flex flex-wrap items-center gap-4">
              <div>
                <h2 className="text-lg font-semibold">{viewDetail.nombre}</h2>
                <Badge variant={viewDetail.tipo === 'B2B' ? 'coffee' : 'info'}>
                  {viewDetail.tipo === 'B2B' ? 'Mayorista (B2B)' : 'Minorista (B2C)'}
                </Badge>
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
                  <p className="text-sm text-[var(--color-text-muted)]">Teléfono</p>
                  <p className="font-medium">{viewDetail.telefono || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Email</p>
                  <p className="font-medium">{viewDetail.email || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Dirección</p>
                  <p className="font-medium">{viewDetail.direccion || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Cliente desde</p>
                  <p className="font-medium">{formatearFecha(viewDetail.creadoEn)}</p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-sm text-[var(--color-text-muted)]">Kilos comprados totales</p>
                  <p className="font-medium text-lg">{formatearKilos(viewDetail.kilosComprados)}</p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-sm text-[var(--color-text-muted)]">Situación de deuda</p>
                  <p className="font-medium">
                    {viewDetail.tieneDeuda && viewDetail.montoDeuda > 0 ? (
                      <span className="text-red-600 dark:text-red-400">
                        {formatearMoneda(viewDetail.montoDeuda)} pendiente
                      </span>
                    ) : (
                      <span className="text-green-600 dark:text-green-400">Al día</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="border-t border-[var(--color-border)] pt-4">
                <h3 className="font-medium text-[var(--color-text-primary)] mb-3">Historial de Pedidos ({pedidosDelCliente.length})</h3>
                {pedidosDelCliente.length > 0 ? (
                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Fecha</th>
                          <th>Estado</th>
                          <th className="text-right">Total</th>
                          <th>Medio Contacto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pedidosDelCliente
                          .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
                          .map(pedido => (
                            <tr key={pedido.id}>
                              <td>{formatearFecha(pedido.fecha)}</td>
                              <td><Badge variant={pedido.estado === 'Entregado' ? 'success' : pedido.estado === 'Listo' ? 'info' : 'warning'}>{pedido.estado}</Badge></td>
                              <td className="text-right font-medium">{formatearMoneda(pedido.total)}</td>
                              <td>{pedido.medioContacto}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-[var(--color-text-muted)] text-center py-4">Sin pedidos registrados</p>
                )}
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
              <p className="text-[var(--color-text-secondary)]">¿Está seguro de eliminar este cliente? Se perderá su historial.</p>
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