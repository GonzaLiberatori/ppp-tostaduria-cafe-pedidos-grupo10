# Tasks

## 1. Prerequisito: desbloquear la creación de tablas

- [x] 1.1 Retirar `ForeignKey("orden_tueste.id")` de `Lote.orden_tueste_id` en `backend/app/modules/inventario/models.py`, conservando la columna y su `index=True`. Verificación: `python -c "from sqlalchemy import create_engine, inspect; from app.core.database import Base; from app.modules.inventario import models; e=create_engine('sqlite://'); Base.metadata.create_all(e); print(sorted(inspect(e).get_table_names()))"` desde `backend/` imprime la lista completa incluyendo `lote`. → `['blend', 'blend_has_tipo_de_cafe', 'lote', 'tipo_de_cafe']`
- [x] 1.2 Dejar comentado en `models.py`, junto a la columna, qué hay que rehacer cuando `produccion` defina `OrdenTueste`. Verificación: `grep -n "orden_tueste" backend/app/modules/inventario/models.py` muestra la columna sin FK y el comentario que nombra el reintegro.

## 2. Capa de datos: crud.py

- [x] 2.1 Implementar `obtener_tipo_de_cafe(db, id) -> TipoDeCafe | None` con `db.get` o `select`. Verificación: test que devuelve el registro con id conocido y `None` con uno inexistente.
- [x] 2.2 Implementar `crear_tipo_de_cafe(db, datos: TipoDeCafeCreate) -> TipoDeCafe`. Verificación: test que inserta y relee el registro persistido.
- [x] 2.3 Implementar `actualizar_tipo_de_cafe(db, tipo, cambios: dict[str, object]) -> TipoDeCafe`, aplicando solo las claves del dict sin hacer commit. Verificación: test con `{"organico": False}` cambia solo `organico`.
- [x] 2.4 Implementar `eliminar_tipo_de_cafe(db, tipo) -> None` sin commit. Verificación: test que llama al borrado.
- [x] 2.5 Implementar `cuentas_de_referencias(db, id) -> dict[str, int]` que recorra la tupla `REFERENCIAS_PROHIBIDAS` y cuente cuántas filas bloquean el borrado. Verificación: test con un tipo referenciado por blend devuelve `{"BlendHasTipoDeCafe": 1}` y con un tipo libre devuelve todos los contadores en 0.
- [x] 2.6 Declarar `REFERENCIAS_PROHIBIDAS` con `BlendHasTipoDeCafe` y `Lote`, y comentar que `detalle_pedido` entra cuando exista. Verificación: `grep -n "REFERENCIAS_PROHIBIDAS\|detalle_pedido" backend/app/modules/inventario/crud.py` muestra la tupla y la nota.

## 3. Capa de negocio: services.py

- [x] 3.1 Definir las excepciones de dominio `TipoDeCafeNoEncontrado` y `TipoDeCafeReferenciado` (esta última con el detalle de entidades bloqueantes). Verificación: test que ambas se levantan con el mensaje esperado.
- [x] 3.2 Implementar `crear_tipo_de_cafe(db, datos) -> TipoDeCafeRead` con commit y rollback ante error, devolviendo `TipoDeCafeRead.model_validate(...)`. Verificación: test que el registro queda persistido, y test que un fallo no deja registros huérfanos.
- [x] 3.3 Implementar `obtener_tipo_de_cafe(db, id) -> TipoDeCafeRead` que lanza `TipoDeCafeNoEncontrado` si no existe. Verificación: test de éxito y test que levanta la excepción con id inexistente.
- [x] 3.4 Implementar `actualizar_tipo_de_cafe(db, id, datos: TipoDeCafeUpdate) -> TipoDeCafeRead`: primero comprueba la existencia y lanza `TipoDeCafeNoEncontrado` si no hay registro, y recién entonces aplica `model_dump(exclude_none=True)` (los atributos en `null` o ausentes no se modifican). Verificación: test que con id inexistente lanza `TipoDeCafeNoEncontrado`, más un test por cada escenario del requirement (un solo atributo, atributo en `null`, cuerpo sin valores) comprobando que el resto no cambia.
- [x] 3.5 Implementar `eliminar_tipo_de_cafe(db, id) -> None`: lanza `TipoDeCafeNoEncontrado` si no existe, `TipoDeCafeReferenciado` si `cuentas_de_referencias` devuelve algún contador distinto de cero, y solo entonces borra con commit. Verificación: test de borrado exitoso, test bloqueado por blend, test bloqueado por lote y test que comprueba que el registro sigue existiendo cuando se bloquea.
- [x] 3.6 Verificar que `services.py` no duplica la validación de `precio_por_kg_verde > 0` y que `pydantic` la resuelve. Verificación: test que `TipoDeCafeCreate(precio_por_kg_verde="0", ...)` falla con `ValidationError` antes de llegar al servicio, y `grep -n "precio_por_kg_verde *<=" backend/app/modules/inventario/services.py` sin coincidencias.

