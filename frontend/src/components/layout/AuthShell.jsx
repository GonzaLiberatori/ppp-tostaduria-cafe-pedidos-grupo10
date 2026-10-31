import { Coffee } from 'lucide-react'

/**
 * Contenedor visual compartido por las pantallas de autenticación.
 * Solo presentación: fondo, logo, card y pie de versión.
 */
export default function AuthShell({ children }) {
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
          {children}
        </div>

        <p className="text-center text-coffee-300/50 text-xs mt-6">
          Café de Finca v1.0 — Tostaduría de especialidad
        </p>
      </div>
    </div>
  )
}
