# Spec Delta

## Purpose

Define el comportamiento de la API para dar de alta, consultar, editar y eliminar un blend, incluyendo la gestión de su composición de tipos de café y las validaciones que impiden nombres repetidos o proporciones inconsistentes.

## ADDED Requirements

### Requirement: Las operaciones exponen el identificador por ruta
Las cuatro operaciones SHALL usar el `id` del blend como parámetro de ruta en lectura, edición y baja, y SHALL usar el cuerpo de la petición para el alta. La respuesta SHALL devolver el estado actual del registro.

#### Scenario: Crear un blend
- **WHEN** se envía una petición de alta con el nombre, los precios y una composición válida
- **THEN** el sistema responde con estado creado y devuelve el registro con su `id` asignado

#### Scenario: Leer un blend existente
- **WHEN** se envía una consulta con el `id` de un blend que existe
- **THEN** el sistema responde con el registro completo

#### Scenario: Editar un blend existente
- **WHEN** se envía una edición con el `id` de un blend que existe
- **THEN** el sistema responde con el registro luego de aplicar los cambios

#### Scenario: Eliminar un blend sin referencias externas
- **WHEN** se envía una baja con el `id` de un blend que existe y que ninguna otra entidad referencia
- **THEN** el sistema responde con estado sin contenido y el blend deja de existir

### Requirement: Las operaciones por identificador exigen que el registro exista
La lectura, la edición y la baja SHALL exigir que el `id` recibido por ruta corresponda a un blend existente. Si no existe, la operación SHALL rechazarse con estado no encontrado sin leer, modificar ni eliminar ningún registro.

#### Scenario: Lectura con un identificador inexistente
- **WHEN** se envía una lectura con un `id` que no corresponde a ningún blend
- **THEN** el sistema responde con estado no encontrado y no devuelve ningún registro

#### Scenario: Edición con un identificador inexistente
- **WHEN** se envía una edición con un `id` que no corresponde a ningún blend
- **THEN** el sistema responde con estado no encontrado y ningún registro se modifica

#### Scenario: Baja con un identificador inexistente
- **WHEN** se envía una baja con un `id` que no corresponde a ningún blend
- **THEN** el sistema responde con estado no encontrado y ningún registro se elimina

### Requirement: La creación valida los atributos de entrada
La creación SHALL rechazar la petición cuando `precio_por_kg_verde` no sea mayor que cero, cuando `nombre` esté vacío o supere los 50 caracteres, o cuando la composición tenga menos de dos tipos de café, repita un `tipo_de_cafe_id` o sume fuera del rango de 99,99 a cien.

#### Scenario: Creación con un precio no positivo
- **WHEN** se envía un alta con `precio_por_kg_verde` igual a cero o negativo
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un nombre vacío
- **WHEN** se envía un alta con `nombre` en cadena vacía
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un solo tipo de café en la composición
- **WHEN** se envía un alta cuya lista de proporciones tiene un único elemento
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un atributo no declarado
- **WHEN** se envía un alta con un atributo que el contrato no conoce
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

### Requirement: La creación rechaza un nombre ya utilizado
La creación SHALL rechazarse con estado de conflicto cuando `nombre` coincida con el de un blend ya registrado, sin crear ningún registro ni modificar los existentes.

#### Scenario: Nombre ya usado por otro blend
- **WHEN** se envía un alta con un `nombre` que ya pertenece a un blend existente
- **THEN** el sistema responde con estado de conflicto y no se crea ningún registro

#### Scenario: Nombre nuevo
- **WHEN** se envía un alta con un `nombre` que ningún blend utiliza
- **THEN** el sistema responde con estado creado

### Requirement: La edición solo modifica los atributos no nulos
La edición SHALL modificar únicamente los atributos cuyo valor enviado no sea nulo. Los atributos enviados como nulo, y los atributos no enviados, SHALL quedar con su valor anterior.

#### Scenario: Edición de un solo atributo
- **WHEN** se envía una edición con un único atributo con valor
- **THEN** únicamente ese atributo cambia y el resto conserva su valor

#### Scenario: Atributo enviado como nulo
- **WHEN** se envía una edición que incluye un atributo con valor nulo
- **THEN** ese atributo conserva su valor anterior

#### Scenario: Edición sin atributos con valor
- **WHEN** se envía una edición cuyo cuerpo no contiene ningún atributo con valor
- **THEN** el sistema responde con el registro sin ningún cambio

### Requirement: La edición valida los atributos enviados y su nombre
La edición SHALL rechazar con estado de validación fallida todo atributo enviado que incumpla sus restricciones de forma, y SHALL rechazar con estado de conflicto un `nombre` que pertenezca a un blend distinto del que se edita.

#### Scenario: Edición con un precio no positivo
- **WHEN** se envía una edición con `precio_por_kg_verde` igual a cero o negativo
- **THEN** el sistema responde con estado de validación fallida y el registro conserva su precio anterior

#### Scenario: Edición con una composición inválida
- **WHEN** se envía una edición cuya lista repite un tipo de café o suma fuera del rango permitido
- **THEN** el sistema responde con estado de validación fallida y la composición anterior queda intacta

#### Scenario: Edición con el nombre de otro blend
- **WHEN** se envía una edición que pone un `nombre` ya usado por un blend distinto
- **THEN** el sistema responde con estado de conflicto y el registro no cambia

#### Scenario: Edición que conserva el propio nombre
- **WHEN** se envía una edición que incluye el `nombre` que el blend ya tiene
- **THEN** la validación es satisfactoria y la edición procede

### Requirement: La lectura devuelve la composición de tipos de café
La lectura SHALL devolver el registro del blend junto con su composición: un elemento por cada tipo de café asociado, cada uno con `tipo_de_cafe_id` y `porcentaje`.

#### Scenario: Blend con dos tipos de café
- **WHEN** se lee un blend que tiene dos filas de composición
- **THEN** la respuesta incluye el registro del blend y una lista de dos elementos con sus porcentajes

#### Scenario: Blend sin composición
- **WHEN** se lee un blend que todavía no tiene ningún tipo de café asociado
- **THEN** la respuesta incluye el registro del blend y la lista de composición vacía

### Requirement: La baja se bloquea y elimina la composición
La baja SHALL eliminarse solo cuando ni `Lote` ni `detalle_pedido` referencien al blend; los registros de composición que le pertenecen no la bloquean. Si una entidad externa lo referencia, la baja SHALL rechazarse con estado de conflicto dejando intactos el blend y su composición. Si procede, SHALL eliminar primero la composición y después el blend.

#### Scenario: Blend referenciado por un lote
- **WHEN** se envía la baja de un blend que tiene al menos un lote asociado
- **THEN** el sistema responde con estado de conflicto y el blend y su composición siguen existiendo

#### Scenario: Blend referenciado por un detalle de pedido
- **WHEN** se envía la baja de un blend que aparece en al menos un detalle de pedido
- **THEN** el sistema responde con estado de conflicto y el blend y su composición siguen existiendo

#### Scenario: Blend con composición pero sin referencias externas
- **WHEN** se envía la baja de un blend que tiene composición y que ninguna entidad externa referencia
- **THEN** el sistema responde con estado sin contenido y desaparecen tanto el blend como todos sus registros de composición

#### Scenario: Composición que no bloquea el borrado
- **WHEN** se envía la baja de un blend cuya única relación es su propia composición
- **THEN** el sistema no la considera bloqueante y procede con la eliminación
