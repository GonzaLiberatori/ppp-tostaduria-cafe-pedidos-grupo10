# Proposal

## Why

El módulo de inventario ya tiene sus modelos persistidos (`Pais`, `Region`, `Variedad`, `TipoDeCafe`, `Blend`, `BlendHasTipoDeCafe`, `Lote`) pero `backend/app/modules/inventario/schemas.py` está vacío. Sin schemas Pydantic no existe contrato de entrada/salida para la API: no hay validación, no hay documentación OpenAPI y los routers no pueden construirse. Se necesita definir esa capa antes de implementar routers, crud y services.

## What Changes

- Se crean los schemas de creación, lectura, actualización y eliminación para `TipoDeCafe`, `Blend` y `Lote` en `backend/app/modules/inventario/schemas.py`.
- `TipoDeCafe` recibe y devuelve `variedad`, `region` y `pais` **como texto** (`str`). El identificador de `TipoDeCafe` es su propio `id`; los nombres de origen son atributos descriptivos y nunca se envían como `variedad_id` ni `region_id`. No se crean endpoints para `Variedad`, `Region` ni `Pais`.
- `Blend` recibe y devuelve su composición como lista de objetos `{tipo_de_cafe_id, porcentaje}`. No se crean endpoints para `BlendHasTipoDeCafe`.
- `Lote` expone además tres schemas de edición puntual: `kg_disponibles`, `kg_reales` y `estado`, todos resueltos por id de lote.
- Regla transversal de opcionalidad:
  - **Create**: los atributos `nullable=True` del modelo no son obligatorios.
  - **Update**: todos los atributos editables son opcionales.
  - **Read**: siempre incluye `id` y devuelve todos los datos de la clase (los nullable pueden ser `null`).
  - **Delete**: solo `id`.

Fuera de alcance de este cambio:

- Routers, `crud.py` y `services.py` del módulo.
- La resolución de los nombres de variedad, región y país (búsqueda, creación implícita o error si no existen). Queda como decisión pendiente del equipo y se documenta en `design.md`.
- Migraciones de base de datos.

## Capabilities

### New Capabilities

- `inventario-schemas`: contratos Pydantic de entrada y salida (Create, Read, Update, Delete) para `TipoDeCafe`, `Blend` y `Lote`, incluyendo las reglas de opcionalidad por operación y las ediciones puntuales de lote.

### Modified Capabilities

Ninguna. `inventario-core-models` describe la persistencia y no cambia; este cambio agrega una capa nueva.

## Impact

- `backend/app/modules/inventario/schemas.py` (hoy vacío): se completa con los schemas de las tres entidades.
- `backend/app/modules/inventario/models.py`: solo se importa (`LoteTipo`, `LoteEstado`); no se modifica.
- Dependencia de Pydantic v2 (`field_validator` / `model_validator`) para el aplanado de nombres y la validación de composición de blend.
- Habilita los cambios posteriores de `router.py`, `crud.py` y `services.py` del módulo de inventario.
- Riesgo detectado: `Lote.orden_tueste_id` declara `ForeignKey("orden_tueste.id")` pero la tabla no existe todavía en `backend/app/modules/produccion/models.py`. El schema de lectura va a exponer el campo igualmente; la deuda se documenta en `design.md`.
