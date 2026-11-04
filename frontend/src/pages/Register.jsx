import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useData } from '../context/DataContext'
import { Eye, EyeOff, User, Mail, Lock } from 'lucide-react'
import Button from '../components/ui/Button'
import AuthShell from '../components/layout/AuthShell'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validarCampos({ nombre, username, email, password, confirmPassword }) {
  const errores = {}

  if (!nombre.trim()) errores.nombre = 'Ingresá tu nombre completo'
  else if (nombre.trim().length < 3) errores.nombre = 'El nombre debe tener al menos 3 caracteres'

  if (!username.trim()) errores.username = 'Ingresá un usuario'
  else if (username.trim().length < 3) errores.username = 'El usuario debe tener al menos 3 caracteres'
  else if (/\s/.test(username.trim())) errores.username = 'El usuario no puede tener espacios'

  if (!email.trim()) errores.email = 'Ingresá tu email'
  else if (!EMAIL_REGEX.test(email.trim())) errores.email = 'Ingresá un email válido'

  if (!password) errores.password = 'Ingresá una contraseña'
  else if (password.length < 6) errores.password = 'La contraseña debe tener al menos 6 caracteres'

  if (!confirmPassword) errores.confirmPassword = 'Repetí la contraseña'
  else if (confirmPassword !== password) errores.confirmPassword = 'Las contraseñas no coinciden'

  return errores
}

function CampoTexto({ id, label, icon: Icon, error, ...props }) {
  return (
    <div>
      <label htmlFor={id} className="label text-coffee-100">{label}</label>
      <div className="relative">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
        <input
          id={id}
          className={`input pl-10 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500 ${error ? 'border-red-400/70' : ''}`}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${id}-error` : undefined}
          {...props}
        />
      </div>
      {error && <p id={`${id}-error`} className="text-xs text-red-300 mt-1" role="alert">{error}</p>}
    </div>
  )
}

export default function Register() {
  const { register } = useAuth()
  const { addCliente } = useData()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    nombre: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [errores, setErrores] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')
  const [loading, setLoading] = useState(false)

  const actualizarCampo = (campo) => (e) => {
    const { value } = e.target
    setForm(prev => ({ ...prev, [campo]: value }))
    setErrores(prev => (prev[campo] ? { ...prev, [campo]: undefined } : prev))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setErrorGeneral('')

    const erroresValidacion = validarCampos(form)
    if (Object.keys(erroresValidacion).length > 0) {
      setErrores(erroresValidacion)
      return
    }

    setLoading(true)
    const result = register(form)
    setLoading(false)

    if (!result.success) {
      if (result.field) {
        setErrores({ [result.field]: result.error })
      } else {
        setErrorGeneral(result.error)
      }
      return
    }

    // Alta en el padrón de clientes con el mismo id que usa la sesión.
    addCliente({
      id: result.user.clienteId,
      nombre: form.nombre.trim(),
      tipo: 'B2C',
      kilosComprados: 0,
      tieneDeuda: false,
      montoDeuda: 0,
      telefono: '',
      email: form.email.trim(),
      direccion: 'Sin especificar',
    })

    navigate('/cliente')
  }

  return (
    <AuthShell>
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="mb-2">
          <h2 className="text-lg font-semibold text-white">Crear cuenta</h2>
          <p className="text-sm text-coffee-200/70 mt-1">Registrate para comprar y programar tus entregas</p>
        </div>

        {errorGeneral && (
          <div className="bg-red-500/20 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg text-sm flex items-center gap-2" role="alert">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            {errorGeneral}
          </div>
        )}

        <CampoTexto
          id="registro-nombre"
          label="Nombre completo"
          icon={User}
          type="text"
          value={form.nombre}
          onChange={actualizarCampo('nombre')}
          placeholder="Ingresar nombre completo"
          autoComplete="name"
          error={errores.nombre}
          disabled={loading}
        />

        <CampoTexto
          id="registro-usuario"
          label="Usuario"
          icon={User}
          type="text"
          value={form.username}
          onChange={actualizarCampo('username')}
          placeholder="Ingresar usuario"
          autoComplete="username"
          error={errores.username}
          disabled={loading}
        />

        <CampoTexto
          id="registro-email"
          label="Email"
          icon={Mail}
          type="email"
          value={form.email}
          onChange={actualizarCampo('email')}
          placeholder="Ingresar email"
          autoComplete="email"
          error={errores.email}
          disabled={loading}
        />

        <div>
          <label htmlFor="registro-password" className="label text-coffee-100">Contraseña</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
            <input
              id="registro-password"
              type={showPassword ? 'text' : 'password'}
              value={form.password}
              onChange={actualizarCampo('password')}
              className={`input pl-10 pr-12 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500 ${errores.password ? 'border-red-400/70' : ''}`}
              placeholder="Ingresar contraseña"
              autoComplete="new-password"
              aria-invalid={errores.password ? 'true' : 'false'}
              aria-describedby={errores.password ? 'registro-password-error' : 'registro-password-help'}
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
          {errores.password ? (
            <p id="registro-password-error" className="text-xs text-red-300 mt-1" role="alert">{errores.password}</p>
          ) : (
            <p id="registro-password-help" className="text-xs text-coffee-300/60 mt-1">Mínimo 6 caracteres</p>
          )}
        </div>

        <div>
          <label htmlFor="registro-confirmar" className="label text-coffee-100">Confirmar contraseña</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-coffee-300" />
            <input
              id="registro-confirmar"
              type={showConfirmPassword ? 'text' : 'password'}
              value={form.confirmPassword}
              onChange={actualizarCampo('confirmPassword')}
              className={`input pl-10 pr-12 bg-white/5 border-white/20 text-white placeholder-coffee-300 focus:ring-coffee-500/30 focus:border-coffee-500 ${errores.confirmPassword ? 'border-red-400/70' : ''}`}
              placeholder="Repetir contraseña"
              autoComplete="new-password"
              aria-invalid={errores.confirmPassword ? 'true' : 'false'}
              aria-describedby={errores.confirmPassword ? 'registro-confirmar-error' : undefined}
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-coffee-300 hover:text-white"
              aria-label={showConfirmPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          {errores.confirmPassword && (
            <p id="registro-confirmar-error" className="text-xs text-red-300 mt-1" role="alert">{errores.confirmPassword}</p>
          )}
        </div>

        <Button type="submit" className="w-full py-3 text-base" loading={loading}>
          Crear cuenta
        </Button>
      </form>

      <p className="text-sm text-coffee-200/70 text-center mt-6">
        ¿Ya tenés cuenta?{' '}
        <Link to="/login" className="font-medium text-coffee-100 hover:text-white hover:underline">
          Iniciar sesión
        </Link>
      </p>
    </AuthShell>
  )
}
