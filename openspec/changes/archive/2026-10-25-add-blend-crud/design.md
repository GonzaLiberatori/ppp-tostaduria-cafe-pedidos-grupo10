# Design

## Context

`Blend` ya existe como modelo (`blend`, `blend_has_tipo_de_cafe`) y como contrato Pydantic (`BlendCreate`, `BlendUpdate`, `BlendRead`, `BlendComposicionItem`), pero `crud.py` y `services.py` solo conocen a `TipoDeCafe` y `router.py` tiene 4 rutas, todas de tipo de café.

Hechos que condicionan este cambio:

- La revisión de `schemas.py` mostró que casi todas las reglas pedidas ya están implementadas; solo faltan dos (mínimo de dos tipos y la tolerancia de suma).
- `REFERENCIAS_PROHIBIDAS` es un `tuple[type, ...]` con `_COLUMNA_TIPO_DE_CAFE` fija. `Lote` es referenciador de `TipoDeCafe` (`tipo_de_cafe_id`) **y** de `Blend` (`blend_id`): la tupla no puede expresar ambas cosas.
- `detalle_pedido` sigue sin definirse.

Ver `proposal.md` para la motivación y `specs/` para los requisitos.

## Goals / Non-Goals

**Goals:**

- Aplicar los mismos principios que `add-tipo-de-cafe-crud` sin reescribir lo que ya funciona.
- Que la composición se mantenga consistente con el blend en todas las operaciones, dentro de una sola transacción.
- Que el mecanismo de bloqueo por referencias admita más entidades sin tocar la lógica.

**Non-Goals:**

- Comprobar que los `tipo_de_cafe_id` de la lista existan (descartado explícitamente).
- Agregar un índice único a `Blend.nombre` (descartado explícitamente).
- Infraestructura de arranque y CRUD de `Lote`.

## Decisions

### Los schemas cambian solo en dos puntos

| Regla | Estado | Acción |
|---|---|---|
| `tipo_de_cafe_id` sin repetir | ya en `_validar_composicion` | ninguna |
| `porcentaje > 0` | ya en `PorcentajeBlend` | ninguna |
| `nombre` no vacío y ≤ 50 | ya en Create y Update | ninguna |
| `precio_por_kg_verde > 0` | ya en `PrecioPorKgVerde` | ninguna |
| Lista válida solo si no es `null` en Update | ya en el validador | ninguna |
| Mínimo dos tipos | `min_length=1` | → `min_length=2` |
| Suma entre 99,99 y 100 | exige exactamente 100 | → rango |

**Por qué:** reescribir validadores que ya pasan sus tests solo para tocar dos líneas es riesgo sin recompensa. Los tests existentes sirven de red de seguridad para el resto.

### Tolerancia de 0,01 por redondeo

```python
if not (Decimal("99.99") <= total <= Decimal("100.00")):
    raise ValueError(...)
```

**Por qué:** tres terceros redondeados a dos decimales dan `33.33 + 33.33 + 33.34 = 100.00`, pero combinaciones reales pueden cerrar en `99.99`. Con precisión de dos decimales, los únicos valores entre `99.99` y `100.00` son esos dos, así que el rango equivale a "acepta 100 y acepta 99,99".

**Por qué no más tolerancia:** una suma de `99.98` o de `100.05` ya no es redondeo, es una proporción mal cargada. Cero para abajo y cero para arriba.

**Alternativa descartada:** comparar con una tolerancia relativa (`abs(total - 100) <= 0.01`). Necesitaría un épsilon arbitrario y admite `100.01`; el rango explícito no deja zonas grises.

### Unicidad de `nombre` solo en el servicio

El servicio consulta si ya existe un blend con ese nombre y responde `409`. No se agrega `unique=True` a `Blend.nombre`.

**Por qué se hizo así:** decisión explícita del pedido de este cambio.

**Consecuencia conocida:** hay una ventana entre el `SELECT` y el `INSERT`. Dos altas simultáneas con el mismo nombre pueden pasar ambas. Ver Risks.

**Detalle en la edición:** el chequeo debe excluir al propio blend, o editar un blend sin cambiarle el nombre se declararía conflicto consigo mismo.

### No se comprueba la existencia de los `tipo_de_cafe_id`

El servicio no valida que cada item de la composición apunte a un `TipoDeCafe` real. Es decisión explícita del pedido.

**Consecuencia conocida:** con un id inexistente, el `INSERT` en `blend_has_tipo_de_cafe` falla por la restricción foránea y el `commit` tira `IntegrityError`, que nadie traduce → **`500`** en vez de un error de validación. Ver Risks.

