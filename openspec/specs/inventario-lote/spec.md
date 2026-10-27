# inventario-lote Specification

## Purpose

Define el comportamiento de la API para dar de alta, consultar, editar y eliminar un lote, con la validación de sus atributos, la regla de origen único y la derivación de los kilos disponibles.

## Requirements

### Requirement: Las operaciones exponen el identificador por ruta
Las cuatro operaciones SHALL usar el `id` del lote como parámetro de ruta en lectura, edición y baja, y SHALL usar el cuerpo de la petición para el alta. La respuesta SHALL devolver el estado actual del registro.

#### Scenario: Crear un lote
- **WHEN** se envía una petición de alta con todos los atributos obligatorios válidos y un origen
- **THEN** el sistema responde con estado creado y devuelve el registro con su `id` asignado

#### Scenario: Leer un lote existente
- **WHEN** se envía una consulta con el `id` de un lote que existe
- **THEN** el sistema responde con el registro completo

#### Scenario: Editar un lote existente
- **WHEN** se envía una edición con el `id` de un lote que existe
- **THEN** el sistema responde con el registro luego de aplicar los cambios

#### Scenario: Eliminar un lote existente
- **WHEN** se envía una baja con el `id` de un lote que existe
- **THEN** el sistema responde con estado sin contenido y el lote deja de existir

### Requirement: Las operaciones por identificador exigen que el registro exista
La lectura, la edición y la baja SHALL exigir que el `id` recibido por ruta corresponda a un lote existente. Si no existe, la operación SHALL rechazarse con estado no encontrado sin leer, modificar ni eliminar ningún registro.

#### Scenario: Lectura con un identificador inexistente
- **WHEN** se envía una lectura con un `id` que no corresponde a ningún lote
- **THEN** el sistema responde con estado no encontrado y no devuelve ningún registro

#### Scenario: Edición con un identificador inexistente
- **WHEN** se envía una edición con un `id` que no corresponde a ningún lote
- **THEN** el sistema responde con estado no encontrado y ningún registro se modifica

#### Scenario: Baja con un identificador inexistente
- **WHEN** se envía una baja con un `id` que no corresponde a ningún lote
- **THEN** el sistema responde con estado no encontrado y ningún registro se elimina

### Requirement: La creación valida los atributos de entrada
La creación SHALL rechazar la petición cuando `tipo` no sea `VERDE` ni `TOSTADO`, cuando `estado` no sea `ABIERTO` ni `CERRADO`, cuando `humedad` esté fuera del rango de 0 a 100, cuando `kg_reales` sea negativo, cuando `ubicacion_fisica` esté vacía o supere los 50 caracteres, cuando el cuerpo incluya `kg_disponibles` o cualquier atributo no declarado.

#### Scenario: Tipo fuera del conjunto permitido
- **WHEN** se envía un alta con `tipo` distinto de `VERDE` y `TOSTADO`
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Estado fuera del conjunto permitido
- **WHEN** se envía un alta con `estado` distinto de `ABIERTO` y `CERRADO`
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Humedad fuera de rango
- **WHEN** se envía un alta con `humedad` menor que cero o mayor que cien
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Kilos reales negativos
- **WHEN** se envía un alta con `kg_reales` negativo
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Kilos reales en cero
- **WHEN** se envía un alta con `kg_reales` igual a cero
- **THEN** la validación es satisfactoria y el registro se crea

#### Scenario: Creación con kilos disponibles en el cuerpo
- **WHEN** se envía un alta que incluye `kg_disponibles`
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un atributo no declarado
- **WHEN** se envía un alta con un atributo que el contrato no conoce
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

### Requirement: La creación exige exactamente un origen válido
La creación SHALL exigir uno y solo uno entre `tipo_de_cafe_id` y `blend_id`. Con ninguno o con ambos, la petición SHALL rechazarse. El identificador elegido SHALL corresponder a un registro existente de su tabla.

#### Scenario: Alta sin origen
- **WHEN** se envía un alta sin `tipo_de_cafe_id` ni `blend_id`
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Alta con ambos orígenes
- **WHEN** se envía un alta con `tipo_de_cafe_id` y `blend_id` informados a la vez
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Origen que no corresponde a un registro existente
- **WHEN** se envía un alta con un `tipo_de_cafe_id` o un `blend_id` que no existe
- **THEN** el sistema responde con estado no encontrado y no se crea ningún registro

#### Scenario: Origen válido
- **WHEN** se envía un alta con un único identificador de origen que existe
- **THEN** la validación es satisfactoria y el registro se crea

### Requirement: La creación deriva los kilos disponibles
La creación SHALL asignar `kg_disponibles` con el mismo valor que `kg_reales`. El contrato SHALL NO recibir `kg_disponibles`.

