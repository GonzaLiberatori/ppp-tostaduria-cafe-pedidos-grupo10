# Proposal

## Why

El módulo de inventario expone endpoints de alta, consulta por id, edición y baja para cada entidad (TipoDeCafe, Blend, Lote), pero no hay forma de listar todos los registros de una colección. El frontend necesita estos endpoints para poblar las vistas de listado, selectores y dashboards que muestran el inventario completo.

## What Changes

- Agregar endpoint `GET /tipos-de-cafe` que devuelva todos los tipos de café registrados.
- Agregar endpoint `GET /blends` que devuelva todos los blends registrados con su composición de tipos de café.
- Agregar endpoint `GET /lotes` que devuelva los lotes filtrados por `tipo_de_cafe_id` o `blend_id` con sus claves foráneas.
- Los endpoints de tipos de café y blends devuelven una lista vacía cuando no hay registros y no requieren parámetros de entrada. El endpoint de lotes requiere exactamente uno de los dos parámetros de filtrado y devuelve una lista vacía cuando no hay lotes asociados al filtro.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `inventario-tipo-de-cafe`: agregar requirement de listado que defina el endpoint `GET /tipos-de-cafe` y su comportamiento (respuesta, orden, lista vacía).
- `inventario-blend`: agregar requirement de listado que defina el endpoint `GET /blends` y su comportamiento (respuesta con composición, orden, lista vacía).
- `inventario-lote`: agregar requirement de listado que defina el endpoint `GET /lotes` con filtrado por `tipo_de_cafe_id` o `blend_id` (restricción XOR), respuesta con claves foráneas, orden y lista vacía cuando no hay lotes asociados.

## Impact

- Backend: módulos `crud.py`, `services.py` y `router.py` del módulo de inventario (nuevas funciones y endpoints).
- `schemas.py`: sin cambios; los schemas Read existentes se reutilizan como tipo de respuesta de lista.
- API: tres nuevos endpoints GET expuestos en Swagger/OpenAPI.
- Sin cambios en modelos de base de datos ni dependencias externas.
