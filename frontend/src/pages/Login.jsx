import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, User, Lock } from 'lucide-react'
import Button from '../components/ui/Button'
import AuthShell from '../components/layout/AuthShell'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const result = login(username, password)
    if (result.success) {
      if (result.user.role === 'cliente') {
        navigate('/cliente')
      } else {
        navigate('/')
      }
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  return (
    <AuthShell>
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            {error}
          </div>
        )}

        <div className="relative">
          <label htmlFor="login-usuario" className="label text-coffee-100">Usuario</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
            <input
              id="login-usuario"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="input pl-10 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500"
              placeholder="Ingresar usuario"
              required
              autoComplete="username"
              disabled={loading}
            />
          </div>
        </div>

        <div className="relative">
          <label htmlFor="login-password" className="label text-coffee-100">Contraseña</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="input pl-10 pr-12 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500"
              placeholder="Ingresar contraseña"
              required
              autoComplete="current-password"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-coffee-300 hover:text-white"
              aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <Button type="submit" className="w-full py-3 text-base" loading={loading}>
          Iniciar sesión
        </Button>
      </form>

      <p className="text-sm text-coffee-200/70 text-center mt-6">
        ¿No tenés cuenta?{' '}
        <Link to="/register" className="font-medium text-coffee-100 hover:text-white hover:underline">
          Registrarse
        </Link>
      </p>
    </AuthShell>
  )
}
