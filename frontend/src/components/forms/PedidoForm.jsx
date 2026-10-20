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

export default function PedidoForm({ isOpen, onClose, initialData, onSubmit }) {
  const { clientes, stock, consumirStockFIFO } = useData()
  const [formData, setFormData] = useState({
    clienteId: '',
    estado: 'Pendiente',
    medioContacto: 'WhatsApp',
    observaciones: '',
    items: [{ stockId: '', kilos: '', precioKg: '' }],
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [consumoPreview, setConsumoPreview] = useState(null)

  function getKilosTotales(stockItem) {
    if (!stockItem.bolsas || !Array.isArray(stockItem.bolsas)) return 0
    return stockItem.bolsas.reduce((sum, b) => sum + (b.kilos || 0), 0)
  }

  const clientesActivos = useMemo(() => clientes.filter(c => c.nombre), [clientes])
  const stockTostado = useMemo(() => stock.filter(s => s.tipo === 'tostado' && getKilosTotales(s) > 0), [stock])

  useEffect(() => {
    if (initialData) {
      setFormData({
        clienteId: initialData.clienteId || '',
        estado: initialData.estado || 'Pendiente',
        medioContacto: initialData.medioContacto || 'WhatsApp',
        observaciones: initialData.observaciones || '',
        items: initialData.items?.length ? initialData.items.map(item => ({
          stockId: item.stockId || '',
          kilos: item.kilos || '',
          precioKg: item.precioKg || '',
        })) : [{ stockId: '', kilos: '', precioKg: '' }],
      })
      setErrors({})
      setConsumoPreview(null)
    } else {
      setFormData({
        clienteId: '',
        estado: 'Pendiente',
        medioContacto: 'WhatsApp',
        observaciones: '',
        items: [{ stockId: '', kilos: '', precioKg: '' }],
      })
      setErrors({})
      setConsumoPreview(null)
    }
  }, [initialData, isOpen])

  // Preview de consumo FIFO cuando cambian los items
  useEffect(() => {
    if (!initialData) {
      const previews = {}
      let hayItems = false
      formData.items.forEach(item => {
        if (item.stockId && item.kilos && parseFloat(item.kilos) > 0) {
          hayItems = true
          const stockItem = stock.find(s => s.id === item.stockId)
          if (stockItem) {
            const { consumo, faltante } = consumirStockFIFO(stockItem.id, parseFloat(item.kilos))
            previews[item.stockId] = { consumo, faltante }
          }
        }
      })
      setConsumoPreview(hayItems ? previews : null)
    }
  }, [formData.items, stock, consumirStockFIFO, initialData])

  const validate = () => {
    const newErrors = {}
    if (!formData.clienteId) newErrors.clienteId = 'Debe seleccionar un cliente'
    if (formData.items.length === 0) newErrors.items = 'Debe agregar al menos un item'
    formData.items.forEach((item, index) => {
      if (!item.stockId) newErrors[`item${index}_stock`] = 'Debe seleccionar un producto'
      if (!item.kilos || parseFloat(item.kilos) <= 0) newErrors[`item${index}_kilos`] = 'Kilos inválidos'
      if (!item.precioKg || parseFloat(item.precioKg) <= 0) newErrors[`item${index}_precio`] = 'Precio inválido'
      // Validar stock disponible
      if (item.stockId && item.kilos) {
        const stockItem = stock.find(s => s.id === item.stockId)
        const disponible = stockItem ? getKilosTotales(stockItem) : 0
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
      const stockItem = stock.find(s => s.id === item.stockId)
      return {
        stockId: item.stockId,
        variedad: stockItem?.variedad || '',
        kilos: parseFloat(item.kilos),
        precioKg: parseFloat(item.precioKg),
      }
    })
    const total = calcularTotalPedido(items)
    
    // Ejecutar consumo FIFO real
    formData.items.forEach(item => {
      if (item.stockId && item.kilos && parseFloat(item.kilos) > 0) {
        consumirStockFIFO(item.stockId, parseFloat(item.kilos))
      }
    })
    
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
        items: prev.items.map((item, i) => i === index ? { ...item, [name]: value } : item)
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
      items: [...prev.items, { stockId: '', kilos: '', precioKg: '' }]
    }))
  }

  const removeItem = (index) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index)
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
              const disponible = stockItem ? getKilosTotales(stockItem) : 0
              const preview = consumoPreview?.[item.stockId]
              
              return (
                <div key={index} className="grid gap-3 sm:grid-cols-[1fr_100px_120px_auto] items-end p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
                  <Select
                    name="stockId"
                    value={item.stockId}
                    onChange={e => handleChange(e, index)}
                    options={stockTostado.map(s => ({ 
                      value: s.id, 
                      label: `${s.variedad} (${formatearKilos(getKilosTotales(s))} disp.)` 
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
                    <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </Button>
                </div>
              )
            })}
          </div>

          {consumoPreview && Object.keys(consumoPreview).length > 0 && (
            <div className="mt-4 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
              <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Vista previa de consumo FIFO (se ejecutará al guardar)
              </h4>
              <div className="space-y-1 text-sm">
                {Object.entries(consumoPreview).map(([stockId, { consumo, faltante }]) => {
                  const stockItem = stock.find(s => s.id === stockId)
                  return (
                    <div key={stockId} className="bg-[var(--color-bg-secondary)] p-2 rounded">
                      <p className="font-medium text-[var(--color-text-primary)]">{stockItem?.variedad}</p>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {consumo.map(c => (
                          <Badge key={c.bolsaId} variant="info" className="text-xs">
                            Bolsa {c.bolsaId.slice(-6)}: -{formatearKilos(c.consumido)}
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
              <span className="text-[var(--color-text-secondary)]">Total:</span>
              <span className="font-semibold text-lg text-coffee-600 dark:text-coffee-400 ml-2">{formatearMoneda(totalPedido)}</span>
            </div>
          </div>
        </div>
      </form>
    </Modal>
  )
}