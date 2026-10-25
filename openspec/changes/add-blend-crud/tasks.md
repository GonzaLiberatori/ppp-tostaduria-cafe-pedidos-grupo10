# Tasks

## 1. Schemas: dos cambios puntuales

- [ ] 1.1 Cambiar `min_length=1` por `min_length=2` en `BlendCreate.tipos_de_cafe` y `BlendUpdate.tipos_de_cafe`. Verificación: test que una composición de un solo elemento se rechaza en Create y en Update.
- [ ] 1.2 Reemplazar en `_validar_composicion` la igualdad exacta con 100 por el rango `99.99 <= total <= 100.00`, y actualizar el docstring. Verificación: tests que aceptan `99.99` y `100.00`, y rechazan `99.98` y `100.01`.
- [ ] 1.3 Reescribir `test_create_rechaza_porcentajes_que_no_suman_cien`, que usa `60.00 + 39.99 = 99.99` y ahora sería válido. Verificación: `python -m pytest tests/modules/inventario/test_schemas_blend.py -q` desde `backend/` sin fallos.

## 2. Capa de datos: crud.py

- [ ] 2.1 Reemplazar `REFERENCIAS_PROHIBIDAS: tuple[type, ...]` y la constante `_COLUMNA_TIPO_DE_CAFE` por un `dict[type, tuple[tuple[type, str], ...]]` que lleve `(entidad referenciadora, columna FK)` por cada entidad borrable. Verificación: la entrada de `Lote` usa `tipo_de_cafe_id` para `TipoDeCafe` y `blend_id` para `Blend`, y el grep ya no encuentra `_COLUMNA_TIPO_DE_CAFE`.
- [ ] 2.2 Adaptar `cuentas_de_referencias(db, entidad, tipo_id)` para que reciba la entidad que se va a borrar. Verificación: los tests existentes de `TipoDeCafe` siguen en verde y los nuevos de `Blend` devuelven `{"Lote": 1}` cuando hay lote.
- [ ] 2.3 Implementar `obtener_blend(db, blend_id) -> Blend | None`. Verificación: test que devuelve el registro con id conocido y `None` con uno inexistente.
- [ ] 2.4 Implementar `crear_blend(db, datos: BlendCreate) -> Blend`: insertar el blend, hacer `flush` para obtener el `id` y luego crear un `BlendHasTipoDeCafe` por item de la lista. Verificación: test que relee el blend con dos filas de composición.
- [ ] 2.5 Implementar `actualizar_blend(db, blend, cambios: dict[str, object]) -> Blend` aplicando solo las claves recibidas, sin commit. Verificación: test con `{"precio_por_kg_verde": "1100.00"}` cambia solo ese atributo.
- [ ] 2.6 Implementar `reemplazar_composicion(db, blend, items) -> None`: borrar todos los `BlendHasTipoDeCafe` del blend y crear los nuevos. Verificación: test que parte de dos tipos, reemplaza por una lista distinta y comprueba que no quedan filas viejas.
- [ ] 2.7 Implementar `eliminar_composicion(db, blend) -> None` y `eliminar_blend(db, blend) -> None`, ambas sin commit. Verificación: test que comprueba que la composición desaparece junto con el blend.
- [ ] 2.8 Implementar `nombre_de_blend_ya_en_usado(db, nombre, excluir_id=None) -> bool`. Verificación: test que devuelve `True` con un nombre ajeno, `False` con uno libre y `False` cuando el nombre es el del propio blend pasado en `excluir_id`.

## 3. Capa de negocio: services.py

