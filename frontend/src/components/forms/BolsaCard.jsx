import { useEffect, useState } from 'react'
import { formatearKilos } from '../../utils/formatters'
import { ESTADO_BOLSA_COLORS } from '../../data/constants'
import { useToast } from '../../hooks/useToast.jsx'
import Badge from '../ui/Badge'

export default function BolsaCard({
  bolsa,
  onUpdateKilos,
  onToggleEstado,
  onDelete,
  editable = false,
  index,
}) {
  const isAbierta = bolsa.estado === 'abierta'
  const { success, error } = useToast()
  const [kilosInput, setKilosInput] = useState(String(bolsa.kilos ?? ''))

  useEffect(() => {
    setKilosInput(String(bolsa.kilos ?? ''))
  }, [bolsa.id, bolsa.kilos])

  const confirmarKilos = async () => {
    const kilos = Number(kilosInput)

    if (!Number.isFinite(kilos) || kilos < 0) {
      setKilosInput(String(bolsa.kilos ?? ''))
      error('Los kilos deben ser un número mayor o igual a 0')
      return
    }

    if (kilos === Number(bolsa.kilos)) return

    try {
      await onUpdateKilos(bolsa.id, kilos)
      success('Kilos de la bolsa actualizados')
    } catch (err) {
      setKilosInput(String(bolsa.kilos ?? ''))
      error(err.message || 'No se pudieron actualizar los kilos')
    }
  }

  const vaciarBolsa = async () => {
    try {
      await onUpdateKilos(bolsa.id, 0)
      setKilosInput('0')
      success('Bolsa vaciada')
    } catch (err) {
      error(err.message || 'No se pudo vaciar la bolsa')
    }
  }

  const cambiarEstado = async () => {
    try {
      await onToggleEstado(bolsa.id)
    } catch (err) {
      error(err.message || 'No se pudo cambiar el estado de la bolsa')
    }
  }

  const eliminarBolsa = async () => {
    try {
      await onDelete(bolsa.id)
    } catch (err) {
      error(err.message || 'No se pudo eliminar la bolsa')
    }
  }

  return (
    <div className={`relative bg-[var(--color-bg-secondary)] border rounded-xl p-4 transition-all ${isAbierta ? 'border-amber-500/30 bg-amber-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={`w-3 h-3 rounded-full flex-shrink-0 ${isAbierta ? 'bg-amber-500' : 'bg-green-500'}`} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-[var(--color-text-primary)]">{bolsa.loteRef || `Bolsa ${index + 1}`}</span>
              <Badge variant={ESTADO_BOLSA_COLORS[bolsa.estado]} className="text-xs">
                {bolsa.estado === 'cerrada' ? 'Cerrada' : 'Abierta'}
              </Badge>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] truncate">
              Creada: {new Date(bolsa.fechaCreacion).toLocaleDateString('es-AR')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="text-right min-w-[80px]">
            <p className="text-2xl font-bold text-[var(--color-text-primary)] tabular-nums">{formatearKilos(bolsa.kilos)}</p>
            <p className="text-xs text-[var(--color-text-muted)]">disponibles</p>
          </div>

          {editable && (
            <div className="flex items-center gap-1">
              <button
                onClick={cambiarEstado}
                className="btn-ghost btn-sm p-1.5 rounded-lg"
                title={isAbierta ? 'Marcar como cerrada' : 'Marcar como abierta'}
              >
                {isAbierta ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9V6m4 0v3m-6 4h12m-6 4h12m-6 4h12" /></svg>
                )}
              </button>
              <button
                onClick={eliminarBolsa}
                className="btn-ghost btn-sm p-1.5 rounded-lg text-red-500 hover:bg-red-500/10"
                title="Eliminar bolsa"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          )}
        </div>
      </div>

      {editable && (
        <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
          <label className="block text-xs text-[var(--color-text-muted)] mb-1">Ajustar kilos</label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.01"
              min="0"
              value={kilosInput}
              onChange={e => setKilosInput(e.target.value)}
              onBlur={confirmarKilos}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  e.currentTarget.blur()
                }
              }}
              className="input flex-1 text-center font-mono"
              aria-label={`Kilos disponibles de ${bolsa.loteRef || `bolsa ${index + 1}`}`}
            />
            <button
              onClick={vaciarBolsa}
              className="btn-ghost btn-sm px-3 text-red-500 hover:bg-red-500/10"
              title="Vaciar bolsa"
            >
              Vaciar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
