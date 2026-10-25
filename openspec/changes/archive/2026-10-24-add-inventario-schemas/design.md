# Design

## Context

`backend/app/modules/inventario/schemas.py` existe pero está vacío, igual que el resto de los `schemas.py` del proyecto: no hay convención previa de Pydantic que heredar. Los modelos ya están implementados en `inventario/models.py` con estilo SQLAlchemy 2.0 (`Mapped` / `mapped_column`), `Base` sale de `app.core.database` y ya existen los enums `LoteTipo` (`VERDE`, `TOSTADO`) y `LoteEstado` (`CERRADO`, `ABIERTO`).

Dos restricciones del modelo condicionan el contrato:

- `TipoDeCafe` guarda `region_id` y `variedad_id`, y `Region` guarda `pais_id`. Los nombres están a dos y tres saltos de relación.
- `Lote` tiene cuatro atributos nullable (`observaciones`, `tipo_de_cafe_id`, `blend_id`, `orden_tueste_id`) sobre once campos.

Ver `proposal.md` para la motivación y `specs/inventario-schemas/spec.md` para los requisitos.

## Goals / Non-Goals

**Goals:**

- Un modelo Pydantic por operación, con contrato explícito y documentación OpenAPI precisa por endpoint.
- Validación de precisión decimal alineada con los tipos de columna, para fallar en la capa de validación y no en la base.
- Que los routers futuros puedan consumir un único schema por caso de uso sin lógica de adaptación.

**Non-Goals:**

- Routers, `crud.py` y `services.py`.
- Resolver si un nombre de variedad, región o país inexistente se crea, se rechaza o se busca (ver Open Questions).
- Migraciones y cambios en `models.py`.

## Decisions

### Un schema por operación, no un modelo único con todo opcional

Se definen `TipoDeCafeCreate`, `TipoDeCafeUpdate` y `TipoDeCafeRead` (y el equivalente para `Blend` y `Lote`), más los tres schemas puntuales de `Lote`. **No hay schema de eliminación**: ver la decisión siguiente.

**Por qué:** un modelo único con todos los campos `Optional` compila, pero el consumidor no puede distinguir qué exige cada endpoint y OpenAPI documenta un contrato falso. Los schemas separados hacen que la regla de opcionalidad sea estructural y no una convención a memorizar.

**Alternativa descartada:** un `Base` con todos los campos y subclases por operación. Genera herencia de la que nadie se acuerda y arrastra campos que la operación no usa.

### La baja no tiene schema: el `id` va por parámetro de ruta

No se definen `TipoDeCafeDelete`, `BlendDelete` ni `LoteDelete`. El `id` de la eliminación se recibe como path parameter en la firma del endpoint (`def eliminar(id: int, ...)` con `/recurso/{id}`), y FastAPI lo valida y documenta en OpenAPI por su cuenta.

**Por qué:** un cuerpo `{"id": 7}` junto a la ruta `/tipo-de-cafe/7` declara la misma identidad dos veces, y obliga a decidir cuál manda cuando discrepan. El path parameter ya es obligatorio, ya está tipado y ya aparece en el contrato; el schema de solo `id` no aporta validación nueva.

**Alternativa descartada:** `DELETE` con body y sin id en la ruta. Funciona, pero rompe la semántica REST, hace que muchos clientes HTTP no lo soporten bien y empeora la documentación de OpenAPI.

**Nota:** la regla de opcionalidad sigue vigente como concepto — "la eliminación solo recibe el `id`" — pero se cumple en el router, no en Pydantic. Los tres endpoints puntuales de `Lote` sí conservan su `id` por ruta y un body de un solo campo, porque ahí el cuerpo aporta el atributo que cambia.

### Los nombres de origen se aplanan en el contrato, no en el modelo

`TipoDeCafeCreate` / `Update` reciben `variedad: str`, `region: str`, `pais: str`, y `TipoDeCafeRead` los devuelve igual, sin `variedad_id` ni `region_id`.

**Por qué:** es el contrato pedido explícitamente. Además evita exponer IDs que el cliente no puede usar, porque no hay endpoints de `Variedad`, `Region` ni `Pais`. El identificador de `TipoDeCafe` sigue siendo su `id`: los tres nombres son atributos descriptivos del origen y no se usan como clave ni como criterio de unicidad.

**Consecuencia asumida:** `TipoDeCafeRead` no se puede poblar con un `model_validate(orm_obj)` directo, porque los nombres viven en `tipo.variedad.nombre`, `tipo.region.nombre` y `tipo.region.pais.nombre`. Se resuelve aplanando contra el objeto ORM antes de validar: o un `model_validator(mode="before")` que lea atributos del ORM y arme el diccionario, o construcción explícita del schema en `services.py`. La segunda es más explícita y testeable; se prefiere esa y el validador queda como atajo opcional.

**Riesgo asociado:** con `from_attributes` y relaciones lazy, cada tipo de café dispara hasta tres queries extra. El `crud` debe usar `joinedload(TipoDeCafe.variedad)` y `joinedload(TipoDeCafe.region).joinedload(Region.pais)`.

**Alternativa descartada:** modelos anidados (`region: RegionRead` con `pais: PaisRead`). Es más expresivo y no necesita aplanado, pero cambia la forma del JSON y el requisito pide `str` plano.

### Los enums se importan desde `models.py`

`LoteTipo` y `LoteEstado` se importan de `app.modules.inventario.models`, no se redefinen en `schemas.py`.

**Por qué:** una sola fuente de verdad. Redefinirlos en `schemas.py` garantiza que un día el schema acepte un valor que el modelo rechaza, y el error aparece en la base en lugar de en la validación.

