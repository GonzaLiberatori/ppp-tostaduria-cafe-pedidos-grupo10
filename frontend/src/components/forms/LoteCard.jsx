import { Droplets, MapPin, CalendarDays, Pencil, Trash2, ClipboardList } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import { formatearFecha, formatearKilos } from '../../utils/formatters'

export default function LoteCard({ lote, ordenTuesteId, onEdit, onDelete }) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={lote.tipo === 'tostado' ? 'coffee' : 'success'} className="text-xs">
            {lote.tipo === 'tostado' ? 'Tostado' : 'Verde'}
          </Badge>
          <Badge variant={lote.estado === 'abierto' ? 'warning' : 'success'} className="text-xs">
            {lote.estado === 'abierto' ? 'Abierto' : 'Cerrado'}
          </Badge>
          {lote.humedad !== null && lote.humedad !== undefined && lote.humedad !== '' && (
            <span className="text-xs text-[var(--color-text-muted)]">{lote.humedad}% hum.</span>
          )}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          <Button type="button" variant="ghost" size="sm" className="p-1.5" onClick={() => onEdit(lote)} aria-label="Editar lote">
            <Pencil className="w-3.5 h-3.5" />
          </Button>
          <Button type="button" variant="ghost" size="sm" className="p-1.5" onClick={() => onDelete(lote)} aria-label="Eliminar lote">
            <Trash2 className="w-3.5 h-3.5 text-red-500" />
          </Button>
        </div>
      </div>

      <p className="mt-2 font-mono text-lg font-semibold tabular-nums text-[var(--color-text-primary)]">
        {formatearKilos(lote.kilos)}
      </p>

      <div className="mt-2 space-y-1 text-xs text-[var(--color-text-muted)]">
        <p className="flex items-center gap-1.5">
          <CalendarDays className="w-3.5 h-3.5 flex-shrink-0" />
          {lote.vencimiento ? `Vence ${formatearFecha(lote.vencimiento)}` : 'Sin vencimiento'}
        </p>
        <p className="flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
          {lote.ubicacion || 'Sin ubicación'}
        </p>
        {lote.humedad !== null && lote.humedad !== undefined && lote.humedad !== '' && (
          <p className="flex items-center gap-1.5">
            <Droplets className="w-3.5 h-3.5 flex-shrink-0" />
            {lote.humedad}% de humedad
          </p>
        )}
        {ordenTuesteId && (
          <p className="flex items-center gap-1.5">
            <ClipboardList className="w-3.5 h-3.5 flex-shrink-0" />
            Orden {ordenTuesteId}
          </p>
        )}
        {lote.observaciones && (
          <p className="italic text-[var(--color-text-secondary)]">{lote.observaciones}</p>
        )}
      </div>
    </div>
  )
}
