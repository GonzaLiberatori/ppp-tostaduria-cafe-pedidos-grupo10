# Design

## Context

`Lote` es la última entidad del inventario con CRUD pendiente. Hoy `LoteCreate` pide `kg_disponibles`, `HumedadPorcentaje` no tiene cota superior y `Kilos` es `ge=0` para todo lo que use kilos. En `crud.py` y `services.py` no hay nada de `Lote`, y `router.py` tiene 8 rutas (4 de `TipoDeCafe`, 4 de `Blend`).

Dos hechos que condicionan el diseño:

- `HumedadPorcentaje` es `ge=0` **sin `le=100`**, así que `humedad = 250` pasa hoy.
- `Lote.orden_tueste_id` es un `Integer` plano sin FK: la retiró `add-tipo-de-cafe-crud` porque `create_all()` reventaba con `NoReferencedTableError`, y `produccion/models.py` sigue en 0 bytes.

Ver `proposal.md` para la motivación y `specs/inventario-lote/spec.md` para los requisitos.

## Goals / Non-Goals

**Goals:**

- Cerrar el CRUD de `Lote` reutilizando el patrón ya probado en `TipoDeCafe` y `Blend`.
- Que cada regla viva en una sola capa: forma en Pydantic, negocio en `services`, queries en `crud`.
- Implementar todo lo que **no** dependa de la tabla `orden_tueste`.

**Non-Goals:**

- Comprobar que `orden_tueste_id` apunta a una fila real (ver Decisions).
- Los tres endpoints puntuales de lote.
- Infraestructura de arranque.

## Decisions

### Los tres cambios de schema y por qué `Kilos` no se toca

| Regla | Cómo |
|---|---|
| `humedad` 0–100 | `HumedadPorcentaje` gana `le=100` |
| `kg_reales >= 0` | `Kilos` ya es `ge=0` | **sin cambio: ya cumple** |
| `kg_disponibles` fuera del alta | se quita de `LoteCreate` |

**Por qué `Kilos` no se toca:** `kg_reales` y `kg_disponibles` piden exactamente la misma cota (`>= 0`), así que comparten el alias sin conflicto. Un lote puede quedar en cero kilos reales y en cero kilos disponibles, y los dos casos pasan la validación tal como está escrita hoy — no hay nada que separar.

**Por qué `kg_disponibles` se quita y no se deja opcional:** si se permite enviarlo, hay dos fuentes de verdad para el mismo número y el servicio tendría que decidir cuál manda. Derivarlo de `kg_reales` en el alta deja una sola.

### Reglas de forma en el schema, reglas de negocio en `services`

Dos reglas cruzan capas y conviene no mezclarlas:

| Regla | Dónde | Por qué |
|---|---|---|
| **Exactamente uno** entre `tipo_de_cafe_id` y `blend_id` | `model_validator` de `LoteCreate` | es una relación entre dos campos del **mismo** payload; no consulta nada |
| El origen elegido **corresponde a un registro real** | `services` | necesita la base |
| **`kg_disponibles = kg_reales`** | `services` | es una derivación, no una regla de forma |

**Por qué el XOR va en Pydantic y no en `services`:** es el mismo caso que la regla de `orden_tueste_id` de más abajo — dos atributos de un payload que se contradicen entre sí. En `services` obligaría a crear una excepción de dominio y traducirla a `422` en el router, cuando FastAPI devuelve `422` solo con rechazar el body. La existencia, en cambio, **no** puede resolverse en el schema, y ahí sí va `services`.

**Consecuencia:** la regla queda partida en dos capas — forma en Pydantic (`422`), existencia en `services` (`404`). Esa partición no es una concesión: es dónde se puede comprobar cada mitad.

### `orden_tueste`: qué entra y qué queda pendiente

**Sí se implementa (no necesita la tabla):**

```python
if tipo == VERDE and orden_tueste_id is not None:  -> rechazar
if tipo == TOSTADO and orden_tueste_id is None:    -> rechazar
```

Va en un `model_validator(mode="after")` de `LoteCreate`: es una relación cruzada entre dos campos del **mismo** payload, que es exactamente lo que ese validador resuelve y no necesita la base.

