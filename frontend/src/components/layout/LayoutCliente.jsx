import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { ShoppingCart, List, User, Clock, Coffee, LogOut } from 'lucide-react'

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
      {/* Top tabs bar */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex">
          <button
            onClick={() => handleTabChange('/cliente')}
            className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${activeTab === '/cliente' ? 'bg-coffee-500 text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
            aria-label="Resumen"
          >
            <ShoppingCart className="w-4 h-4 mr-2" />
            Resumen
          </button>
          <button
            onClick={() => handleTabChange('/cliente/comprar')}
            className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${activeTab === '/cliente/comprar' ? 'bg-coffee-500 text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
            aria-label="Comprar"
          >
            <Coffee className="w-4 h-4 mr-2" />
            Comprar
          </button>
          <button
            onClick={() => handleTabChange('/cliente/mis-pedidos')}
            className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${activeTab === '/cliente/mis-pedidos' ? 'bg-coffee-500 text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
            aria-label="Mis pedidos"
          >
            <List className="w-4 h-4 mr-2" />
            Mis pedidos
          </button>
          <button
            onClick={() => handleTabChange('/cliente/perfil')}
            className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${activeTab === '/cliente/perfil' ? 'bg-coffee-500 text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
            aria-label="Perfil"
          >
            <User className="w-4 h-4 mr-2" />
            Perfil
          </button>
          <button
            onClick={() => handleTabChange('/cliente/suscripciones')}
            className={`flex-1 py-3 text-sm font-medium transition-colors rounded-t-lg ${activeTab === '/cliente/suscripciones' ? 'bg-coffee-500 text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
            aria-label="Suscripciones"
          >
            <Clock className="w-4 h-4 mr-2" />
            Suscripciones
          </button>
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