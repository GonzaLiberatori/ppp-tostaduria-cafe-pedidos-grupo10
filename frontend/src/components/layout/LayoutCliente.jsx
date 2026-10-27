import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import SidebarCliente from './SidebarCliente'
import { LogOut } from 'lucide-react'
import { useState } from 'react'

export default function LayoutCliente() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isCollapsed, setIsCollapsed] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <SidebarCliente 
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)} 
        isCollapsed={isCollapsed}
      />
      
      <main className="pt-0 min-h-screen" role="main" tabIndex={-1}>
        <div className="container-app py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Mi cuenta</h1>
              <p className="text-[var(--color-text-muted)]">Bienvenido, {user?.nombre || 'Cliente'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="btn-ghost btn-sm flex items-center gap-2 rounded-lg text-[var(--color-text-secondary)] hover:text-red-600 hover:bg-[var(--color-bg-tertiary)] transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Cerrar sesión</span>
            </button>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