### `REFERENCIAS_PROHIBIDAS` pasa a estar parametrizado

```python
REFERENCIAS_PROHIBIDAS: dict[type, tuple[tuple[type, str], ...]] = {
    TipoDeCafe: ((BlendHasTipoDeCafe, "tipo_de_cafe_id"), (Lote, "tipo_de_cafe_id")),
    Blend: ((Lote, "blend_id"),),
}
```

**Por qué:** la clave es `(entidad referenciadora, columna FK)`. `Lote` aparece en ambas entradas con columnas distintas; con el `tuple[type, ...]` actual y la constante `_COLUMNA_TIPO_DE_CAFE` fija, el contador de `Blend` habría mirado `lote.tipo_de_cafe_id` y devuelto cero siempre, dejando el guard sin efecto.

`cuentas_de_referencias` recibe la entidad que se va a borrar. El contador sigue devolviendo todos los valores, ceros incluidos.

**Extensibilidad:** `detalle_pedido` entra como una pareja más en cada lista.

### La composición no bloquea el borrado

`BlendHasTipoDeCafe` es la composición propia del blend, no un tercero que la use. El bloqueo son solo `Lote` y `detalle_pedido`. Si se contara como bloqueante, ningún blend se podría borrar nunca.

### Orden de escritura dentro de la transacción

| Operación | Orden |
|---|---|
| **Alta** | insertar el blend → `flush` para obtener el `blend.id` → insertar la composición → `commit` |
| **Edición con lista nueva** | borrar la composición previa → crear la nueva → `commit` |
| **Baja** | comprobar bloqueos → borrar la composición → borrar el blend → `commit` |

**Por qué:** en el alta, sin el `flush` no hay con qué poblar `blend_id`. En el reemplazo, `INSERT` antes que `DELETE` dejaría dos composiciones conviviendo durante el batch si falla el índice.

### Excepciones de dominio y mapeo a HTTP

Tres excepciones en `services.py`: `BlendNoEncontrado` → `404`, `BlendReferenciado` → `409`, `NombreDeBlendEnUso` → `409`. El mapeo vive en `router.py` como `if / elif / else`, igual que en `TipoDeCafe`.

**Sobre `elif`:** aplica porque son casos mutuamente excluyentes sobre un mismo sujeto (el tipo de excepción). En cambio los bloqueos del borrado **no** son cadena de `elif`: son comprobaciones independientes que se cuentan todas.

### Tests con app local y SQLite en memoria

Mismo patrón que `add-tipo-de-cafe-crud`. Se reutiliza la lección del cambio anterior: `create_engine("sqlite://")` necesita `StaticPool` y `check_same_thread=False`, porque `TestClient` atiende las peticiones en otro hilo y con el pool por defecto recibiría una base en memoria distinta y vacía.

## Risks / Trade-offs

- **Carrera en el nombre del blend** → dos altas simultáneas con el mismo nombre pueden colar. Mitigación futura: `unique=True` en `Blend.nombre` (descartada en este cambio) y mapeo de `IntegrityError` a `409`.
- **`tipo_de_cafe_id` inexistente → `500`** → el error de restricción foránea no está traducido. Mitigación futura: comprobar los ids antes de insertar.
- **`detalle_pedido` no se puede comprobar** → el requirement lo nombra y el código no. Se cierra de una línea al definir la tabla.
- **Un test existente queda obsoleto** → `test_create_rechaza_porcentajes_que_no_suman_cien` usa `60.00 + 39.99 = 99.99`, que ahora es válido. Hay que reescribirlo con un total fuera de tolerancia (por ejemplo `99.98`).
- **El cambio de `min_length` endurece el contrato** → una lista con un solo tipo pasaba a ser aceptada y ahora da `422`. Es el requisito pedido, pero es un cambio observable del contrato de `inventario-schemas`.
- **`router.py` pasa de 4 a 8 rutas** → todavía está dentro del módulo, pero conviene revisar el tamaño antes del próximo CRUD.
- **Endpoints no registrados en el `FastAPI` real** → `config.py`, `database.py` y `main.py` siguen vacíos y `get_db()` sigue roto.

## Migration Plan

Sin migraciones: `backend/alembic/versions/` está vacío.

**Rollback:** revertir `schemas.py`, `crud.py`, `services.py`, `router.py` y el test afectado. Los cambios de validación son de contrato, así que si se revierten hay que revisar el main spec `inventario-schemas`.

## Open Questions

- **Infraestructura de arranque** (`core/config.py`, `core/database.py`, `app/main.py`, arreglo de `deps.get_db()`): sigue fuera de alcance y bloquea levantar la API en producción. Convendría ponerle fecha antes de la primera migración.
