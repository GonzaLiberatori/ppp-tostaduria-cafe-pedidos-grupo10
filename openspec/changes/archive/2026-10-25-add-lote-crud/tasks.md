# Tasks

## 1. Schemas

- [x] 1.1 Agregar `le=100` a `HumedadPorcentaje`. Verificación: test que acepta `100.00` y rechaza `100.01` y `-0.01`.
- [x] 1.2 Verificar que `kg_reales` sigue usando `Kilos` (`ge=0`) en `LoteCreate`, `LoteUpdate` y `LoteKgRealesUpdate`, y que no hace falta ningún alias nuevo. Verificación: tests que aceptan `kg_reales = 0` en los tres y que rechazan un valor negativo.
- [x] 1.3 Quitar `kg_disponibles` de `LoteCreate`. Verificación: `LoteCreate.model_fields` no contiene la clave y enviarla devuelve error de validación.
- [x] 1.4 Agregar un `model_validator(mode="after")` en `LoteCreate` con la regla `if / elif / else`: `VERDE` con `orden_tueste_id` se rechaza, `TOSTADO` sin `orden_tueste_id` se rechaza, lo contrario pasa. Verificación: cuatro tests cubriendo las cuatro combinaciones.
- [x] 1.5 Agregar el validador de origen único en `LoteCreate`: exactamente uno entre `tipo_de_cafe_id` y `blend_id`. Verificación: tests de ninguno, ambos y cada uno por separado.
- [x] 1.6 Adaptar `test_schemas_lote.py`: sacar `kg_disponibles` de `PAYLOAD_BASE`, cambiar el assert de `kg_disponibles` para comparar contra `kg_reales`, quitar esa clave de `test_create_rechaza_campo_obligatorio_faltante` y apuntar `test_precision_coincide_con_la_columna_del_modelo` a `LoteRead`. Verificación: `python -m pytest tests/modules/inventario/test_schemas_lote.py -q` desde `backend/` sin fallos.

## 2. Capa de datos: crud.py

- [x] 2.1 Implementar `obtener_lote(db, lote_id) -> Lote | None`. Verificación: test que devuelve el registro con id conocido y `None` con uno inexistente.
- [x] 2.2 Implementar `crear_lote(db, datos: LoteCreate, kg_disponibles: Decimal) -> Lote`, recibiendo el valor derivado por quien llama. Verificación: test que relee el registro con `kg_disponibles` igual al valor pasado.
- [x] 2.3 Implementar `actualizar_lote(db, lote, cambios: dict[str, Any]) -> Lote` sin commit. Verificación: test con `{"estado": "CERRADO"}` cambia solo `estado`.
- [x] 2.4 Implementar `eliminar_lote(db, lote) -> None` sin commit. Verificación: test que comprueba el borrado.
- [x] 2.5 Implementar `existe_registro(db, entidad, entidad_id) -> bool` para consultar cualquier tabla por su clave primaria. Verificación: test que devuelve `True` con un registro existente y `False` con uno inexistente, y que funciona tanto para `TipoDeCafe` como para `Blend`.

## 3. Capa de negocio: services.py

