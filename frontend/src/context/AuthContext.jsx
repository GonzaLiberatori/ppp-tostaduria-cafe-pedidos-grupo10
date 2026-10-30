import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../services/api'

const AuthContext = createContext(null)

const CLAVE_TOKEN = 'auth_token'
const CLAVE_USUARIO = 'user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  // Restaura la sesión validando el token contra el backend.
  useEffect(() => {
    let activo = true

    async function restaurarSesion() {
      const token = localStorage.getItem(CLAVE_TOKEN)
      if (!token) {
        localStorage.removeItem(CLAVE_USUARIO)
        if (activo) setLoading(false)
        return
      }

      try {
        const perfil = await api.me()
        if (!activo) return
        setUser(perfil)
        localStorage.setItem(CLAVE_USUARIO, JSON.stringify(perfil))
      } catch {
        if (!activo) return
        localStorage.removeItem(CLAVE_TOKEN)
        localStorage.removeItem(CLAVE_USUARIO)
        setUser(null)
      } finally {
        if (activo) setLoading(false)
      }
    }

    restaurarSesion()
    return () => {
      activo = false
    }
  }, [])

  // El cliente HTTP avisa cuando el backend rechaza el token.
  useEffect(() => {
    const alExpirarSesion = () => setUser(null)
    window.addEventListener('auth:expirada', alExpirarSesion)
    return () => window.removeEventListener('auth:expirada', alExpirarSesion)
  }, [])

  const login = useCallback(async (email, password) => {
    try {
      const { access_token: accessToken } = await api.login({
        email: email.trim(),
        password,
      })

      localStorage.setItem(CLAVE_TOKEN, accessToken)
      const perfil = await api.me()
      localStorage.setItem(CLAVE_USUARIO, JSON.stringify(perfil))
      setUser(perfil)

      return { success: true, user: perfil }
    } catch (error) {
      localStorage.removeItem(CLAVE_TOKEN)
      localStorage.removeItem(CLAVE_USUARIO)
      setUser(null)

      return {
        success: false,
        error: error instanceof ApiError
          ? error.message
          : 'No se pudo iniciar sesión.',
      }
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(CLAVE_TOKEN)
    localStorage.removeItem(CLAVE_USUARIO)
    localStorage.removeItem('cafe-finca-auth')
    setUser(null)
    navigate('/login')
  }, [navigate])

  const hasRole = useCallback((roles) => {
    if (!user) return false
    const permitidos = Array.isArray(roles) ? roles : [roles]
    return permitidos.includes(user.role)
  }, [user])

  const value = {
    user,
    loading,
    login,
    logout,
    hasRole,
    isAuthenticated: Boolean(user),
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
    throw new Error('useAuth debe usarse dentro de un AuthProvider')
  }
  return context
}
