import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Coffee, User, Lock } from 'lucide-react'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

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
      navigate('/')
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 z-0">
        <img
          src="https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&q=80"
          alt="Granos de café"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-coffee-950/90 via-coffee-900/80 to-coffee-800/70" />
        <div className="absolute inset-0 backdrop-blur-sm bg-black/20" />
      </div>

      <div className="relative z-10 w-full max-w-md px-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-sm mb-4">
            <Coffee className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Café de Finca</h1>
          <p className="text-coffee-200/80 mt-1">Sistema de gestión tostaduría</p>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 sm:p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/20 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                {error}
              </div>
            )}

            <div className="relative">
              <label className="label text-coffee-100">Usuario</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="input pl-10 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500"
                  placeholder="admin, empleado, vendedor"
                  required
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="relative">
              <label className="label text-coffee-100">Contraseña</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="input pl-10 pr-12 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500"
                  placeholder="111"
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

          <div className="mt-6 pt-6 border-t border-white/10">
            <p className="text-xs text-coffee-300/60 text-center mb-3">Usuarios de prueba (contraseña: 111)</p>
            <div className="grid gap-2">
              {['admin', 'empleado', 'vendedor'].map(role => (
                <button
                  key={role}
                  type="button"
                  onClick={() => { setUsername(role); setPassword('111'); }}
                  className="text-left px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors text-coffee-100"
                >
                  <span className="font-medium">{role}</span> <span className="text-coffee-300/60 ml-2">({role === 'admin' ? 'Acceso total' : role === 'empleado' ? 'Sin contabilidad' : 'Solo pedidos'})</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-coffee-300/50 text-xs mt-6">
          Café de Finca v1.0 — Tostaduría de especialidad
        </p>
      </div>
    </div>
  )
}