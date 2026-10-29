# Spec Delta

## ADDED Requirements

### Requirement: El listado devuelve todos los tipos de café registrados

La operación SHALL devolver todos los tipos de café registrados mediante el endpoint `GET /tipos-de-cafe`. El endpoint SHALL retornar una lista con todos los registros, ordenados por `id` ascendente. Cuando no haya tipos de café registrados, el endpoint SHALL devolver una lista vacía.

#### Scenario: Listado con tipos de café existentes

- **WHEN** se envía un GET a `/tipos-de-cafe` y existen tipos de café registrados
- **THEN** el sistema devuelve una lista con todos los tipos de café, ordenados por id ascendente

#### Scenario: Listado sin tipos de café

- **WHEN** se envía un GET a `/tipos-de-cafe` y no existen tipos de café registrados
- **THEN** el sistema devuelve una lista vacía

#### Scenario: Respuesta determina el estado actual

- **WHEN** se envía un GET a `/tipos-de-cafe`
- **THEN** el sistema responde con estado 200 y una lista de registros completos
