# Proposal

## Why

`TipoDeCafe` almacena su origen en tres tablas (`Pais`, `Region`, `Variedad`) para guardar tres nombres que el sistema **solo lee como texto**: no hay endpoints para esas entidades, y el contrato Pydantic ya recibe y devuelve `variedad`, `region` y `pais` como `str`. El costo de mantener las tablas (tres joins, un flujo de get-or-create en dos niveles, riesgo de N+1, carrera por falta de índices únicos) no está pagado por nada.

## What Changes

- Se eliminan los modelos `Pais`, `Region` y `Variedad` y sus relaciones inversas hacia `TipoDeCafe`.
- `TipoDeCafe.variedad_id` y `TipoDeCafe.region_id` (FKs) pasan a ser las columnas `variedad`, `region` y `pais` de tipo `String(50)`, sin claves foráneas.
- Se elimina `TipoDeCafeRead.desde_orm`. Como `TipoDeCafeRead` y `LoteRead` son copia campo por campo de sus modelos, habilitan `from_attributes=True` y se arman con `model_validate(obj)`. `BlendRead` queda con el único adaptador de la capa, porque sí transforma la composición.
- Se ajustan los tests que construían instancias de `Pais`, `Region` y `Variedad`.
- Delta sobre la capability existente `inventario-core-models`: un requirement eliminado y otro renombrado y modificado.

**Sin migraciones:** `backend/alembic/versions/` no tiene archivos y `.env` está vacío, así que no existe ninguna base creada. Es refactor de código, no un esquema migrado.

Fuera de alcance:

- El contrato Pydantic (`inventario-schemas`) no cambia: ya expone los tres nombres como `str` y ya no expone `variedad_id` ni `region_id`.
- El cambio archivado `2026-10-24-add-inventario-core-models` no se toca: es historia.
- Routers, `crud.py` y `services.py` del módulo (siguen vacíos).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `inventario-core-models`: se elimina el requirement de las entidades geográficas de origen y se modifica el que define `TipoDeCafe`, reemplazando las FKs por campos de texto.

## Impact

- `backend/app/modules/inventario/models.py`: −3 clases, −2 FKs, +3 columnas `String(50)`.
- `backend/app/modules/inventario/schemas.py`: se borra `TipoDeCafeRead.desde_orm`, se agrega `from_attributes=True` a `TipoDeCafeRead` y `LoteRead`, y se crea `BlendRead.desde_orm`. Los campos de los 13 schemas no cambian.
- `backend/tests/modules/inventario/test_schemas_tipo_de_cafe.py`: rompe en la línea 9 (importa `Pais`, `Region`, `Variedad`) y en 104-106 (los instancia).
- `openspec/specs/inventario-core-models/spec.md`: 4 requirements → 3.
- **Se elimina el riesgo de N+1** que `design.md` del cambio archivado documentaba con `joinedload(variedad)` y `joinedload(region).joinedload(pais)`: no queda ninguna relación que eager-loadear.
- Se pierde la integridad referencial en base para el origen: la validación de que el nombre no esté vacío o fuera de límite queda solo en Pydantic.