## 4. Capa HTTP: router.py

- [x] 4.1 Registrar el router con prefijo `/tipos-de-cafe` y exponer `POST /` con `response_model=TipoDeCafeRead` y `status_code=201`. Verificación: test con `TestClient` que devuelve 201 y el cuerpo con `id`.
- [x] 4.2 Exponer `GET /{id}` con `response_model=TipoDeCafeRead`. Verificación: test que devuelve 200 con el registro y 404 con id inexistente.
- [x] 4.3 Exponer `PATCH /{id}` con `response_model=TipoDeCafeRead`. Verificación: test que devuelve 200 y solo cambia el atributo enviado; test que devuelve 404 con id inexistente; test que devuelve 422 con precio no positivo.
- [x] 4.4 Exponer `DELETE /{id}` con `status_code=204` y sin `response_model`. Verificación: test que devuelve 204, 404 con id inexistente y 409 cuando el tipo está referenciado, con el detalle nombrando a la entidad bloqueante.
- [x] 4.5 Implementar el mapeo de excepciones de dominio a códigos HTTP con `if / elif / else`, y verificar que `router.py` no abre sesión directamente. Verificación: los tests de 4.2-4.4 pasan y `grep -n "Session(" backend/app/modules/inventario/router.py` no tiene coincidencias.

## 5. Verificación de integración

- [x] 5.1 Escribir `backend/tests/modules/inventario/test_services_tipo_de_cafe.py` cubriendo 3.1 a 3.5 y verificar con `python -m pytest tests/modules/inventario/test_services_tipo_de_cafe.py -q` desde `backend/`. → 22 passed.
- [x] 5.2 Escribir `backend/tests/modules/inventario/test_router_tipo_de_cafe.py` con app local, `dependency_overrides` sobre `get_db` y base SQLite en memoria, cubriendo 4.1 a 4.4. Verificación: `python -m pytest tests/modules/inventario/test_router_tipo_de_cafe.py -q` desde `backend/`. → 15 passed (con `StaticPool` + `check_same_thread=False`, porque `TestClient` atiende en otro hilo).
- [x] 5.3 Verificar que la separación de capas se sostiene: `services.py` no importa FastAPI, `crud.py` no hace commit y `router.py` no toca la sesión. Verificación: `grep -n "from fastapi\|HTTPException" backend/app/modules/inventario/crud.py` vacío; `grep -n "\.commit()" backend/app/modules/inventario/crud.py` vacío; `grep -n "from fastapi\|HTTPException" backend/app/modules/inventario/services.py` vacío. → los cuatro contadores en 0.
- [x] 5.4 Correr la suite completa del módulo con `python -m pytest tests/modules/inventario -q` desde `backend/` y confirmar que no hay fallos. → 168 passed.
- [x] 5.5 Correr `openspec validate add-tipo-de-cafe-crud --strict` y `openspec validate --specs` desde la raíz; ambos deben terminar en `valid` / `passed`. → `valid` y `2 passed`.

## Workflow follow-up

- Archivar el cambio con `/opsx-archive` una vez revisado: la delta crea la capability `inventario-tipo-de-cafe` con un `## Purpose` propio.
- Resolver la Open Question de infraestructura de arranque (`config.py`, `database.py`, `main.py`) antes de la primera migración.
- El commit requiere aprobación explícita del usuario antes de ejecutarse.
