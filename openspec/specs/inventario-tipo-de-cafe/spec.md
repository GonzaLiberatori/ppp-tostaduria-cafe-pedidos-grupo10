# inventario-tipo-de-cafe Specification

## Purpose

Define el comportamiento de la API para dar de alta, consultar, editar y eliminar un tipo de café, con las validaciones de entrada, las reglas de negocio y los códigos de estado que cada operación expone.

## Requirements

### Requirement: Las operaciones exponen el identificador por ruta
Las cuatro operaciones SHALL usar el `id` del tipo de café como parámetro de ruta en lectura, edición y baja, y SHALL usar el cuerpo de la petición para el alta. La respuesta SHALL devolver el estado actual del registro.

#### Scenario: Crear un tipo de café
- **WHEN** se envía una petición de alta con todos los atributos obligatorios válidos
- **THEN** el sistema responde con estado creado y devuelve el registro con su `id` asignado

#### Scenario: Leer un tipo de café existente
- **WHEN** se envía una consulta con el `id` de un tipo de café que existe
- **THEN** el sistema responde con el registro completo

#### Scenario: Editar un tipo de café existente
- **WHEN** se envía una edición con el `id` de un tipo de café que existe
- **THEN** el sistema responde con el registro luego de aplicar los cambios

#### Scenario: Eliminar un tipo de café sin referencias
- **WHEN** se envía una baja con el `id` de un tipo de café que existe y que ninguna otra entidad referencia
- **THEN** el sistema responde con estado sin contenido y el registro deja de existir

### Requirement: Las operaciones por identificador exigen que el registro exista
La lectura, la edición y la baja SHALL exigir que el `id` recibido por ruta corresponda a un tipo de café existente. Si no existe, la operación SHALL rechazarse con estado no encontrado sin leer, modificar ni eliminar ningún registro.

#### Scenario: Lectura con un identificador inexistente
- **WHEN** se envía una lectura con un `id` que no corresponde a ningún tipo de café
- **THEN** el sistema responde con estado no encontrado y no devuelve ningún registro

#### Scenario: Edición con un identificador inexistente
- **WHEN** se envía una edición con un `id` que no corresponde a ningún tipo de café
- **THEN** el sistema responde con estado no encontrado y ningún registro se modifica

#### Scenario: Baja con un identificador inexistente
- **WHEN** se envía una baja con un `id` que no corresponde a ningún tipo de café
- **THEN** el sistema responde con estado no encontrado y ningún registro se elimina

### Requirement: La creación valida los atributos de entrada
La creación SHALL rechazar la petición cuando `precio_por_kg_verde` no sea mayor que cero, cuando `variedad`, `region` o `pais` estén vacíos o superen los 50 caracteres, o cuando el cuerpo incluya atributos no declarados.

#### Scenario: Creación con un precio no positivo
- **WHEN** se envía un alta con `precio_por_kg_verde` igual a cero o negativo
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un nombre de origen vacío
- **WHEN** se envía un alta con `variedad`, `region` o `pais` en cadena vacía
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

#### Scenario: Creación con un atributo no declarado
- **WHEN** se envía un alta con un atributo que el contrato no conoce
- **THEN** el sistema responde con estado de validación fallida y no se crea ningún registro

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

### Requirement: La edición valida los atributos enviados
La edición SHALL rechazar la petición cuando un atributo con valor no cumpla su restricción: `precio_por_kg_verde` mayor que cero, y `variedad`, `region` o `pais` no vacíos y hasta 50 caracteres.

#### Scenario: Edición con un precio no positivo
- **WHEN** se envía una edición con `precio_por_kg_verde` igual a cero o negativo
- **THEN** el sistema responde con estado de validación fallida y el registro conserva su precio anterior

#### Scenario: Edición con un nombre de origen fuera de límite
- **WHEN** se envía una edición con `variedad`, `region` o `pais` de más de 50 caracteres
- **THEN** el sistema responde con estado de validación fallida y el registro no cambia

### Requirement: La baja se bloquea mientras el tipo esté referenciado
La baja SHALL eliminarse solo cuando ninguna entidad referencie al tipo de café. Si `BlendHasTipoDeCafe`, `Lote` o `detalle_pedido` poseen registros con el `id` del tipo, la baja SHALL rechazarse con estado de conflicto y el registro SHALL permanecer intacto.

#### Scenario: Tipo referenciado por composiciones de blend
- **WHEN** se envía la baja de un tipo de café que integra al menos un blend
- **THEN** el sistema responde con estado de conflicto y el tipo de café sigue existiendo

#### Scenario: Tipo referenciado por lotes
- **WHEN** se envía la baja de un tipo de café que tiene al menos un lote asociado
- **THEN** el sistema responde con estado de conflicto y el tipo de café sigue existiendo

#### Scenario: Tipo referenciado por detalle de pedido
- **WHEN** se envía la baja de un tipo de café que aparece en al menos un detalle de pedido
- **THEN** el sistema responde con estado de conflicto y el tipo de café sigue existiendo

#### Scenario: Tipo sin ninguna referencia
- **WHEN** se envía la baja de un tipo de café que ninguna entidad referencia
- **THEN** el sistema responde con estado sin contenido y el registro deja de existir

#### Scenario: Baja con múltiples referencias simultáneas
- **WHEN** un tipo de café está referenciado a la vez por un blend y por un lote
- **THEN** el sistema responde con estado de conflicto y el motivo identifica al menos una de las entidades que lo bloquean

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
