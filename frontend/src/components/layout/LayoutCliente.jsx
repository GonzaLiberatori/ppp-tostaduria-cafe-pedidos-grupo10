import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { ShoppingCart, List, User, Clock, Coffee, LogOut } from 'lucide-react'

const TABS = [
  { path: '/cliente', label: 'Resumen', icon: ShoppingCart },
  { path: '/cliente/comprar', label: 'Comprar', icon: Coffee },
  { path: '/cliente/mis-pedidos', label: 'Mis pedidos', icon: List },
  { path: '/cliente/perfil', label: 'Perfil', icon: User },
  { path: '/cliente/suscripciones', label: 'Suscripciones', icon: Clock },
]

export default function LayoutCliente() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname: activeTab } = useLocation()

  const handleTabChange = (path) => {
    navigate(path)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex">
          {TABS.map(({ path, label, icon: Icon }) => (
            <button
              key={path}
              onClick={() => handleTabChange(path)}
              className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${
                activeTab === path
                  ? 'bg-coffee-500 text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'
              }`}
              aria-label={label}
            >
              <Icon className="w-4 h-4 mr-2 inline" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <main className="pt-0 min-h-screen" role="main" tabIndex={-1}>
        <div className="container-app py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Mi cuenta</h1>
              <p className="text-[var(--color-text-muted)]">Bienvenido, {user?.nombre || 'Cliente'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="btn-ghost btn-sm flex items-center gap-2 rounded-lg text-[var(--color-text-secondary)] hover:text-red-600 hover:bg-[var(--color-bg-tertiary)] transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Cerrar sesión</span>
            </button>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
