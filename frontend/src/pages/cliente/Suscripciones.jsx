import { useState, useMemo } from 'react'
import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { FRECUENCIA_SUSCRIPCION, MEDIOS_PAGO } from '../../data/constants'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { formatearFecha } from '../../utils/formatters'
import { nombreCafe, kilosCafe } from '../../utils/cafes'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import { Clock, Coffee, Package, AlertTriangle } from 'lucide-react'

export default function Suscripciones() {
  const { addPedido, cafes } = useData()
  const { user } = useAuth()

  const [formData, setFormData] = useState({
    cafeId: '',
    kilos: '',
    frecuencia: 'semanal',
    medioPago: 'transferencia',
    comprobante: null,
    observaciones: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [enviado, setEnviado] = useState(false)

  const clienteId = user?.clienteId

  // Solo cafés con café tostado disponible para entregas recurrentes
  const cafesDisponibles = useMemo(
    () => cafes.filter(cafe => kilosCafe(cafe, 'tostado') > 0),
    [cafes]
  )

  const cafeSeleccionado = cafes.find(c => c.id === formData.cafeId)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const handleFileChange = (e) => {
    setFormData(prev => ({ ...prev, comprobante: e.target.files?.[0] || null }))
    if (errors.comprobante) setErrors(prev => ({ ...prev, comprobante: '' }))
  }

  const validate = () => {
    const newErrors = {}
    if (!formData.cafeId) newErrors.cafeId = 'Selecciona un tipo de café'
    if (!formData.kilos || parseFloat(formData.kilos) <= 0) newErrors.kilos = 'Kilos inválidos'
    if (formData.medioPago === 'transferencia' && !formData.comprobante) {
      newErrors.comprobante = 'Debe adjuntar el comprobante de transferencia'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)

    const kilos = parseFloat(formData.kilos)
    const precioKg = cafeSeleccionado?.precioKg || 0
    const total = kilos * precioKg

    const pedido = {
      clienteId: clienteId || '',
      fecha: new Date().toISOString(),
      estado: 'Pendiente',
      medioPago: formData.medioPago,
      comprobanteAdjunto: formData.comprobante ? formData.comprobante.name : null,
      items: [
        {
          cafeId: formData.cafeId,
          nombre: nombreCafe(cafeSeleccionado),
          kilos,
          precioKg,
        },
      ],
      total,
      tipo: 'suscripcion',
      frecuencia: formData.frecuencia,
      observaciones: formData.observaciones.trim(),
    }

    addPedido(pedido)
    setSubmitting(false)
    setEnviado(true)
  }

  if (enviado) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Suscripción solicitada</h1>
          <p className="text-[var(--color-text-muted)]">Tu pedido recurrente ha sido registrado</p>
        </div>
        <div className="card p-8 text-center">
          <Package className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-2">Solicitud enviada</h2>
          <p className="text-[var(--color-text-muted)] mb-6">
            Tu suscripción quedará activa una vez que el equipo de administración apruebe y genere el primer pedido.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 text-left">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Café</p>
              <p className="font-medium">{nombreCafe(cafeSeleccionado) || '—'}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Kilos por entrega</p>
              <p className="font-medium">{formatearKilos(formData.kilos)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Frecuencia</p>
              <p className="font-medium">
                {FRECUENCIA_SUSCRIPCION.find(f => f.value === formData.frecuencia)?.label}
              </p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Medio de pago</p>
              <p className="font-medium">{formData.medioPago}</p>
            </div>
          </div>
          <Button onClick={() => setEnviado(false)}>Nueva suscripción</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Suscripciones</h1>
        <p className="text-[var(--color-text-muted)]">
          Programa pedidos recurrentes semanales o mensuales. El pedido se genera y aprueba desde la administración.
        </p>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-medium text-amber-900">Importante</h3>
            <p className="text-sm text-amber-700 mt-1">
              Esta solicitud queda registrada como pendiente. El pedido concreto se crea y aprueba internamente desde el panel de administración.
            </p>
          </div>
        </div>
      </div>

      <div className="card p-6 max-w-2xl mx-auto">
        <h2 className="font-semibold text-[var(--color-text-primary)] mb-6">Nueva suscripción</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Tipo de café *"
              name="cafeId"
              value={formData.cafeId}
              onChange={handleChange}
              options={cafesDisponibles.map(cafe => ({
                value: cafe.id,
                label: `${nombreCafe(cafe)} (${formatearKilos(kilosCafe(cafe, 'tostado'))} disp.)`,
              }))}
              placeholder="Seleccionar café"
              error={errors.cafeId}
            />
            <Input
              label="Kilos por entrega *"
              name="kilos"
              type="number"
              step="0.01"
              min="0.01"
              value={formData.kilos}
              onChange={handleChange}
              placeholder="Ej: 5"
              error={errors.kilos}
            />
          </div>

          <Select
            label="Frecuencia *"
            name="frecuencia"
            value={formData.frecuencia}
            onChange={handleChange}
            options={FRECUENCIA_SUSCRIPCION}
            placeholder="Seleccionar frecuencia"
          />

          <Select
            label="Medio de pago *"
            name="medioPago"
            value={formData.medioPago}
            onChange={handleChange}
            options={MEDIOS_PAGO}
            placeholder="Seleccionar medio de pago"
          />

          {formData.medioPago === 'transferencia' && (
            <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span className="font-medium text-amber-800">Comprobante obligatorio</span>
              </div>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
              />
              {errors.comprobante && (
                <p className="mt-2 text-sm text-red-600">{errors.comprobante}</p>
              )}
            </div>
          )}

          {formData.medioPago === 'efectivo' && (
            <div className="border border-blue-500/20 bg-blue-500/5 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-blue-600" />
                <span className="font-medium text-blue-800">Ticket opcional</span>
              </div>
              <p className="text-sm text-blue-700 mb-3">
                Puedes adjuntar el ticket de pago si lo deseas, pero no es obligatorio.
              </p>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
              />
            </div>
          )}

          <Input
            label="Observaciones"
            name="observaciones"
            value={formData.observaciones}
            onChange={handleChange}
            placeholder="Notas adicionales..."
            multiline
            rows={2}
          />

          <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-lg p-4 mt-2">
            <div className="grid gap-2 sm:grid-cols-3 text-sm">
              <div>
                <span className="text-[var(--color-text-secondary)]">Total estimado:</span>
                <span className="font-medium text-[var(--color-text-primary)] ml-2">
                  {formData.cafeId && formData.kilos
                    ? formatearMoneda(parseFloat(formData.kilos) * (cafeSeleccionado?.precioKg || 0))
                    : formatearMoneda(0)}
                </span>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">Estado:</span>
                <span className="font-medium text-[var(--color-text-primary)] ml-2">Pendiente de aprobación</span>
              </div>
            </div>
          </div>

          <Button type="submit" variant="primary" loading={submitting} className="w-full py-3">
            <Clock className="w-4 h-4 mr-2" />
            Solicitar suscripción
          </Button>
        </form>
      </div>
    </div>
  )
}
