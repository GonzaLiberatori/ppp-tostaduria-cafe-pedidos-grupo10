import { useState, useEffect } from 'react'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import { ESTADOS_LOTE, TIPOS_LOTE } from '../../data/constants'
import { formatearFecha } from '../../utils/formatters'

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
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    if (initialData) {
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
      setFormData({ ...FORM_INICIAL, cafeId: cafeIdInicial || '' })
    }
    setErrors({})
    setApiError(null)
  }, [isOpen, initialData, cafeIdInicial])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const newErrors = {}
    const isEdicion = !!initialData
    
    // En modo edición, no validar cafeId (el origen ya está definido)
    if (!isEdicion) {
      const cafe = cafes.find(c => c.id === Number(formData.cafeId))
      if (!cafe) newErrors.cafeId = 'Seleccioná el café del lote'
    }
    
    if (!formData.vencimiento) newErrors.vencimiento = 'La fecha de vencimiento es obligatoria'
    if (!formData.kilos || parseFloat(formData.kilos) <= 0) newErrors.kilos = 'Los kilos deben ser mayores a 0'
    if (!formData.ubicacion.trim()) newErrors.ubicacion = 'La ubicación es obligatoria'
    
    // Humedad es obligatoria (el backend la requiere)
    if (formData.humedad === '' || formData.humedad === null) {
      newErrors.humedad = 'La humedad es obligatoria'
    } else if (isNaN(parseFloat(formData.humedad)) || parseFloat(formData.humedad) < 0 || parseFloat(formData.humedad) > 100) {
      newErrors.humedad = 'La humedad debe estar entre 0 y 100'
    }
    
    // Para lotes TOSTADO, la orden de tueste es obligatoria
    if (formData.tipo === 'tostado' && !formData.ordenTuesteId) {
      newErrors.ordenTuesteId = 'La orden de tueste es obligatoria para lotes tostados'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    setApiError(null)
    
    const isEdicion = !!initialData
    
    try {
      const payload = {
        tipo: formData.tipo,
        estado: formData.estado,
        vencimiento: `${formData.vencimiento}T12:00:00.000Z`,
        humedad: parseFloat(formData.humedad),
        kilos: parseFloat(formData.kilos),
        ubicacion: formData.ubicacion.trim(),
        observaciones: formData.observaciones.trim(),
        ordenTuesteId: formData.ordenTuesteId || null,
      }
      
      // Solo enviar cafeId en modo creación
      if (!isEdicion) {
        payload.cafeId = formData.cafeId
      }
      
      await onSubmit(payload, initialData?.id, cafeIdInicial)
    } catch (err) {
      setApiError(err.message || 'Error al guardar el lote')
    } finally {
      setSubmitting(false)
    }
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
        {apiError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
            <p className="text-sm text-red-700 dark:text-red-300">{apiError}</p>
          </div>
        )}

        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
          <h3 className="mb-3 flex items-center gap-2 font-medium text-[var(--color-text-primary)]">
            <span className="h-2 w-2 rounded-full bg-green-500"></span>
            Datos del lote
          </h3>

          <div className="grid gap-3 sm:grid-cols-2">
            {!initialData && (
              <Select
                label="Tipo de lote *"
                name="tipo"
                value={formData.tipo}
                onChange={handleChange}
                options={TIPOS_LOTE}
              />
            )}
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

          {!initialData && (
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
          )}

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
