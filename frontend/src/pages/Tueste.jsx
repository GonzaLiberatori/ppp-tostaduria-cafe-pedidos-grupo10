import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Coffee, Flame, History, RefreshCw, Scale } from 'lucide-react'
import api from '../services/api'
import { useToast } from '../hooks/useToast.jsx'
import { formatearFechaHora } from '../utils/formatters'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'

const FORM_INICIAL = {
  tipoDeCafeId: '',
  gramosVerde: '',
  gramosTostado: '',
}

function formatearGramos(gramos) {
  return `${new Intl.NumberFormat('es-AR').format(gramos)} g`
}

function etiquetaTipo(tipo) {
  if (!tipo) return 'Sin tipo'
  return `${tipo.variedad} · ${tipo.region}, ${tipo.pais}`
}

function TarjetaResumen({ titulo, valor, detalle, icono: Icono, color }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-[var(--color-text-muted)]">{titulo}</p>
          <p className="mt-1 text-2xl font-bold text-[var(--color-text-primary)] tabular-nums">
            {valor}
          </p>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">{detalle}</p>
        </div>
        <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl ${color}`}>
          <Icono className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}

export default function Tueste() {
  const { success, error: mostrarError } = useToast()

  const [tipos, setTipos] = useState([])
  const [tuestes, setTuestes] = useState([])
  const [lotes, setLotes] = useState([])
  const [cargando, setCargando] = useState(true)
  const [cargandoLotes, setCargandoLotes] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')
  const [errores, setErrores] = useState({})
  const [formulario, setFormulario] = useState(FORM_INICIAL)

  const cargarDatos = useCallback(async () => {
    setCargando(true)
    setErrorGeneral('')

    try {
      const [tiposDeCafe, ordenes] = await Promise.all([
        api.getTiposDeCafe(),
        api.getTuestes(),
      ])
      setTipos(tiposDeCafe)
      setTuestes(ordenes)
    } catch (error) {
      setErrorGeneral(error.message)
      mostrarError(error.message)
    } finally {
      setCargando(false)
    }
  }, [mostrarError])

  useEffect(() => {
    cargarDatos()
  }, [cargarDatos])

  useEffect(() => {
    if (!formulario.tipoDeCafeId) {
      setLotes([])
      return undefined
    }

    let vigente = true
    setCargandoLotes(true)

    api
      .getLotes({ tipo_de_cafe_id: formulario.tipoDeCafeId })
      .then((datos) => {
        if (vigente) setLotes(datos)
      })
      .catch((error) => {
        if (vigente) {
          setLotes([])
          mostrarError(error.message)
        }
      })
      .finally(() => {
        if (vigente) setCargandoLotes(false)
      })

    return () => {
      vigente = false
    }
  }, [formulario.tipoDeCafeId, mostrarError])

  const tipoPorId = useMemo(
    () => new Map(tipos.map((tipo) => [tipo.id, etiquetaTipo(tipo)])),
    [tipos]
  )

  const opcionesTipo = useMemo(
    () =>
      tipos.map((tipo) => ({
        value: String(tipo.id),
        label: etiquetaTipo(tipo),
      })),
    [tipos]
  )

  const lotesVerdes = useMemo(
    () =>
      lotes.filter(
        (lote) =>
          lote.tipo === 'VERDE' &&
          lote.estado === 'ABIERTO' &&
          Number(lote.kg_disponibles) > 0
      ),
    [lotes]
  )

  const stockVerdeGramos = useMemo(
    () =>
      Math.round(
        lotesVerdes.reduce(
          (total, lote) => total + Number(lote.kg_disponibles) * 1000,
          0
        )
      ),
    [lotesVerdes]
  )

  const gramosVerde = Number(formulario.gramosVerde) || 0
  const gramosTostado = Number(formulario.gramosTostado) || 0
  const mermaGramos = gramosVerde - gramosTostado
  const mermaPorcentaje =
    gramosVerde > 0 ? (mermaGramos / gramosVerde) * 100 : 0
  const stockRestante = stockVerdeGramos - gramosVerde

  const mermaPromedio = useMemo(() => {
    if (tuestes.length === 0) return null
    const total = tuestes.reduce(
      (suma, orden) => suma + Number(orden.merma_porcentaje),
      0
    )
    return total / tuestes.length
  }, [tuestes])

  const ultimoTueste = tuestes[0]

  const actualizarCampo = (campo, valor) => {
    setFormulario((anterior) => ({ ...anterior, [campo]: valor }))
    setErrores((anteriores) => ({ ...anteriores, [campo]: undefined }))
  }

  const validar = () => {
    const nuevosErrores = {}

    if (!formulario.tipoDeCafeId) {
      nuevosErrores.tipoDeCafeId = 'Seleccione el tipo de café a tostar.'
    }

    if (!Number.isInteger(gramosVerde) || gramosVerde <= 0) {
      nuevosErrores.gramosVerde = 'Ingrese gramos enteros mayores a cero.'
    } else if (
      formulario.tipoDeCafeId &&
      !cargandoLotes &&
      gramosVerde > stockVerdeGramos
    ) {
      nuevosErrores.gramosVerde = `Stock insuficiente: hay ${formatearGramos(stockVerdeGramos)}.`
    }

    if (!Number.isInteger(gramosTostado) || gramosTostado <= 0) {
      nuevosErrores.gramosTostado = 'Ingrese gramos enteros mayores a cero.'
    } else if (gramosTostado > gramosVerde) {
      nuevosErrores.gramosTostado =
        'Los gramos tostados no pueden superar a los verdes.'
    }

    setErrores(nuevosErrores)
    return Object.keys(nuevosErrores).length === 0
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!validar()) return

    const tipoDeCafeId = Number(formulario.tipoDeCafeId)
    setEnviando(true)
    setErrorGeneral('')

    try {
      const resultado = await api.createTueste({
        gramos_verde: gramosVerde,
        gramos_tostado: gramosTostado,
        tipo_de_cafe_id: tipoDeCafeId,
      })

      success(
        `Tueste registrado: ${formatearGramos(resultado.gramos_gastados)} verdes → ${formatearGramos(resultado.gramos_obtenidos)} tostados.`
      )
      setFormulario((anterior) => ({
        ...anterior,
        gramosVerde: '',
        gramosTostado: '',
      }))
      setTuestes((anteriores) => [resultado, ...anteriores])

      try {
        const lotesActualizados = await api.getLotes({
          tipo_de_cafe_id: tipoDeCafeId,
        })
        setLotes(lotesActualizados)
      } catch (error) {
        mostrarError(
          `El tueste se guardó, pero no se pudo refrescar el stock: ${error.message}`
        )
      }
    } catch (error) {
      setErrorGeneral(error.message)
      mostrarError(error.message)
    } finally {
      setEnviando(false)
    }
  }

  const columnas = [
    {
      key: 'fecha_tueste',
      header: 'Fecha',
      render: (valor) => formatearFechaHora(valor),
    },
    {
      key: 'tipo_de_cafe_id',
      header: 'Tipo de café',
      render: (valor) =>
        valor ? tipoPorId.get(valor) || `Tipo #${valor}` : 'Sin tipo',
    },
    {
      key: 'gramos_gastados',
      header: 'Verde',
      render: (valor) => formatearGramos(valor),
    },
    {
      key: 'gramos_obtenidos',
      header: 'Tostado',
      render: (valor) => formatearGramos(valor),
    },
    {
      key: 'merma_gramos',
      header: 'Merma',
      render: (valor, fila) =>
        `${formatearGramos(valor)} (${Number(fila.merma_porcentaje).toFixed(2)} %)`,
    },
    {
      key: 'lote_tostado_id',
      header: 'Lote tostado',
      render: (valor) => (valor ? `#${valor}` : '—'),
    },
    {
      key: 'consumos',
      header: 'Lotes verdes consumidos',
      render: (consumos) =>
        consumos?.length
          ? consumos
              .map(
                (consumo) =>
                  `#${consumo.lote_id} (${formatearGramos(consumo.gramos_consumidos)})`
              )
              .join(', ')
          : '—',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Tueste
          </h1>
          <p className="text-[var(--color-text-muted)]">
            Convierte café verde en café tostado descontando los lotes en orden FIFO.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={cargarDatos}
          disabled={cargando}
          loading={cargando}
        >
          <RefreshCw className="h-4 w-4" />
          Actualizar
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <TarjetaResumen
          titulo="Verde disponible"
          valor={
            formulario.tipoDeCafeId
              ? cargandoLotes
                ? 'Calculando...'
                : formatearGramos(stockVerdeGramos)
              : '—'
          }
          detalle={
            formulario.tipoDeCafeId
              ? 'Stock abierto del tipo seleccionado'
              : 'Seleccione un tipo de café'
          }
          icono={Coffee}
          color="bg-green-500/10 text-green-600 dark:text-green-400"
        />
        <TarjetaResumen
          titulo="Órdenes registradas"
          valor={tuestes.length}
          detalle="Tuestes cargados en el historial"
          icono={History}
          color="bg-blue-500/10 text-blue-600 dark:text-blue-400"
        />
        <TarjetaResumen
          titulo="Merma promedio"
          valor={mermaPromedio === null ? '—' : `${mermaPromedio.toFixed(2)} %`}
          detalle="Sobre el café verde procesado"
          icono={Scale}
          color="bg-amber-500/10 text-amber-600 dark:text-amber-400"
        />
        <TarjetaResumen
          titulo="Último tueste"
          valor={ultimoTueste ? formatearGramos(ultimoTueste.gramos_obtenidos) : '—'}
          detalle={ultimoTueste ? formatearFechaHora(ultimoTueste.fecha_tueste) : 'Sin registros'}
          icono={Flame}
          color="bg-coffee-500/10 text-coffee-600 dark:text-coffee-400"
        />
      </div>

      {errorGeneral && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{errorGeneral}</span>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="card-header">
            <h2 className="font-semibold text-[var(--color-text-primary)]">
              Registrar un tueste
            </h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Informe los gramos que entran verdes y los gramos que salen tostados.
            </p>
          </div>
          <form className="card-body" onSubmit={handleSubmit}>
            <Select
              label="Tipo de café"
              options={opcionesTipo}
              placeholder={
                tipos.length === 0
                  ? 'No hay tipos de café cargados'
                  : 'Seleccionar tipo de café...'
              }
              value={formulario.tipoDeCafeId}
              onChange={(event) =>
                actualizarCampo('tipoDeCafeId', event.target.value)
              }
              error={errores.tipoDeCafeId}
              help="Solo se descuenta café verde del tipo elegido."
              disabled={cargando || tipos.length === 0}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Café verde (g)"
                type="number"
                min="1"
                step="1"
                inputMode="numeric"
                placeholder="Ej. 5000"
                value={formulario.gramosVerde}
                onChange={(event) =>
                  actualizarCampo('gramosVerde', event.target.value)
                }
                error={errores.gramosVerde}
                help="Gramos de materia prima que entran al tostador."
              />
              <Input
                label="Café tostado (g)"
                type="number"
                min="1"
                step="1"
                inputMode="numeric"
                placeholder="Ej. 4000"
                value={formulario.gramosTostado}
                onChange={(event) =>
                  actualizarCampo('gramosTostado', event.target.value)
                }
                error={errores.gramosTostado}
                help="Gramos obtenidos después del tueste."
              />
            </div>

            <div className="flex flex-col gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
              <span className="text-[var(--color-text-muted)]">
                Merma estimada:{' '}
                <span
                  className={`font-medium tabular-nums ${
                    mermaGramos < 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-[var(--color-text-primary)]'
                  }`}
                >
                  {formatearGramos(mermaGramos)} (
                  {mermaPorcentaje.toFixed(2)} %)
                </span>
              </span>
              <span className="text-[var(--color-text-muted)]">
                Stock restante:{' '}
                <span
                  className={`font-medium tabular-nums ${
                    stockRestante < 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-[var(--color-text-primary)]'
                  }`}
                >
                  {formulario.tipoDeCafeId && !cargandoLotes
                    ? stockRestante < 0
                      ? 'Insuficiente'
                      : formatearGramos(stockRestante)
                    : '—'}
                </span>
              </span>
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                loading={enviando}
                disabled={cargando || tipos.length === 0}
              >
                <Flame className="h-4 w-4" />
                Registrar tueste
              </Button>
            </div>
          </form>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-[var(--color-text-primary)]">
              Resumen del proceso
            </h2>
          </div>
          <div className="card-body">
            <dl className="space-y-4 text-sm">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[var(--color-text-muted)]">Tipo</dt>
                <dd className="text-right font-medium text-[var(--color-text-primary)]">
                  {formulario.tipoDeCafeId
                    ? tipoPorId.get(Number(formulario.tipoDeCafeId)) ||
                      'Tipo seleccionado'
                    : '—'}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[var(--color-text-muted)]">Stock verde</dt>
                <dd className="font-medium text-[var(--color-text-primary)] tabular-nums">
                  {formulario.tipoDeCafeId && !cargandoLotes
                    ? formatearGramos(stockVerdeGramos)
                    : '—'}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[var(--color-text-muted)]">Entrada</dt>
                <dd className="font-medium text-[var(--color-text-primary)] tabular-nums">
                  {formatearGramos(gramosVerde)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[var(--color-text-muted)]">Salida</dt>
                <dd className="font-medium text-[var(--color-text-primary)] tabular-nums">
                  {formatearGramos(gramosTostado)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[var(--color-text-muted)]">Merma</dt>
                <dd
                  className={`font-medium tabular-nums ${
                    mermaGramos < 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-[var(--color-text-primary)]'
                  }`}
                >
                  {formatearGramos(mermaGramos)} ({mermaPorcentaje.toFixed(2)} %)
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4 border-t border-[var(--color-border)] pt-4">
                <dt className="text-[var(--color-text-muted)]">Lote tostado</dt>
                <dd className="text-right font-medium text-[var(--color-text-primary)]">
                  Se crea automáticamente
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex items-center justify-between gap-4">
          <div>
            <h2 className="font-semibold text-[var(--color-text-primary)]">
              Historial de tuestes
            </h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Cada orden deja trazabilidad del lote tostado y de los lotes verdes consumidos.
            </p>
          </div>
          <Badge variant="info">{tuestes.length}</Badge>
        </div>
        {cargando ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-coffee-500 border-t-transparent" />
          </div>
        ) : (
          <Table
            columns={columnas}
            data={tuestes}
            keyField="id"
            emptyMessage="Todavía no hay órdenes de tueste registradas."
          />
        )}
      </div>
    </div>
  )
}
