import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { ShoppingCart, List, User, Clock, Coffee, LogOut } from 'lucide-react'

export default function LayoutCliente() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const navigation = [
    { name: 'Resumen', href: '/cliente', icon: ShoppingCart },
    { name: 'Comprar', href: '/cliente/comprar', icon: Coffee },
    { name: 'Mis pedidos', href: '/cliente/mis-pedidos', icon: List },
    { name: 'Perfil', href: '/cliente/perfil', icon: User },
    { name: 'Suscripciones', href: '/cliente/suscripciones', icon: Clock },
  ]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <div className="border-b bg-[var(--color-bg-secondary)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center justify-center w-full">
              <div className="flex items-center gap-8">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${isActive ? 'bg-coffee-500 text-white hover:bg-coffee-600' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]'}`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <item.icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                      <span>{item.name}</span>
                    </NavLink>
                  )
                })}
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="btn-ghost btn-sm flex items-center gap-2 rounded-lg text-[var(--color-text-secondary)] hover:text-red-600 hover:bg-[var(--color-bg-tertiary)] transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </div>
      </div>

      <main className="pt-0 min-h-screen" role="main" tabIndex={-1}>
        <div className="container-app py-6">
          {location.pathname === '/cliente/perfil' && (
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Mi cuenta</h1>
                <p className="text-[var(--color-text-muted)]">Bienvenido, {user?.nombre || 'Cliente'}</p>
              </div>
            </div>
          )}
          <Outlet />
        </div>
      </main>
    </div>
  )
}
