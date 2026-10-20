import { useTheme } from '../../context/ThemeContext'
import ThemeToggle from '../ui/ThemeToggle'
import { Menu, Bell, User, LogOut } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

export default function Header({ onMenuClick, sidebarCollapsed }) {
  const { theme } = useTheme()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const notificationsRef = useRef(null)
  const userMenuRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
        setNotificationsOpen(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const notifications = [
    { id: 1, message: 'Nuevo pedido de Cafetería El Aroma', time: 'Hace 10 min', read: false },
    { id: 2, message: 'Stock bajo: Arábica Typica (30 kg)', time: 'Hace 2 horas', read: false },
    { id: 3, message: 'Pago recibido de Distribuidora Café Sur', time: 'Ayer', read: true },
  ]

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <header 
      className={`fixed top-0 right-0 z-30 h-16 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] transition-all duration-300 ${sidebarCollapsed ? 'left-16' : 'left-64'}`}
      role="banner"
    >
      <div className="flex items-center justify-between h-full px-4 sm:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="btn-ghost btn-sm p-2 rounded-lg lg:hidden"
            aria-label="Abrir menú"
            aria-expanded={!sidebarCollapsed}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="hidden sm:block border-l border-[var(--color-border)] pl-4">
            <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">Café de Finca</h1>
            <p className="text-xs text-[var(--color-text-muted)]">Sistema de gestión tostaduría</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative" ref={notificationsRef}>
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="btn-ghost btn-sm p-2 rounded-lg relative"
              aria-label={`Notificaciones${unreadCount > 0 ? `, ${unreadCount} sin leer` : ''}`}
              aria-expanded={notificationsOpen}
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl shadow-lg py-2 z-50">
                <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
                  <h3 className="font-medium text-[var(--color-text-primary)]">Notificaciones</h3>
                  {unreadCount > 0 && (
                    <button className="text-xs text-coffee-500 hover:underline">Marcar todas como leídas</button>
                  )}
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {notifications.map(notif => (
                    <button
                      key={notif.id}
                      className={`w-full px-4 py-3 text-left hover:bg-[var(--color-bg-tertiary)] ${!notif.read ? 'bg-coffee-500/5' : ''}`}
                    >
                      <p className="text-sm text-[var(--color-text-primary)]">{notif.message}</p>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{notif.time}</p>
                    </button>
                  ))}
                </div>
                <div className="px-4 py-2 border-t border-[var(--color-border)]">
                  <button className="w-full text-sm text-coffee-500 hover:underline">Ver todas las notificaciones</button>
                </div>
              </div>
            )}
          </div>

          <ThemeToggle />

          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)]"
              aria-label="Menú de usuario"
              aria-expanded={userMenuOpen}
            >
              <div className="w-8 h-8 rounded-full bg-coffee-500 flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <span className="hidden sm:block text-sm font-medium text-[var(--color-text-primary)]">Admin</span>
            </button>

            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl shadow-lg py-2 z-50">
                <div className="px-4 py-2 border-b border-[var(--color-border)]">
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">Administrador</p>
                  <p className="text-xs text-[var(--color-text-muted)]">admin@cafedefinca.com</p>
                </div>
                <button className="w-full px-4 py-2 text-left text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Mi perfil
                </button>
                <button className="w-full px-4 py-2 text-left text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] flex items-center gap-2">
                  <LogOut className="w-4 h-4" />
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}