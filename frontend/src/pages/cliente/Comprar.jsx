import { useState, useMemo } from 'react'
import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { MEDIOS_PAGO } from '../../data/constants'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { calcularTotalPedido } from '../../utils/calculations'
import { nombreCafe, origenCafe, esOrganico, kilosCafe } from '../../utils/cafes'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import { ShoppingCart, Package, CreditCard, DollarSign, Upload, Clock, Plus, X } from 'lucide-react'

const FORM_INICIAL = {
  items: [{ cafeId: '', kilos: '' }],
  medioPago: 'transferencia',
  comprobante: null,
  ticket: null,
  observaciones: '',
}

export default function Comprar() {
  const { cafes, addPedido } = useData()
  const { user } = useAuth()
  const clienteId = user?.clienteId

  const cafesPorId = useMemo(
    () => Object.fromEntries(cafes.map(cafe => [cafe.id, cafe])),
    [cafes]
  )

  // Solo cafés con kilos tostados disponibles
  const cafesDisponibles = useMemo(
    () => cafes.filter(cafe => kilosCafe(cafe, 'tostado') > 0),
    [cafes]
  )

  const [formData, setFormData] = useState(FORM_INICIAL)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [enviado, setEnviado] = useState(false)

  const handleItemChange = (index, name, value) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.map((item, i) => (i === index ? { ...item, [name]: value } : item)),
    }))
    setErrors(prev => ({ ...prev, [`item${index}_${name === 'cafeId' ? 'stock' : 'kilos'}`]: '', items: '' }))
  }

  const addItem = () => {
    setFormData(prev => ({ ...prev, items: [...prev.items, { cafeId: '', kilos: '' }] }))
  }

  const removeItem = (index) => {
    setFormData(prev => {
      if (prev.items.length <= 1) return prev
      return { ...prev, items: prev.items.filter((_, i) => i !== index) }
    })
    setErrors({})
  }

  const handleFileChange = (field, e) => {
    setFormData(prev => ({ ...prev, [field]: e.target.files?.[0] || null }))
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }))
  }

  // Sin useCallback: así siempre valida con los datos actuales del formulario
  const validate = () => {
    const newErrors = {}
    let hayValido = false

    formData.items.forEach((item, index) => {
      if (!item.cafeId) {
        newErrors[`item${index}_stock`] = 'Selecciona un tipo de café'
        return
      }
      const cafe = cafes.find(c => c.id === item.cafeId)
      const disponible = kilosCafe(cafe, 'tostado')
      const kilos = parseFloat(item.kilos)
      if (!kilos || kilos <= 0) {
        newErrors[`item${index}_kilos`] = 'Cantidad inválida'
      } else if (kilos > disponible + 0.001) {
        newErrors[`item${index}_kilos`] = `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
      } else {
        hayValido = true
      }
    })

    if (!hayValido && Object.keys(newErrors).length === 0) {
      newErrors.items = 'Agrega al menos un producto con stock disponible'
    }

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

    const items = formData.items
      .filter(item => item.cafeId && parseFloat(item.kilos) > 0)
      .map(item => {
        const cafe = cafes.find(c => c.id === item.cafeId)
        return {
          cafeId: item.cafeId,
          nombre: nombreCafe(cafe),
          kilos: parseFloat(item.kilos),
          precioKg: cafe?.precioKg || 0,
        }
      })

    const pedido = {
      clienteId: clienteId || '',
      fecha: new Date().toISOString(),
      estado: 'Pendiente',
      medioPago: formData.medioPago,
      comprobanteAdjunto:
        formData.medioPago === 'transferencia' && formData.comprobante
          ? formData.comprobante.name
          : formData.medioPago === 'efectivo' && formData.ticket
            ? formData.ticket.name
            : null,
      items,
      total: calcularTotalPedido(items),
      observaciones: formData.observaciones.trim(),
      reservado: true, // stock no descontado hasta aprobación admin
    }

    addPedido(pedido)
    setSubmitting(false)
    setEnviado(true)
  }

  const totalKilos = useMemo(
    () => formData.items.reduce((sum, i) => sum + (parseFloat(i.kilos) || 0), 0),
    [formData.items]
  )

  const totalPedido = useMemo(() => {
    const itemsValidos = formData.items
      .filter(i => i.cafeId && parseFloat(i.kilos) > 0)
      .map(i => {
        const cafe = cafes.find(c => c.id === i.cafeId)
        return { kilos: parseFloat(i.kilos), precioKg: cafe?.precioKg || 0 }
      })
    return calcularTotalPedido(itemsValidos)
  }, [formData.items, cafes])

  const nuevaCompra = () => {
    setFormData(FORM_INICIAL)
    setErrors({})
    setEnviado(false)
  }

  if (enviado) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Compra realizada</h1>
          <p className="text-[var(--color-text-muted)]">
            Tu pedido ha sido registrado y queda pendiente de aprobación
          </p>
        </div>
        <div className="card p-8 text-center">
          <Package className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <div className="grid gap-4 sm:grid-cols-2 text-left mb-6">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total kilos</p>
              <p className="font-medium text-[var(--color-text-primary)]">{formatearKilos(totalKilos)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total a pagar</p>
              <p className="font-medium text-[var(--color-text-primary)]">{formatearMoneda(totalPedido)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Medio de pago</p>
              <p className="font-medium text-[var(--color-text-primary)]">{formData.medioPago}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Estado</p>
              <p className="font-medium text-[var(--color-text-primary)]">Pendiente</p>
            </div>
          </div>
          <Button onClick={nuevaCompra} className="w-full py-3">
            Nueva compra
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Comprar café</h1>
        <p className="text-[var(--color-text-muted)]">Selecciona el tipo de café y la cantidad en kilos</p>
      </div>

      {/* Catálogo */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-[var(--color-text-primary)]">Catálogo disponible</h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              {cafesDisponibles.length} café{cafesDisponibles.length !== 1 ? 's' : ''} con stock tostado
            </p>
          </div>
          <Badge variant="coffee" className="text-xs">{cafesDisponibles.length} disponibles</Badge>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cafesDisponibles.map(cafe => {
            const esBlend = cafe.tipoProducto === 'blend'
            const organico = esOrganico(cafe, cafesPorId)
            return (
              <div key={cafe.id} className="card p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-medium text-[var(--color-text-primary)]">{nombreCafe(cafe)}</h3>
                    <p className="text-sm text-[var(--color-text-muted)]">{origenCafe(cafe)}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {esBlend ? 'Blend' : 'Café simple'} · {organico ? 'Orgánico' : 'Convencional'}
                    </p>
                  </div>
                  <Badge variant={esBlend ? 'coffee' : 'success'} className="text-xs">
                    {esBlend ? 'Blend' : 'Simple'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[var(--color-text-muted)]">Precio / kg</p>
                    <p className="font-bold text-[var(--color-text-primary)]">{formatearMoneda(cafe.precioKg)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[var(--color-text-muted)]">Tostado disponible</p>
                    <p className="font-medium font-mono tabular-nums">{formatearKilos(kilosCafe(cafe, 'tostado'))}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Formulario */}
      <div className="card p-6">
        <h2 className="font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
          <ShoppingCart className="w-4 h-4" />
          Tu compra
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {formData.items.map((item, index) => (
            <div key={index} className="grid gap-3 sm:grid-cols-[1fr_140px_auto] items-start">
              <Select
                name={`cafeId-${index}`}
                value={item.cafeId}
                onChange={e => handleItemChange(index, 'cafeId', e.target.value)}
                options={cafesDisponibles.map(cafe => ({
                  value: cafe.id,
                  label: `${nombreCafe(cafe)} (${formatearKilos(kilosCafe(cafe, 'tostado'))} disp.)`,
                }))}
                placeholder="Seleccionar café"
                error={errors[`item${index}_stock`]}
              />
              <Input
                name={`kilos-${index}`}
                type="number"
                step="0.01"
                min="0.01"
                placeholder="Kilos"
                value={item.kilos}
                onChange={e => handleItemChange(index, 'kilos', e.target.value)}
                error={errors[`item${index}_kilos`]}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeItem(index)}
                disabled={formData.items.length === 1}
                aria-label="Eliminar producto"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ))}

          {errors.items && <p className="text-sm text-red-600">{errors.items}</p>}

          <Button type="button" variant="ghost" size="sm" onClick={addItem}>
            <Plus className="w-3 h-3 mr-2" />
            Agregar producto
          </Button>

          {/* Medio de pago */}
          <div className="pt-4">
            <h3 className="font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" /> Medio de pago
            </h3>

            <Select
              label="Selecciona cómo pagar *"
              name="medioPago"
              value={formData.medioPago}
              onChange={e => {
                setFormData(prev => ({ ...prev, medioPago: e.target.value }))
                setErrors(prev => ({ ...prev, comprobante: '' }))
              }}
              options={MEDIOS_PAGO}
            />

            {formData.medioPago === 'transferencia' && (
              <div className="mt-4 p-4 rounded-lg border border-amber-500/20 bg-amber-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <Upload className="w-4 h-4 text-amber-600" />
                  <span className="font-medium text-amber-800">Comprobante de transferencia (obligatorio)</span>
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => handleFileChange('comprobante', e)}
                  className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
                />
                {errors.comprobante && <p className="mt-2 text-sm text-red-600">{errors.comprobante}</p>}
                <p className="text-xs text-[var(--color-text-muted)] mt-2">
                  Adjunta el comprobante de tu transferencia bancaria. Sin él no se puede enviar el pedido.
                </p>
              </div>
            )}

            {formData.medioPago === 'tarjeta' && (
              <div className="mt-4 p-4 rounded-lg border border-coffee-500/20 bg-coffee-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <CreditCard className="w-4 h-4 text-coffee-500" />
                  <span className="font-medium text-[var(--color-text-primary)]">Tarjeta de crédito/débito</span>
                </div>
                <p className="text-xs text-[var(--color-text-muted)]">
                  Los campos de tarjeta son solo informativos. No se procesa ningún pago en este momento.
                </p>
              </div>
            )}

            {formData.medioPago === 'efectivo' && (
              <div className="mt-4 p-4 rounded-lg border border-blue-500/20 bg-blue-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-800">Ticket de pago (opcional)</span>
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => handleFileChange('ticket', e)}
                  className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
                />
                <p className="text-xs text-[var(--color-text-muted)] mt-2">
                  Puedes adjuntar el ticket si lo deseas, pero no es obligatorio para pagar en efectivo.
                </p>
              </div>
            )}
          </div>

          <Input
            label="Observaciones"
            name="observaciones"
            value={formData.observaciones}
            onChange={e => setFormData(prev => ({ ...prev, observaciones: e.target.value }))}
            placeholder="Notas adicionales..."
            multiline
            rows={2}
          />

          {/* Resumen */}
          <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-lg p-4">
            <div className="grid gap-2 sm:grid-cols-3 text-sm">
              <div>
                <span className="text-[var(--color-text-secondary)]">Total kilos:</span>
                <span className="font-medium text-[var(--color-text-primary)] ml-2">{formatearKilos(totalKilos)}</span>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">Productos:</span>
                <span className="font-medium text-[var(--color-text-primary)] ml-2">
                  {formData.items.filter(i => i.cafeId).length}
                </span>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">Total:</span>
                <span className="font-semibold text-[var(--color-text-primary)] ml-2">{formatearMoneda(totalPedido)}</span>
              </div>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-2">
              El stock se reserva pero no se descuenta hasta que la administración concrete la venta.
            </p>
          </div>

          <Button type="submit" variant="primary" loading={submitting} className="w-full py-3">
            <Clock className="w-4 h-4 mr-2" /> Enviar compra
          </Button>
        </form>
      </div>
    </div>
  )
}
