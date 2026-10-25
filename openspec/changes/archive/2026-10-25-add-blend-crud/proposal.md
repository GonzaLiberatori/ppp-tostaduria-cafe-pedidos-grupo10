# Proposal

## Why

`Blend` tiene modelo y contrato Pydantic completos, pero ni una línea de acceso a datos ni de HTTP: lo mismo que le pasó a `TipoDeCafe` antes del cambio `add-tipo-de-cafe-crud`. Además, la composición de un blend solo existe como tabla de asociación (`BlendHasTipoDeCafe`), de modo que sin CRUD no hay forma de crear ni leer un blend en toda la aplicación.

Este cambio reutiliza los principios ya establecidos: identificador por ruta, existencia comprobada en `services`, tres capas separadas y las mismas excepciones de dominio mapeadas a códigos HTTP.

## What Changes

### Schemas (`schemas.py`) — dos cambios puntuales

La revisión de `schemas.py` mostró que **casi todo lo pedido ya está validado**: `tipo_de_cafe_id` sin repetir, `porcentaje > 0`, `nombre` no vacío y ≤ 50, `precio_por_kg_verde > 0`, lista válida solo si no es `null` en Update, `extra="forbid"` y `BlendRead.desde_orm`. Quedan dos cosas:

| Cambio | Dónde |
|---|---|
| Lista con **mínimo dos** tipos de café (hoy `min_length=1`) | `BlendCreate.tipos_de_cafe`, `BlendUpdate.tipos_de_cafe` |
| Suma de porcentajes con **tolerancia de 99,99 a 100** (hoy exactamente 100) | `_validar_composicion` |

### Capa de datos (`crud.py`)

- Consultas de blend: obtener por id, crear con composición, reemplazar composición, eliminar.
- **Generalizar `REFERENCIAS_PROHIBIDAS`**: el `tuple[type, ...]` actual fija la columna en `_COLUMNA_TIPO_DE_CAFE = "tipo_de_cafe_id"` y no sirve para `Blend`, cuyo bloqueante es `Lote.blend_id`. Pasa a estar parametrizado por la entidad que se borra.
- Borrar los `BlendHasTipoDeCafe` de un blend como operación propia.

### Capa de negocio (`services.py`)

- Excepciones de dominio: `BlendNoEncontrado`, `BlendReferenciado`, `NombreDeBlendEnUso`.
- Alta con un registro de composición por item, en una transacción.
- Edición que reemplaza la composición completa: borra los registros previos y crea los nuevos.
- Baja que elimina la composición antes que el blend.

### Capa HTTP (`router.py`)

Cuatro rutas con el `id` por camino: `POST /blends` → 201, `GET|PATCH|DELETE /blends/{id}` → 200/204.

### Validaciones por operación

| Operación | Validación | Dónde se resuelve |
|---|---|---|
| **Create** | `precio_por_kg_verde > 0`, `nombre` no vacío y ≤ 50, lista con ≥ 2 cafés sin repetir y sumando entre 99,99 y 100, sin atributos desconocidos | Pydantic → `422` |
| **Create** | `nombre` ya usado por otro blend | `services` → `409` |
| **Read** | el `id` de la ruta debe existir | `services` → `404` |
| **Update** | el `id` de la ruta debe existir; mismas reglas de forma que Create **solo cuando el atributo viene con valor**; `nombre` no repetido si se envía | `services` → `404` / `409` · Pydantic → `422` |
| **Delete** | el `id` debe existir y no estar referenciado por `Lote` ni `detalle_pedido` | `services` → `404` / `409` |

## Decisión explícita de alcance

El pedido descartó dos protecciones, y quedan **fuera de alcance** con su riesgo registrado en `design.md`:

1. **No se comprueba que cada `tipo_de_cafe_id` de la lista exista.** Un id inexistente provoca `IntegrityError` en el `commit` y el cliente recibe `500` en vez de `422`/`404`.
2. **No se agrega `unique=True` a `Blend.nombre`.** El chequeo de unicidad vive solo en el servicio, con la ventana clásica entre `SELECT` e `INSERT`: dos altas simultáneas con el mismo nombre pueden colar.

Fuera de alcance también: infraestructura de arranque (`config.py`, `database.py`, `main.py`), CRUD de `Lote`, la definición de `detalle_pedido`, y el listado de blends (`GET /blends` sin id).

## Capabilities

### New Capabilities

- `inventario-blend`: alta, consulta, edición y baja de blends a través de la API, con la gestión de su composición de tipos de café, las validaciones de entrada y los códigos de estado que las rutas exponen.

### Modified Capabilities

- `inventario-schemas`: se ajusta el requirement `La composición del blend se valida` — pasa de rechazar una composición *vacía* a rechazar una con *menos de dos* tipos, y la regla de suma pasa de *exactamente cien* a *entre 99,99 y cien*.

## Impact

- **Agregados:** `inventario/router.py` (mezcla con las 4 rutas de `TipoDeCafe`), `tests/modules/inventario/test_services_blend.py`, `test_router_blend.py`.
- **Modificados:** `inventario/crud.py` (generalización de referencias + consultas de blend), `inventario/services.py` (+4 operaciones y 3 excepciones), `inventario/schemas.py` (2 cambios de validación), `tests/modules/inventario/test_schemas_blend.py` (un test existente queda obsoleto).
- **Sin migraciones:** no existen archivos de migración.
- **Habilita:** construir blends completos desde la API y, más adelante, el CRUD de `Lote` que depende de `blend_id`.
