# Design

## Context

`inventario/models.py` define `TipoDeCafe` y `inventario/schemas.py` define sus 13 contratos, pero los tres archivos de comportamiento — `crud.py`, `services.py`, `router.py` — están en 0 bytes. No hay ninguna ruta registrada en el proyecto: `app/main.py` y `core/config.py` también están vacíos, y `deps.get_db()` devuelve `UnboundExecutionError` porque `Session()` no tiene `bind`.

Dos hechos que condicionan el diseño:

- `precio_por_kg_verde` ya tiene restricción `gt=0` en el alias compartido `PrecioPorKgVerde`, usado por Create y Update.
- `Base.metadata.create_all()` **falla** con `NoReferencedTableError` por la FK de `Lote.orden_tueste_id` a `orden_tueste`, tabla que no existe. Sin `create_all` no hay forma de probar ninguna operación.

Ver `proposal.md` para la motivación y `specs/inventario-tipo-de-cafe/spec.md` para los requisitos.

## Goals / Non-Goals

**Goals:**

- Que las cuatro operaciones de `TipoDeCafe` sean probables de punta a punta con la base de datos real del módulo.
- Que cada validación viva en una sola capa, sin duplicación entre Pydantic y el servicio.
- Que el guard de borrado sea extensible a `detalle_pedido` sin reescribirlo.

**Non-Goals:**

- Levantar la API en producción (`config.py`, `database.py`, `main.py`).
- CRUD de `Blend` y `Lote`, y el listado de tipos de café.

## Decisions

### Tres archivos, una responsabilidad cada uno

| Capa | Archivo | Hace | No hace |
|---|---|---|---|
| Datos | `crud.py` | queries: leer, insertar, aplicar, borrar, contar referencias | decide nada, no hace commit |
| Negocio | `services.py` | reglas, excepciones de dominio, commit/rollback | no conoce HTTP ni `404` |
| HTTP | `router.py` | rutas, schemas, códigos de estado, `Depends(get_db)` | no toca la sesión, no decide reglas |

**Por qué:** es la regla de `AGENTS.md` y no es estética. Si el guard de borrado vive en `crud.py`, ese archivo decide si un borrado procede (ya no es "acceso a datos puro"); si vive en `router.py`, decide negocio y además necesita la sesión. En `services.py` queda testeable sin HTTP y reutilizable por `produccion` o `pedidos`.

**Alternativa descartada:** meter todo en `router.py` para sonar con dos archivos. Viola el propio AGENTS.md y deja las reglas sin test unitario.

### Edición con `exclude_none=True`

```python
cambios = datos.model_dump(exclude_none=True)   # {organico: False}  -> se aplica
                                                  # {organico: None}  -> no entra
                                                  # {}                -> nada cambia
```

**Por qué:** tu regla es "no modificar lo enviado como `null`", que es exactamente `exclude_none`. La alternativa habitual, `exclude_unset`, distinguiría *no enviado* de *enviado como nulo* — y en este caso lo que pediste es que ambos se comporten igual.

**Límite conocido:** con esto no se puede poner un atributo a `NULL`. Hoy no importa: los seis campos de `TipoDeCafe` son no nulos. Si alguno pasa a ser nullable, hay que replantear la regla.

### El precio no se revalida en el servicio

`gt=0` ya está en `PrecioPorKgVerde`, que usan `TipoDeCafeCreate` y `TipoDeCafeUpdate`. Repetir el chequeo en `services.py` obliga a mantener dos lugares para la misma regla y a decidir cuál manda.

**Consecuencia:** el spec describe solo el comportamiento observable (precio ≤ 0 → validación fallida) y no dice en qué capa se resuelve. El 422 lo produce FastAPI al validar el body, antes de que el servicio se entere.

### La existencia se valida en `services`, una sola vez por operación

`obtener_tipo_de_cafe`, `actualizar_tipo_de_cafe` y `eliminar_tipo_de_cafe` levantan `TipoDeCafeNoEncontrado` cuando el `id` de la ruta no corresponde a ningún registro. El router no comprueba nada antes de llamar.

**Por qué:** es una regla de negocio — ¿qué significa leer o editar algo que no existe? — y no una comprobación de HTTP. El `404` nace de mapear esa excepción, no de un `SELECT` previo en la capa de rutas.

**Alternativa descartada:** un `Depends(tipo_existe)` en el router. Haría el `SELECT` dos veces (una en la dependencia y otra dentro del servicio, que necesita el objeto para aplicar cambios), y si el servicio se llama desde `produccion` o `pedidos` quedaría sin proteger.

**Detalle para la edición:** el servicio primero comprueba la existencia y **después** aplica los cambios. Si no, `model_dump(exclude_none=True)` con un cuerpo vacío sobre un id inexistente devolvería un objeto fantasma en lugar de `404`.

