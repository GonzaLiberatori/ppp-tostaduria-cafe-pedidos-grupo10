# Spec Delta

## MODIFIED Requirements

### Requirement: La creación solo exige los atributos no nulos
En las operaciones de creación, el contrato SHALL exigir únicamente los atributos que en el modelo de datos no admiten nulo, y SHALL tratar como no obligatorios todos los atributos declarados nullable. Excepción: un atributo derivado SHALL no solicitarse aunque el modelo no admita nulo.

#### Scenario: Creación con solo los campos obligatorios
- **WHEN** se envía una petición de creación omitiendo todos los atributos nullable
- **THEN** la validación es satisfactoria y esos atributos quedan con valor nulo

#### Scenario: Creación sin un campo obligatorio
- **WHEN** se envía una petición de creación omitiendo un atributo no nulo que el contrato sí solicita
- **THEN** la petición se rechaza con un error de validación que identifica el campo faltante

#### Scenario: Atributo derivado no solicitado
- **WHEN** se envía la creación de un lote que incluye `kg_disponibles`
- **THEN** la petición se rechaza con un error de validación
