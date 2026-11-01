import { useState, useEffect, useMemo } from 'react'
import { useData } from '../../context/DataContext'
import { ESTADOS_PEDIDO, MEDIOS_CONTACTO } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { calcularTotalPedido, calcularKilosTotales } from '../../utils/calculations'

function itemVacio() {
  return { stockId: '', kilos: '' }
}

export default function PedidoForm({ isOpen, onClose, initialData, onSubmit }) {
  const { clientes, stock, kilosDeStock } = useData()
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
  const stockTostado = useMemo(
    () => stock.filter(item => item.tipo === 'tostado'),
    [stock],
  )

  // Al editar, el stock del pedido ya fue descontado: se suma de vuelta para
  // que la validación local no rechace los mismos kilos.
  const reservadoPorStock = useMemo(() => {
    const reservado = {}
    if (!initialData?.items) return reservado

    initialData.items.forEach(item => {
      reservado[item.stockId] = (reservado[item.stockId] || 0) + (item.kilos || 0)
    })

    return reservado
  }, [initialData])

  useEffect(() => {
    if (initialData) {
      setFormData({
        clienteId: initialData.clienteId || '',
        estado: initialData.estado || 'Pendiente',
        medioContacto: initialData.medioContacto || 'WhatsApp',
        observaciones: initialData.observaciones || '',
        items: initialData.items?.length
          ? initialData.items.map(item => ({
            stockId: item.stockId || '',
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

  const disponibleDe = (stockItem) => (
    kilosDeStock(stockItem) + (reservadoPorStock[stockItem?.id] || 0)
  )

  const precioDe = (stockId) => (
    stock.find(item => item.id === stockId)?.precioKg || 0
  )

  const validate = () => {
    const newErrors = {}

    if (!formData.clienteId) newErrors.clienteId = 'Debe seleccionar un cliente'
    if (formData.items.length === 0) newErrors.items = 'Debe agregar al menos un item'

    formData.items.forEach((item, index) => {
      if (!item.stockId) newErrors[`item${index}_stock`] = 'Debe seleccionar un producto'
      if (!item.kilos || parseFloat(item.kilos) <= 0) {
        newErrors[`item${index}_kilos`] = 'Kilos inválidos'
      }
    })

    const solicitadoPorStock = {}
    formData.items.forEach(item => {
      if (!item.stockId || !item.kilos) return
      solicitadoPorStock[item.stockId] = (
        (solicitadoPorStock[item.stockId] || 0) + parseFloat(item.kilos)
      )
    })

    Object.entries(solicitadoPorStock).forEach(([stockId, solicitado]) => {
      const stockItem = stock.find(item => item.id === stockId)
      const disponible = disponibleDe(stockItem)

      if (solicitado > disponible + 0.001) {
        formData.items.forEach((item, index) => {
          if (item.stockId === stockId) {
            newErrors[`item${index}_kilos`] = `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
          }
        })
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
      estado: formData.estado,
      medioContacto: formData.medioContacto,
      observaciones: formData.observaciones.trim(),
      items: formData.items.map(item => ({
        stockId: item.stockId,
        kilos: parseFloat(item.kilos),
      })),
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
        items: prev.items.map((item, i) => (
          i === index ? { ...item, [name]: value } : item
        )),
      }))
      if (errors[`item${index}_${name}`]) {
        setErrors(prev => ({ ...prev, [`item${index}_${name}`]: '' }))
      }
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
      if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const addItem = () => {
    setFormData(prev => ({
      ...prev,
      items: [...prev.items, itemVacio()],
    }))
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
      precioKg: precioDe(item.stockId),
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
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-[var(--color-text-primary)]">Items del pedido</h3>
            <Button type="button" variant="ghost" size="sm" onClick={addItem}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
              Agregar item
            </Button>
          </div>

          <div className="space-y-3">
            {formData.items.map((item, index) => {
              const stockItem = stock.find(s => s.id === item.stockId)
              const disponible = stockItem ? disponibleDe(stockItem) : 0
              const precioKg = precioDe(item.stockId)

              return (
                <div key={index} className="grid gap-3 sm:grid-cols-[1fr_100px_130px_auto] items-end p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
                  <Select
                    name="stockId"
                    value={item.stockId}
                    onChange={e => handleChange(e, index)}
                    options={stockTostado.map(stockItemOption => ({
                      value: stockItemOption.id,
                      label: `${stockItemOption.variedad} (${formatearKilos(kilosDeStock(stockItemOption))} disp.)`,
                    }))}
                    placeholder="Seleccionar café tostado"
                    error={errors[`item${index}_stock`]}
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
                    value={item.stockId ? formatearMoneda(precioKg) : ''}
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
                    <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </Button>
                </div>
              )
            })}
          </div>
          {errors.items && (
            <p className="form-error mt-2" role="alert">{errors.items}</p>
          )}
        </div>

        <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-lg p-4">
          <div className="grid gap-2 sm:grid-cols-3 text-sm">
            <div>
              <span className="text-[var(--color-text-secondary)]">Total kilos:</span>
              <span className="font-medium text-[var(--color-text-primary)] ml-2">{formatearKilos(totalKilos)}</span>
            </div>
            <div>
              <span className="text-[var(--color-text-secondary)]">Items:</span>
              <span className="font-medium text-[var(--color-text-primary)] ml-2">{formData.items.length}</span>
            </div>
            <div className="text-right sm:text-left">
              <span className="text-[var(--color-text-secondary)]">Total estimado:</span>
              <span className="font-semibold text-lg text-coffee-600 dark:text-coffee-400 ml-2">{formatearMoneda(totalPedido)}</span>
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