### Precisión decimal declarada igual que la columna

`precio_por_kg_verde` → `max_digits=10, decimal_places=2`; `humedad` → `5,2`; `kg_disponibles` y `kg_reales` → `10,2`; `porcentaje` → `5,2`. Se expresan con `Annotated[Decimal, Field(...)]` y restricciones `gt`/`ge` según corresponda.

**Por qué:** si la validación acepta `123456789.999`, el error real aparece como truncamiento silencioso de MySQL. Validar en el borde convierte un bug de datos en un 422.

### Composición de blend: lista plana y reemplazo total

`BlendComposicionItem` (`tipo_de_cafe_id: int`, `porcentaje: Decimal`) se reutiliza en Create, Read y Update. En Update, si la lista viene, reemplaza la composición completa.

**Por qué:** el cliente envía el estado deseado, no un diff. Semántica de replace es la única que no ambigua con `PATCH`.

**Validaciones en el schema (`model_validator(mode="after")`):** lista con al menos un elemento, `tipo_de_cafe_id` sin repetidos y suma de porcentajes igual a `100`. La comparación se hace cuantizando a dos decimales antes de comparar, para que `33.33 + 33.33 + 33.34` no falle por representación.

**Alternativa descartada:** validar la suma en `services.py`. Es una regla del contrato de entrada, no del negocio de persistencia; rechazarla temprano da mejor error.

### `extra="forbid"` en todos los schemas de entrada

Create, Update y los tres puntuales de lote rechazan campos no declarados. El `Read` también, aunque es solo de salida: impide que una respuesta arrastre atributos ajenos al contrato.

**Por qué:** el requisito del lote (no poder recibir `tipo` ni las FKs) se cumple de forma estructural con `extra="forbid"`, sin un validador que enumere campos prohibidos y se desactualice. Es el mismo mecanismo que protege el resto de los contratos ante un typo del cliente.

**Alternativa descartada:** `extra="ignore"`. Acepta la petición y descarta el campo en silencio; el cliente cree que actualizó `tipo` y no pasó nada.

### Ediciones puntuales de lote con cuerpo de un solo campo

`LoteKgDisponiblesUpdate`, `LoteKgRealesUpdate` y `LoteEstadoUpdate` toman el `id` por path y solo el atributo correspondiente en el cuerpo.

**Por qué:** describe exactamente la intención operativa (corregir un pesaje, cerrar un lote) y la documentación OpenAPI lo muestra así. Reutilizar `LoteUpdate` permitiría cambiar el resto de los campos desde un endpoint que promete una sola cosa.

**Decisión registrada:** estos campos (`kg_disponibles`, `kg_reales`, `estado`) siguen siendo editables también desde `LoteUpdate`, tal como se pidió. La semántica de si un pesaje debe dejar rastro en `MovimientoStock` es responsabilidad de `services.py`, fuera de este cambio.

## Risks / Trade-offs

- **N+1 en la lectura de tipo de café** → `joinedload` obligatorio en `crud.py` para `variedad` y `region.pais`; se deja como tarea explícita, no como nota al pie.
- **`Lote.orden_tueste_id` apunta a una tabla inexistente** (`ForeignKey("orden_tueste.id")` sin `OrdenTueste` definido en `backend/app/modules/produccion/models.py`) → el schema expone el campo porque el modelo lo declara, pero la migración que cree `lote` va a fallar hasta que exista `orden_tueste`. Se resuelve antes de generar la primera migración, no acá.
- **La relación `Lote.orden_tueste` quedó comentada durante la implementación.** Estaba escrita como `Mapped[Optional["object"]] = relationship()`; SQLAlchemy resuelve la anotación `"object"` como el nombre de una entidad, no la encuentra y `configure_mappers()` revienta, lo que impedía instanciar cualquier objeto ORM del módulo (el registro de `Base` es compartido y la configuración es en cascada). La columna `orden_tueste_id` sigue intacta, así que `LoteRead` no cambia. **Siempre que `produccion` defina `OrdenTueste`, hay que reactivar esa relación con la anotación correcta** o los accesos a la orden desde un lote seguirán sin existir.
- **Doble camino de escritura para `kg_disponibles`, `kg_reales` y `estado`** (`LoteUpdate` y los endpoints puntuales) → se acepta por pedido explícito; la consistencia se garantiza en `services.py`, que debe ser el único punto que aplique ambos caminos.
- **Contrato de `TipoDeCafe` desacoplado de `Variedad`/`Region`/`Pais`** → si mañana se agregan endpoints a esas entidades, el contrato puede necesitar revisión. Se asume el costo: hoy el requisito es nombres planos.
- **`extra="forbid"` es estricto con clientes que mandan campos de más** → es intencional; el 422 temprano es mejor que una actualización parcial silenciosa.

## Migration Plan

Sin cambios de base de datos: solo se completa un archivo Python vacío.

- Despliegue: agregar los schemas a `inventario/schemas.py`. Al no haber routers que los importen todavía, el cambio no altera el comportamiento en ejecución.
- Rollback: revertir el archivo a vacío. Sin estado persistido ni migraciones involucradas.
- Verificación: `python -c "import app.modules.inventario.schemas"` desde `backend/`, más los casos de validación cubiertos por los escenarios de la spec.

## Open Questions

- **Resolución de nombres de variedad, región y país:** si no existen, ¿se crean al vuelo, se rechaza la petición con 404/422, o se asume que llegan por seed? Decisión diferida por el equipo. No afecta este cambio: los schemas solo declaran `str` de entrada y `str` de salida. Impactará `services.py` y el comportamiento del endpoint.
