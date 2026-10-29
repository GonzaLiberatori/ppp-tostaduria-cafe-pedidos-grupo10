# Spec Delta

## ADDED Requirements

### Requirement: El listado devuelve todos los blends registrados

La operación SHALL devolver todos los blends registrados mediante el endpoint `GET /blends`. El endpoint SHALL retornar una lista con todos los registros, ordenados por `id` ascendente. Cada blend SHALL incluir su composición de tipos de café. Cuando no haya blends registrados, el endpoint SHALL devolver una lista vacía.

#### Scenario: Listado con blends existentes

- **WHEN** se envía un GET a `/blends` y existen blends registrados
- **THEN** el sistema devuelve una lista con todos los blends, ordenados por id ascendente, cada uno con su composición de tipos de café

#### Scenario: Listado sin blends

- **WHEN** se envía un GET a `/blends` y no existen blends registrados
- **THEN** el sistema devuelve una lista vacía

#### Scenario: Respuesta incluye la composición

- **WHEN** se envía un GET a `/blends`
- **THEN** el sistema responde con estado 200 y cada blend incluye su lista de tipos de café con sus porcentajes
