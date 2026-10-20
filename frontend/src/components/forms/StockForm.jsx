import { useState, useEffect } from 'react'
import { TIPOS_STOCK } from '../../data/constants'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Modal from '../ui/Modal'
import { formatearMoneda } from '../../utils/formatters'

export default function StockForm({ isOpen, onClose, initialData, onSubmit }) {
  const [formData, setFormData] = useState({
    tipo: 'verde',
    variedad: '',
    origen: '',
    precioKg: '',
    lotePrincipal: '',
    // Para nueva bolsa inicial
    bolsaInicialEstado: 'cerrada',
    bolsaInicialKilos: '',
    bolsaInicialLoteRef: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [agregarMasBolsas, setAgregarMasBolsas] = useState(false)
  const [bolsasAdicionales, setBolsasAdicionales] = useState([])

  useEffect(() => {
    if (initialData) {
      setFormData({
        tipo: initialData.tipo,
        variedad: initialData.variedad || '',
        origen: initialData.origen || '',
        precioKg: initialData.precioKg || '',
        lotePrincipal: initialData.lotePrincipal || '',
        bolsaInicialEstado: 'cerrada',
        bolsaInicialKilos: '',
        bolsaInicialLoteRef: '',
      })
      setBolsasAdicionales([])
      setAgregarMasBolsas(false)
      setErrors({})
    } else {
      setFormData({
        tipo: 'verde',
        variedad: '',
        origen: '',
        precioKg: '',
        lotePrincipal: '',
        bolsaInicialEstado: 'cerrada',
        bolsaInicialKilos: '',
        bolsaInicialLoteRef: '',
      })
      setBolsasAdicionales([])
      setAgregarMasBolsas(false)
      setErrors({})
    }
  }, [initialData, isOpen])

  const validate = () => {
    const newErrors = {}
    if (!formData.variedad.trim()) newErrors.variedad = 'La variedad es obligatoria'
    if (!formData.origen.trim()) newErrors.origen = 'El origen es obligatorio'
    if (!formData.precioKg || parseFloat(formData.precioKg) <= 0) newErrors.precioKg = 'El precio por kg debe ser mayor a 0'
    if (!formData.lotePrincipal.trim()) newErrors.lotePrincipal = 'El lote principal es obligatorio'
    if (!formData.bolsaInicialKilos || parseFloat(formData.bolsaInicialKilos) <= 0) {
      newErrors.bolsaInicialKilos = 'Los kilos de la bolsa inicial deben ser mayor a 0'
    }
    if (!formData.bolsaInicialLoteRef.trim()) newErrors.bolsaInicialLoteRef = 'La referencia de lote es obligatoria'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    
    setSubmitting(true)
    const bolsaInicial = {
      estado: formData.bolsaInicialEstado,
      kilos: parseFloat(formData.bolsaInicialKilos),
      loteRef: formData.bolsaInicialLoteRef.trim().toUpperCase(),
    }
    const bolsas = [bolsaInicial, ...bolsasAdicionales.filter(b => b.kilos > 0)]
    
    const data = {
      tipo: formData.tipo,
      variedad: formData.variedad.trim(),
      origen: formData.origen.trim(),
      precioKg: parseFloat(formData.precioKg),
      lotePrincipal: formData.lotePrincipal.trim().toUpperCase(),
      bolsas,
    }
    onSubmit(data, initialData?.id)
    setSubmitting(false)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const handleBolsaChange = (index, field, value) => {
    setBolsasAdicionales(prev => prev.map((b, i) => i === index ? { ...b, [field]: value } : b))
  }

  const addBolsaAdicional = () => {
    setBolsasAdicionales(prev => [...prev, { estado: 'cerrada', kilos: '', loteRef: '' }])
  }

  const removeBolsaAdicional = (index) => {
    setBolsasAdicionales(prev => prev.filter((_, i) => i !== index))
  }

  const totalKilos = [
    parseFloat(formData.bolsaInicialKilos) || 0,
    ...bolsasAdicionales.map(b => parseFloat(b.kilos) || 0)
  ].reduce((a, b) => a + b, 0)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Editar Café' : 'Nuevo Café'}
      confirmAction={handleSubmit}
      confirmText={initialData ? 'Actualizar' : 'Crear'}
      loading={submitting}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="bg-coffee-500/5 border border-coffee-500/20 rounded-xl p-4">
          <h3 className="font-medium text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-coffee-500"></span>
            Información del Café
          </h3>
          <div className="form-row">
            <Select
              label="Tipo"
              name="tipo"
              value={formData.tipo}
              onChange={handleChange}
              options={TIPOS_STOCK}
              error={errors.tipo}
            />
            <Input
              label="Lote Principal"
              name="lotePrincipal"
              value={formData.lotePrincipal}
              onChange={handleChange}
              placeholder="Ej: LOTE-2026-001"
              error={errors.lotePrincipal}
            />
          </div>

          <Input
            label="Variedad"
            name="variedad"
            value={formData.variedad}
            onChange={handleChange}
            placeholder="Ej: Arábica Bourbon"
            error={errors.variedad}
          />

          <Input
            label="Origen"
            name="origen"
            value={formData.origen}
            onChange={handleChange}
            placeholder="Ej: Colombia - Huila"
            error={errors.origen}
          />

          <Input
            label="Precio por Kg"
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

        <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-[var(--color-text-primary)] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Bolsas Iniciales
            </h3>
            {!agregarMasBolsas && !initialData && (
              <Button type="button" variant="ghost" size="sm" onClick={() => setAgregarMasBolsas(true)}>
                + Agregar más bolsas
              </Button>
            )}
          </div>

          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <Select
                label="Estado"
                name="bolsaInicialEstado"
                value={formData.bolsaInicialEstado}
                onChange={handleChange}
                options={[
                  { value: 'cerrada', label: 'Cerrada (sellada)' },
                  { value: 'abierta', label: 'Abierta (en uso)' },
                ]}
              />
              <Input
                label="Kilos"
                name="bolsaInicialKilos"
                type="number"
                step="0.01"
                min="0.01"
                value={formData.bolsaInicialKilos}
                onChange={handleChange}
                placeholder="0.00"
                error={errors.bolsaInicialKilos}
              />
              <Input
                label="Ref. Lote"
                name="bolsaInicialLoteRef"
                value={formData.bolsaInicialLoteRef}
                onChange={handleChange}
                placeholder="Ej: LOTE-2026-001-A"
                error={errors.bolsaInicialLoteRef}
              />
            </div>

            {agregarMasBolsas && bolsasAdicionales.map((bolsa, index) => (
              <div key={index} className="grid gap-3 sm:grid-cols-3 items-end p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
                <Select
                  value={bolsa.estado}
                  onChange={e => handleBolsaChange(index, 'estado', e.target.value)}
                  options={[
                    { value: 'cerrada', label: 'Cerrada' },
                    { value: 'abierta', label: 'Abierta' },
                  ]}
                  label=""
                />
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={bolsa.kilos}
                  onChange={e => handleBolsaChange(index, 'kilos', e.target.value)}
                  placeholder="Kilos"
                  label=""
                />
                <div className="flex gap-2">
                  <Input
                    value={bolsa.loteRef}
                    onChange={e => handleBolsaChange(index, 'loteRef', e.target.value)}
                    placeholder="Ref. Lote"
                    label=""
                  />
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeBolsaAdicional(index)} aria-label="Eliminar bolsa">
                    <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  </Button>
                </div>
              </div>
            ))}

            {!agregarMasBolsas && !initialData && (
              <Button type="button" variant="secondary" size="sm" onClick={addBolsaAdicional} className="w-full sm:w-auto">
                + Agregar primera bolsa adicional
              </Button>
            )}
          </div>
        </div>

        {(totalKilos > 0 || formData.precioKg) && (
          <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Total kilos: <strong className="text-[var(--color-text-primary)]">{totalKilos.toFixed(2)} kg</strong>
              {formData.precioKg && (
                <> · Valor estimado: <strong className="text-[var(--color-text-primary)]">{formatearMoneda(totalKilos * parseFloat(formData.precioKg))}</strong></>
              )}
            </p>
          </div>
        )}
      </form>
    </Modal>
  )
}