import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthContext = createContext(null)

const MOCK_USERS = [
  { username: 'admin', password: '111', role: 'admin', nombre: 'Administrador' },
  { username: 'empleado', password: '111', role: 'empleado', nombre: 'Empleado' },
  { username: 'vendedor', password: '111', role: 'vendedor', nombre: 'Vendedor' },
  { username: 'Cliente', password: '111', role: 'cliente', nombre: 'Cliente', clienteId: 'cliente-1' },
]

const STORAGE_KEY = 'cafe-finca-auth'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback((username, password) => {
    const found = MOCK_USERS.find(u => u.username === username && u.password === password)
    if (found) {
      const userData = { username: found.username, role: found.role, nombre: found.nombre }
      setUser(userData)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userData))
      return { success: true, user: userData }
    }
    return { success: false, error: 'Usuario o contraseña incorrectos' }
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
    navigate('/login')
  }, [navigate])

  const hasRole = useCallback((roles) => {
    if (!user) return false
    const allowed = Array.isArray(roles) ? roles : [roles]
    return allowed.includes(user.role)
  }, [user])

  const value = {
    user,
    loading,
    login,
    logout,
    hasRole,
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}