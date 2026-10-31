import { useState, useEffect } from 'react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import SegmentedToggle from '../ui/SegmentedToggle'
import { TIPOS_CAFE } from '../../data/constants'
import { formatearKilos } from '../../utils/formatters'
import { kilosCafe, nombreCafe, origenCafe, sugerirPorcentajes } from '../../utils/cafes'

const FORM_INICIAL = {
  tipoProducto: 'simple',
  variedad: '',
  pais: '',
  region: '',
  organico: false,
  precioKg: '',
  nombre: '',
  descripcion: '',
  mezcla: [],
}

export default function CafeForm({ isOpen, onClose, onSubmit, initialData, cafes = [] }) {
  const [formData, setFormData] = useState(FORM_INICIAL)
  const [nuevoComponente, setNuevoComponente] = useState('')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState(null)

  const simples = cafes.filter(cafe => cafe.tipoProducto === 'simple')

  useEffect(() => {
    if (!isOpen) return
    if (initialData) {
      setFormData({
        tipoProducto: initialData.tipoProducto || 'simple',
        variedad: initialData.variedad || '',
        pais: initialData.pais || '',
        region: initialData.region || '',
        organico: !!initialData.organico,
        precioKg: initialData.precioKg || '',
        nombre: initialData.nombre || '',
        descripcion: initialData.descripcion || '',
        mezcla: initialData.mezcla
          ? initialData.mezcla
              .filter(m => cafes.some(cafe => cafe.id === Number(m.cafeId)))
              .map(m => ({ ...m }))
          : [],
      })
    } else {
      setFormData(FORM_INICIAL)
    }
    setNuevoComponente('')
    setErrors({})
    setApiError(null)
  }, [isOpen, initialData, cafes])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const handleTipoProducto = (tipo) => {
    setFormData(prev => ({ ...prev, tipoProducto: tipo }))
    setErrors({})
  }

  const mezclaSeleccionada = formData.mezcla
    .map(m => ({ ...m, cafe: cafes.find(c => c.id === Number(m.cafeId)) }))
    .filter(m => m.cafe)

  const totalPorcentaje = formData.mezcla.reduce((sum, m) => sum + (Number(m.porcentaje) || 0), 0)

  const recalcularMezcla = (cafeIds) => {
    const seleccionados = cafeIds.map(id => cafes.find(c => c.id === Number(id))).filter(Boolean)
    return sugerirPorcentajes(seleccionados).map(({ cafeId, porcentaje }) => ({ cafeId, porcentaje }))
  }

  const agregarComponente = () => {
    if (!nuevoComponente) return
    const ids = [...formData.mezcla.map(m => m.cafeId), Number(nuevoComponente)]
    setFormData(prev => ({ ...prev, mezcla: recalcularMezcla(ids) }))
    setNuevoComponente('')
    setErrors(prev => ({ ...prev, mezcla: '' }))
  }

  const quitarComponente = (cafeId) => {
    const ids = formData.mezcla.filter(m => m.cafeId !== Number(cafeId)).map(m => m.cafeId)
    setFormData(prev => ({
      ...prev,
      mezcla: ids.length === 0 ? [] : recalcularMezcla(ids),
    }))
  }

  const ajustarPorcentaje = (cafeId, porcentaje) => {
    const valor = Math.min(100, Math.max(0, Number(porcentaje) || 0))
    setFormData(prev => ({
      ...prev,
      mezcla: prev.mezcla.map(m => (m.cafeId === Number(cafeId) ? { ...m, porcentaje: valor } : m)),
    }))
  }

  const validate = () => {
    const newErrors = {}
    if (!formData.precioKg || parseFloat(formData.precioKg) <= 0) {
      newErrors.precioKg = 'El precio por kilo debe ser mayor a 0'
    }

    if (formData.tipoProducto === 'simple') {
      if (!formData.variedad.trim()) newErrors.variedad = 'La variedad es obligatoria'
      if (!formData.pais.trim()) newErrors.pais = 'El país es obligatorio'
      if (!formData.region.trim()) newErrors.region = 'La región es obligatoria'
    } else {
      if (!formData.nombre.trim()) newErrors.nombre = 'El nombre del blend es obligatorio'
      if (formData.mezcla.length < 2) {
        newErrors.mezcla = 'El blend debe combinar al menos 2 cafés simples'
      } else if (totalPorcentaje !== 100) {
        newErrors.mezcla = `Los porcentajes deben sumar 100% (actual: ${totalPorcentaje}%)`
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    setApiError(null)
    
    try {
      const precioKg = parseFloat(formData.precioKg)

      const data = formData.tipoProducto === 'simple'
        ? {
            tipoProducto: 'simple',
            variedad: formData.variedad.trim(),
            pais: formData.pais.trim(),
            region: formData.region.trim(),
            organico: formData.organico,
            precioKg,
            nombre: '',
            descripcion: '',
            mezcla: [],
          }
        : {
            tipoProducto: 'blend',
            nombre: formData.nombre.trim(),
            descripcion: formData.descripcion.trim(),
            precioKg,
            mezcla: formData.mezcla.map(m => ({ cafeId: m.cafeId, porcentaje: Number(m.porcentaje) })),
            variedad: '',
            pais: '',
            region: '',
            organico: false,
          }

      await onSubmit(data, initialData?.id)
    } catch (err) {
      setApiError(err.message || 'Error al guardar el café')
    } finally {
      setSubmitting(false)
    }
  }

  const sugerido = (cafeId) => {
    const seleccionados = mezclaSeleccionada.map(m => m.cafe)
    const sugerencia = sugerirPorcentajes(seleccionados).find(m => m.cafeId === cafeId)
    return sugerencia?.porcentaje ?? 0
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar café' : 'Nuevo café'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear'}
      loading={submitting}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {apiError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
            <p className="text-sm text-red-700 dark:text-red-300">{apiError}</p>
          </div>
        )}
        <div className="rounded-xl border border-coffee-500/20 bg-coffee-500/5 p-4">
          <SegmentedToggle
            value={formData.tipoProducto}
            onChange={handleTipoProducto}
            options={TIPOS_CAFE}
            label="Tipo de café"
          />

          {formData.tipoProducto === 'simple' ? (
            <div className="mt-4 space-y-3">
              <Input
                label="Variedad *"
                name="variedad"
                value={formData.variedad}
                onChange={handleChange}
                placeholder="Ej: Arábica Bourbon"
                error={errors.variedad}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="País *"
                  name="pais"
                  value={formData.pais}
                  onChange={handleChange}
                  placeholder="Ej: Colombia"
                  error={errors.pais}
                />
                <Input
                  label="Región *"
                  name="region"
                  value={formData.region}
                  onChange={handleChange}
                  placeholder="Ej: Huila"
                  error={errors.region}
                />
              </div>

              <div className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2.5">
                <div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">¿Es orgánico?</p>
                  <p className="text-xs text-[var(--color-text-muted)]">Certificación orgánica del café</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={formData.organico}
                  aria-label="Café orgánico"
                  onClick={() => setFormData(prev => ({ ...prev, organico: !prev.organico }))}
                  className={`relative h-6 w-11 flex-shrink-0 rounded-full transition-colors duration-150 ${formData.organico ? 'bg-coffee-500' : 'bg-[var(--color-border)]'}`}
                >
                  <span
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-150 ${formData.organico ? 'translate-x-5' : 'translate-x-0.5'}`}
                  />
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              <Input
                label="Nombre *"
                name="nombre"
                value={formData.nombre}
                onChange={handleChange}
                placeholder="Ej: Blend Casa"
                error={errors.nombre}
              />
              <Input
                label="Descripción"
                name="descripcion"
                value={formData.descripcion}
                onChange={handleChange}
                placeholder="Perfil de sabor, uso recomendado..."
                multiline
                rows={2}
              />

              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">Mezcla de cafés *</p>
                    <p className="text-xs text-[var(--color-text-muted)]">Porcentajes sugeridos según kilos verdes disponibles</p>
                  </div>
                  {formData.mezcla.length > 0 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setFormData(prev => ({ ...prev, mezcla: recalcularMezcla(prev.mezcla.map(m => m.cafeId)) }))}
                    >
                      Recalcular
                    </Button>
                  )}
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <div className="flex-1">
                    <Select
                      value={nuevoComponente}
                      onChange={e => setNuevoComponente(e.target.value)}
                      options={simples
                        .filter(cafe => !formData.mezcla.some(m => m.cafeId === cafe.id))
                        .map(cafe => ({
                          value: cafe.id,
                          label: `${nombreCafe(cafe)} — ${origenCafe(cafe)} (${formatearKilos(kilosCafe(cafe, 'verde'))} verde)`,
                        }))}
                      placeholder="Seleccionar café simple"
                    />
                  </div>
                  <Button type="button" variant="secondary" onClick={agregarComponente} disabled={!nuevoComponente}>
                    Agregar café
                  </Button>
                </div>

                {formData.mezcla.length > 0 && (
                  <div className="mt-3 space-y-3">
                    {mezclaSeleccionada.map(({ cafeId, porcentaje, cafe }) => (
                      <div key={cafeId} className="rounded-lg bg-[var(--color-bg-tertiary)] p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium text-[var(--color-text-primary)]">{nombreCafe(cafe)}</p>
                            <p className="text-xs text-[var(--color-text-muted)]">
                              {origenCafe(cafe)} · {formatearKilos(kilosCafe(cafe, 'verde'))} verdes · sugerido {sugerido(cafeId)}%
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-12 text-right font-mono text-sm tabular-nums text-[var(--color-text-primary)]">{porcentaje}%</span>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="p-1"
                              onClick={() => quitarComponente(cafeId)}
                              aria-label={`Quitar ${nombreCafe(cafe)} del blend`}
                            >
                              <svg className="h-4 w-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </Button>
                          </div>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={porcentaje}
                          onChange={e => ajustarPorcentaje(cafeId, e.target.value)}
                          aria-label={`Porcentaje de ${nombreCafe(cafe)}`}
                          className="mt-2 h-2 w-full cursor-pointer appearance-none rounded-full bg-[var(--color-border)] accent-coffee-500"
                        />
                      </div>
                    ))}

                    <p className={`text-sm font-medium ${totalPorcentaje === 100 ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                      Total de la mezcla: {totalPorcentaje}%
                      {totalPorcentaje !== 100 && ` (${totalPorcentaje < 100 ? `faltan ${100 - totalPorcentaje}` : `sobran ${totalPorcentaje - 100}`} puntos)`}
                    </p>
                  </div>
                )}

                {errors.mezcla && <p className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">{errors.mezcla}</p>}
              </div>
            </div>
          )}

          <div className="mt-3">
            <Input
              label="Precio por kilo *"
              name="precioKg"
              type="number"
              step="0.01"
              min="0.01"
              value={formData.precioKg}
              onChange={handleChange}
              placeholder="0.00"
              error={errors.precioKg}
            />
          </div>
        </div>

        <p className="text-xs text-[var(--color-text-muted)]">Los campos marcados con * son obligatorios. El stock se carga después mediante lotes.</p>
      </form>
    </Modal>
  )
}
