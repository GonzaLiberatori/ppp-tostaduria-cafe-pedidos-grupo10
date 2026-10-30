import { useMemo, useState } from 'react'
import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { FRECUENCIA_SUSCRIPCION, MEDIOS_PAGO } from '../../data/constants'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import { Clock, Package, AlertTriangle } from 'lucide-react'

export default function Suscripciones() {
  const { addPedido, stock, kilosDeStock } = useData()
  const { user } = useAuth()

  const clienteId = user?.clienteId

  // El portal solo vende café tostado; el verde es materia prima interna.
  const cafesDisponibles = useMemo(
    () => stock.filter(item => item.tipo === 'tostado' && kilosDeStock(item) > 0),
    [stock, kilosDeStock],
  )

  const [formData, setFormData] = useState({
    stockId: '',
    kilos: '',
    frecuencia: 'semanal',
    medioPago: 'transferencia',
    observaciones: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [enviado, setEnviado] = useState(false)

  const stockSeleccionado = cafesDisponibles.find(item => item.id === formData.stockId)
  const disponible = stockSeleccionado ? kilosDeStock(stockSeleccionado) : 0

  const etiquetaFrecuencia = FRECUENCIA_SUSCRIPCION
    .find(opcion => opcion.value === formData.frecuencia)?.label
  const etiquetaPago = MEDIOS_PAGO
    .find(opcion => opcion.value === formData.medioPago)?.label

  const totalEstimado = stockSeleccionado && formData.kilos
    ? parseFloat(formData.kilos) * stockSeleccionado.precioKg
    : 0

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const newErrors = {}

    if (!clienteId) newErrors.cliente = 'La cuenta no está vinculada a un cliente.'
    if (!formData.stockId) newErrors.stockId = 'Selecciona un café tostado'

    const kilos = parseFloat(formData.kilos)
    if (!formData.kilos || Number.isNaN(kilos) || kilos <= 0) {
      newErrors.kilos = 'Kilos inválidos'
    } else if (kilos > disponible + 0.001) {
      newErrors.kilos = `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    setSubmitError('')

    const notas = formData.observaciones.trim()
    const observaciones = [
      `Suscripción ${etiquetaFrecuencia || formData.frecuencia}`,
      `Pago: ${etiquetaPago || formData.medioPago}`,
      notas,
    ].filter(Boolean).join(' | ')

    const pedido = {
      clienteId: String(clienteId),
      estado: 'Pendiente',
      medioContacto: 'Email',
      observaciones,
      items: [
        {
          stockId: formData.stockId,
          kilos: parseFloat(formData.kilos),
        },
      ],
    }

    try {
      await addPedido(pedido)
      setEnviado(true)
    } catch (err) {
      setSubmitError(err.message || 'No se pudo registrar la suscripción')
    } finally {
      setSubmitting(false)
    }
  }

  const reiniciarFormulario = () => {
    setFormData({
      stockId: '',
      kilos: '',
      frecuencia: 'semanal',
      medioPago: 'transferencia',
      observaciones: '',
    })
    setErrors({})
    setSubmitError('')
    setEnviado(false)
  }

  if (enviado) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Suscripción solicitada</h1>
          <p className="text-[var(--color-text-muted)]">Tu pedido recurrente quedó registrado</p>
        </div>
        <div className="card p-8 text-center">
          <Package className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-2">Solicitud enviada</h2>
          <p className="text-[var(--color-text-muted)] mb-6">
            La administración revisará la solicitud y programará las entregas.
            El primer despacho se genera cuando se confirme la suscripción.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 text-left">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Café</p>
              <p className="font-medium">{stockSeleccionado?.variedad || '—'}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Kilos por entrega</p>
              <p className="font-medium">{formatearKilos(formData.kilos)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Frecuencia</p>
              <p className="font-medium">{etiquetaFrecuencia}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Medio de pago</p>
              <p className="font-medium">{etiquetaPago}</p>
            </div>
          </div>
          <Button onClick={reiniciarFormulario}>Nueva suscripción</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Suscripciones</h1>
        <p className="text-[var(--color-text-muted)]">
          Programa pedidos recurrentes semanales o mensuales de café tostado.
          El despacho se genera automáticamente cuando la administración activa la suscripción.
        </p>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-medium text-amber-900">Importante</h3>
            <p className="text-sm text-amber-700 mt-1">
              Esta solicitud queda registrada como pendiente y no descuenta stock.
              La programación de los días de entrega se acuerda con la administración.
            </p>
          </div>
        </div>
      </div>

      <div className="card p-6 max-w-2xl">
        <h2 className="font-semibold text-[var(--color-text-primary)] mb-6">Nueva suscripción</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          {cafesDisponibles.length === 0 ? (
            <div className="p-4 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-secondary)]">
              No hay café tostado con stock disponible en este momento.
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="Café tostado *"
                  name="stockId"
                  value={formData.stockId}
                  onChange={handleChange}
                  options={cafesDisponibles.map(item => ({
                    value: item.id,
                    label: `${item.variedad} (${formatearKilos(kilosDeStock(item))} disp.)`,
                  }))}
                  placeholder="Seleccionar café"
                  error={errors.stockId}
                />
                <Input
                  label="Kilos por entrega *"
                  name="kilos"
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={disponible || undefined}
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

              <Input
                label="Observaciones"
                name="observaciones"
                value={formData.observaciones}
                onChange={handleChange}
                placeholder="Días preferidos de entrega, referencias, etc."
                multiline
                rows={2}
              />

              <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-lg p-4 mt-2">
                <div className="grid gap-2 sm:grid-cols-2 text-sm">
                  <div>
                    <span className="text-[var(--color-text-secondary)]">Total estimado por entrega:</span>
                    <span className="font-medium text-[var(--color-text-primary)] ml-2">
                      {formatearMoneda(totalEstimado)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--color-text-secondary)]">Estado:</span>
                    <span className="font-medium text-[var(--color-text-primary)] ml-2">Pendiente de aprobación</span>
                  </div>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-3">
                  El precio final lo calcula el sistema al generar cada pedido.
                </p>
              </div>

              {errors.cliente && (
                <p className="form-error" role="alert">{errors.cliente}</p>
              )}
              {submitError && (
                <p className="form-error" role="alert">{submitError}</p>
              )}

              <Button type="submit" variant="primary" loading={submitting} className="w-full py-3">
                <Clock className="w-4 h-4 mr-2" />
                Solicitar suscripción
              </Button>
            </>
          )}
        </form>
      </div>
    </div>
  )
}
