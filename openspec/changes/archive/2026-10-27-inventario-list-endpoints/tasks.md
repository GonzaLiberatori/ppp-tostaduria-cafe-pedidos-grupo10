# Tasks

## 1. Capa CRUD - Funciones de listado

- [x] 1.1 Agregar función `listar_tipos_de_cafe` en `backend/app/modules/inventario/crud.py` que ejecute `select(TipoDeCafe).order_by(TipoDeCafe.id)` y devuelva todos los registros, verificando que retorne una lista vacía cuando no hay registros y todos los registros cuando existen
- [x] 1.2 Agregar función `listar_blends` en `backend/app/modules/inventario/crud.py` que ejecute `select(Blend).order_by(Blend.id)` y devuelva todos los registros con sus relaciones de composición cargadas, verificando que retorne una lista vacía cuando no hay registros y todos los blends cuando existen
- [x] 1.3 Agregar función `listar_lotes` en `backend/app/modules/inventario/crud.py` que acepte `tipo_de_cafe_id` y `blend_id` como parámetros opcionales, ejecute `select(Lote)` filtrando por el parámetro proporcionado y ordenando por `Lote.id`, verificando que retorne una lista vacía cuando no hay registros asociados y todos los lotes cuando existen, sin validar que el ID corresponda a un registro existente

## 2. Capa de Servicios - Lógica de negocio

- [x] 2.1 Agregar función `listar_tipos_de_cafe` en `backend/app/modules/inventario/services.py` que llame a `crud.listar_tipos_de_cafe` y convierta cada resultado a `TipoDeCafeRead` usando `model_validate`, verificando que retorne una lista de schemas válidos
- [x] 2.2 Agregar función `listar_blends` en `backend/app/modules/inventario/services.py` que llame a `crud.listar_blends` y convierta cada resultado a `BlendRead` usando `BlendRead.desde_orm`, verificando que retorne una lista de schemas válidos con sus composiciones
- [x] 2.3 Agregar función `listar_lotes` en `backend/app/modules/inventario/services.py` que valide la restricción XOR (exactamente uno de `tipo_de_cafe_id` o `blend_id` debe tener valor, el otro debe ser null), lance una excepción de validación si ambos son null o ambos tienen valor, llame a `crud.listar_lotes` con el parámetro válido y convierta cada resultado a `LoteRead` usando `model_validate`

## 3. Capa Router - Endpoints HTTP

- [x] 3.1 Agregar endpoint `GET /tipos-de-cafe` en `backend/app/modules/inventario/router.py` con `response_model=list[TipoDeCafeRead]` que llame a `services.listar_tipos_de_cafe`, verificando con una petición HTTP que responda 200 con una lista vacía o con registros
- [x] 3.2 Agregar endpoint `GET /blends` en `backend/app/modules/inventario/router.py` con `response_model=list[BlendRead]` que llame a `services.listar_blends`, verificando con una petición HTTP que responda 200 con una lista vacía o con registros incluyendo sus composiciones
- [x] 3.3 Agregar endpoint `GET /lotes` en `backend/app/modules/inventario/router.py` con `response_model=list[LoteRead]` que acepte `tipo_de_cafe_id` y `blend_id` como query parameters opcionales, llame a `services.listar_lotes`, maneje la excepción de validación XOR retornando 422, y verifique con peticiones HTTP que responda 200 con lista filtrada o vacía según corresponda

## 4. Validación y Documentación

- [x] 4.1 Verificar que los tres nuevos endpoints aparezcan en Swagger UI en `http://localhost:8000/docs` con sus schemas de respuesta correctos
- [x] 4.2 Ejecutar pruebas manuales de los endpoints de tipos de café y blends con la base de datos vacía, verificando que retornen 200 con lista vacía `[]`. Para el endpoint de lotes, verificar que retorne 422 cuando ambos parámetros son null
- [x] 4.3 Ejecutar pruebas manuales de los endpoints de tipos de café y blends con datos existentes, verificando que retornen 200 con todos los registros ordenados por id ascendente. Para el endpoint de lotes, verificar que retorne 200 con los lotes filtrados por el parámetro proporcionado (tipo_de_cafe_id o blend_id)

## Workflow follow-up

- Archivar el cambio después de que las pruebas estén completas y validadas
