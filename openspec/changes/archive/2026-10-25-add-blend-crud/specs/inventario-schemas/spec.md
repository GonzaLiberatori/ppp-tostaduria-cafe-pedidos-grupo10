# Spec Delta

## MODIFIED Requirements

### Requirement: La composición del blend se valida
El contrato de blend SHALL rechazar una composición vacía, una composición con un solo tipo de café, una composición con `tipo_de_cafe_id` repetidos y una composición cuyos porcentajes sumen menos de 99,99 o más de cien.

#### Scenario: Composición vacía
- **WHEN** se envía un blend con la lista de proporciones vacía
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Tipo de café repetido
- **WHEN** se envía un blend con dos proporciones para el mismo `tipo_de_cafe_id`
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Porcentajes que no suman cien
- **WHEN** se envía un blend cuyos porcentajes suman menos de 99,99 o más de cien
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Composición con un solo tipo
- **WHEN** se envía un blend con la lista de proporciones de un único elemento
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Porcentajes que suman 99,99 por redondeo
- **WHEN** se envía un blend cuyos porcentajes suman 99,99
- **THEN** la validación es satisfactoria y la composición se acepta
