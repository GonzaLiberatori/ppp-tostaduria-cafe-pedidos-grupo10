# Design

## Context

El módulo de inventario ya implementa el CRUD completo de `Lote` siguiendo una arquitectura de tres capas (router → services → crud) con validación Pydantic en schemas separados. Los schemas para las tres operaciones puntuales (`LoteKgRealesUpdate`, `LoteKgDisponiblesUpdate`, `LoteEstadoUpdate`) ya existen y cubren las validaciones de tipo, rango y enum. El endpoint PATCH general de `Lote` (`LoteUpdate`) permite actualizar múltiples campos a la vez, pero no puede expresar las reglas de acoplamiento entre `kg_reales` y `kg_disponibles`.

## Goals / Non-Goals

**Goals:**
- Exponer tres endpoints PATCH independientes para actualizar `kg_reales`, `kg_disponibles` y `estado` de un lote
- Aplicar las reglas de negocio de acoplamiento entre kilos en la capa de servicio
- Mantener consistencia con el patrón existente (capas, manejo de errores, transacciones)

**Non-Goals:**
- Modificar el endpoint PATCH general de `Lote` (`LoteUpdate`)
- Agregar nuevas reglas de negocio a la creación o lectura de lotes
- Cambiar la estructura de la base de datos o los modelos

## Decisions

**Separar los endpoints por campo en lugar de extender `LoteUpdate`**: los tres endpoints propuestos prometen actualizar exactamente un campo. Esto mantiene las reglas de acoplamiento localizadas y evita que el PATCH general crezca en complejidad condicional. Alternativa considerada: agregar un flag o modo a `LoteUpdate` para activar la propagación de kilos, descartada porque acopla reglas de negocio distintas en un solo endpoint.

**Propagación de `kg_reales` a `kg_disponibles` en la capa de servicio**: cuando `kg_reales` aumenta, la diferencia se suma a `kg_disponibles` dentro de la misma transacción. La capa CRUD solo ejecuta las escrituras; el servicio calcula la diferencia y decide qué campos persistir. Alternativa considerada: derivar `kg_disponibles` automáticamente en la base de datos, descartada porque el modelo tiene `kg_disponibles` como campo independiente que puede divergir (por despachos).

**Validación de `kg_disponibles <= kg_reales` en el servicio**: el schema ya valida tipo y rango, pero la comparación contra `kg_reales` requiere leer el estado actual del lote, lo cual es responsabilidad del servicio. Se lanza `KgDisponiblesExcedeKgReales` (400) cuando se incumple.

**Reutilizar `LoteNoEncontrado` para los tres endpoints**: todos requieren que el lote exista. No se crea una excepción nueva por endpoint.

**Respuesta uniforme `LoteRead`**: los tres endpoints devuelven el estado actualizado completo del lote, consistente con los endpoints CRUD existentes.

## Risks / Trade-offs

- **[Inconsistencia temporal entre kg_reales y kg_disponibles]** → La propagación es transaccional (mismo commit), así que no hay ventana de inconsistencia visible. Si `kg_reales` disminuye, `kg_disponibles` puede quedar mayor que `kg_reales` hasta que un operador lo ajuste manualmente. Esto es correcto según la regla de negocio definida.
- **[Doble fuente de verdad para los kilos]** → `kg_disponibles` es un campo independiente que puede divergir de `kg_reales` por operaciones externas (despachos). La propagación automática solo aplica cuando `kg_reales` aumenta; si disminuye, no se toca `kg_disponibles`. Esto es intencional.
