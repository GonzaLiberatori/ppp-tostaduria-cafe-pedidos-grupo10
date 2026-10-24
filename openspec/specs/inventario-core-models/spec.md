# inventario-core-models Specification

## Purpose

Define las entidades base del módulo de inventario (países, regiones, variedades, tipos de café, blends, lotes y su asociación) para soportar la trazabilidad del café en el sistema.

## Requirements

### Requirement: El sistema SHALL tener las entidades geográficas y de origen
El sistema SHALL contar con los modelos `Pais` (id, nombre), `Region` (id, nombre, pais_id con FK a pais) y `Variedad` (id, nombre) para representar orígenes y variedades de café.

#### Scenario: Crear país, región y variedad
- **WHEN** se crean instancias de `Pais`, `Region` y `Variedad` con sus campos obligatorios
- **THEN** se pueden persistir respetando las relaciones FK entre región y país

### Requirement: El sistema SHALL tener TipoDeCafe con relación a región y variedad
El sistema SHALL contar con el modelo `TipoDeCafe` con `organico` (booleano), `precio_por_kg_verde` (Decimal), `region_id` y `variedad_id` con FKs a `region` y `variedad` respectivamente.

#### Scenario: Crear tipo de café
- **WHEN** se crea un `TipoDeCafe` asociado a una `Region` y una `Variedad` válidas
- **THEN** la entidad queda correctamente relacionada y sus campos numéricos/booleanos se almacenan con el tipo correcto

### Requirement: El sistema SHALL tener Blend y su asociación con tipos de café
El sistema SHALL contar con el modelo `Blend` (id, nombre, precio_por_kg_verde Decimal, descripcion Text) y la tabla de asociación `BlendHasTipoDeCafe` (blend_id, tipo_de_cafe_id, porcentaje Decimal) con clave compuesta.

#### Scenario: Crear blend con composición
- **WHEN** se crea un `Blend` y se añaden registros en `BlendHasTipoDeCafe` con porcentajes válidos para distintos `TipoDeCafe`
- **THEN** la composición del blend queda representada con clave compuesta y relaciones correctas

### Requirement: El sistema SHALL tener Lote con trazabilidad y estados
El sistema SHALL contar con el modelo `Lote` con `id` (MEDIUMINT UNSIGNED), `tipo` (ENUM VERDE/TOSTADO), `estado` (ENUM CERRADO/ABIERTO), `fecha_vencimiento` (DATETIME), `humedad`, `kg_disponibles`, `kg_reales` (Decimal), `ubicacion_fisica`, `observaciones` (Text nullable), y FKs opcionales a `tipo_de_cafe_id`, `blend_id`, `orden_tueste_id`.

#### Scenario: Crear lote verde asociado a tipo de café
- **WHEN** se crea un `Lote` con `tipo=VERDE` y `tipo_de_cafe_id` asociado
- **THEN** el lote queda registrado con sus campos obligatorios y deja a `blend_id` y `orden_tueste_id` en null

#### Scenario: Crear lote tostado asociado a tipo de cafe
- **WHEN** se crea un `Lote` con `tipo=TOSTADO` y `tipo_de_cafe_id` asociado
- **THEN** el lote queda registrado con sus campos obligatorios mas `orden_tueste_id` dejando `blend_id` en null

#### Scenario: Crear lote verde asociado a blend
- **WHEN** se crea un `Lote` con `tipo=VERDE` y `blend_id` asociado
- **THEN** el lote queda registrado con sus campos obligatorios y deja a `tipo_de_cafe_id` y `orden_tueste_id` en null

#### Scenario: Crear lote tostado asociado a blend
- **WHEN** se crea un `Lote` con `tipo=TOSTADO` y `blend_id` asociado
- **THEN** el lote queda registrado con sus campos obligatorios mas `orden_tueste_id` dejando `tipo_de_cafe_id` en null