### El guard de borrado es un conteo, no una cadena de `if`

```python
REFERENCIAS_PROHIBIDAS = (BlendHasTipoDeCafe, Lote)   # + DetallePedido cuando exista
```

**Por qué:** las tres referencias **no son mutuamente excluyentes** — un tipo de café puede estar en un blend *y* tener lotes a la vez. Una cadena `if / elif` descartaría la segunda consulta en cuanto la primera coincidiera, y el mensaje de error diría solo una cosa cuando hay tres. Lo correcto es contar las que coincidan y devolver todas.

**Extensibilidad:** agregar `detalle_pedido` es agregar un elemento a la tupla. El spec ya lo nombra; el código no puede comprobarlo porque la tabla no existe.

### Guía de estructuras condicionales

Pediste atención a esto, así que queda escrita como regla del módulo:

- **`elif`** cuando los casos son mutuamente excluyentes sobre un mismo sujeto. En este cambio aplica al mapeo excepción de dominio → código HTTP:

  ```python
  if isinstance(exc, TipoDeCafeNoEncontrado):
      raise HTTPException(404, ...)
  elif isinstance(exc, TipoDeCafeReferenciado):
      raise HTTPException(409, ...)
  else:
      raise
  ```

- **Sin `elif`** para las referencias de borrado: se cuentan todas (arriba).
- **Guard clauses** para pasos secuenciales: `if tipo is None: raise ...` y seguir, sin anidar el resto en un `else`.

### Excepciones de dominio en el módulo, no en `core/`

`TipoDeCafeNoEncontrado` y `TipoDeCafeReferenciado` viven en `services.py`. `AGENTS.md` dice que `core/` es *"sin lógica de negocio"*: meter excepciones de inventario ahí convierte el núcleo en un cajón de sábanas. `services.py` las lanza, `router.py` las traduce.

**Alternativa descartada:** que `services.py` lance `HTTPException` directamente. Funciona, pero acopla el módulo a FastAPI y hace imposible reutilizarlo desde un job de APScheduler o una tarea programada.

### Tests con app local y base SQLite en memoria

```python
app = FastAPI(); app.include_router(router_tipo_de_cafe)
app.dependency_overrides[get_db] = lambda: sesion_de_prueba
Base.metadata.create_all(engine)   # sqlite:// en memoria
```

**Por qué:** `get_db()` está roto y `main.py` no existe. Con `dependency_overrides` el `get_db` roto **nunca se ejecuta**, así que el test es real (ruta → schema → service → crud → SQL) sin tocar la infraestructura.

**Alternativa descartada:** mockear la sesión con `unittest.mock`. Prueba que el código llama a los métodos correctos, no que las reglas funcionan. Inútil para el guard de borrado.

## Risks / Trade-offs

- **`Lote.orden_tueste_id` pierde su clave foránea** → la columna queda como `Integer` sin constraint. **Qué queda roto:** la base deja de garantizar que el id de orden de tueste apunte a una fila real, y si `orden_tueste_id` trae un valor inválido hoy nadie lo rechaza. **Qué se recupera:** `create_all()` deja de fallar, y con él toda posibilidad de crear `lote`. Cuando `produccion` defina `OrdenTueste` hay que **rehacer la FK y regenerar la migración**; es el mismo trabajo que cuesta ahora, no menos.
- **`detalle_pedido` no se puede comprobar** → el requirement lo nombra y el código no. Mientras la tabla no exista, un tipo de café borrable hoy podría dejar de serlo mañana sin aviso. Se cierra de una línea al definirla.
- **Conteo y borrado no son atómicos** → entre `contar_referencias()` y `eliminar()` otra transacción puede crear un lote. Las FKs reales lo impedirán cuando las tablas existan en MySQL; hoy, con SQLite sin FK activas, no. Aceptado por baja concurrencia.
- **`Numeric` en SQLite almacena como real** → redondeos distintos a MySQL en decimales. No afecta este cambio (no hay cálculos), pero no se debe usar SQLite para testear reglas de dinero.
- **Endpoints no registrados en el `FastAPI` real** → los tests levantan su propia app; `app/main.py` sigue vacío. La API no se puede levantar hasta que la infraestructura exista.

## Migration Plan

Sin migraciones: `backend/alembic/versions/` está vacío y `.env` tiene 1 byte. Los tests crean las tablas con `create_all` sobre SQLite en memoria.

**Rollback:** revertir `crud.py`, `services.py`, `router.py` y el cambio en `models.py`. Sin estado persistido.

## Open Questions

- **Infraestructura de arranque:** `core/config.py`, `core/database.py` (engine + sessionmaker), el arreglo de `deps.get_db()` y `app/main.py` con `include_router`. Sin eso los endpoints existen en el código y no en la API desplegada. Fue dejado fuera de este cambio; conviene decidir si va en un cambio propio o antes de la primera migración.
