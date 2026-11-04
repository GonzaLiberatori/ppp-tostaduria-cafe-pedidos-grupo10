# Design

## Context

`TipoDeCafe` hoy referencia su origen con dos FKs:

```python
region_id:   Mapped[int] = mapped_column(ForeignKey("region.id"), nullable=False, index=True)
variedad_id: Mapped[int] = mapped_column(ForeignKey("variedad.id"), nullable=False, index=True)
```

`Region` a su vez tiene `pais_id` con FK a `pais`, así que un nombre de país está a **tres saltos** del tipo de café. Eso ya obliga a `TipoDeCafeRead.desde_orm` a aplanar `tipo.variedad.nombre`, `tipo.region.nombre` y `tipo.region.pais.nombre`, y el `design.md` del cambio archivado registra el riesgo de N+1 que conlleva.

Datos que condicionan el cambio:

- El contrato Pydantic **ya es strings**: `TipoDeCafeCreate` y `TipoDeCafeRead` reciben y devuelven `variedad`, `region` y `pais` como `str`, sin `variedad_id` ni `region_id`. La capa de modelos es la única que todavía piensa en entidades.
- No hay endpoints para `Pais`, `Region` ni `Variedad`.
- No hay índices únicos en `nombre` de ninguna de las tres tablas, así que el get-or-create de dos niveles que exigiría el flujo de alta tiene race condition desde el día uno.
- No hay migraciones y `.env` está vacío: no existe ninguna base creada.

Ver `proposal.md` para la motivación y `openspec/specs/inventario-core-models/spec.md` para los requisitos.

## Goals / Non-Goals

**Goals:**

- Que `TipoDeCafe` sea autosuficiente en su origen: tres columnas planas, cero joins.
- Mantener el límite de 50 caracteres que hoy imponen `String(50)` y que el schema ya valida.
- Eliminar el riesgo de N+1 y el flujo de get-or-create de dos niveles.

**Non-Goals:**

- Cambiar el contrato Pydantic de `inventario-schemas`.
- Modificar el cambio archivado `2026-10-24-add-inventario-core-models` o su `design.md`.
- Routers, `crud.py` y `services.py` (siguen vacíos).

## Decisions

### Texto plano en lugar de tablas

Se borran `Pais`, `Region` y `Variedad`, y `TipoDeCafe` pasa a tener `variedad: Mapped[str]`, `region: Mapped[str]` y `pais: Mapped[str]`.

**Por qué:** las tres tablas solo alimentaban tres columnas de texto que el sistema lee como nombre, nunca como identificador. No hay endpoints que las administren ni contratos que las expongan. La normalización que aportaban (corregir un typo en un solo lugar) no se usaba, y su costo era concreto: dos tablas intermedias, tres joins, un get-or-create de dos niveles y una carrera por la falta de índices únicos.

**Alternativa descartada:** mantener las tablas y agregar `unique=True`. No resuelve nada de lo que el cambio busca y obligaría a un unique **compuesto** `(pais_id, nombre)` en `region` — un `unique=True` simple en `nombre` estaría mal, porque "Huila" deja de ser única si dos países la tienen.

### `String(50)`, no `Text`

**Por qué:** es exactamente el límite que ya imponen `Pais.nombre`, `Region.nombre` y `Variedad.nombre`, y el que el schema aplica con `Field(max_length=50)` en `variedad`, `region` y `pais`. Cambiar a `Text` rompería la simetría: el modelo aceptaría lo que la validación rechaza.

**Consecuencia:** se mantiene el mismo error de validación por longitud que existe hoy, en la misma capa.

### Los Read se construyen desde el ORM: `from_attributes` salvo donde hay transformación

`TipoDeCafeRead` y `LoteRead` habilitan `from_attributes=True` y no tienen método propio: quien los usa hace `TipoDeCafeRead.model_validate(obj)` directamente. `BlendRead` sí conserva un `desde_orm()`.

