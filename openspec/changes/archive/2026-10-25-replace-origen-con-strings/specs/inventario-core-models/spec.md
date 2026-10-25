# Spec Delta

## MODIFIED Requirements

### Requirement: El sistema SHALL tener TipoDeCafe con origen como texto
El sistema SHALL contar con el modelo `TipoDeCafe` con `organico` (booleano), `precio_por_kg_verde` (Decimal) y los campos `variedad`, `region` y `pais` como cadenas de texto de hasta 50 caracteres, sin claves foráneas ni tablas de referencia.

#### Scenario: Crear tipo de café
- **WHEN** se crea un `TipoDeCafe` con `variedad`, `region` y `pais` como texto
- **THEN** la entidad se persiste sin relaciones externas y sus campos numéricos/booleanos se almacenan con el tipo correcto

## REMOVED Requirements

### Requirement: El sistema SHALL tener las entidades geográficas y de origen
El sistema SHALL contar con los modelos `Pais` (id, nombre), `Region` (id, nombre, pais_id con FK a pais) y `Variedad` (id, nombre) para representar orígenes y variedades de café.

#### Scenario: Crear país, región y variedad
- **WHEN** se crean instancias de `Pais`, `Region` y `Variedad` con sus campos obligatorios
- **THEN** se pueden persistir respetando las relaciones FK entre región y país

**Reason**: El origen de `TipoDeCafe` pasa a guardarse como texto plano en las columnas `variedad`, `region` y `pais`. Estas tres tablas solo alimentaban esas columnas, no tenían endpoints propios y su contrato Pydantic ya las representaba como `str`.

**Migration**: Los nombres de origen se leen y escriben directamente desde las columnas `String(50)` de `tipo_de_cafe`. No hay datos persistidos que migrar porque no existe ninguna base creada: `backend/alembic/versions/` no tiene archivos y `.env` está vacío.

## RENAMED Requirements

- FROM: `### Requirement: El sistema SHALL tener TipoDeCafe con relación a región y variedad`
- TO: `### Requirement: El sistema SHALL tener TipoDeCafe con origen como texto`
