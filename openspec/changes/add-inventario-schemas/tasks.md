# Tasks

## 1. Preparación del contrato

- [ ] 1.1 Confirmar el entorno de validación: `python -c "import pydantic; print(pydantic.VERSION)"` en `backend/` debe reportar 2.x, y `python -c "from app.modules.inventario.models import LoteTipo, LoteEstado"` debe importar sin error.
- [ ] 1.2 Definir en `inventario/schemas.py` los tipos anotados de decimal reutilizables (`Annotated[Decimal, Field(...)]`) con precisión igual a la columna: 10,2 para precios y kilos, 5,2 para humedad y porcentaje. Verificación: un test que envía `Decimal("1.999")` a un campo 5,2 y espera error de validación.
- [ ] 1.3 Verificar que la precisión declarada coincide con `models.py` campo por campo (`precio_por_kg_verde` 10,2 · `humedad` 5,2 · `kg_disponibles` 10,2 · `kg_reales` 10,2 · `porcentaje` 5,2) leyendo `Numeric(...)` de cada `mapped_column`; corregir el alias si alguno difiere.

## 2. Schemas de TipoDeCafe

- [ ] 2.1 Implementar `TipoDeCafeCreate` con `organico`, `precio_por_kg_verde`, `variedad`, `region` y `pais` obligatorios, `variedad`/`region`/`pais` como `str` no vacío y `extra="forbid"`. Verificación: test que acepta el payload mínimo y otro que omite cada campo y espera error.
- [ ] 2.2 Implementar `TipoDeCafeUpdate` con los mismos cinco atributos, todos `Optional[...] = None`. Verificación: tests de actualización de un solo campo y de payload vacío, ambos válidos.
- [ ] 2.3 Implementar `TipoDeCafeRead` con `id`, `organico`, `precio_por_kg_verde`, `variedad`, `region`, `pais` como `str`, sin `variedad_id` ni `region_id`, y documentar en el design el aplanado desde el ORM. Verificación: test que confirma que `model_json_schema()` expone `id` como identificador y no expone `variedad_id` ni `region_id`.
- [ ] 2.4 Implementar el aplanado de `TipoDeCafeRead` desde el objeto ORM (`tipo.variedad.nombre`, `tipo.region.nombre`, `tipo.region.pais.nombre`). Verificación: test que arma el schema desde una instancia de `TipoDeCafe` con relaciones asignadas y comprueba los tres nombres.
- [ ] 2.5 Implementar `TipoDeCafeDelete` con solo `id` y `extra="forbid"`. Verificación: test que rechaza un payload con `id` más otro campo.
- [ ] 2.6 Escribir `backend/tests/modules/inventario/test_schemas_tipo_de_cafe.py` cubriendo 2.1 a 2.5 y verificar con `python -m pytest tests/modules/inventario/test_schemas_tipo_de_cafe.py -q` desde `backend/`.
- [ ] 2.7 Agregar `description` en cada `Field` de los cuatro schemas de TipoDeCafe para que Swagger documente el contrato. Verificación: `TipoDeCafeRead.model_json_schema()` incluye descripción en todos los campos.

## 3. Schemas de Blend

- [ ] 3.1 Implementar `BlendComposicionItem` con `tipo_de_cafe_id: int` y `porcentaje` decimal 5,2 mayor a cero, y `extra="forbid"`. Verificación: test que rechaza `porcentaje` cero y campos no declarados.
- [ ] 3.2 Implementar `BlendCreate` con `nombre`, `precio_por_kg_verde`, `descripcion` y `tipos_de_cafe` como lista del ítem anterior. Verificación: test que acepta un blend con tres proporciones válidas.
- [ ] 3.3 Implementar la validación de composición en `BlendCreate` y `BlendUpdate`: al menos un elemento, `tipo_de_cafe_id` sin repetir y suma de porcentajes igual a `100` comparando con `Decimal` cuantizado a dos decimales. Verificación: tres tests negativos (lista vacía, id repetido, suma 99.99) y uno positivo con `33.33 + 33.33 + 33.34`.
- [ ] 3.4 Implementar `BlendUpdate` con los cuatro atributos opcionales, donde `tipos_de_cafe` reemplaza la composición completa. Verificación: test que actualiza solo `nombre` y otro que actualiza solo la composición.
- [ ] 3.5 Implementar `BlendRead` con `id` más los cuatro atributos y `BlendDelete` con solo `id`, ambos `extra="forbid"` en el de borrado. Verificación: test de serialización de un blend con composición y test de rechazo de campos extra en el borrado.
- [ ] 3.6 Escribir `backend/tests/modules/inventario/test_schemas_blend.py` cubriendo 3.1 a 3.5 y verificar con `python -m pytest tests/modules/inventario/test_schemas_blend.py -q` desde `backend/`.
- [ ] 3.7 Documentar con `description` los campos de los cinco schemas de blend. Verificación: `BlendRead.model_json_schema()` describe el ítem de composición y sus dos campos.