**Por qué:** con las tres columnas planas, `TipoDeCafeRead` y `LoteRead` son copia campo por campo de los atributos del modelo — cero transformación. Un adaptador que no transforma es boilerplate: hay que mantenerlo, tiparlo y testearlo a cambio de nada. Verificado: `desde_orm(tipo)` y `model_validate(tipo)` devuelven el mismo dict.

**Dónde sí hace falta el adaptador:** `BlendRead` recibe `blend.tipos_de_cafe`, una lista de filas de `BlendHasTipoDeCafe` con `blend_id`, `tipo_de_cafe_id`, `porcentaje`, `blend` y `tipo_de_cafe`, y debe entregar una lista de `BlendComposicionItem` con solo `tipo_de_cafe_id` y `porcentaje`. Ahí hay selección y transformación reales.

**Regla:** `from_attributes` cuando el modelo y el schema coinciden campo por campo; adaptador explícito cuando hay que derivar algo.

**Por qué no se propaga `from_attributes` a `BlendComposicionItem`:** verificado que habilitándolo en el ítem anidado, `BlendRead` también se arma sin adaptador y `extra="forbid"` sigue rechazando campos extra en los payloads de diccionario. Se descarta igual porque `BlendComposicionItem` es un schema de **entrada** (`BlendCreate` / `BlendUpdate`): darle esa config pone una bandera de lectura ORM en un payload de request.

**Verificación de la flag:** `extra="forbid"` sigue funcionando con `from_attributes` habilitado, tanto en objetos ORM como en diccionarios.

**Corrección:** la primera versión de este documento recomendaba conservar `desde_orm()` por simetría y afirmaba que `BlendRead` no podía resolverse con `from_attributes`. Ambas cosas se revisaron con pruebas: `model_validate` sobre el ORM falla con `model_type` sin la flag y pasa con ella.

### `extra="forbid"` sigue rechazando los ids viejos

Los schemas no cambian, así que `TipoDeCafeCreate` y `TipoDeCafeUpdate` siguen rechazando `variedad_id` y `region_id` con 422. Eso ahora es **más** importante: los clientes que ya mandaban esos campos reciben un error claro en lugar de ignorarse en silencio.

### Sin migración y sin `DROP TABLE`

**Por qué:** `backend/alembic/versions/` está vacío y `.env` tiene 1 byte. No existe ninguna base con esas tablas, así que no hay nada que eliminar en disco. El cambio es refactor de código.

**Rollback:** revertir los tres archivos (`models.py`, `schemas.py`, `test_schemas_tipo_de_cafe.py`). Sin estado persistido que deshacer.

## Risks / Trade-offs

- **Se pierde la integridad referencial del origen** → el límite de longitud y el carácter no vacío quedan solo en Pydantic. Es aceptable porque el origen es atributo descriptivo, no clave; si algún día se necesita una lista canónica de países, se reintroduce como entidad aparte sin tocar `tipo_de_cafe`.
- **Se pierde la normalización** → "Huila" y "huila" dejan de ser la misma fila y pasan a ser dos strings distintos. Hoy tampoco se corregía en un solo lado porque no había forma de editar `Region`, así que el riesgo no es nuevo, solo deja de estar protegido por el modelo.
- **El `design.md` del cambio archivado queda obsoleto** → documenta `joinedload(variedad)` y `joinedload(region).joinedload(pais)` como obligatorios. No se edita (es historia), pero hay que tenerlo presente al leerlo.
- **`test_schemas_tipo_de_cafe.py` rompe de entrada** → importa `Pais`, `Region`, `Variedad` en la línea 9 y los instancia en 104-106. Se reescribe el helper `_tipo_de_cafe_de_ejemplo()` con strings directos.

## Migration Plan

No aplica: no hay base creada ni migraciones. Despliegue = revertir los tres archivos.

## Open Questions

Ninguna. El límite de longitud quedó resuelto (`String(50)`).
