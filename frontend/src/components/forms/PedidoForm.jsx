import { useState, useEffect, useMemo } from 'react'
import { useData } from '../../context/DataContext'
import { ESTADOS_PEDIDO, MEDIOS_CONTACTO } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import Badge from '../ui/Badge'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { calcularTotalPedido, calcularKilosTotales } from '../../utils/calculations'
import { nombreCafe, kilosCafe } from '../../utils/cafes'

export default function PedidoForm({ isOpen, onClose, initialData, onSubmit }) {
  const { clientes, cafes, previewConsumoFIFO, consumirStockFIFO } = useData()
  const [formData, setFormData] = useState({
    clienteId: '',
    estado: 'Pendiente',
    medioContacto: 'WhatsApp',
    observaciones: '',
    items: [{ cafeId: '', kilos: '', precioKg: '' }],
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const clientesActivos = useMemo(() => clientes.filter(c => c.nombre), [clientes])
  const cafesConTostado = useMemo(
    () => cafes.filter(cafe => kilosCafe(cafe, 'tostado') > 0),
    [cafes]
  )

  useEffect(() => {
    const items = initialData?.items?.length
      ? initialData.items.map(item => ({
          cafeId: item.cafeId || item.stockId || '',
          kilos: item.kilos || '',
          precioKg: item.precioKg || '',
        }))
      : [{ cafeId: '', kilos: '', precioKg: '' }]

    setFormData({
      clienteId: initialData?.clienteId || '',
      estado: initialData?.estado || 'Pendiente',
      medioContacto: initialData?.medioContacto || 'WhatsApp',
      observaciones: initialData?.observaciones || '',
      items,
    })
    setErrors({})
  }, [initialData, isOpen])

  // Vista previa del consumo FIFO (sin modificar stock)
  const consumoPreview = useMemo(() => {
    if (initialData) return null
    const previews = {}
    let hayItems = false
    formData.items.forEach(item => {
      if (item.cafeId && item.kilos && parseFloat(item.kilos) > 0) {
        hayItems = true
        previews[item.cafeId] = previewConsumoFIFO(item.cafeId, parseFloat(item.kilos))
      }
    })
    return hayItems ? previews : null
  }, [formData.items, previewConsumoFIFO, initialData])

  const getCafe = (cafeId) => cafes.find(c => c.id === cafeId)

  const validate = () => {
    const newErrors = {}
    if (!formData.clienteId) newErrors.clienteId = 'Debe seleccionar un cliente'
    if (formData.items.length === 0) newErrors.items = 'Debe agregar al menos un item'
    formData.items.forEach((item, index) => {
      if (!item.cafeId) newErrors[`item${index}_cafe`] = 'Debe seleccionar un producto'
      if (!item.kilos || parseFloat(item.kilos) <= 0) newErrors[`item${index}_kilos`] = 'Kilos inválidos'
      if (!item.precioKg || parseFloat(item.precioKg) <= 0) newErrors[`item${index}_precio`] = 'Precio inválido'
      // Al editar, el stock ya fue descontado en la creación del pedido
      if (!initialData && item.cafeId && item.kilos) {
        const cafe = getCafe(item.cafeId)
        const disponible = cafe ? kilosCafe(cafe, 'tostado') : 0
        if (parseFloat(item.kilos) > disponible + 0.001) {
          newErrors[`item${index}_kilos`] = `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
        }
      }
    })
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    const items = formData.items.map(item => {
      const cafe = getCafe(item.cafeId)
      return {
        cafeId: item.cafeId,
        nombre: nombreCafe(cafe),
        kilos: parseFloat(item.kilos),
        precioKg: parseFloat(item.precioKg),
      }
    })
    const total = calcularTotalPedido(items)

    // Ejecutar consumo FIFO real sobre lotes tostados (solo en pedidos nuevos)
    if (!initialData) {
      formData.items.forEach(item => {
        if (item.cafeId && item.kilos && parseFloat(item.kilos) > 0) {
          consumirStockFIFO(item.cafeId, parseFloat(item.kilos))
        }
      })
    }

    const data = {
      clienteId: formData.clienteId,
      estado: formData.estado,
      medioContacto: formData.medioContacto,
      observaciones: formData.observaciones.trim(),
      items,
      total,
    }
    onSubmit(data, initialData?.id)
    setSubmitting(false)
  }

  const handleChange = (e, index = null) => {
    const { name, value } = e.target
    if (index !== null) {
      setFormData(prev => ({
        ...prev,
        items: prev.items.map((item, i) => {
          if (i !== index) return item
          if (name === 'cafeId') {
            const cafe = getCafe(value)
            return { ...item, cafeId: value, precioKg: cafe?.precioKg || '' }
          }
          return { ...item, [name]: value }
        }),
      }))
      const errorKey = name === 'cafeId' ? `item${index}_cafe` : `item${index}_${name}`
      if (errors[errorKey]) setErrors(prev => ({ ...prev, [errorKey]: '' }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
      if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const addItem = () => {
    setFormData(prev => ({
      ...prev,
      items: [...prev.items, { cafeId: '', kilos: '', precioKg: '' }],
    }))
  }

  const removeItem = (index) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }))
  }

  const totalKilos = calcularKilosTotales(
    formData.items.map(item => ({ kilos: parseFloat(item.kilos) || 0 }))
  )
  const totalPedido = calcularTotalPedido(
    formData.items.map(item => ({ kilos: parseFloat(item.kilos) || 0, precioKg: parseFloat(item.precioKg) || 0 }))
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar Pedido' : 'Nuevo Pedido'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear'}
      loading={submitting}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Cliente *"
            name="clienteId"
            value={formData.clienteId}
            onChange={handleChange}
            options={clientesActivos.map(c => ({ value: c.id, label: `${c.nombre} (${c.tipo})` }))}
            placeholder="Seleccionar cliente"
            error={errors.clienteId}
          />
          <Select
            label="Estado"
            name="estado"
            value={formData.estado}
            onChange={handleChange}
            options={ESTADOS_PEDIDO}
          />
        </div>

        <Select
          label="Medio de contacto"
          name="medioContacto"
          value={formData.medioContacto}
          onChange={handleChange}
          options={MEDIOS_CONTACTO}
        />

        <Input
          label="Observaciones"
          name="observaciones"
          value={formData.observaciones}
          onChange={handleChange}
          placeholder="Notas adicionales..."
          multiline
          rows={2}
        />

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-medium text-[var(--color-text-primary)]">Items del pedido</h3>
            <Button type="button" variant="ghost" size="sm" onClick={addItem}>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
              Agregar item
            </Button>
          </div>

          <div className="space-y-3">
            {formData.items.map((item, index) => {
              const cafe = getCafe(item.cafeId)
              const disponible = cafe ? kilosCafe(cafe, 'tostado') : 0

              return (
                <div key={index} className="grid gap-3 rounded-lg bg-[var(--color-bg-tertiary)] p-3 sm:grid-cols-[1fr_100px_120px_auto] sm:items-end">
                  <Select
                    name="cafeId"
                    value={item.cafeId}
                    onChange={e => handleChange(e, index)}
                    options={cafesConTostado.map(c => ({
                      value: c.id,
                      label: `${nombreCafe(c)} (${formatearKilos(kilosCafe(c, 'tostado'))} disp.)`,
                    }))}
                    placeholder="Seleccionar café tostado"
                    error={errors[`item${index}_cafe`]}
                    label=""
                  />
                  <Input
                    name="kilos"
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={disponible || undefined}
                    value={item.kilos}
                    onChange={e => handleChange(e, index)}
                    placeholder="Kilos"
                    error={errors[`item${index}_kilos`]}
                    label=""
                  />
                  <Input
                    name="precioKg"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={item.precioKg}
                    onChange={e => handleChange(e, index)}
                    placeholder="Precio/kg"
                    error={errors[`item${index}_precio`]}
                    label=""
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeItem(index)}
                    disabled={formData.items.length === 1}
                    aria-label="Eliminar item"
                  >
                    <svg className="h-4 w-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </Button>
                </div>
              )
            })}
          </div>

          {consumoPreview && Object.keys(consumoPreview).length > 0 && (
            <div className="mt-4 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
              <h4 className="mb-2 flex items-center gap-2 font-medium text-blue-700 dark:text-blue-300">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Vista previa de consumo FIFO (se ejecutará al guardar)
              </h4>
              <div className="space-y-1 text-sm">
                {Object.entries(consumoPreview).map(([cafeId, { consumo, faltante }]) => {
                  const cafe = getCafe(cafeId)
                  return (
                    <div key={cafeId} className="rounded bg-[var(--color-bg-secondary)] p-2">
                      <p className="font-medium text-[var(--color-text-primary)]">{nombreCafe(cafe)}</p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {consumo.map(c => (
                          <Badge key={c.loteId} variant="info" className="text-xs">
                            Lote {c.loteId.slice(-6)}: -{formatearKilos(c.consumido)}
                          </Badge>
                        ))}
                        {faltante > 0.001 && (
                          <Badge variant="danger" className="text-xs">
                            ⚠ Faltante: {formatearKilos(faltante)}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-coffee-500/20 bg-coffee-500/5 p-4">
          <div className="grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <span className="text-[var(--color-text-secondary)]">Total kilos:</span>
              <span className="ml-2 font-medium text-[var(--color-text-primary)]">{formatearKilos(totalKilos)}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-secondary)]">Items:</span>
              <span className="ml-2 font-medium text-[var(--color-text-primary)]">{formData.items.length}</span>
            </div>
            <div className="text-right sm:text-left">
              <span className="text-[var(--color-text-secondary)]">Total:</span>
              <span className="ml-2 text-lg font-semibold text-coffee-600 dark:text-coffee-400">{formatearMoneda(totalPedido)}</span>
            </div>
          </div>
        </div>
      </form>
    </Modal>
  )
}
