import { useState, useEffect } from 'react'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import SegmentedToggle from '../ui/SegmentedToggle'
import { ESTADOS_LOTE, TIPOS_CAFE, TIPOS_LOTE } from '../../data/constants'
import { formatearFecha } from '../../utils/formatters'
import { nombreCafe, origenCafe } from '../../utils/cafes'

const FORM_INICIAL = {
  cafeId: '',
  tipo: 'verde',
  estado: 'cerrado',
  vencimiento: '',
  humedad: '',
  kilos: '',
  ubicacion: '',
  observaciones: '',
  ordenTuesteId: '',
}

export default function LoteForm({ isOpen, onClose, onSubmit, initialData, cafeIdInicial, cafes = [], ordenesTueste = [] }) {
  const [formData, setFormData] = useState(FORM_INICIAL)
  const [tipoProducto, setTipoProducto] = useState('simple')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    if (initialData) {
      const cafe = cafes.find(c => c.id === cafeIdInicial)
      setTipoProducto(cafe?.tipoProducto || 'simple')
      setFormData({
        cafeId: cafeIdInicial || '',
        tipo: initialData.tipo || 'verde',
        estado: initialData.estado || 'cerrado',
        vencimiento: initialData.vencimiento ? initialData.vencimiento.slice(0, 10) : '',
        humedad: initialData.humedad ?? '',
        kilos: initialData.kilos ?? '',
        ubicacion: initialData.ubicacion || '',
        observaciones: initialData.observaciones || '',
        ordenTuesteId: initialData.ordenTuesteId || '',
      })
    } else {
      const cafe = cafes.find(c => c.id === cafeIdInicial)
      setTipoProducto(cafe?.tipoProducto || 'simple')
      setFormData({ ...FORM_INICIAL, cafeId: cafeIdInicial || '' })
    }
    setErrors({})
  }, [isOpen, initialData, cafeIdInicial, cafes])

  const cafesFiltrados = cafes.filter(cafe => cafe.tipoProducto === tipoProducto)
  const cafeSeleccionado = cafes.find(cafe => cafe.id === formData.cafeId)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const handleTipoProducto = (tipo) => {
    setTipoProducto(tipo)
    setFormData(prev => {
      const cafeActual = cafes.find(c => c.id === prev.cafeId)
      return { ...prev, cafeId: cafeActual?.tipoProducto === tipo ? prev.cafeId : '' }
    })
    setErrors(prev => ({ ...prev, cafeId: '' }))
  }

  const validate = () => {
    const newErrors = {}
    const cafe = cafes.find(c => c.id === formData.cafeId)
    if (!cafe) newErrors.cafeId = 'Seleccioná el café del lote'
    if (!formData.vencimiento) newErrors.vencimiento = 'La fecha de vencimiento es obligatoria'
    if (!formData.kilos || parseFloat(formData.kilos) <= 0) newErrors.kilos = 'Los kilos deben ser mayores a 0'
    if (!formData.ubicacion.trim()) newErrors.ubicacion = 'La ubicación es obligatoria'
    if (formData.humedad !== '' && (isNaN(parseFloat(formData.humedad)) || parseFloat(formData.humedad) < 0 || parseFloat(formData.humedad) > 100)) {
      newErrors.humedad = 'La humedad debe estar entre 0 y 100'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    onSubmit({
      cafeId: formData.cafeId,
      tipo: formData.tipo,
      estado: formData.estado,
      vencimiento: `${formData.vencimiento}T12:00:00.000Z`,
      humedad: formData.humedad === '' ? null : parseFloat(formData.humedad),
      kilos: parseFloat(formData.kilos),
      ubicacion: formData.ubicacion.trim(),
      observaciones: formData.observaciones.trim(),
      ordenTuesteId: formData.ordenTuesteId || null,
    }, initialData?.id, cafeIdInicial)
    setSubmitting(false)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar lote' : 'Crear lote'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear lote'}
      loading={submitting}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="rounded-xl border border-coffee-500/20 bg-coffee-500/5 p-4">
          <h3 className="mb-3 flex items-center gap-2 font-medium text-[var(--color-text-primary)]">
            <span className="h-2 w-2 rounded-full bg-coffee-500"></span>
            Café asociado
          </h3>

          <SegmentedToggle
            value={tipoProducto}
            onChange={handleTipoProducto}
            options={TIPOS_CAFE}
            label="Categoría"
          />

          <div className="mt-3">
            <Select
              label={tipoProducto === 'blend' ? 'Blend' : 'Café simple'}
              name="cafeId"
              value={formData.cafeId}
              onChange={handleChange}
              options={cafesFiltrados.map(cafe => ({
                value: cafe.id,
                label: `${nombreCafe(cafe)}${tipoProducto === 'simple' ? ` — ${origenCafe(cafe)}` : ''}`,
              }))}
              placeholder={tipoProducto === 'blend' ? 'Seleccionar blend' : 'Seleccionar café simple'}
              error={errors.cafeId}
            />
          </div>

          {/* Campos derivados del café elegido: se completan solos y no se editan */}
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Input
              label={tipoProducto === 'blend' ? 'ID Blend' : 'ID Café'}
              value={cafeSeleccionado?.id || ''}
              placeholder="Se completa al elegir el café"
              readOnly
              tabIndex={-1}
              aria-readonly="true"
              title={cafeSeleccionado?.id || ''}
              className="cursor-not-allowed bg-[var(--color-bg-tertiary)] font-mono text-xs text-[var(--color-text-secondary)]"
            />
            <Input
              label="Tipo de café"
              value={
                cafeSeleccionado
                  ? cafeSeleccionado.tipoProducto === 'blend' ? 'Blend' : 'Simple'
                  : ''
              }
              placeholder="Se completa al elegir el café"
              readOnly
              tabIndex={-1}
              aria-readonly="true"
              className="cursor-not-allowed bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]"
            />
          </div>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">
            ID y tipo de café se completan automáticamente con el café seleccionado y no son editables.
          </p>
        </div>

        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
          <h3 className="mb-3 flex items-center gap-2 font-medium text-[var(--color-text-primary)]">
            <span className="h-2 w-2 rounded-full bg-green-500"></span>
            Datos del lote
          </h3>

          <div className="grid gap-3 sm:grid-cols-2">
            <Select
              label="Tipo de lote *"
              name="tipo"
              value={formData.tipo}
              onChange={handleChange}
              options={TIPOS_LOTE}
            />
            <Select
              label="Estado *"
              name="estado"
              value={formData.estado}
              onChange={handleChange}
              options={ESTADOS_LOTE}
            />
            <Input
              label="Vencimiento *"
              name="vencimiento"
              type="date"
              value={formData.vencimiento}
              onChange={handleChange}
              error={errors.vencimiento}
            />
            <Input
              label="Kilos *"
              name="kilos"
              type="number"
              step="0.01"
              min="0.01"
              value={formData.kilos}
              onChange={handleChange}
              placeholder="0.00"
              error={errors.kilos}
            />
            <Input
              label="Humedad (%)"
              name="humedad"
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={formData.humedad}
              onChange={handleChange}
              placeholder="Opcional"
              error={errors.humedad}
            />
            <Input
              label="Ubicación *"
              name="ubicacion"
              value={formData.ubicacion}
              onChange={handleChange}
              placeholder="Ej: Depósito A - Estante 2"
              error={errors.ubicacion}
            />
          </div>

          <div className="mt-3">
            <Select
              label="Orden de tueste"
              name="ordenTuesteId"
              value={formData.ordenTuesteId}
              onChange={handleChange}
              options={ordenesTueste.map(orden => ({
                value: orden.id,
                label: `${orden.id} · ${formatearFecha(orden.fecha)} · ${orden.estado}`,
              }))}
              placeholder="Sin orden asociada"
            />
          </div>

          <div className="mt-3">
            <Input
              label="Observaciones"
              name="observaciones"
              value={formData.observaciones}
              onChange={handleChange}
              placeholder="Notas opcionales del lote..."
              multiline
              rows={2}
            />
          </div>
        </div>

        <p className="text-xs text-[var(--color-text-muted)]">Los campos marcados con * son obligatorios.</p>
      </form>
    </Modal>
  )
}
