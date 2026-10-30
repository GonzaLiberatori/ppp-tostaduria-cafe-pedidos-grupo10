import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthContext = createContext(null)

// Usuarios de demostración: se eliminan cuando se conecte el backend de autenticación.
const MOCK_USERS = [
  { username: 'admin', password: '111', role: 'admin', nombre: 'Administrador' },
  { username: 'empleado', password: '111', role: 'empleado', nombre: 'Empleado' },
  { username: 'vendedor', password: '111', role: 'vendedor', nombre: 'Vendedor' },
  { username: 'Cliente', password: '111', role: 'cliente', nombre: 'Cliente', email: 'cliente@cafedefinca.com.ar', clienteId: 'cliente-1' },
]

const STORAGE_KEY = 'cafe-finca-auth'
const REGISTERED_KEY = 'cafe-finca-users'

function leerUsuariosRegistrados() {
  try {
    const guardados = localStorage.getItem(REGISTERED_KEY)
    return guardados ? JSON.parse(guardados) : []
  } catch {
    localStorage.removeItem(REGISTERED_KEY)
    return []
  }
}

function guardarUsuariosRegistrados(usuarios) {
  localStorage.setItem(REGISTERED_KEY, JSON.stringify(usuarios))
}

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

  // Arma el objeto de sesión sin credenciales sensibles y lo persiste.
  const iniciarSesion = useCallback((usuario) => {
    const userData = {
      username: usuario.username,
      role: usuario.role,
      nombre: usuario.nombre,
      ...(usuario.email ? { email: usuario.email } : {}),
      ...(usuario.clienteId ? { clienteId: usuario.clienteId } : {}),
    }
    setUser(userData)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(userData))
    return userData
  }, [])

  const login = useCallback((username, password) => {
    const usuarios = [...MOCK_USERS, ...leerUsuariosRegistrados()]
    const found = usuarios.find(
      u => u.username.toLowerCase() === username.trim().toLowerCase() && u.password === password
    )
    if (found) {
      return { success: true, user: iniciarSesion(found) }
    }
    return { success: false, error: 'Usuario o contraseña incorrectos' }
  }, [iniciarSesion])

  const register = useCallback(({ nombre, username, password, email }) => {
    const usuarioNormalizado = username.trim().toLowerCase()
    const emailNormalizado = email.trim().toLowerCase()
    const registrados = leerUsuariosRegistrados()

    const duplicado = [...MOCK_USERS, ...registrados].find(
      u =>
        u.username.toLowerCase() === usuarioNormalizado ||
        (u.email && u.email.toLowerCase() === emailNormalizado)
    )
    if (duplicado) {
      if (duplicado.username.toLowerCase() === usuarioNormalizado) {
        return { success: false, field: 'username', error: 'Ese nombre de usuario ya está en uso' }
      }
      return { success: false, field: 'email', error: 'Ese email ya está registrado' }
    }

    const nuevoUsuario = {
      username: username.trim(),
      email: email.trim(),
      password,
      role: 'cliente',
      nombre: nombre.trim(),
      clienteId: `cliente-${Date.now()}`,
    }
    guardarUsuariosRegistrados([...registrados, nuevoUsuario])

    return { success: true, user: iniciarSesion(nuevoUsuario) }
  }, [iniciarSesion])

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
    register,
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
