# inventario-schemas Specification

## Purpose

Define los contratos de entrada y salida de la API de inventario para tipos de café, blends y lotes, estableciendo qué atributos son obligatorios, opcionales o de solo lectura en cada operación.

## Requirements

### Requirement: La creación solo exige los atributos no nulos
En las operaciones de creación, el contrato SHALL exigir únicamente los atributos que en el modelo de datos no admiten nulo, y SHALL tratar como no obligatorios todos los atributos declarados nullable.

#### Scenario: Creación con solo los campos obligatorios
- **WHEN** se envía una petición de creación omitiendo todos los atributos nullable
- **THEN** la validación es satisfactoria y esos atributos quedan con valor nulo

#### Scenario: Creación sin un campo obligatorio
- **WHEN** se envía una petición de creación omitiendo un atributo no nulo
- **THEN** la petición se rechaza con un error de validación que identifica el campo faltante

### Requirement: La actualización acepta cualquier subconjunto de atributos editables
En las operaciones de actualización, el contrato SHALL marcar como opcionales todos los atributos editables, de modo que se pueda enviar uno solo o varios sin exigir el resto.

#### Scenario: Actualización parcial
- **WHEN** se envía una petición de actualización con un único atributo editable
- **THEN** la validación es satisfactoria y solo ese atributo se considera provisto

#### Scenario: Actualización vacía
- **WHEN** se envía una petición de actualización sin ningún atributo
- **THEN** la validación es satisfactoria y ningún atributo se considera provisto

### Requirement: La lectura devuelve el identificador y todos los atributos
En las operaciones de lectura, el contrato SHALL incluir siempre el `id` de la entidad y SHALL devolver todos los atributos de la clase, admitiendo `null` en aquellos declarados nullable.

#### Scenario: Lectura de entidad con atributos nullable nulos
- **WHEN** se lee una entidad cuyos atributos nullable no tienen valor
- **THEN** la respuesta incluye el `id` y todos los atributos, con `null` en los no informados

### Requirement: La eliminación no declara schema propio
Las operaciones de eliminación SHALL recibir únicamente el `id` de la entidad como parámetro de ruta, sin cuerpo de petición. Los schemas de eliminación SHALL quedar ausentes de la capa de contratos.

#### Scenario: Eliminación sin cuerpo
- **WHEN** se invoca la eliminación de un recurso identificado por su `id`
- **THEN** el único dato de entrada es el `id` por ruta y el módulo no expone ningún schema de eliminación

### Requirement: El tipo de café recibe los nombres de origen como texto
El contrato de creación y actualización de tipo de café SHALL recibir `variedad`, `region` y `pais` como texto. El tipo de café se identifica por su propio `id`; los nombres de origen son atributos descriptivos y SHALL NO usarse como identificadores de la entidad.

#### Scenario: Creación con nombres de origen
- **WHEN** se envía una creación de tipo de café con `variedad`, `region` y `pais` como texto
- **THEN** la validación es satisfactoria y el contrato no exige `variedad_id` ni `region_id`

#### Scenario: Nombres de origen vacíos
- **WHEN** se envía una creación o actualización de tipo de café con alguno de los nombres `variedad`, `region` o `pais` vacío
- **THEN** la petición se rechaza con un error de validación

### Requirement: La lectura de tipo de café devuelve los nombres de origen como texto
El contrato de lectura de tipo de café SHALL devolver `variedad`, `region` y `pais` como texto e incluir `id` como identificador del tipo de café. SHALL NO exponer `variedad_id` ni `region_id`.

#### Scenario: Lectura de tipo de café
- **WHEN** se lee un tipo de café
- **THEN** la respuesta contiene `id`, `organico`, `precio_por_kg_verde`, `variedad`, `region` y `pais`, sin `variedad_id` ni `region_id`

### Requirement: La composición del blend se recibe como lista de proporciones
Los contratos de creación, actualización y lectura de blend SHALL representar la composición como una lista de objetos, cada uno con `tipo_de_cafe_id` entero y `porcentaje` decimal, sin exponer la entidad de asociación como recurso independiente.

#### Scenario: Creación de blend con composición
- **WHEN** se envía una creación de blend con una lista de proporciones
- **THEN** la validación es satisfactoria y la composición se acepta como parte del mismo contrato

#### Scenario: Lectura de blend con composición
- **WHEN** se lee un blend
- **THEN** la respuesta incluye `id`, `nombre`, `precio_por_kg_verde`, `descripcion` y la lista de proporciones con `tipo_de_cafe_id` y `porcentaje`

#### Scenario: Actualización total de la composición
- **WHEN** se envía una actualización de blend que incluye la lista de proporciones
- **THEN** la lista provista reemplaza por completo la composición anterior

### Requirement: La composición del blend se valida
El contrato de blend SHALL rechazar una composición vacía, una composición con `tipo_de_cafe_id` repetidos y una composición cuyos porcentajes no sumen exactamente cien.

#### Scenario: Composición vacía
- **WHEN** se envía un blend con la lista de proporciones vacía
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Tipo de café repetido
- **WHEN** se envía un blend con dos proporciones para el mismo `tipo_de_cafe_id`
- **THEN** la petición se rechaza con un error de validación

#### Scenario: Porcentajes que no suman cien
- **WHEN** se envía un blend cuyos porcentajes suman un valor distinto de cien
- **THEN** la petición se rechaza con un error de validación

### Requirement: La actualización de lote excluye tipo y referencias de origen
El contrato de actualización de lote SHALL permitir editar `estado`, `fecha_vencimiento`, `humedad`, `kg_disponibles`, `kg_reales`, `ubicacion_fisica` y `observaciones`, y SHALL rechazar cualquier intento de modificar `tipo`, `tipo_de_cafe_id`, `blend_id` u `orden_tueste_id`.

#### Scenario: Actualización de atributos permitidos
- **WHEN** se envía una actualización de lote con uno o más de los atributos permitidos
- **THEN** la validación es satisfactoria

#### Scenario: Intento de modificar el tipo del lote
- **WHEN** se envía una actualización de lote incluyendo `tipo`, `tipo_de_cafe_id`, `blend_id` u `orden_tueste_id`
- **THEN** la petición se rechaza con un error de validación

### Requirement: El lote admite ediciones puntuales por identificador
El sistema SHALL exponer contratos de edición puntual que reciban el `id` del lote por ruta y un único atributo editable en el cuerpo: `kg_disponibles` en uno, `kg_reales` en otro y `estado` en el último.

#### Scenario: Edición de kilos disponibles
- **WHEN** se envía el `id` de un lote y un valor de `kg_disponibles`
- **THEN** la validación es satisfactoria y el cuerpo no admite otros atributos

#### Scenario: Edición de kilos reales
- **WHEN** se envía el `id` de un lote y un valor de `kg_reales`
- **THEN** la validación es satisfactoria y el cuerpo no admite otros atributos

#### Scenario: Cambio de estado
- **WHEN** se envía el `id` de un lote y un valor de `estado` perteneciente al conjunto permitido
- **THEN** la validación es satisfactoria y el cuerpo no admite otros atributos

#### Scenario: Estado fuera del conjunto permitido
- **WHEN** se envía un `estado` que no es `CERRADO` ni `ABIERTO`
- **THEN** la petición se rechaza con un error de validación
