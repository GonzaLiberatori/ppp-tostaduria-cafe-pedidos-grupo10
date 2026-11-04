# Tasks

## 1. Modelos

- [x] 1.1 Eliminar las clases `Pais`, `Region` y `Variedad` de `backend/app/modules/inventario/models.py` junto con sus `relationship`. Verificación: `grep -n "class Pais\|class Region\|class Variedad" backend/app/modules/inventario/models.py` no devuelve nada.
- [x] 1.2 Reemplazar las FKs de `TipoDeCafe` por las columnas `variedad`, `region` y `pais` de tipo `String(50)` con `nullable=False`. Verificación: `python -c "from app.modules.inventario.models import TipoDeCafe; print(sorted(TipoDeCafe.__table__.c.keys()))"` imprime `['id', 'organico', 'pais', 'precio_por_kg_verde', 'region', 'variedad']`.
- [x] 1.3 Confirmar que ningún otro modelo del proyecto dependía de las tres tablas borradas. Verificación: `grep -rn "Pais\|Region\|Variedad\|variedad_id\|region_id" backend/app` devuelve como único resultado el docstring de `TipoDeCafeRead` que explica por qué no expone `variedad_id` ni `region_id`, y `configure_mappers()` termina sin excepción.

## 2. Schemas

- [x] 2.1 Reescribir el cuerpo de `TipoDeCafeRead.desde_orm` leyendo `tipo.variedad`, `tipo.region` y `tipo.pais` directamente, sin recorrer relaciones. Verificación: `test_read_desde_orm_aplama_los_tres_nombres` pasa. → Superado por 5.1: el método se eliminó al adoptar `from_attributes`.
- [x] 2.2 Verificar que la superficie de los 13 schemas no cambió: mismos campos, mismos tipos. Verificación: `test_schemas_integracion.py` sigue en verde y `TipoDeCafeRead.model_fields` es exactamente `['id', 'organico', 'precio_por_kg_verde', 'variedad', 'region', 'pais']`.

## 3. Tests

- [x] 3.1 Quitar el import de `Pais`, `Region` y `Variedad` de `test_schemas_tipo_de_cafe.py` (línea 9). Verificación: el archivo no importa ninguna clase eliminada.
- [x] 3.2 Reescribir `_tipo_de_cafe_de_ejemplo()` para construir el `TipoDeCafe` con `variedad="Caturra"`, `region="Huila"` y `pais="Colombia"` como texto. Verificación: `test_read_desde_orm_aplama_los_tres_nombres` comprueba los tres nombres. → Test renombrado en 5.3.
- [x] 3.3 Correr la suite del módulo con `python -m pytest tests/modules/inventario -q` desde `backend/` y confirmar que no hay fallos.

## 4. Verificación de integración

- [x] 4.1 Verificar que la capa de modelos ya no referencia ninguna tabla de origen: `grep -rn "class Pais\|class Region\|class Variedad" backend/app` vacío y `python -c "from sqlalchemy.orm import configure_mappers; from app.modules.inventario import models; configure_mappers(); print('ok')"` imprime `ok`.
- [x] 4.2 Verificar que el contrato Pydantic quedó intacto: `python -m pytest tests/modules/inventario/test_schemas_integracion.py -q` en verde y los 13 schemas siguen exponiendo descripción en todos sus campos.
- [x] 4.3 Correr `openspec validate replace-origen-con-strings --strict` y `openspec validate --specs` desde la raíz; ambos deben terminar en `valid` / `passed`.

## 5. Construcción de los Read desde el ORM

- [x] 5.1 Habilitar `from_attributes=True` en `TipoDeCafeRead` y `LoteRead`, y eliminar `TipoDeCafeRead.desde_orm`. Verificación: `grep -n "def desde_orm" backend/app/modules/inventario/schemas.py` devuelve una sola línea, la de `BlendRead`. → línea 196.
- [x] 5.2 Implementar `BlendRead.desde_orm(blend)` que convierta `blend.tipos_de_cafe` en `BlendComposicionItem` conservando solo `tipo_de_cafe_id` y `porcentaje`. Verificación: test que arma un blend con dos filas y comprueba la lista resultante.
- [x] 5.3 Reescribir `test_read_desde_orm_aplama_los_tres_nombres` para que use `model_validate(tipo)` en lugar del adaptador. Verificación: el test pasa y sigue verificando los tres nombres. → renombrado a `test_read_se_construye_desde_el_orm_sin_adaptador`, más un test que asegura que `desde_orm` no existe en `TipoDeCafeRead`.
- [x] 5.4 Verificar que `extra="forbid"` sigue rechazando campos extra tras habilitar la flag y que la suite completa del módulo no tiene fallos. Verificación: `python -m pytest tests/modules/inventario -q` desde `backend/`. → 131 passed.

## Workflow follow-up

- Archivar el cambio con `/opsx-archive` una vez revisado (la delta modifica `inventario-core-models`: 1 REMOVED + 1 RENAMED/MODIFIED, así que al archivar sincroniza ese main spec).
- El commit requiere aprobación explícita del usuario antes de ejecutarse.
