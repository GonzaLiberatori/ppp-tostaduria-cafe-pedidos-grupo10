import { useState, useMemo, useCallback } from 'react'
import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { MEDIOS_PAGO } from '../../data/constants'
import { formatearMoneda, formatearKilos, formatearFecha } from '../../utils/formatters'
import { calcularTotalPedido, calcularKilosTotales } from '../../utils/calculations'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import { ShoppingCart, Coffee, Package, AlertTriangle, CreditCard, DollarSign, Upload, Clock } from 'lucide-react'

export default function Comprar() {
  const { stock, addPedido, getTotalKilosStock } = useData()
  const { user } = useAuth()

  const clienteId = user?.clienteId

  // Solo café disponible (con kilos > 0)
  const stockDisponible = useMemo(() => {
    return stock.filter(s => {
      const kilos = calcKilosTotales(s)
      return kilos > 0
    })
  }, [stock])

  const [formData, setFormData] = useState({
    items: [{ stockId: '', kilos: '' }],
    medioPago: 'transferencia',
    comprobante: null,
    ticket: null,
    observaciones: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const [stockAlert, setStockAlert] = useState(null) // { stockId, mensaje }

  function getKilosTotales(stockItem) {
    if (!stockItem.bolsas || !Array.isArray(stockItem.bolsas)) return 0
    return stockItem.bolsas.reduce((sum, b) => sum + (b.kilos || 0), 0)
  }

  const handleItemChange = (index, name, value) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.map((item, i) =>
        i === index ? { ...item, [name]: value } : item
      ),
    }))
    // Limpiar alerta de stock de este item al editar
    if (stockAlert?.stockId === value && name === 'stockId') {
      setStockAlert(null)
    }
    if (errors[`item${index}_${name}`]) {
      setErrors(prev => ({ ...prev, [`item${index}_${name}`]: '' }))
    }
  }

  const addItem = () => {
    setFormData(prev => ({
      ...prev,
      items: [...prev.items, { stockId: '', kilos: '' }],
    }))
  }

  const removeItem = (index) => {
    if (formData.items.length <= 1) return
    setFormData(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }))
  }

  const handleFileChange = (field, e) => {
    setFormData(prev => ({ ...prev, [field]: e.target.files?.[0] || null }))
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }))
  }

  const validate = useCallback(() => {
    const newErrors = {}
    let hayValido = false

    formData.items.forEach((item, index) => {
      if (!item.stockId) {
        newErrors[`item${index}_stock`] = 'Selecciona un tipo de café'
      } else {
        const stockItem = stock.find(s => s.id === item.stockId)
        const disponible = stockItem ? getKilosTotales(stockItem) : 0
        if (!item.kilos || parseFloat(item.kilos) <= 0) {
          newErrors[`item${index}_kilos`] = 'Cantidad inválida'
        } else if (parseFloat(item.kilos) > disponible + 0.001) {
          newErrors[`item${index}_kilos`] = `Stock insuficiente (disponible: ${formatearKilos(disponible)})`
          setStockAlert({ stockId: item.stockId, mensaje: `No hay suficiente stock de ${stockItem?.variedad}` })
        } else {
          hayValido = true
        }
      }
    })

    if (formData.items.length === 0 || !hayValido) {
      newErrors.items = 'Agrega al menos un producto con stock disponible'
    }

    if (formData.medioPago === 'transferencia' && !formData.comprobante) {
      newErrors.comprobante = 'Debe adjuntar el comprobante de transferencia'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }, [formData, stock, formatearKilos])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)

    const items = formData.items
      .filter(item => item.stockId && item.kilos && parseFloat(item.kilos) > 0)
      .map(item => {
        const stockItem = stock.find(s => s.id === item.stockId)
        return {
          stockId: item.stockId,
          variedad: stockItem?.variedad || '',
          kilos: parseFloat(item.kilos),
          precioKg: stockItem?.precioKg || 0,
        }
      })

    const total = calcularTotalPedido(items)

    const pedido = {
      clienteId: clienteId || '',
      fecha: new Date().toISOString(),
      estado: 'Pendiente',
      medioPago: formData.medioPago,
      comprobanteAdjunto: formData.medioPago === 'transferencia' && formData.comprobante
        ? formData.comprobante.name
        : formData.medioPago === 'efectivo' && formData.ticket
          ? formData.ticket.name
          : null,
      items,
      total,
      observaciones: formData.observaciones.trim(),
      reservado: true, // stock no descontado hasta aprobación admin
    }

    addPedido(pedido)
    setSubmitting(false)
    setEnviado(true)
  }

  const totalKilos = useMemo(() =>
    formData.items.reduce((sum, i) => sum + (parseFloat(i.kilos) || 0), 0)
  , [formData.items])

  const totalPedido = useMemo(() => {
    const itemsValidos = formData.items
      .filter(i => i.stockId && i.kilos && parseFloat(i.kilos) > 0)
      .map(i => {
        const stockItem = stock.find(s => s.id === i.stockId)
        return { kilos: parseFloat(i.kilos), precioKg: stockItem?.precioKg || 0 }
      })
    return calcularTotalPedido(itemsValidos)
  }, [formData.items, stock])

  if (enviado) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Compra realizada</h1>
          <p className="text-[var(--color-text-muted)]">Tu pedido ha sido registrado y queda pendiente de aprobación</p>
        </div>
        <div className="card p-8 text-center">
          <Package className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-2">Pedido enviado</h2>
          <p className="text-[var(--color-text-muted)] mb-6">
            El stock no se descuenta hasta que la venta se concrete desde el panel de administración.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 text-left">
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total kilos</p>
              <p className="font-medium">{formatearKilos(totalKilos)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Total a pagar</p>
              <p className="font-medium text-coffee-600 dark:text-coffee-400">{formatearMoneda(totalPedido)}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Medio de pago</p>
              <p className="font-medium">{formData.medioPago}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Estado</p>
              <p className="font-medium text-amber-700">Pendiente</p>
            </div>
          </div>
          <Button onClick={() => setEnviado(false)}>Nueva compra</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Comprar café</h1>
        <p className="text-[var(--color-text-muted)]">
          Selecciona el tipo de café y la cantidad en kilos. El stock se muestra en kilos totales disponibles.
        </p>
      </div>

      {/* Stock disponible */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <Package className="w-4 h-4" />
            Catálogo disponible
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] ml-4">
            {stockDisponible.length} tipo{stockDisponible.length !== 1 ? 's' : ''} de café con stock
          </p>
        </div>
        <div className="card-body p-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {stockDisponible.map(item => {
              const kilos = getKilosTotales(item)
              const esTostado = item.tipo === 'tostado'
              return (
                <div key={item.id} className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg-secondary)]">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-medium text-[var(--color-text-primary)]">{item.variedad}</h3>
                      <p className="text-xs text-[var(--color-text-muted)]">{item.origen}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {esTostado ? 'Café tostado' : 'Café verde'} · Lote {item.lotePrincipal}
                      </p>
                    </div>
                    <Badge variant={esTostado ? 'coffee' : 'success'} className="text-xs">
                      {esTostado ? 'Tostado' : 'Verde'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-right">
                      <p className="text-xs text-[var(--color-text-muted)]">Precio / kg</p>
                      <p className="font-bold text-coffee-600 dark:text-coffee-400">{formatearMoneda(item.precioKg)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[var(--color-text-muted)]">Disponible</p>
                      <p className="font-medium font-mono tabular-nums">{formatearKilos(kilos)}</p>
                    </div>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div>
                      <span className="text-xs text-[var(--color-text-muted)] block mb-1">Bolsas</span>
                      <div className="flex gap-1">
                        {item.bolsas.map(b => (
                          <span key={b.id} className={`px-2 py-1 rounded text-xs border ${
                            b.estado === 'cerrada'
                              ? 'border-coffee-500/30 bg-coffee-500/10 text-coffee-600'
                              : 'border-amber-500/30 bg-amber-500/10 text-amber-600'
                          }`} title={`Bolsa ${b.kilos} kg`}>
                            {formatearKilos(b.kilos)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Formulario de compra */}
      <div className="card p-6 max-w-3xl">
        <h2 className="font-semibold text-[var(--color-text-primary)] mb-6 flex items-center gap-2">
          <ShoppingCart className="w-4 h-4" />
          Tu compra
        </h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg-tertiary)]/50">
            <h3 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
              <Coffee className="w-4 h-4" />
              Productos
            </h3>
            <div className="space-y-3">
              {formData.items.map((item, index) => {
                const stockItem = stock.find(s => s.id === item.stockId)
                const disponible = stockItem ? getKilosTotales(stockItem) : 0
                return (
                  <div key={index} className="grid gap-3 sm:grid-cols-[1fr_120px_auto] items-end p-3 bg-[var(--color-bg-secondary)] rounded-lg border border-[var(--color-border)]/50">
                    <Select
                      name="stockId"
                      value={item.stockId}
                      onChange={e => handleItemChange(index, 'stockId', e.target.value)}
                      options={stockDisponible.map(s => ({
                        value: s.id,
                        label: `${s.variedad} (${formatearKilos(getKilosTotales(s))} disp.)`,
                      }))}
                      placeholder="Seleccionar café"
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
                      onChange={e => handleItemChange(index, 'kilos', e.target.value)}
                      placeholder="Kilos"
                      error={errors[`item${index}_kilos`]}
                      label=""
                    />
                    {disponible <= 0 && (
                      <Badge variant="danger" className="text-xs self-end">Sin stock</Badge>
                    )}
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
              {stockAlert && (
                <div className="mt-3 p-3 bg-red-500/5 border border-red-500/20 rounded-lg text-sm">
                  <AlertTriangle className="w-4 h-4 text-red-600 mr-2" />
                  <span className="text-red-700">{stockAlert.mensaje}</span>
                </div>
              )}
            </div>
            <div className="flex justify-end mt-3">
              <Button type="button" variant="ghost" size="sm" onClick={addItem}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Agregar producto
              </Button>
            </div>
          </div>

          {/* Medio de pago */}
          <div className="border border-[var(--color-border)] rounded-lg p-4 bg-[var(--color-bg-tertiary)]/50">
            <h3 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Medio de pago
            </h3>
            <Select
              label="Selecciona cómo pagar *"
              name="medioPago"
              value={formData.medioPago}
              onChange={e => {
                setFormData(prev => ({ ...prev, medioPago: e.target.value }))
                if (errors.comprobante) setErrors(prev => ({ ...prev, comprobante: '' }))
                if (errors.ticket) setErrors(prev => ({ ...prev, ticket: '' }))
              }}
              options={MEDIOS_PAGO}
              error={errors.comprobante || errors.ticket}
            />

            {formData.medioPago === 'transferencia' && (
              <div className="mt-4 border border-amber-500/20 bg-amber-500/5 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Upload className="w-4 h-4 text-amber-600" />
                  <span className="font-medium text-amber-800">Comprobante de transferencia (obligatorio)</span>
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => handleFileChange('comprobante', e)}
                  className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
                />
                <p className="mt-2 text-xs text-amber-700">
                  Adjunta el comprobante de tu transferencia bancaria. Sin él no se puede enviar el pedido.
                </p>
                {errors.comprobante && <p className="mt-1 text-sm text-red-600">{errors.comprobante}</p>}
              </div>
            )}

            {formData.medioPago === 'tarjeta' && (
              <div className="mt-4 border border-blue-500/20 bg-blue-500/5 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <CreditCard className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-800">Tarjeta de crédito/débito</span>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input
                    placeholder="Número de tarjeta"
                    value=""
                    onChange={() => {}}
                    disabled
                    className="bg-[var(--color-bg-secondary)]"
                    label=""
                  />
                  <Input
                    placeholder="Vencimiento (MM/AA)"
                    value=""
                    onChange={() => {}}
                    disabled
                    className="bg-[var(--color-bg-secondary)]"
                    label=""
                  />
                </div>
                <Input
                  placeholder="CVV"
                  value=""
                  onChange={() => {}}
                  disabled
                  className="bg-[var(--color-bg-secondary)]"
                  label=""
                />
                <p className="mt-2 text-xs text-blue-700">
                  Los campos de tarjeta son solo informativos. No se procesa ningún pago en este momento.
                </p>
              </div>
            )}

            {formData.medioPago === 'efectivo' && (
              <div className="mt-4 border border-blue-500/20 bg-blue-500/5 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Upload className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-800">Ticket de pago (opcional)</span>
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => handleFileChange('ticket', e)}
                  className="block w-full text-sm text-[var(--color-text-muted)] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-coffee-500 file:text-white hover:file:bg-coffee-600"
                />
                <p className="mt-2 text-xs text-blue-700">
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
                  {formData.items.filter(i => i.stockId).length}
                </span>
              </div>
              <div className="text-right sm:text-left">
                <span className="text-[var(--color-text-secondary)]">Total:</span>
                <span className="font-semibold text-lg text-coffee-600 dark:text-coffee-400 ml-2">
                  {formatearMoneda(totalPedido)}
                </span>
              </div>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-3">
              El stock se reserva pero no se descuenta hasta que la administración concrete la venta.
            </p>
          </div>

          <Button type="submit" variant="primary" loading={submitting} className="w-full py-3 mt-4">
            <Clock className="w-4 h-4 mr-2" />
            Enviar compra
          </Button>
        </form>
      </div>
    </div>
  )
}
