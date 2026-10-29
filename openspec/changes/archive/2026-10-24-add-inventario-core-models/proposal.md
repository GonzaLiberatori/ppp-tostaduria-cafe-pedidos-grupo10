# Proposal

## Why

El módulo de inventario necesita contar con las entidades base para representar la trazabilidad del café (orígenes, variedades, tipos de café, blends, lotes) tal como se define en el esquema provisto. Actualmente `backend/app/modules/inventario/models.py` está vacío y no existe correspondencia con ese modelo de datos, lo que impide avanzar con el resto del módulo.

## What Changes

- **Agregar modelos SQLAlchemy en inventario**: Crear `Pais`, `Region`, `Variedad`, `TipoDeCafe`, `Blend`, `Lote` y la asociación `BlendHasTipoDeCafe` en `backend/app/modules/inventario/models.py`, siguiendo el esquema MySQL provisto.
- **Definir enums para lote**: Añadir `Enum` para `tipo` (`VERDE`/`TOSTADO`) y `estado` (`CERRADO`/`ABIERTO`).
- **Establecer relaciones y FKs**: Configurar claves foráneas, índices según el esquema, relaciones ORM y referencias entre módulos usando nombres de tabla (evitar imports circulares).
- **Mantener compatibilidad con el patrón del proyecto**: Usar `Mapped`/`mapped_column`, tipado estricto, sin SQL crudo, siguiendo la estructura vertical slice del proyecto.

## Capabilities

### New Capabilities
- `inventario-core-models`: Modelado de entidades geográficas/orígenes, variedades, tipos de café, blends y lotes con sus asociaciones, listo para ser usado por CRUD/services del módulo.

### Modified Capabilities
- (ninguna)

## Impact

- **Código afectado**: `backend/app/modules/inventario/models.py` (único archivo modificado en este cambio). Posiblemente se aprovechan imports desde `app.core.database` y se referencian tablas de otros módulos (`orden_tueste`).
- **APIs**: Ninguna (solo modelos).
- **Dependencias**: Sin nuevas dependencias.
- **Sistemas**: Preparación para futuras migraciones Alembic y para capas CRUD/services.