- [x] 3.1 Definir `LoteNoEncontrado` (con el id) y `OrigenDeLoteNoEncontrado` (con la entidad y el id). Verificación: test que ambas se levantan con el mensaje esperado.
- [x] 3.2 Implementar `crear_lote(db, datos) -> LoteRead`: comprobar que el origen elegido existe (→ `OrigenDeLoteNoEncontrado`), derivar `kg_disponibles = kg_reales`, crear y hacer commit en una sola transacción. Verificación: test que el registro creado tiene `kg_disponibles == kg_reales`, test con origen inexistente que lanza la excepción y no deja registros, y test que un fallo no deja nada huérfano.
- [x] 3.3 Implementar `obtener_lote(db, id) -> LoteRead` que lanza `LoteNoEncontrado` si no existe. Verificación: test de éxito y test con id inexistente.
- [x] 3.4 Implementar `actualizar_lote(db, id, datos: LoteUpdate) -> LoteRead`: existencia primero, luego `model_dump(exclude_none=True)` y commit. Verificación: tests para un solo atributo, atributo en `null`, cuerpo vacío, id inexistente, humedad fuera de rango y `kg_reales` negativo.
- [x] 3.5 Implementar `eliminar_lote(db, id) -> None`: existencia y commit, sin bloqueos (nadie tiene FK hacia `lote`). Verificación: test de borrado exitoso, test con id inexistente, y test que comprueba que `TipoDeCafe` y `Blend` referenciados siguen existiendo.
- [x] 3.6 Verificar que `services.py` no duplica validaciones de forma (enums, rangos, longitud). Verificación: `grep -n "humedad *<\|min_length\|LoteTipo ==" backend/app/modules/inventario/services.py` sin coincidencias relevantes.

## 4. Capa HTTP: router.py

- [x] 4.1 Exponer `POST /lotes` con `response_model=LoteRead` y `status_code=201`. Verificación: test con `TestClient` que devuelve 201 con el `id` y con `kg_disponibles` igual a `kg_reales`.
- [x] 4.2 Exponer `GET /lotes/{id}` con `response_model=LoteRead`. Verificación: test que devuelve 200 con las claves foráneas sin resolver y 404 con id inexistente.
- [x] 4.3 Exponer `PATCH /lotes/{id}` con `response_model=LoteRead`. Verificación: test que devuelve 200 cambiando solo el atributo enviado, 404 con id inexistente y 422 con `humedad` fuera de rango.
- [x] 4.4 Exponer `DELETE /lotes/{id}` con `status_code=204` y sin `response_model`. Verificación: test que devuelve 204 y 404 con id inexistente.
- [x] 4.5 Extender `_a_codigo_http` con `LoteNoEncontrado` y `OrigenDeLoteNoEncontrado`, y verificar que `router.py` no abre sesión directamente. Verificación: los tests de 4.2-4.4 pasan y `grep -n "Session(" backend/app/modules/inventario/router.py` sin coincidencias.

## 5. Verificación de integración

- [x] 5.1 Escribir `backend/tests/modules/inventario/test_services_lote.py` cubriendo 3.1 a 3.5 y verificar con `python -m pytest tests/modules/inventario/test_services_lote.py -q` desde `backend/`.
- [x] 5.2 Escribir `backend/tests/modules/inventario/test_router_lote.py` con app local, `dependency_overrides` sobre `get_db` y SQLite en memoria con `StaticPool` y `check_same_thread=False`, cubriendo 4.1 a 4.4. Verificación: `python -m pytest tests/modules/inventario/test_router_lote.py -q` desde `backend/`.
- [x] 5.3 Verificar la separación de capas: `crud.py` sin FastAPI ni `.commit()`, `services.py` sin FastAPI y `router.py` sin `Session(`. Verificación: los cuatro contadores del grep en 0.
- [x] 5.4 Correr la suite completa del módulo con `python -m pytest tests/modules/inventario -q` desde `backend/` y confirmar que no hay fallos.
- [x] 5.5 Correr `openspec validate add-lote-crud --strict` y `openspec validate --specs` desde la raíz; ambos deben terminar en `valid` / `passed`.

## Workflow follow-up

- Archivar el cambio con `/opsx-archive` una vez revisado: crea la capability `inventario-lote` y sincroniza el delta `MODIFIED` sobre `inventario-schemas`.
- Retomar la comprobación referencial de `orden_tueste_id` cuando `produccion` defina `OrdenTueste` (implica rehacer la FK y regenerar la migración).
- Resolver la Open Question de infraestructura de arranque antes de la primera migración.
- El commit requiere aprobación explícita del usuario antes de ejecutarse.
