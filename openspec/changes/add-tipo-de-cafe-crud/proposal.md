# Proposal

## Why

El módulo de inventario tiene modelos y schemas, pero ni una línea de acceso a datos ni de HTTP: `crud.py`, `services.py` y `router.py` están en 0 bytes. `TipoDeCafe` es la entidad con contrato Pydantic completo, así que es la primera que puede cerrar el ciclo de punta a punta. Sin esto, los 13 schemas no se usan en ningún endpoint y la API no expone inventario.

## What Changes

- **`backend/app/modules/inventario/crud.py`**: queries puras — obtener por id, insertar, aplicar cambios, eliminar y contar referencias. Sin reglas de negocio.
- **`backend/app/modules/inventario/services.py`**: reglas de negocio y frontera transaccional (commit/rollback) para crear, leer, editar y eliminar `TipoDeCafe`.
- **`backend/app/modules/inventario/router.py`**: cuatro rutas, con el `id` **siempre por parámetro de ruta**. Solo HTTP: schemas, códigos de estado y `Depends(get_db)`.
- **Prerrequisito en `models.py`**: se retira el `ForeignKey("orden_tueste.id")` de `Lote.orden_tueste_id`, conservando la columna. Verificado: `Base.metadata.create_all()` falla con `NoReferencedTableError` mientras esa referencia apunte a una tabla inexistente, y sin `create_all` no se puede probar ninguna de las cuatro operaciones.
- Tests de `services` y de `router` contra SQLite en memoria.

**Los archivos son tres, no dos.** `AGENTS.md` lo impone: `router.py` es *"solo HTTP... sin reglas de negocio ni acceso directo a la sesión"* y `crud.py` es *"acceso a datos puro (queries sin reglas de negocio)"*. El bloqueo de borrado es una regla de negocio con decisión (`409` vs `204`), así que vive en `services.py`, *"la única capa que otros módulos pueden importar"*.

### Validaciones por operación

| Operación | Validación | Dónde se resuelve |
|---|---|---|
| **Read** | el `id` de la ruta debe corresponder a un tipo existente | `services` → `404` |
| **Create** | `precio_por_kg_verde > 0`, `variedad`/`region`/`pais` no vacíos y ≤ 50, sin atributos desconocidos | Pydantic → `422` |
| **Update** | el `id` de la ruta debe existir; `precio_por_kg_verde > 0` **solo si se envía**; misma validez de texto; atributos en `null` no modifican nada | `services` → `404` · Pydantic + `services` → `422` |
| **Delete** | el `id` debe existir y no estar referenciado | `services` → `404` / `409` |

`precio_por_kg_verde > 0` **ya lo valida Pydantic**: `PrecioPorKgVerde = Annotated[Decimal, Field(max_digits=10, decimal_places=2, gt=0)]`, usado tanto por `TipoDeCafeCreate` como por `TipoDeCafeUpdate`. Siguiendo la condición del pedido ("salvo que la clase de pydantic ya lo valide"), el servicio **no duplica** la comprobación.

### Borrado bloqueado

No se elimina un `TipoDeCafe` mientras otra entidad lo referencie:

| Referencia | Estado |
|---|---|
| `BlendHasTipoDeCafe.tipo_de_cafe_id` | existe, comprobable hoy |
| `Lote.tipo_de_cafe_id` | existe, pero su tabla no se crea hasta retirar la FK de `orden_tueste` (tarea 1.1) |
| `detalle_pedido` | **tabla inexistente** todavía; irá en la lista de referencias |

Fuera de alcance:

- Infraestructura de arranque: `core/config.py`, `core/database.py` (engine/sessionmaker) y `app/main.py` siguen vacíos, y `deps.get_db()` devuelve `UnboundExecutionError`. Ver `design.md` → Risks.
- Listado de tipos de café (`GET /tipos-de-cafe` sin id).
- CRUD de `Blend` y `Lote`, y la definición de `detalle_pedido`.

## Capabilities

### New Capabilities

- `inventario-tipo-de-cafe`: alta, consulta, edición parcial y baja de tipo de café a través de la API, con las validaciones de entrada, las reglas de negocio y los códigos de estado que las rutas exponen.

### Modified Capabilities

Ninguna. `inventario-core-models` describe la persistencia y `inventario-schemas` los contratos Pydantic; ambos quedan como están.

## Impact

- **Agregados:** `inventario/crud.py`, `inventario/services.py`, `inventario/router.py` (los tres hoy en 0 bytes).
- **Modificado:** `inventario/models.py` — se retira `ForeignKey("orden_tueste.id")` de `Lote.orden_tueste_id`. Mismo criterio que ya se aplicó a la relación `Lote.orden_tueste`, que quedó comentada.
- **Tests nuevos:** `tests/modules/inventario/test_services_tipo_de_cafe.py` y `test_router_tipo_de_cafe.py`.
- **Habilita:** que cualquier otro módulo use `TipoDeCafe` importando `inventario.services`.
- **No habilita todavía:** levantar la API en producción. Sin `config.py`, `database.py` y `main.py`, los tests levantan una app local propia y las rutas no quedan registradas en el `FastAPI` real.
