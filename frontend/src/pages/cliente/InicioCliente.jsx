import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { formatearMoneda, formatearKilos, formatearFecha } from '../../utils/formatters'
import { ShoppingCart, List, User, Clock, Package } from 'lucide-react'

export default function InicioCliente() {
  const { getPedidosByCliente, getTotalKilosStock, getClienteById } = useData()
  const { user } = useAuth()

  const clienteId = user?.clienteId
  const cliente = clienteId ? getClienteById(clienteId) : null
  const misPedidos = clienteId ? getPedidosByCliente(clienteId) : []
  const pedidosPendientes = misPedidos.filter(p => p.estado === 'Pendiente')
  const pedidosEntregados = misPedidos.filter(p => p.estado === 'Entregado')
  const totalGastado = misPedidos
    .filter(p => p.estado === 'Entregado')
    .reduce((sum, p) => sum + (p.total || 0), 0)
  const totalKilosComprados = misPedidos
    .filter(p => p.estado === 'Entregado')
    .reduce((sum, p) => sum + p.items.reduce((s, i) => s + i.kilos, 0), 0)

  const totalTostado = getTotalKilosStock('tostado')
  const saldoPendiente = cliente?.montoDeuda || 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Resumen</h1>
        <p className="text-[var(--color-text-muted)]">Estado de tu cuenta y pedidos recientes</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5 border-l-4 border-coffee-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Pedidos pendientes</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{pedidosPendientes.length}</p>
            </div>
            <ShoppingCart className="w-8 h-8 text-coffee-500" />
          </div>
        </div>
        <div className="card p-5 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Pedidos entregados</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{pedidosEntregados.length}</p>
            </div>
            <Package className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        <div className="card p-5 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total gastado</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearMoneda(totalGastado)}</p>
            </div>
            <User className="w-8 h-8 text-green-500" />
          </div>
        </div>
        <div className="card p-5 border-l-4 border-purple-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Kilos comprados</p>
              <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{formatearKilos(totalKilosComprados)}</p>
            </div>
            <List className="w-8 h-8 text-purple-500" />
          </div>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-3">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-[var(--color-text-primary)]">Café tostado disponible</h3>
              <p className="text-sm text-[var(--color-text-muted)]">Producto listo para vender</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-[var(--color-text-primary)]">{formatearKilos(totalTostado)}</p>
            </div>
          </div>
        </div>
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-[var(--color-text-primary)]">Saldo de cuenta</h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                {cliente?.tieneDeuda ? 'Deuda pendiente' : 'Sin deudas'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                {formatearMoneda(saldoPendiente)}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-6 flex flex-col justify-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-coffee-500" />
            <span className="font-medium text-[var(--color-text-primary)]">Suscripciones activas</span>
          </div>
          <p className="text-sm text-[var(--color-text-muted)] text-center">
            Gestiona tus pedidos recurrentes desde <strong>Suscripciones</strong>.
          </p>
        </div>
      </div>

      {misPedidos.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Tus pedidos recientes</h2>
          </div>
          <div className="card-body p-0">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    <th scope="col" className="text-right">Kilos</th>
                    <th scope="col" className="text-right">Total</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Medio de contacto</th>
                  </tr>
                </thead>
                <tbody>
                  {misPedidos.slice(0, 5).map(pedido => (
                    <tr key={pedido.id}>
                      <td>{formatearFecha(pedido.fecha)}</td>
                      <td className="text-right font-mono tabular-nums">
                        {formatearKilos(pedido.items.reduce((s, i) => s + i.kilos, 0))}
                      </td>
                      <td className="text-right font-mono tabular-nums font-medium">
                        {formatearMoneda(pedido.total)}
                      </td>
                      <td>{pedido.estado}</td>
                      <td>{pedido.medioContacto || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {misPedidos.length > 5 && (
              <div className="text-center py-4 text-[var(--color-text-muted)] text-sm">
                Ver todos tus pedidos en Mis pedidos
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
