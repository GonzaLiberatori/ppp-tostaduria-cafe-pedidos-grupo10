import { useState, useEffect } from 'react'
import { CATEGORIAS_GASTO } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'

export default function GastoForm({ isOpen, onClose, initialData, onSubmit }) {
  const [formData, setFormData] = useState({
    categoria: 'Producción',
    descripcion: '',
    monto: '',
    fecha: new Date().toISOString().split('T')[0],
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (initialData) {
      setFormData({
        categoria: initialData.categoria || 'Producción',
        descripcion: initialData.descripcion || '',
        monto: initialData.monto || '',
        fecha: initialData.fecha ? initialData.fecha.split('T')[0] : new Date().toISOString().split('T')[0],
      })
      setErrors({})
    } else {
      setFormData({
        categoria: 'Producción',
        descripcion: '',
        monto: '',
        fecha: new Date().toISOString().split('T')[0],
      })
      setErrors({})
    }
  }, [initialData, isOpen])

  const validate = () => {
    const newErrors = {}
    if (!formData.descripcion.trim()) newErrors.descripcion = 'La descripción es obligatoria'
    if (!formData.monto || parseFloat(formData.monto) <= 0) newErrors.monto = 'El monto debe ser mayor a 0'
    if (!formData.fecha) newErrors.fecha = 'La fecha es obligatoria'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    
    setSubmitting(true)
    const data = {
      categoria: formData.categoria,
      descripcion: formData.descripcion.trim(),
      monto: parseFloat(formData.monto),
      fecha: new Date(formData.fecha).toISOString(),
    }
    onSubmit(data, initialData?.id)
    setSubmitting(false)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar Gasto' : 'Nuevo Gasto'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear'}
      loading={submitting}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select
          label="Categoría"
          name="categoria"
          value={formData.categoria}
          onChange={handleChange}
          options={CATEGORIAS_GASTO}
        />

        <Input
          label="Descripción *"
          name="descripcion"
          value={formData.descripcion}
          onChange={handleChange}
          placeholder="Ej: Compra café verde, Alquiler, Publicidad..."
          error={errors.descripcion}
        />

        <div className="form-row">
          <Input
            label="Monto *"
            name="monto"
            type="number"
            step="0.01"
            min="0.01"
            value={formData.monto}
            onChange={handleChange}
            placeholder="0.00"
            error={errors.monto}
          />
          <Input
            label="Fecha *"
            name="fecha"
            type="date"
            value={formData.fecha}
            onChange={handleChange}
            error={errors.fecha}
          />
        </div>
      </form>
    </Modal>
  )
}