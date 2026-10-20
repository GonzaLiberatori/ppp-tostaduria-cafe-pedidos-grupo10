import { useState, useEffect } from 'react'
import { TIPOS_CLIENTE } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'

export default function ClienteForm({ isOpen, onClose, initialData, onSubmit }) {
  const [formData, setFormData] = useState({
    nombre: '',
    tipo: 'B2C',
    telefono: '',
    email: '',
    direccion: '',
    kilosComprados: '',
    tieneDeuda: false,
    montoDeuda: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (initialData) {
      setFormData({
        nombre: initialData.nombre || '',
        tipo: initialData.tipo || 'B2C',
        telefono: initialData.telefono || '',
        email: initialData.email || '',
        direccion: initialData.direccion || '',
        kilosComprados: initialData.kilosComprados || '',
        tieneDeuda: initialData.tieneDeuda || false,
        montoDeuda: initialData.montoDeuda || '',
      })
      setErrors({})
    } else {
      setFormData({
        nombre: '',
        tipo: 'B2C',
        telefono: '',
        email: '',
        direccion: '',
        kilosComprados: '',
        tieneDeuda: false,
        montoDeuda: '',
      })
      setErrors({})
    }
  }, [initialData, isOpen])

  const validate = () => {
    const newErrors = {}
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es obligatorio'
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Email inválido'
    }
    if (formData.tieneDeuda && (!formData.montoDeuda || parseFloat(formData.montoDeuda) <= 0)) {
      newErrors.montoDeuda = 'El monto de deuda debe ser mayor a 0'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    
    setSubmitting(true)
    const data = {
      nombre: formData.nombre.trim(),
      tipo: formData.tipo,
      telefono: formData.telefono.trim(),
      email: formData.email.trim(),
      direccion: formData.direccion.trim(),
      kilosComprados: parseFloat(formData.kilosComprados) || 0,
      tieneDeuda: formData.tieneDeuda,
      montoDeuda: parseFloat(formData.montoDeuda) || 0,
    }
    onSubmit(data, initialData?.id)
    setSubmitting(false)
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar Cliente' : 'Nuevo Cliente'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear'}
      loading={submitting}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Nombre *"
          name="nombre"
          value={formData.nombre}
          onChange={handleChange}
          placeholder="Nombre completo o razón social"
          error={errors.nombre}
        />

        <div className="form-row">
          <Select
            label="Tipo de cliente"
            name="tipo"
            value={formData.tipo}
            onChange={handleChange}
            options={TIPOS_CLIENTE}
          />
          <div className="form-group flex items-end">
            <label className="flex items-center gap-2 cursor-pointer w-full">
              <input
                type="checkbox"
                name="tieneDeuda"
                checked={formData.tieneDeuda}
                onChange={handleChange}
                className="w-4 h-4 rounded border-[var(--color-border)] text-coffee-500 focus:ring-coffee-500"
              />
              <span className="text-sm text-[var(--color-text-secondary)]">Tiene deuda pendiente</span>
            </label>
          </div>
        </div>

        <div className="form-row">
          <Input
            label="Teléfono"
            name="telefono"
            type="tel"
            value={formData.telefono}
            onChange={handleChange}
            placeholder="+54 11 4567-8901"
          />
          <Input
            label="Email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="cliente@email.com"
            error={errors.email}
          />
        </div>

        <Input
          label="Dirección"
          name="direccion"
          value={formData.direccion}
          onChange={handleChange}
          placeholder="Dirección completa"
        />

        <div className="form-row">
          <Input
            label="Kilos comprados totales"
            name="kilosComprados"
            type="number"
            step="0.01"
            min="0"
            value={formData.kilosComprados}
            onChange={handleChange}
            placeholder="0.00"
          />
          {formData.tieneDeuda && (
            <Input
              label="Monto de deuda"
              name="montoDeuda"
              type="number"
              step="0.01"
              min="0.01"
              value={formData.montoDeuda}
              onChange={handleChange}
              placeholder="0.00"
              error={errors.montoDeuda}
            />
          )}
        </div>
      </form>
    </Modal>
  )
}