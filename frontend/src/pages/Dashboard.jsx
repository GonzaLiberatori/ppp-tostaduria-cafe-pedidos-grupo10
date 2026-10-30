import { useData } from '../context/DataContext'
import { 
  Package, 
  Users, 
  ShoppingCart, 
  DollarSign, 
  TrendingUp, 
  AlertTriangle,
  Coffee
} from 'lucide-react'
import Badge from '../components/ui/Badge'
import { formatearMoneda, formatearKilos, getMesNombre } from '../utils/formatters'
import { kilosCafe } from '../utils/cafes'

export default function Dashboard() {
  const { 
    cafes, 
    clientes, 
    pedidos, 
    gastos, 
    getTotalKilosPorTipo, 
    getClientesConDeuda, 
    getPedidosByEstado,
    getTotalesGenerales,
    getContabilidadMensual 
  } = useData()

  const totales = getTotalesGenerales()
  const contabilidad = getContabilidadMesActual()
  const pedidosPendientes = getPedidosByEstado('Pendiente')
  const pedidosListos = getPedidosByEstado('Listo')
  const clientesConDeuda = getClientesConDeuda()
  const stockVerde = getTotalKilosPorTipo('verde')
  const stockTostado = getTotalKilosPorTipo('tostado')

  // Cafés con lotes de cada tipo por debajo del mínimo operativo
  const stockBajo = cafes.filter(cafe =>
    (cafe.lotes || []).some(l => l.tipo === 'tostado') && kilosCafe(cafe, 'tostado') < 5
  )
  const stockVerdeBajo = cafes.filter(cafe =>
    (cafe.lotes || []).some(l => l.tipo === 'verde') && kilosCafe(cafe, 'verde') < 30
  )

  function getContabilidadMesActual() {
    const mesActual = new Date().toISOString().substring(0, 7)
    const contabilidadMensual = getContabilidadMensual()
    return contabilidadMensual.find(m => m.mes === mesActual) || { ventasTotales: 0, gastosTotales: 0, gananciaNeta: 0 }
  }

  const stats = [
    {
      title: 'Stock Café Verde',
      value: formatearKilos(stockVerde),
      icon: Coffee,
      color: 'coffee',
      trend: stockVerdeBajo.length > 0 ? `${stockVerdeBajo.length} variedades bajas` : 'OK',
      trendColor: stockVerdeBajo.length > 0 ? 'warning' : 'success',
    },
    {
      title: 'Stock Café Tostado',
      value: formatearKilos(stockTostado),
      icon: Package,
      color: 'coffee',
      trend: stockBajo.length > 0 ? `${stockBajo.length} variedades bajas` : 'OK',
      trendColor: stockBajo.length > 0 ? 'warning' : 'success',
    },
    {
      title: 'Clientes Totales',
      value: clientes.length,
      icon: Users,
      color: 'info',
      trend: `${clientes.filter(c => c.tipo === 'B2B').length} B2B · ${clientes.filter(c => c.tipo === 'B2C').length} B2C`,
      trendColor: 'default',
    },
    {
      title: 'Pedidos Pendientes',
      value: pedidosPendientes.length,
      icon: ShoppingCart,
      color: 'warning',
      trend: `${pedidosListos.length} listos para entregar`,
      trendColor: 'info',
    },
    {
      title: 'Ventas del Mes',
      value: formatearMoneda(contabilidad.ventasTotales),
      icon: DollarSign,
      color: 'success',
      trend: `Ganancia: ${formatearMoneda(contabilidad.gananciaNeta)}`,
      trendColor: contabilidad.gananciaNeta >= 0 ? 'success' : 'danger',
    },
    {
      title: 'Clientes con Deuda',
      value: clientesConDeuda.length,
      icon: AlertTriangle,
      color: 'danger',
      trend: `Total adeudado: ${formatearMoneda(clientesConDeuda.reduce((sum, c) => sum + c.montoDeuda, 0))}`,
      trendColor: 'danger',
    },
  ]

  const recentPedidos = [...pedidos]
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 5)

  const recentGastos = [...gastos]
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 5)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Dashboard</h1>
          <p className="text-[var(--color-text-muted)]">Resumen general de Café de Finca</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {stats.map((stat, index) => (
          <div key={index} className="card p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-[var(--color-text-muted)]">{stat.title}</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{stat.value}</p>
                <p className={`text-xs mt-1 badge-${stat.trendColor}`}>{stat.trend}</p>
              </div>
              <div className={`w-12 h-12 rounded-xl bg-${stat.color}-500/10 flex items-center justify-center`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}-600 dark:text-${stat.color}-400`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Pedidos Recientes</h2>
            <Badge variant="coffee">{pedidos.length} total</Badge>
          </div>
          <div className="card-body p-0">
            {recentPedidos.length > 0 ? (
              <div className="divide-y divide-[var(--color-border)]">
                {recentPedidos.map(pedido => {
                  const cliente = clientes.find(c => c.id === pedido.clienteId)
                  return (
                    <div key={pedido.id} className="px-6 py-4 flex items-center justify-between hover:bg-[var(--color-bg-tertiary)] transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-2 h-2 rounded-full ${
                          pedido.estado === 'Entregado' ? 'bg-green-500' :
                          pedido.estado === 'Listo' ? 'bg-blue-500' :
                          'bg-amber-500'
                        }`} />
                        <div>
                          <p className="font-medium text-[var(--color-text-primary)]">
                            {cliente?.nombre || 'Cliente desconocido'}
                          </p>
                          <p className="text-sm text-[var(--color-text-muted)]">
                            {new Date(pedido.fecha).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-[var(--color-text-primary)]">{formatearMoneda(pedido.total)}</p>
                        <Badge variant={pedido.estado === 'Entregado' ? 'success' : pedido.estado === 'Listo' ? 'info' : 'warning'}>{pedido.estado}</Badge>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state">
                <Package className="w-12 h-12" />
                <p className="empty-state-title">Sin pedidos</p>
                <p className="empty-state-description">Los pedidos aparecerán aquí cuando se creen</p>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-text-primary)]">Gastos Recientes</h2>
            <Badge variant="info">{gastos.length} total</Badge>
          </div>
          <div className="card-body p-0">
            {recentGastos.length > 0 ? (
              <div className="divide-y divide-[var(--color-border)]">
                {recentGastos.map(gasto => (
                  <div key={gasto.id} className="px-6 py-4 flex items-center justify-between hover:bg-[var(--color-bg-tertiary)] transition-colors">
                    <div className="flex items-center gap-4">
                      <Badge variant={gasto.categoria === 'Producción' ? 'coffee' : gasto.categoria === 'Operativo' ? 'info' : gasto.categoria === 'Marketing' ? 'warning' : 'success'}>{gasto.categoria}</Badge>
                      <div>
                        <p className="font-medium text-[var(--color-text-primary)]">{gasto.descripcion}</p>
                        <p className="text-sm text-[var(--color-text-muted)]">{new Date(gasto.fecha).toLocaleDateString('es-AR')}</p>
                      </div>
                    </div>
                    <span className="font-semibold text-[var(--color-text-primary)]">{formatearMoneda(gasto.monto)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <DollarSign className="w-12 h-12" />
                <p className="empty-state-title">Sin gastos registrados</p>
                <p className="empty-state-description">Los gastos aparecerán aquí cuando se agreguen</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Resumen Contable por Mes</h2>
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
                {getContabilidadMensual().slice(0, 12).map(item => (
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
  )
}