## 4. Schemas de Lote

- [ ] 4.1 Implementar `LoteCreate` con `tipo` y `estado` tipados con `LoteTipo`/`LoteEstado` importados de `models.py`, más `fecha_vencimiento`, `humedad`, `kg_disponibles`, `kg_reales` y `ubicacion_fisica` obligatorios. Verificación: test que acepta el payload mínimo.
- [ ] 4.2 Marcar como no obligatorios en `LoteCreate` los cuatro atributos nullable del modelo (`observaciones`, `tipo_de_cafe_id`, `blend_id`, `orden_tueste_id`) con valor por defecto `None`. Verificación: test que crea un lote omitiendo los cuatro y otro que los envía en `null`.
- [ ] 4.3 Implementar `LoteUpdate` con `estado`, `fecha_vencimiento`, `humedad`, `kg_disponibles`, `kg_reales`, `ubicacion_fisica` y `observaciones` opcionales, y `extra="forbid"` para rechazar `tipo`, `tipo_de_cafe_id`, `blend_id` y `orden_tueste_id`. Verificación: un test por cada campo prohibido esperando error de validación, más un test de actualización parcial válida.
- [ ] 4.4 Implementar `LoteRead` con `id` y los once atributos restantes, admitiendo `null` en los cuatro nullable, y `LoteDelete` con solo `id`. Verificación: test de serialización de un lote con los cuatro nullable en `None` y test de rechazo de campos extra en el borrado.
- [ ] 4.5 Verificar que `LoteRead` no omite `orden_tueste_id` pese a que la tabla `orden_tueste` aún no existe, y dejar registrada la deuda en el design. Verificación: `model_fields` de `LoteRead` contiene `orden_tueste_id` y el design ya lo documenta en Risks.
- [ ] 4.6 Escribir `backend/tests/modules/inventario/test_schemas_lote.py` cubriendo 4.1 a 4.5 y verificar con `python -m pytest tests/modules/inventario/test_schemas_lote.py -q` desde `backend/`.
- [ ] 4.7 Documentar con `description` los campos de los cuatro schemas de lote, incluyendo los valores admitidos de `tipo` y `estado`. Verificación: `LoteCreate.model_json_schema()` muestra los enums con `VERDE`/`TOSTADO` y `CERRADO`/`ABIERTO`.

## 5. Ediciones puntuales de Lote

- [ ] 5.1 Implementar `LoteKgDisponiblesUpdate` con solo `kg_disponibles` decimal 10,2 y `extra="forbid"`. Verificación: test que acepta el campo y rechaza un payload con `kg_reales`.
- [ ] 5.2 Implementar `LoteKgRealesUpdate` con solo `kg_reales` decimal 10,2 y `extra="forbid"`. Verificación: test que acepta el campo y rechaza un payload con `kg_disponibles`.
- [ ] 5.3 Implementar `LoteEstadoUpdate` con solo `estado` tipado con `LoteEstado` y `extra="forbid"`. Verificación: test que rechaza un `estado` fuera del enum.
- [ ] 5.4 Agregar los tres casos a `test_schemas_lote.py` y verificar con `python -m pytest tests/modules/inventario/test_schemas_lote.py -q` desde `backend/`.

## 6. Verificación de integración

- [ ] 6.1 Verificar que el módulo importa limpio: `python -c "from app.modules.inventario import schemas"` desde `backend/`, sin warnings de Pydantic.
- [ ] 6.2 Verificar que los 16 schemas generan JSON Schema sin error, recorriendo con un test que llame a `model_json_schema()` sobre cada uno, y que ningún schema de entrada admite campos no declarados.
- [ ] 6.3 Correr la suite completa del módulo con `python -m pytest tests/modules/inventario -q` desde `backend/` y confirmar que no hay fallos.

## Workflow follow-up

- Revisar los artefactos antes de implementar y resolver la Open Question de resolución de nombres de variedad, región y país cuando se aborde `services.py`.
- Archivar el cambio con `/opsx-archive` una vez implementado y revisado.
- El commit requiere aprobación explícita del usuario antes de ejecutarse.
