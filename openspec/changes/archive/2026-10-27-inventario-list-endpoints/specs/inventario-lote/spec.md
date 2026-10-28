# Spec Delta

## ADDED Requirements

### Requirement: El listado de lotes filtra por tipo_de_cafe_id o blend_id

La operación SHALL devolver los lotes filtrados por `tipo_de_cafe_id` o `blend_id` mediante el endpoint `GET /lotes`. El endpoint SHALL aceptar ambos parámetros como query parameters, pero SHALL exigir que exactamente uno de ellos tenga un valor distinto de null (XOR). Cuando ambos sean null o ambos tengan un valor, la petición SHALL rechazarse con estado de validación fallida. El endpoint SHALL retornar la lista de lotes ordenada por `id` ascendente. El endpoint NO SHALL validar que el `id` enviado corresponda a un registro existente de TipoDeCafe o Blend; si no hay lotes asociados al id proporcionado, el endpoint SHALL devolver una lista vacía.

#### Scenario: Listado filtrado por tipo_de_cafe_id

- **WHEN** se envía un GET a `/lotes` con `tipo_de_cafe_id` con valor y `blend_id` null
- **THEN** el sistema devuelve la lista de lotes asociados a ese `tipo_de_cafe_id`, ordenados por id ascendente

#### Scenario: Listado filtrado por blend_id

- **WHEN** se envía un GET a `/lotes` con `blend_id` con valor y `tipo_de_cafe_id` null
- **THEN** el sistema devuelve la lista de lotes asociados a ese `blend_id`, ordenados por id ascendente

#### Scenario: Listado con ambos parámetros en null

- **WHEN** se envía un GET a `/lotes` con `tipo_de_cafe_id` null y `blend_id` null
- **THEN** el sistema responde con estado de validación fallida y no devuelve ningún registro

#### Scenario: Listado con ambos parámetros con valor

- **WHEN** se envía un GET a `/lotes` con `tipo_de_cafe_id` y `blend_id` ambos con valor
- **THEN** el sistema responde con estado de validación fallida y no devuelve ningún registro

#### Scenario: Listado con id inexistente

- **WHEN** se envía un GET a `/lotes` con un `tipo_de_cafe_id` o `blend_id` que no corresponde a ningún registro existente
- **THEN** el sistema responde con estado 200 y una lista vacía, sin validar la existencia del id

#### Scenario: Listado sin lotes asociados al filtro

- **WHEN** se envía un GET a `/lotes` con un id válido pero no existen lotes asociados
- **THEN** el sistema responde con estado 200 y una lista vacía
