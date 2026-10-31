import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { User, Mail, Phone, MapPin, CreditCard, Building } from 'lucide-react'

export default function PerfilCliente() {
  const { user } = useAuth()
  const { clientes, getClienteById } = useData()

  const cliente = user?.clienteId ? getClienteById(user.clienteId) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Perfil</h1>
        <p className="text-[var(--color-text-muted)]">Tus datos de cuenta</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div className="card p-6">
          <h2 className="font-semibold text-[var(--color-text-primary)] mb-4">Cuenta</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Nombre de usuario</p>
                <p className="font-medium text-[var(--color-text-primary)]">{user?.username}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Nombre completo</p>
                <p className="font-medium text-[var(--color-text-primary)]">{user?.nombre}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Building className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Tipo de cliente</p>
                <p className="font-medium text-[var(--color-text-primary)]">{cliente?.tipo || 'B2C'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Estado de cuenta</p>
                <p className="font-medium text-[var(--color-text-primary)]">
                  {cliente?.tieneDeuda ? 'Con deuda pendiente' : 'Al día'}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="font-semibold text-[var(--color-text-primary)] mb-4">Contacto</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Email</p>
                <p className="font-medium text-[var(--color-text-primary)]">{cliente?.email || '—'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Teléfono</p>
                <p className="font-medium text-[var(--color-text-primary)]">{cliente?.telefono || '—'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-coffee-500" />
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Dirección</p>
                <p className="font-medium text-[var(--color-text-primary)]">{cliente?.direccion || '—'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="font-semibold text-[var(--color-text-primary)] mb-4">Resumen de compras</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Kilos comprados (histórico)</p>
            <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">
              {cliente?.kilosComprados ? cliente.kilosComprados : 0} kg
            </p>
          </div>
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Monto de deuda</p>
            <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">
              {cliente?.montoDeuda ? `$${cliente.montoDeuda.toLocaleString('es-AR')}` : '$0'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
