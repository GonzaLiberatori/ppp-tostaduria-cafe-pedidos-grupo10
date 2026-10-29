# Proposal

## Why

`Lote` es la entidad que materializa la trazabilidad de la producción: tiene modelo y contrato Pydantic completos, pero `crud.py`, `services.py` y `router.py` no lo conocen. Además es el último bloque del módulo de inventario que falta por cerrar, después de `TipoDeCafe` y `Blend`. Con esto el CRUD básico de inventario queda completo.

Este cambio reutiliza los principios ya establecidos: identificador por ruta, existencia comprobada en `services`, tres capas separadas y las mismas excepciones de dominio mapeadas a códigos HTTP.

## What Changes

### Schemas (`schemas.py`) — cuatro cambios

La revisión de `schemas.py` confirmó que varias reglas ya están implementadas: `tipo` con `LoteTipo`, `estado` con `LoteEstado`, `fecha_vencimiento`, `ubicacion_fisica` no vacía y ≤ 50, `observaciones` nullable, y `LoteUpdate` rechazando `tipo`, `tipo_de_cafe_id`, `blend_id` y `orden_tueste_id` por no declararlos con `extra="forbid"`. Las cuatro reglas pedidas quedan así, y solo tres necesitan tocar el archivo:

| Regla | Estado actual | Acción |
|---|---|---|
| `humedad` entre 0 y 100 | `HumedadPorcentaje` es `ge=0`, **sin cota superior** | agregar `le=100` |
| `kg_reales >= 0` | usa `Kilos`, que es `ge=0` | **sin cambio: ya cumple** |
| **`kg_disponibles` no se envía en el alta** | está en `LoteCreate` | **quitarlo** |
| Origen único y `orden_tueste_id` según el tipo | sin validar | dos `model_validator` en `LoteCreate` |

`Kilos` no se toca: `kg_reales` y `kg_disponibles` piden exactamente la misma cota (`>= 0`), así que comparten el alias sin ningún conflicto. Un lote puede tener 0 kilos reales y 0 disponibles, y ambos casos pasan la validación tal como está escrita hoy.

Las dos reglas cruzadas van en el schema porque son relaciones entre dos atributos del **mismo** payload y no consultan nada — lo mismo que resuelve un `model_validator`. Lo que sí necesita la base vive en `services`.

### Capa de datos (`crud.py`)

Consultas de lote: obtener por id, crear, aplicar cambios y eliminar. No hay bloqueos de borrado: verifiqué que **ninguna tabla tiene FK hacia `lote`**, así que no se agrega ninguna entrada a `REFERENCIAS_PROHIBIDAS`.

### Capa de negocio (`services.py`)

- Excepciones nuevas: `LoteNoEncontrado` y `OrigenDeLoteNoEncontrado`.
- En el alta:
  - el origen elegido (sea `tipo_de_cafe_id` o `blend_id`) **corresponde a un registro real** de su tabla;
  - `kg_disponibles` se **copia de `kg_reales`**.

Lo que **no** va acá porque no necesita la base — vive en `model_validator` de `LoteCreate`:

- exactamente uno de `tipo_de_cafe_id` / `blend_id`;
- `orden_tueste_id` obligatorio si `tipo = TOSTADO`, rechazado si `tipo = VERDE`.

### Capa HTTP (`router.py`)

`POST /lotes` → 201, `GET|PATCH|DELETE /lotes/{id}` → 200/204.

### Validaciones por operación

| Operación | Validación | Dónde |
|---|---|---|
| **Create** | `tipo` VERDE/TOSTADO, `estado` ABIERTO/CERRADO, `humedad` 0–100, `kg_reales >= 0`, sin `kg_disponibles`, sin atributos desconocidos | Pydantic → `422` |
| **Create** | exactamente uno entre `tipo_de_cafe_id` y `blend_id` | Pydantic → `422` |
| **Create** | el origen elegido corresponde a un registro real | `services` → `404` |
| **Create** | `orden_tueste_id` según `tipo` | Pydantic → `422` |
| **Read** | el `id` de la ruta debe existir | `services` → `404` |
| **Update** | el `id` debe existir; sin `tipo` ni las tres FK (ni se declaran); validez de cada atributo enviado con valor | `services` → `404` · Pydantic → `422` |
| **Delete** | el `id` debe existir; solo borra el lote | `services` → `404` |

## Decisión explícita de alcance: `orden_tueste`

Opción 2 del equipo: **el CRUD avanza y la comprobación referencial queda pendiente**.

Lo que **sí** se implementa en este cambio (no necesita la tabla): que `tipo = VERDE` rechace `orden_tueste_id` y que `tipo = TOSTADO` lo exija.

Lo que **queda pendiente**: comprobar que ese `orden_tueste_id` corresponde a un registro real de la tabla `orden_tueste`. La tabla no existe — `produccion/models.py` está en 0 bytes — y su FK la retiró `add-tipo-de-cafe-crud` porque rompía `create_all()`. La deuda queda escrita en `design.md`.

Fuera de alcance también:

- Los tres endpoints puntuales de lote (`LoteKgDisponiblesUpdate`, `LoteKgRealesUpdate`, `LoteEstadoUpdate`): sus schemas existen desde `add-inventario-schemas` pero este cambio solo cubre las cuatro operaciones CRUD.
- Infraestructura de arranque (`config.py`, `database.py`, `main.py`).
- La definición de `detalle_pedido` y de `OrdenTueste`.

## Capabilities

### New Capabilities

- `inventario-lote`: alta, consulta, edición y baja de lotes a través de la API, con la validación de sus atributos, la regla de origen único, la derivación de kilos disponibles y los códigos de estado que las rutas exponen.

### Modified Capabilities

- `inventario-schemas`: el requirement `La creación solo exige los atributos no nulos` no contempla que un atributo **derivado** se rechace aunque el modelo no admita nulo. Se agrega esa excepción con un escenario sobre `kg_disponibles`.

## Impact

- **Modificados:** `inventario/schemas.py` (3 cambios), `inventario/crud.py` (4 funciones), `inventario/services.py` (2 excepciones + 4 operaciones), `inventario/router.py` (de 8 a 12 rutas).
- **Tests nuevos:** `tests/modules/inventario/test_services_lote.py` y `test_router_lote.py`.
- **Tests a adaptar:** `test_schemas_lote.py` — `PAYLOAD_BASE` deja de llevar `kg_disponibles`, el assert de `kg_disponibles` pasa a comparar contra `kg_reales`, `test_create_rechaza_campo_obligatorio_faltante` deja de incluir esa clave, y `test_precision_coincide_con_la_columna_del_modelo` apunta a `LoteRead` porque `kg_disponibles` ya no está en `LoteCreate`.
- **Sin migraciones:** no existen archivos de migración.
