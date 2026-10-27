import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { formatearMoneda, formatearKilos, formatearFecha } from '../../utils/formatters'
import { ShoppingCart, Clock, CheckCircle, Package } from 'lucide-react'

const ESTADO_ICON = {
  Pendiente: Clock,
  Listo: CheckCircle,
  Entregado: Package,
}

const ESTADO_COLOR = {
  Pendiente: 'warning',
  Listo: 'info',
  Entregado: 'success',
}

export default function MisPedidos() {
  const { pedidos, getPedidosByCliente } = useData()
  const { user } = useAuth()

  const clienteId = user?.clienteId
  const misPedidos = clienteId ? getPedidosByCliente(clienteId) : []

  const misPedidosOrdenados = [...misPedidos].sort(
    (a, b) => new Date(b.fecha) - new Date(a.fecha)
  )

  if (misPedidosOrdenados.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Mis pedidos</h1>
          <p className="text-[var(--color-text-muted)]">Historial de tus compras</p>
        </div>
        <div className="empty-state">
          <ShoppingCart className="empty-state-icon w-12 h-12" />
          <p className="empty-state-title">Sin pedidos aún</p>
          <p className="empty-state-description">Realiza tu primera compra desde Comprar.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Mis pedidos</h1>
        <p className="text-[var(--color-text-muted)]">Historial de tus compras</p>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Productos</th>
                  <th scope="col" className="text-right">Kilos</th>
                  <th scope="col" className="text-right">Total</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Medio de pago</th>
                </tr>
              </thead>
              <tbody>
                {misPedidosOrdenados.map(pedido => {
                  const Icon = ESTADO_ICON[pedido.estado]
                  const badgeColor = ESTADO_COLOR[pedido.estado] === 'warning'
                    ? 'bg-amber-500/10 text-amber-700'
                    : ESTADO_COLOR[pedido.estado] === 'info'
                      ? 'bg-blue-500/10 text-blue-700'
                      : 'bg-green-500/10 text-green-700'

                  return (
                    <tr key={pedido.id}>
                      <td>
                        <p className="font-medium text-[var(--color-text-primary)]">
                          {formatearFechaHora(pedido.fecha)}
                        </p>
                        <p className="text-xs text-[var(--color-text-muted)]">
                          #{pedido.id.slice(0, 8)}
                        </p>
                      </td>
                      <td>
                        {pedido.items.map((item, i) => (
                          <div key={i} className="text-sm">
                            {item.variedad} ({formatearKilos(item.kilos)})
                          </div>
                        ))}
                      </td>
                      <td className="text-right font-mono tabular-nums">
                        {formatearKilos(pedido.items.reduce((s, i) => s + i.kilos, 0))}
                      </td>
                      <td className="text-right font-mono tabular-nums font-medium">
                        {formatearMoneda(pedido.total)}
                      </td>
                      <td>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${badgeColor}`}>
                          <Icon className="w-3 h-3" />
                          {pedido.estado}
                        </span>
                      </td>
                      <td>{pedido.medioPago || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatearFechaHora(fechaISO) {
  return new Date(fechaISO).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
