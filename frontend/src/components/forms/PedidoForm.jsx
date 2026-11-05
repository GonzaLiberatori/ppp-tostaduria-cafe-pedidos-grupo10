import { useState, useEffect, useMemo } from 'react'
import { useData } from '../../context/DataContext'
import { ESTADOS_PEDIDO, MEDIOS_CONTACTO } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { calcularTotalPedido, calcularKilosTotales } from '../../utils/calculations'
import { nombreCafe, kilosCafe, stockIdDeCafe } from '../../utils/cafes'

function itemVacio() {
  return { cafeId: '', kilos: '' }
}

export default function PedidoForm({ isOpen, onClose, initialData, onSubmit }) {
  const { clientes, cafes } = useData()
  const [formData, setFormData] = useState({
    clienteId: '',
    estado: 'Pendiente',
    medioContacto: 'WhatsApp',
    observaciones: '',
    items: [itemVacio()],
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const clientesActivos = useMemo(
    () => clientes.filter(cliente => cliente.nombre),
    [clientes],
  )

  // Solo se puede vender café tostado.
  const cafesConTostado = useMemo(
    () => cafes.filter(cafe => kilosCafe(cafe, 'tostado') > 0),
    [cafes],
  )

  // La entrega crea la venta y exige la condición de pago, así que no se elige
  // desde el formulario: se confirma desde el kanban con el modal de entrega.
  const estadosDisponibles = useMemo(
    () => ESTADOS_PEDIDO.filter(estado => estado.value !== 'Entregado'),
    [],
  )

  // Al editar, los ítems llegan del backend con `stockId` (`tc-3-TOSTADO`).
  // Se traducen al café local para poder mostrarlos en el select.
  const cafeIdDesdeStockId = (stockId) => {
    if (!stockId) return ''
    const cafe = cafes.find(item => stockIdDeCafe(item) === stockId)
    return cafe?.id || ''
  }

  useEffect(() => {
    if (initialData) {
      setFormData({
        clienteId: initialData.clienteId || '',
        estado: initialData.estado || 'Pendiente',
        medioContacto: initialData.medioContacto || 'WhatsApp',
        observaciones: initialData.observaciones || '',
        items: initialData.items?.length
          ? initialData.items.map(item => ({
            cafeId: item.cafeId ?? cafeIdDesdeStockId(item.stockId),
            kilos: item.kilos || '',
          }))
          : [itemVacio()],
      })
    } else {
      setFormData({
        clienteId: '',
        estado: 'Pendiente',
        medioContacto: 'WhatsApp',
        observaciones: '',
        items: [itemVacio()],
      })
    }

    setErrors({})
  }, [initialData, isOpen])

  const cafeDe = (cafeId) => cafes.find(cafe => cafe.id === cafeId)

  const validate = () => {
    const newErrors = {}

    if (!formData.clienteId) newErrors.clienteId = 'Debe seleccionar un cliente'
    if (formData.items.length === 0) newErrors.items = 'Debe agregar al menos un item'

    formData.items.forEach((item, index) => {
      if (!item.cafeId) newErrors[`item${index}_cafe`] = 'Debe seleccionar un producto'
      if (!item.kilos || parseFloat(item.kilos) <= 0) {
        newErrors[`item${index}_kilos`] = 'Kilos inválidos'
        return
      }
      // Al editar, el stock ya fue descontado en la creación del pedido.
      if (!initialData) {
        const cafe = cafeDe(item.cafeId)
        const disponible = kilosCafe(cafe, 'tostado')
        if (parseFloat(item.kilos) > disponible + 0.001) {
          newErrors[`item${index}_kilos`] =
            `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
        }
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)

    const data = {
      clienteId: formData.clienteId,
      // Un pedido ya entregado no reenvía el estado: la entrega se gestiona
      // desde el kanban y volver a mandarlo exigiría una condición de pago.
      ...(formData.estado !== 'Entregado' ? { estado: formData.estado } : {}),
      medioContacto: formData.medioContacto,
      observaciones: formData.observaciones.trim(),
      items: formData.items.map(item => {
        const cafe = cafeDe(item.cafeId)
        return {
          // El backend recalcula el precio a partir del producto de stock.
          stockId: stockIdDeCafe(cafe),
          kilos: parseFloat(item.kilos),
        }
      }),
    }

    try {
      await onSubmit(data, initialData?.id)
    } finally {
      setSubmitting(false)
    }
  }

  const handleChange = (e, index = null) => {
    const { name, value } = e.target

    if (index !== null) {
      setFormData(prev => ({
        ...prev,
        items: prev.items.map((item, i) => (i === index ? { ...item, [name]: value } : item)),
      }))
      const errorKey = name === 'cafeId' ? `item${index}_cafe` : `item${index}_${name}`
      if (errors[errorKey]) setErrors(prev => ({ ...prev, [errorKey]: '' }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
      if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const addItem = () => {
    setFormData(prev => ({ ...prev, items: [...prev.items, itemVacio()] }))
  }

  const removeItem = (index) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }))
  }

  const totalKilos = calcularKilosTotales(
    formData.items.map(item => ({ kilos: parseFloat(item.kilos) || 0 })),
  )
  const totalPedido = calcularTotalPedido(
    formData.items.map(item => ({
      kilos: parseFloat(item.kilos) || 0,
      precioKg: cafeDe(item.cafeId)?.precioKg || 0,
    })),
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
            options={clientesActivos.map(cliente => ({
              value: cliente.id,
              label: `${cliente.nombre} (${cliente.tipo})`,
            }))}
            placeholder="Seleccionar cliente"
            error={errors.clienteId}
          />
          {formData.estado === 'Entregado' ? (
            <Input
              label="Estado"
              value="Entregado"
              disabled
              help="La entrega ya fue confirmada; el estado se gestiona desde el kanban."
            />
          ) : (
            <Select
              label="Estado"
              name="estado"
              value={formData.estado}
              onChange={handleChange}
              options={estadosDisponibles}
            />
          )}
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
              const cafe = cafeDe(item.cafeId)
              const disponible = kilosCafe(cafe, 'tostado')

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
                    value={cafe ? formatearMoneda(cafe.precioKg) : ''}
                    placeholder="Precio/kg"
                    disabled
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
          <p className="text-xs text-[var(--color-text-muted)] mt-2">
            El precio se toma del catálogo y el backend calcula el total definitivo.
          </p>
        </div>
      </form>
    </Modal>
  )
}
