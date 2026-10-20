import { useState, useRef, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { 
  Package, 
  Users, 
  ShoppingCart, 
  Calculator, 
  Coffee, 
  LogOut,
  User,
  ChevronDown
} from 'lucide-react'
import ThemeToggle from '../ui/ThemeToggle'
import { useAuth } from '../../context/AuthContext'

const navigation = [
  { name: 'Stock', href: '/stock', icon: Package, roles: ['admin', 'empleado'] },
  { name: 'Clientes', href: '/clientes', icon: Users, roles: ['admin', 'empleado', 'vendedor'] },
  { name: 'Pedidos', href: '/pedidos', icon: ShoppingCart, roles: ['admin', 'empleado', 'vendedor'] },
  { name: 'Contabilidad', href: '/contabilidad', icon: Calculator, roles: ['admin'] },
]

export default function TopTabs() {
  const { user, logout, hasRole } = useAuth()
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

  const filteredNav = navigation.filter(item => hasRole(item.roles))

  const roleLabels = {
    admin: 'Administrador',
    empleado: 'Empleado',
    vendedor: 'Vendedor',
  }

  const roleColors = {
    admin: 'bg-purple-500',
    empleado: 'bg-blue-500',
    vendedor: 'bg-green-500',
  }

  return (
    <header className="sticky top-0 z-40 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2" aria-label="Café de Finca - Inicio">
              <div className="w-9 h-9 rounded-lg bg-coffee-500 flex items-center justify-center">
                <Coffee className="w-5 h-5 text-white" />
              </div>
              <span className="font-semibold text-lg text-[var(--color-text-primary)]">Café de Finca</span>
            </NavLink>
            
            <nav className="flex items-center gap-1" aria-label="Navegación principal">
              {filteredNav.map((item) => {
                const isActive = location.pathname === item.href || (item.href !== '/' && location.pathname.startsWith(item.href))
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={({ isActive: active }) => `
                      flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors duration-150
                      ${active 
                        ? 'bg-coffee-500 text-white' 
                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]'
                      }
                    `}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <item.icon className="w-4 h-4" aria-hidden="true" />
                    <span>{item.name}</span>
                  </NavLink>
                )
              })}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <ThemeToggle />
            
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors"
                aria-label="Menú de usuario"
                aria-expanded={userMenuOpen}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${roleColors[user?.role] || 'bg-coffee-500'}`}>
                  <User className="w-4 h-4 text-white" />
                </div>
                <span className="hidden sm:block text-sm font-medium text-[var(--color-text-primary)]">
                  {user?.nombre || 'Usuario'}
                </span>
                <ChevronDown className={`w-4 h-4 text-[var(--color-text-muted)] transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl shadow-lg py-2 z-50 animate-slide-in">
                  <div className="px-4 py-3 border-b border-[var(--color-border)]">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{user?.nombre}</p>
                    <p className="text-xs text-[var(--color-text-muted)] capitalize">{user?.role}</p>
                  </div>
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
  )
}