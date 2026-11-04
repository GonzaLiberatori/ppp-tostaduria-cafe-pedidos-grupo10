# Design

## Context

El proyecto sigue el patrón vertical slice con SQLAlchemy 2.0. `backend/app/modules/inventario/models.py` está vacío. El esquema SQL provisto define tablas con FKs entre ellas y una FK hacia `orden_tueste` (módulo `produccion`). Hay que alinearse con `app.core.database.Base` y con las convenciones del proyecto.

## Goals / Non-Goals

**Goals:**
- Implementar los modelos SQLAlchemy correspondientes al esquema provisto en `inventario/models.py`
- Usar `Mapped`/`mapped_column`, tipado estricto, enums para `tipo`/`estado`, `Decimal` para montos/pesos/porcentajes
- Mantener referencias a otros módulos usando nombres de tabla (ej. `ForeignKey("orden_tueste.id")`) para evitar imports circulares
- Seguir el patrón del proyecto (sin SQL crudo, sin lógica de negocio en modelos)

**Non-Goals:**
- Crear migraciones Alembic (se hace después)
- Implementar CRUD/services/routers
- Modificar otros módulos

## Decisions

- **Estilo SQLAlchemy 2.0**: Usar `DeclarativeBase` desde `app.core.database`, `Mapped[...]`, `mapped_column`. Si el proyecto usa otro estilo, se ajustará al existente.
- **Enums**: Definir `enum.Enum` para `LoteTipo` (`VERDE`, `TOSTADO`) y `LoteEstado` (`CERRADO`, `ABIERTO`) y mapearlos con `Enum(...)` de SQLAlchemy.
- **Tipos numéricos**: `DECIMAL(10,2)` -> `Numeric(10,2)`, `DECIMAL(5,2)` -> `Numeric(5,2)`, `TINYINT(1)` -> `Boolean`. `MEDIUMTEXT` -> `Text`. `MEDIUMINT UNSIGNED` -> `Integer` (suficiente para el modelo).
- **FKs cruzadas**: `lote.orden_tueste_id` referencia `orden_tueste.id` vía string FK. `produccion/models.py` puede estar vacío ahora, pero la tabla debe existir en esquema futuro; el modelo debe compilar/importar.
- **Relaciones**: Añadir `relationship` bidireccionales donde útil (`Region.pais`, `TipoDeCafe.region/variedad`, `Blend.tipos_de_cafe` via asociación, `Lote.tipo_de_cafe/blend/orden_tueste`).
- **Asociación**: `BlendHasTipoDeCafe` como modelo de asociación (con `porcentaje`) para poder acceder a él directamente si fuera necesario.

## Risks / Trade-offs

- **Riesgo**: Import circular entre `inventario` y `produccion`. → Mitigación: usar `ForeignKey("orden_tueste.id")` con string, sin importar `produccion.models`.
- **Riesgo**: Diferentes estilos de Base en el proyecto. → Mitigación: leer `backend/app/core/database.py` antes de escribir y ajustar imports.
- **Trade-off**: Añadir relaciones ORM es conveniente pero puede generar joins inesperados; se mantiene mínimo y necesario.
