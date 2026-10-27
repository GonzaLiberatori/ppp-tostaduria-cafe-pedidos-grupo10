# Proposal

## Why

El módulo de inventario tiene implementado el CRUD completo de lote, pero quedaron pendientes tres operaciones de actualización puntual que ya cuentan con sus schemas (`LoteKgRealesUpdate`, `LoteKgDisponiblesUpdate`, `LoteEstadoUpdate`). Estas operaciones permiten corregir datos específicos de un lote sin necesidad de reenviar todos los atributos, lo cual es necesario para el flujo operativo diario.

## What Changes

- Agregar tres nuevos endpoints PATCH en `router.py`:
  - `PATCH /lotes/{lote_id}/kg-reales`
  - `PATCH /lotes/{lote_id}/kg-disponibles`
  - `PATCH /lotes/{lote_id}/estado`
- Agregar tres funciones de servicio en `services.py` que implementen las reglas de negocio específicas para cada operación
- Agregar tres funciones de acceso a datos en `crud.py` para actualizar atributos individuales
- Validar que el lote exista antes de cualquier actualización
- Aplicar validaciones de negocio exclusivas para las operaciones de kilos:
  - `kg_disponibles` no puede ser mayor a `kg_reales`
  - Si aumenta `kg_reales`, el incremento se propaga automáticamente a `kg_disponibles`
  - Si `kg_reales` disminuye, `kg_disponibles` permanece intacto
  - Si `kg_disponibles` cambia, `kg_reales` permanece intacto

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `inventario-lote`: Agregar tres endpoints de actualización puntual con validaciones de negocio específicas para la modificación de kilos reales, kilos disponibles y estado del lote.

## Impact

- Backend: módulos `router.py`, `services.py`, `crud.py` del módulo de inventario
- API: tres nuevos endpoints PATCH expuestos en la documentación Swagger/OpenAPI
- No hay cambios en schemas (ya existen)
- No hay cambios en modelos de base de datos
- No hay dependencias externas afectadas
