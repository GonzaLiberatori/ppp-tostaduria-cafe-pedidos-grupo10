import { NavLink, useLocation } from 'react-router-dom'
import { 
  ShoppingCart, 
  List, 
  User, 
  Clock, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Coffee
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'

const navigation = [
  { name: 'Comprar', href: '/cliente/comprar', icon: ShoppingCart },
  { name: 'Mis pedidos', href: '/cliente/mis-pedidos', icon: List },
  { name: 'Perfil', href: '/cliente/perfil', icon: User },
  { name: 'Suscripciones', href: '/cliente/suscripciones', icon: Clock },
]

export default function SidebarCliente({ onToggleCollapse, isCollapsed }) {
  const location = useLocation()
  const { logout } = useAuth()

  return (
    <aside 
      className={`fixed left-0 top-0 z-40 h-screen transition-all duration-300 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col ${isCollapsed ? 'w-16' : 'w-64'}`}
      aria-label="Navegación principal"
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-[var(--color-border)]">
        {!isCollapsed && (
          <NavLink to="/cliente" className="flex items-center gap-2" aria-label="Café de Finca - Cliente">
            <div className="w-8 h-8 rounded-lg bg-coffee-500 flex items-center justify-center">
              <Coffee className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg text-[var(--color-text-primary)]">Café de Finca</span>
          </NavLink>
        )}
        {isCollapsed && (
          <NavLink to="/cliente" className="flex items-center justify-center" aria-label="Café de Finca - Cliente">
            <div className="w-8 h-8 rounded-lg bg-coffee-500 flex items-center justify-center">
              <Coffee className="w-5 h-5 text-white" />
            </div>
          </NavLink>
        )}
        <button
          onClick={onToggleCollapse}
          className="btn-ghost btn-sm p-1.5 rounded-lg"
          aria-label={isCollapsed ? 'Expandir menú' : 'Colapsar menú'}
          aria-expanded={!isCollapsed}
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Menú principal">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href || (item.href !== '/cliente' && location.pathname.startsWith(item.href))
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive: active }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150
                ${active 
                  ? 'bg-coffee-500/10 text-coffee-600 dark:text-coffee-400' 
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]'
                }
                ${isCollapsed ? 'justify-center' : ''}
              `}
              aria-current={isActive ? 'page' : undefined}
              title={isCollapsed ? item.name : undefined}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {!isCollapsed && <span>{item.name}</span>}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-[var(--color-border)] mt-auto">
        <button
          onClick={() => logout()}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-red-600`}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          {!isCollapsed && <span>Cerrar sesión</span>}
        </button>
        {!isCollapsed && (
          <div className="text-xs text-[var(--color-text-muted)] text-center mt-3">
            Café de Finca v1.0
          </div>
        )}
      </div>
    </aside>
  )
}
