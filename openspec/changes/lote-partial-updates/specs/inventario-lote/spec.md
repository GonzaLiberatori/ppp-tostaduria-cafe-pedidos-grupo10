# Spec Delta

## ADDED Requirements

### Requirement: Actualización puntual de kilos reales

La operación SHALL permitir actualizar únicamente el campo `kg_reales` de un lote identificado por su `id` mediante el endpoint `PATCH /lotes/{lote_id}/kg-reales`. El endpoint SHALL validar que el lote exista antes de aplicar cambios. Cuando el nuevo valor de `kg_reales` sea mayor al actual, el endpoint SHALL sumar la diferencia al campo `kg_disponibles`. Cuando el nuevo valor de `kg_reales` sea menor o igual al actual, el endpoint SHALL mantener `kg_disponibles` sin cambios.

#### Scenario: Aumento de kilos reales propaga a disponibles

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-reales` con `kg_reales` mayor al valor actual
- **THEN** el sistema actualiza `kg_reales` al nuevo valor y suma la diferencia a `kg_disponibles`

#### Scenario: Disminución de kilos reales no afecta disponibles

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-reales` con `kg_reales` menor o igual al valor actual
- **THEN** el sistema actualiza `kg_reales` al nuevo valor y mantiene `kg_disponibles` sin cambios

#### Scenario: Lote inexistente en actualización de kilos reales

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-reales` con un `lote_id` que no existe
- **THEN** el sistema rechaza la operación con estado 404 sin modificar ningún registro

### Requirement: Actualización puntual de kilos disponibles

La operación SHALL permitir actualizar únicamente el campo `kg_disponibles` de un lote identificado por su `id` mediante el endpoint `PATCH /lotes/{lote_id}/kg-disponibles`. El endpoint SHALL validar que el lote exista antes de aplicar cambios. El endpoint SHALL rechazar la operación cuando el nuevo valor de `kg_disponibles` sea mayor al valor actual de `kg_reales` del lote. Cualquier cambio en `kg_disponibles` SHALL mantener `kg_reales` sin cambios.

#### Scenario: Actualización válida de kilos disponibles

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-disponibles` con `kg_disponibles` menor o igual a `kg_reales`
- **THEN** el sistema actualiza `kg_disponibles` al nuevo valor y mantiene `kg_reales` sin cambios

#### Scenario: Kilos disponibles excede kilos reales

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-disponibles` con `kg_disponibles` mayor a `kg_reales`
- **THEN** el sistema rechaza la operación con estado 400 sin modificar ningún registro

#### Scenario: Lote inexistente en actualización de kilos disponibles

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/kg-disponibles` con un `lote_id` que no existe
- **THEN** el sistema rechaza la operación con estado 404 sin modificar ningún registro

### Requirement: Actualización puntual de estado

La operación SHALL permitir actualizar únicamente el campo `estado` de un lote identificado por su `id` mediante el endpoint `PATCH /lotes/{lote_id}/estado`. El endpoint SHALL validar que el lote exista antes de aplicar cambios. El campo `estado` solo acepta los valores `ABIERTO` o `CERRADO`, validados por el schema existente.

#### Scenario: Actualización válida de estado

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/estado` con `estado` igual a `ABIERTO` o `CERRADO`
- **THEN** el sistema actualiza `estado` al nuevo valor

#### Scenario: Lote inexistente en actualización de estado

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/estado` con un `lote_id` que no existe
- **THEN** el sistema rechaza la operación con estado 404 sin modificar ningún registro

#### Scenario: Estado inválido rechazado por validación

- **WHEN** se envía un PATCH a `/lotes/{lote_id}/estado` con un valor distinto de `ABIERTO` o `CERRADO`
- **THEN** el sistema rechaza la operación con estado 422 por validación de schema
