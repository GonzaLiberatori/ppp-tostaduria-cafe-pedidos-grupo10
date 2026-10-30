import { useState, useRef, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { ShoppingCart, List, User, Clock, Coffee, LogOut, ChevronDown } from 'lucide-react'
import ThemeToggle from '../ui/ThemeToggle'

const navigation = [
  { name: 'Resumen', href: '/cliente', icon: ShoppingCart, end: true },
  { name: 'Comprar', href: '/cliente/comprar', icon: Coffee },
  { name: 'Mis pedidos', href: '/cliente/mis-pedidos', icon: List },
  { name: 'Perfil', href: '/cliente/perfil', icon: User },
  { name: 'Suscripciones', href: '/cliente/suscripciones', icon: Clock },
]

export default function LayoutCliente() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="sticky top-0 z-40 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            <div className="flex items-center gap-8 min-w-0">
              <NavLink to="/cliente" className="flex items-center gap-2 flex-shrink-0" aria-label="Café de Finca - Mis compras">
                <div className="w-9 h-9 rounded-lg bg-coffee-500 flex items-center justify-center">
                  <Coffee className="w-5 h-5 text-white" />
                </div>
                <span className="hidden md:block font-semibold text-lg text-[var(--color-text-primary)]">Café de Finca</span>
              </NavLink>

              <nav className="flex items-center gap-1 overflow-x-auto" aria-label="Navegación del cliente">
                {navigation.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    end={item.end}
                    className={({ isActive }) => `
                      flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg whitespace-nowrap transition-colors duration-150
                      ${isActive
                        ? 'bg-coffee-500 text-white'
                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]'
                      }
                    `}
                  >
                    <item.icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                    <span>{item.name}</span>
                  </NavLink>
                ))}
              </nav>
            </div>

            <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
              <ThemeToggle />

              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors"
                  aria-label="Menú de usuario"
                  aria-expanded={userMenuOpen}
                >
                  <div className="w-8 h-8 rounded-full bg-coffee-500 flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <span className="hidden sm:block text-sm font-medium text-[var(--color-text-primary)]">
                    {user?.nombre || 'Cliente'}
                  </span>
                  <ChevronDown className={`hidden sm:block w-4 h-4 text-[var(--color-text-muted)] transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl shadow-lg py-2 z-50 animate-slide-in">
                    <div className="px-4 py-3 border-b border-[var(--color-border)]">
                      <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">{user?.nombre || 'Cliente'}</p>
                      <p className="text-xs text-[var(--color-text-muted)] truncate">{user?.email || 'Sin email registrado'}</p>
                    </div>
                    <NavLink
                      to="/cliente/perfil"
                      onClick={() => setUserMenuOpen(false)}
                      className="w-full px-4 py-2 text-left text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] flex items-center gap-2"
                    >
                      <User className="w-4 h-4" />
                      Mi perfil
                    </NavLink>
                    <button
                      onClick={logout}
                      className="w-full px-4 py-2 text-left text-sm text-red-500 hover:bg-red-500/10 flex items-center gap-2"
                    >
                      <LogOut className="w-4 h-4" />
                      Cerrar sesión
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="min-h-screen" role="main" tabIndex={-1}>
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
