# Design

## Context

El módulo de inventario ya implementa el CRUD completo para TipoDeCafe, Blend y Lote siguiendo una arquitectura de tres capas (router → services → crud) con validación Pydantic en schemas separados. Los endpoints existentes operan sobre registros individuales identificados por `id`, pero no hay forma de listar los registros de una colección. Para TipoDeCafe y Blend se requiere listar todos los registros, mientras que para Lote se requiere un filtrado por `tipo_de_cafe_id` o `blend_id`.

Los schemas de lectura (`TipoDeCafeRead`, `BlendRead`, `LoteRead`) ya existen y pueden reutilizarse directamente. `BlendRead` requiere el adaptador `desde_orm()` para aplanar la relación de composición, mientras que los otros dos usan `model_validate()` directo.

## Goals / Non-Goals

**Goals:**
- Exponer tres endpoints GET para listar registros de cada entidad: todos los tipos de café, todos los blends, y los lotes filtrados por origen
- Mantener consistencia con el patrón de tres capas existente
- Devolver respuestas determinísticas con orden por `id` ascendente
- Retornar lista vacía cuando no hay registros (no error 404)

**Non-Goals:**
- Paginación (se puede agregar después si es necesario)
- Filtrado adicional más allá del requerido para lotes (tipo_de_cafe y blend no requieren filtros)
- Búsqueda por texto u otros criterios
- Ordenamiento configurable por el cliente
- Inclusión de relaciones anidadas más allá de lo que ya devuelven los schemas Read

## Decisions

**Reutilizar los schemas Read existentes**: cada endpoint devuelve `list[TipoDeCafeRead]`, `list[BlendRead]` o `list[LoteRead]`. No se crean schemas nuevos porque los contratos de lectura individuales ya cubren exactamente lo que necesita el listado.

**Filtrado de lotes por origen (tipo_de_cafe_id o blend_id)**: el endpoint `GET /lotes` acepta ambos parámetros como query parameters, pero impone una restricción XOR: exactamente uno debe tener valor, el otro debe ser null. Esta validación se implementa en la capa de servicios, no en el schema Pydantic, porque requiere una validación condicional entre dos campos opcionales. Si ambos son null o ambos tienen valor, se rechaza con 422 (Unprocessable Entity). La capa CRUD aplica el filtro según el parámetro recibido, sin validar que el id corresponda a un registro existente de TipoDeCafe o Blend. Si no hay lotes asociados, retorna lista vacía.

**Orden determinístico por `id` ascendente**: la capa CRUD aplica `.order_by(Entidad.id)` en todas las queries. Esto garantiza que la respuesta sea estable entre llamadas y que el frontend pueda mostrar listas consistentes. Alternativa considerada: devolver sin orden específico (más rápido), descartada porque rompe la predictibilidad para el cliente.

**Lista vacía en lugar de 404**: cuando no hay registros, los endpoints devuelven 200 con una lista vacía. Un 404 implicaría "no encontrado", pero la colección sí existe, solo está vacía. Esto es coherente con REST y simplifica el manejo en el frontend.

**Sin paginación en el MVP**: se devuelve la colección completa de una sola vez. Si el volumen de registros crece (especialmente en Lote), se puede agregar paginación después sin romper el contrato actual, simplemente cambiando la respuesta a un envelope con `items`, `total` y `page`.

**Conversión ORM a Read en la capa de servicio**: la capa CRUD devuelve objetos ORM puros; la capa de servicio es responsable de convertirlos a schemas de lectura. Para Blend se usa `BlendRead.desde_orm()` (por la relación de composición); para TipoDeCafe y Lote se usa `model_validate()` directo.

## Risks / Trade-offs

- **[Sin paginación]** → Si alguna tabla crece mucho (especialmente Lote con el tiempo), devolver todos los registros puede ser lento y consumir mucha memoria. Mitigación: monitorear el tamaño de las tablas y agregar paginación cuando sea necesario, manteniendo el endpoint actual como fallback.
- **[Filtrado parcial]** → Los endpoints de tipos de café y blends devuelven todos los registros sin filtrado, por lo que el cliente debe filtrar en el frontend si solo necesita un subconjunto. El endpoint de lotes ya filtra por origen en el backend. Para el volumen esperado del MVP esto es aceptable; si se necesitan filtros adicionales, se pueden agregar como query params sin romper el contrato.