- [ ] 3.1 Definir `BlendNoEncontrado`, `BlendReferenciado` (con el detalle de entidades bloqueantes) y `NombreDeBlendEnUso` (con el nombre en conflicto). Verificación: test que las tres se levantan con el mensaje esperado.
- [ ] 3.2 Implementar `crear_blend(db, datos) -> BlendRead`: comprobar el nombre (→ `NombreDeBlendEnUso`), crear con composición y hacer commit en una sola transacción. Verificación: test que persiste el blend con su composición, test con nombre repetido que lanza la excepción y no deja registros, y test que un fallo deja todo como estaba.
- [ ] 3.3 Implementar `obtener_blend(db, id) -> BlendRead` que lanza `BlendNoEncontrado` si no existe. Verificación: test de éxito y test con id inexistente.
- [ ] 3.4 Implementar `actualizar_blend(db, id, datos: BlendUpdate) -> BlendRead`: existencia primero, luego `model_dump(exclude_none=True)`, chequeo de nombre excluyendo al propio blend y reemplazo de composición si viene lista, todo con commit. Verificación: tests para cada escenario del requirement — un solo atributo, atributo en `null`, cuerpo vacío, id inexistente, precio inválido, composición inválida, nombre de otro blend y nombre propio.
- [ ] 3.5 Implementar `eliminar_blend(db, id) -> None`: existencia, chequeo de bloqueos (`Lote`, `detalle_pedido`) ignorando la composición propia, borrado de composición y luego del blend, con commit. Verificación: test de borrado exitoso con composición, test bloqueado por lote que deja todo intacto, y test con id inexistente.
- [ ] 3.6 Verificar que `services.py` no duplica las validaciones de precio, longitud de nombre ni composición. Verificación: `grep -n "precio_por_kg_verde *<=\|min_length\|sum(" backend/app/modules/inventario/services.py` sin coincidencias relevantes.

## 4. Capa HTTP: router.py

- [ ] 4.1 Agregar el prefijo `/blends` y exponer `POST` con `response_model=BlendRead` y `status_code=201`. Verificación: test con `TestClient` que devuelve 201, el `id` y la lista de composición.
- [ ] 4.2 Exponer `GET /{id}` con `response_model=BlendRead`. Verificación: test que devuelve 200 con la composición y 404 con id inexistente.
- [ ] 4.3 Exponer `PATCH /{id}` con `response_model=BlendRead`. Verificación: test que devuelve 200 cambiando solo el atributo enviado, 404 con id inexistente, 422 con precio no positivo y 409 con nombre de otro blend.
- [ ] 4.4 Exponer `DELETE /{id}` con `status_code=204` y sin `response_model`. Verificación: test que devuelve 204, 404 con id inexistente y 409 cuando un lote lo referencia, con el detalle nombrando a la entidad.
- [ ] 4.5 Extender el mapeo de excepciones de dominio a códigos HTTP con `if / elif / else` para cubrir las tres excepciones nuevas, y verificar que `router.py` no abre sesión directamente. Verificación: los tests de 4.2-4.4 pasan y `grep -n "Session(" backend/app/modules/inventario/router.py` sin coincidencias.

## 5. Verificación de integración

- [ ] 5.1 Escribir `backend/tests/modules/inventario/test_services_blend.py` cubriendo 3.1 a 3.5 y verificar con `python -m pytest tests/modules/inventario/test_services_blend.py -q` desde `backend/`.
- [ ] 5.2 Escribir `backend/tests/modules/inventario/test_router_blend.py` con app local, `dependency_overrides` sobre `get_db` y SQLite en memoria con `StaticPool` y `check_same_thread=False`, cubriendo 4.1 a 4.4. Verificación: `python -m pytest tests/modules/inventario/test_router_blend.py -q` desde `backend/`.
- [ ] 5.3 Verificar la separación de capas: `crud.py` sin FastAPI ni `.commit()`, `services.py` sin FastAPI y `router.py` sin `Session(`. Verificación: los cuatro contadores del grep en 0.
- [ ] 5.4 Correr la suite completa del módulo con `python -m pytest tests/modules/inventario -q` desde `backend/` y confirmar que no hay fallos.
- [ ] 5.5 Correr `openspec validate add-blend-crud --strict` y `openspec validate --specs` desde la raíz; ambos deben terminar en `valid` / `passed`.

## Workflow follow-up

- Archivar el cambio con `/opsx-archive` una vez revisado: crea la capability `inventario-blend` y sincroniza el delta `MODIFIED` sobre `inventario-schemas`.
- Resolver la Open Question de infraestructura de arranque antes de la primera migración.
- El commit requiere aprobación explícita del usuario antes de ejecutarse.
