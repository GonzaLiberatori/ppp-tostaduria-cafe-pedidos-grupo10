# Tasks

## 1. Preparación
- [ ] 1.1 Revisar `backend/app/core/database.py` para confirmar `Base` (DeclarativeBase), imports y estilo SQLAlchemy 2.0. Verificar que se puede importar sin errores.
- [ ] 1.2 Revisar estructura de módulos para confirmar convenciones (sin imports circulares problemáticos) y estado actual de `backend/app/modules/produccion/models.py`.

## 2. Implementación de modelos en inventario
- [ ] 2.1 Crear enums `LoteTipo` (`VERDE`, `TOSTADO`) y `LoteEstado` (`CERRADO`, `ABIERTO`) en `backend/app/modules/inventario/models.py`.
- [ ] 2.2 Implementar `Pais`, `Region` (FK a pais con relación), `Variedad` con `Mapped`/`mapped_column` y tipos correctos.
- [ ] 2.3 Implementar `TipoDeCafe` (organico Boolean, precio_por_kg_verde Numeric(10,2), FKs a region/variedad con relaciones).
- [ ] 2.4 Implementar `Blend` (id, nombre, precio_por_kg_verde Numeric(10,2), descripcion Text) y `BlendHasTipoDeCafe` (clave compuesta + porcentaje Numeric(5,2), FKs a blend/tipo_de_cafe).
- [ ] 2.5 Implementar `Lote` con todos los campos, enums, FKs opcionales a tipo_de_cafe/blend/orden_tueste (usar `ForeignKey("orden_tueste.id")` string), relaciones y restricciones según esquema. Verificar que el archivo compila/importa correctamente.

## 3. Verificación
- [ ] 3.1 Importar `app.modules.inventario.models` desde Python (verificar sintaxis/tipado sin errores). Verificar que los símbolos principales están definidos.
- [ ] 3.2 Comprobar que no hay imports circulares entre módulos al importar los modelos.