**No se implementa:** que `orden_tueste_id` corresponda a una fila real. La tabla no existe y su FK no puede volver hasta que `produccion` defina `OrdenTueste`.

**Consecuencia asumida:** hoy un lote `TOSTADO` se crea con un `orden_tueste_id` que nadie puede verificar. Es un entero en una columna sin restricción. Ver Risks.

### Lote no entra a `REFERENCIAS_PROHIBIDAS`

Verifiqué con grep: **ninguna tabla tiene `ForeignKey("lote...")`**. `Lote` es hoja del grafo, así que su borrado no tiene bloqueos y no se agrega ninguna entrada.

**Lo que sí hay que fijar** es lo contrario: que el borrado **no arrastre** a `tipo_de_cafe`, `blend` ni `orden_tueste`. Esas son tablas padre y el comportamiento por defecto de SQLAlchemy ya no las toca — pero queda escrito como scenario para que nadie le ponga `cascade="all"` sin darse cuenta.

### Lectura sin joins

`LoteRead` ya declara `tipo_de_cafe_id`, `blend_id` y `orden_tueste_id` como enteros y tiene `from_attributes=True`. Igual que `TipoDeCafeRead` y `LoteRead` antes del cambio de origen: **copiapuro campo por campo, así que sin adaptador**.

```python
return LoteRead.model_validate(lote)
```

No hay relaciones que recorrer — `Lote` no tiene ninguna `relationship` activa — así que tampoco hay riesgo de N+1.

### Guía de estructuras condicionales

- **`elif`** en el mapeo excepción de dominio → código HTTP, que ya es la cadena de `router.py` y crece con `LoteNoEncontrado` y `OrigenDeLoteInvalido`.
- **`if / elif / else`** en la regla de `orden_tueste`, porque `tipo` tiene exactamente dos valores y las ramas son mutuamente excluyentes sobre el mismo sujeto.
- **Sin `elif`** en la comprobación de origen: son dos chequeos independientes (¿hay exactamente uno?, ¿existe?), y el aviso debe poder nombrar a los dos problemas.

### Tests con app local y SQLite

Mismo patrón que los dos cambios anteriores: `FastAPI()` local, `dependency_overrides` sobre `get_db`, y `create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)` — obligatorio porque `TestClient` atiende en otro hilo.

## Risks / Trade-offs

- **`orden_tueste_id` es un entero verificable** → un lote `TOSTADO` puede apuntar a cualquier número, y un `VERDE` con el atributo en `null` pasa igual. La verificación real queda pendiente hasta que exista la tabla. **Hay que retomarla en `produccion`.**
- **`kg_disponibles` y `kg_reales` divergen después del alta** → el primero se deriva solo al crear; después son editables por caminos distintos (`LoteUpdate` y los endpoints puntuales). Si `kg_reales` baja, `kg_disponibles` no lo sigue. Es el comportamiento que pide el pedido, pero conviene saberlo.
- **`LoteCreate` deja de aceptar `kg_disponibles`** → es un cambio de contrato observable: cualquier cliente que lo enviara recibe `422`. Es lo pedido, pero rompe compatibilidad hacia atrás.
- **Los tres endpoints puntuales no tienen ruta** → sus schemas existen desde `add-inventario-schemas` y siguen sin usarse.
- **Endpoints no registrados en el `FastAPI` real** → `config.py`, `database.py` y `main.py` siguen vacíos y `get_db()` sigue roto.

## Migration Plan

Sin migraciones: `backend/alembic/versions/` está vacío. El cambio de `LoteCreate` es de contrato, no de esquema.

**Rollback:** revertir `schemas.py`, `crud.py`, `services.py`, `router.py` y los tests afectados. Si se revierte, hay que revisar el delta aplicado sobre `inventario-schemas`.

## Open Questions

- **Infraestructura de arranque** (`core/config.py`, `core/database.py`, `app/main.py`, arreglo de `deps.get_db()`): sigue fuera de alcance y bloquea levantar la API en producción.
- **Comprobación referencial de `orden_tueste_id`**: pendiente hasta que `produccion/models.py` defina `OrdenTueste`. Ese trabajo implica rehacer la FK que se retiró y regenerar la migración.