#### Scenario: Los kilos disponibles quedan iguales a los reales
- **WHEN** se envía un alta con `kg_reales` informado y sin `kg_disponibles`
- **THEN** el registro creado tiene `kg_disponibles` igual a `kg_reales`

### Requirement: La creación exige la orden de tueste según el tipo
La creación SHALL exigir `orden_tueste_id` cuando `tipo` sea `TOSTADO`, y SHALL rechazar el alta cuando `tipo` sea `VERDE` e incluya `orden_tueste_id`.

#### Scenario: Lote verde sin orden de tueste
- **WHEN** se envía un alta con `tipo = VERDE` y sin `orden_tueste_id`
- **THEN** la validación es satisfactoria y el registro se crea

#### Scenario: Lote verde con orden de tueste
- **WHEN** se envía un alta con `tipo = VERDE` y un `orden_tueste_id` informado
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Lote tostado sin orden de tueste
- **WHEN** se envía un alta con `tipo = TOSTADO` y sin `orden_tueste_id`
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Lote tostado con orden de tueste
- **WHEN** se envía un alta con `tipo = TOSTADO` y un `orden_tueste_id` informado
- **THEN** la validación es satisfactoria y el registro se crea

### Requirement: La edición solo modifica los atributos no nulos
La edición SHALL modificar únicamente los atributos cuyo valor enviado no sea nulo. Los atributos enviados como nulo, y los atributos no enviados, SHALL quedar con su valor anterior. El contrato de edición SHALL NO aceptar `tipo`, `tipo_de_cafe_id`, `blend_id` ni `orden_tueste_id`.

#### Scenario: Edición de un solo atributo
- **WHEN** se envía una edición con un único atributo con valor
- **THEN** únicamente ese atributo cambia y el resto conserva su valor

#### Scenario: Atributo enviado como nulo
- **WHEN** se envía una edición que incluye un atributo con valor nulo
- **THEN** ese atributo conserva su valor anterior

#### Scenario: Edición sin atributos con valor
- **WHEN** se envía una edición cuyo cuerpo no contiene ningún atributo con valor
- **THEN** el sistema responde con el registro sin ningún cambio

#### Scenario: Intento de cambiar el tipo o un origen
- **WHEN** se envía una edición con `tipo`, `tipo_de_cafe_id`, `blend_id` u `orden_tueste_id`
- **THEN** el sistema responde con estado de validación fallida y el registro no cambia

### Requirement: La edición valida los atributos enviados
La edición SHALL rechazar con estado de validación fallida todo atributo enviado con valor que incuma sus restricciones: `humedad` entre 0 y 100, `kg_reales` no negativo, `kg_disponibles` no negativo y `ubicacion_fisica` no vacía y hasta 50 caracteres.

#### Scenario: Humedad fuera de rango en la edición
- **WHEN** se envía una edición con `humedad` mayor que cien
- **THEN** el sistema responde con estado de validación fallida y el registro conserva su humedad anterior

#### Scenario: Kilos reales negativos en la edición
- **WHEN** se envía una edición con `kg_reales` negativo
- **THEN** el sistema responde con estado de validación fallida y el registro conserva sus kilos anteriores

#### Scenario: Atributo válido en la edición
- **WHEN** se envía una edición con un atributo que cumple sus restricciones
- **THEN** la validación es satisfactoria y el valor se aplica

### Requirement: La lectura devuelve todos los atributos con sus claves foráneas
La lectura SHALL devolver el lote con todos sus atributos, incluidos `tipo_de_cafe_id`, `blend_id` y `orden_tueste_id` con su valor tal como está almacenado, sin resolver ni sustituir por el registro referenciado.

#### Scenario: Lote con origen de tipo de café
- **WHEN** se lee un lote que tiene `tipo_de_cafe_id` informado
- **THEN** la respuesta incluye el `id` del lote, todos sus atributos y el `tipo_de_cafe_id` tal como está guardado

#### Scenario: Lote con atributos no informados
- **WHEN** se lee un lote cuyos atributos opcionales no tienen valor
- **THEN** la respuesta incluye todos los atributos con `null` en los no informados

### Requirement: La baja elimina únicamente el lote
La baja SHALL eliminar solo el registro del lote. Los registros de `tipo_de_cafe`, `blend` y `orden_tueste` que el lote referencie SHALL permanecer intactos.

#### Scenario: Baja de un lote con origen
- **WHEN** se envía la baja de un lote que tiene `tipo_de_cafe_id` informado
- **THEN** el sistema responde con estado sin contenido, el lote desaparece y el tipo de café referenciado sigue existiendo

#### Scenario: Baja de un lote con origen de blend
- **WHEN** se envía la baja de un lote que tiene `blend_id` informado
- **THEN** el sistema responde con estado sin contenido, el lote desaparece y el blend referenciado sigue existiendo

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
