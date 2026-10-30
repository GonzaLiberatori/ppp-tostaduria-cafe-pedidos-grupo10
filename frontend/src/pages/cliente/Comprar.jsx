import { useState, useMemo, useCallback } from 'react'
import { useData } from '../../context/DataContext'
import { useAuth } from '../../context/AuthContext'
import { MEDIOS_PAGO } from '../../data/constants'
import { formatearMoneda, formatearKilos } from '../../utils/formatters'
import { calcularTotalPedido } from '../../utils/calculations'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import { ShoppingCart, Coffee, Package, AlertTriangle, DollarSign, Clock } from 'lucide-react'

export default function Comprar() {
  const { stock, addPedido, kilosDeStock } = useData()
  const { user } = useAuth()

  const clienteId = user?.clienteId

  // Solo café tostado disponible (con kilos > 0)
  const stockDisponible = useMemo(
    () => stock.filter(item => item.tipo === 'tostado' && kilosDeStock(item) > 0),
    [stock, kilosDeStock],
  )

  const [formData, setFormData] = useState({
    items: [{ stockId: '', kilos: '' }],
    medioPago: 'transferencia',
    observaciones: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [enviado, setEnviado] = useState(false)
  const [stockAlert, setStockAlert] = useState(null) // { stockId, mensaje }

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

  const validate = useCallback(() => {
    const newErrors = {}
    let hayValido = false

    if (!clienteId) {
      newErrors.cliente = 'La cuenta no está vinculada a un cliente.'
    }

    formData.items.forEach((item, index) => {
      if (!item.stockId) {
        newErrors[`item${index}_stock`] = 'Selecciona un tipo de café'
      } else {
        const stockItem = stock.find(s => s.id === item.stockId)
        const disponible = stockItem ? kilosDeStock(stockItem) : 0
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

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }, [clienteId, formData, stock, formatearKilos])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    setSubmitError('')

    const items = formData.items
      .filter(item => item.stockId && item.kilos && parseFloat(item.kilos) > 0)
      .map(item => ({
        stockId: item.stockId,
        kilos: parseFloat(item.kilos),
      }))

    const medioPago = MEDIOS_PAGO.find(opcion => opcion.value === formData.medioPago)
    const notas = formData.observaciones.trim()
    const observaciones = [
      `Pago: ${medioPago?.label || formData.medioPago}`,
      notas,
    ].filter(Boolean).join(' | ')

    const pedido = {
      clienteId: String(clienteId),
      estado: 'Pendiente',
      medioContacto: 'Email',
      observaciones,
      items,
    }

    try {
      await addPedido(pedido)
      setEnviado(true)
    } catch (err) {
      setSubmitError(err.message || 'No se pudo registrar el pedido')
    } finally {
      setSubmitting(false)
    }
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

  const reiniciarCompra = () => {
    setFormData({
      items: [{ stockId: '', kilos: '' }],
      medioPago: 'transferencia',
      observaciones: '',
    })
    setErrors({})
    setSubmitError('')
    setStockAlert(null)
    setEnviado(false)
  }

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
            El pedido fue registrado y el stock quedó reservado en el inventario.
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
              <p className="font-medium">
                {MEDIOS_PAGO.find(opcion => opcion.value === formData.medioPago)?.label}
              </p>
            </div>
            <div>
              <p className="text-sm text-[var(--color-text-muted)]">Estado</p>
              <p className="font-medium text-amber-700">Pendiente</p>
            </div>
          </div>
          <Button onClick={reiniciarCompra}>Nueva compra</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Comprar café</h1>
        <p className="text-[var(--color-text-muted)]">
          Selecciona el café tostado y la cantidad en kilos. El stock se muestra en kilos totales disponibles.
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
              const kilos = kilosDeStock(item)
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
                const disponible = stockItem ? kilosDeStock(stockItem) : 0
                return (
                  <div key={index} className="grid gap-3 sm:grid-cols-[1fr_120px_auto] items-end p-3 bg-[var(--color-bg-secondary)] rounded-lg border border-[var(--color-border)]/50">
                    <Select
                      name="stockId"
                      value={item.stockId}
                      onChange={e => handleItemChange(index, 'stockId', e.target.value)}
                      options={stockDisponible.map(s => ({
                        value: s.id,
                        label: `${s.variedad} (${formatearKilos(kilosDeStock(s))} disp.)`,
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
              onChange={e => setFormData(prev => ({ ...prev, medioPago: e.target.value }))}
              options={MEDIOS_PAGO}
            />
            <p className="mt-2 text-xs text-[var(--color-text-muted)]">
              El medio de pago queda registrado en las observaciones del pedido.
              La administración coordina el cobro y la entrega.
            </p>
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
              El pedido queda pendiente hasta que la administración confirme la entrega.
              El precio final lo calcula el sistema con el catálogo vigente.
            </p>
          </div>

          {errors.cliente && (
            <p className="form-error" role="alert">{errors.cliente}</p>
          )}
          {submitError && (
            <p className="form-error" role="alert">{submitError}</p>
          )}

          <Button type="submit" variant="primary" loading={submitting} className="w-full py-3 mt-4">
            <Clock className="w-4 h-4 mr-2" />
            Enviar compra
          </Button>
        </form>
      </div>
    </div>
  )
}
