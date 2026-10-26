# Tasks

## 1. Capa de Servicios - Lógica de Negocio

- [ ] 1.1 Crear excepción `KgDisponiblesExcedeKgReales` en `backend/app/modules/inventario/services.py` que reciba los valores de `kg_disponibles` y `kg_reales`, y verificar que el mensaje sea descriptivo
- [ ] 1.2 Implementar función `actualizar_kg_reales` en `services.py` que: valide existencia del lote, calcule diferencia si el nuevo valor es mayor, propague el incremento a `kg_disponibles`, y verifique con un test que el lote actualizado tenga los valores correctos
- [ ] 1.3 Implementar función `actualizar_kg_disponibles` en `services.py` que: valide existencia del lote, valide que `kg_disponibles <= kg_reales`, lance `KgDisponiblesExcedeKgReales` si no cumple, y verifique con un test que valide ambos caminos (válido e inválido)
- [ ] 1.4 Implementar función `actualizar_estado` en `services.py` que: valide existencia del lote, actualice el estado, y verifique con un test que el estado cambió correctamente

## 2. Capa CRUD - Acceso a Datos

- [ ] 2.1 Implementar función `actualizar_kg_reales` en `backend/app/modules/inventario/crud.py` que reciba el lote y el nuevo valor, actualice el atributo, haga flush, y verifique que los cambios persisten en la sesión
- [ ] 2.2 Implementar función `actualizar_kg_disponibles` en `crud.py` siguiendo el mismo patrón, y verificar que actualiza correctamente
- [ ] 2.3 Implementar función `actualizar_estado` en `crud.py` siguiendo el mismo patrón, y verificar que actualiza correctamente

## 3. Capa Router - Endpoints HTTP

- [ ] 3.1 Crear endpoint `PATCH /lotes/{lote_id}/kg-reales` en `backend/app/modules/inventario/router.py` que use `LoteKgRealesUpdate`, llame al servicio, retorne `LoteRead`, maneje `LoteNoEncontrado` (404), y verificar con una petición HTTP que responda correctamente
- [ ] 3.2 Crear endpoint `PATCH /lotes/{lote_id}/kg-disponibles` en `router.py` que use `LoteKgDisponiblesUpdate`, maneje `LoteNoEncontrado` (404) y `KgDisponiblesExcedeKgReales` (400), y verificar con peticiones HTTP ambos escenarios
- [ ] 3.3 Crear endpoint `PATCH /lotes/{lote_id}/estado` en `router.py` que use `LoteEstadoUpdate`, maneje `LoteNoEncontrado` (404), y verificar con una petición HTTP que responda correctamente
- [ ] 3.4 Actualizar función `_a_codigo_http` en `router.py` para mapear `KgDisponiblesExcedeKgReales` a HTTP 400, y verificar que el endpoint de kg-disponibles retorne 400 cuando corresponde

## 4. Documentación y Validación

- [ ] 4.1 Verificar que los tres nuevos endpoints aparezcan en Swagger UI en `http://localhost:8000/docs` con sus schemas correctos
- [ ] 4.2 Ejecutar pruebas manuales de los tres endpoints con datos válidos e inválidos, verificando los códigos de estado y mensajes de error esperados
- [ ] 4.3 Confirmar que las transacciones funcionen correctamente: que los cambios se persistan solo cuando no hay errores, y que se haga rollback en caso de excepción

## Workflow follow-up

- Archivar el cambio después de que las pruebas estén completas y validadas
