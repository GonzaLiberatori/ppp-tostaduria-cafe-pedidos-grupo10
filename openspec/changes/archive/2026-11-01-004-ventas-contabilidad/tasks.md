# Tasks: Integración de ventas con Contabilidad

## 1. Backend: resumen mensual de ventas

- [x] 1.1 Agregar `resumen_por_mes` en `backend/app/modules/ventas/crud.py`: dos consultas agrupadas por `func.strftime('%Y-%m', VentaComercial.fecha)` (una por mes con `count`/`sum(total)`, otra por mes + `PagoVenta.metodo_de_pago`), filtrando `VentaComercial.estado == CONFIRMADA` y el rango opcional con `_filtrar_por_fechas`. Verificar con tests nuevos en `backend/tests/modules/ventas/test_crud.py` que cubran dos meses, una venta `ANULADA` excluida y un rango sin ventas.
- [x] 1.2 Agregar `VentaResumenMensualRead` en `backend/app/modules/ventas/schemas.py` (`mes: str`, `cantidad_ventas: int`, `total_facturado: Decimal`, `totales_por_metodo: list[ResumenPorMetodo]`) y exportarlo en `__all__`. Verificar con `pytest tests/modules/ventas/test_schemas.py -q`.
- [x] 1.3 Implementar `VentaService.resumen_mensual(fecha_desde, fecha_hasta)` en `backend/app/modules/ventas/services.py` combinando ambas consultas en una lista ordenada por mes descendente. Verificar con `pytest tests/modules/ventas/test_services.py -q` (meses, métodos por mes, lista vacía).
- [x] 1.4 Exponer `GET /api/v1/ventas/resumen-mensual` en `backend/app/modules/ventas/router.py` antes de `/{venta_id}`, con `ROLES_CONSULTA` y `response_model=list[VentaResumenMensualRead]`. Verificar con `pytest tests/modules/ventas/test_router.py -q`: 200 para Administrador/Cajero/Operario, 403 para Cliente y 401 sin token; confirmar la ruta en `GET /openapi.json`.
- [x] 1.5 Documentar el endpoint y la integración con Contabilidad en `docs/feature-ventas.md` (semántica de "ventas totales", exclusión de anuladas, agrupación por mes de la venta). Verificar que la ruta aparece en `/docs` al levantar la app.

## 2. Frontend: Contabilidad alimentada por ventas

- [x] 2.1 Agregar en `frontend/src/services/api.js`: `getVentas(params)`, `getResumenMensualVentas(params)` y `anularVenta(id, motivo)` usando `conQuery` y `request`. Verificar con `npm run build` que el cliente compila.
- [x] 2.2 En `frontend/src/context/DataContext.jsx`, agregar los estados `resumenVentasMensual` y `ventas`, cargarlos en la carga inicial solo para roles internos y con `.catch(() => [])` para que un fallo de ventas no vacíe el panel (`errors.contabilidad`). Reescribir `getContabilidadMensual()` para unir meses de ventas y gastos conservando `{ mes, ventasTotales, gastosTotales, gananciaNeta }`, y exponer un método que refresque ventas + resumen tras una anulación. Verificar con `npm run build` y comprobando que Dashboard y Contabilidad siguen renderizando con datos del seed.
- [x] 2.3 En `frontend/src/pages/Contabilidad.jsx`, agregar el bloque "Ventas registradas" con `Table` (comprobante, fecha, cliente, métodos, total, estado), filtro por estado y búsqueda, y la acción **Anular** con `Modal` (motivo obligatorio) para Administrador. Al confirmar, llamar a `anularVenta`, mostrar toast y refrescar listado + resumen. Verificar con `npm run build` y un recorrido manual: anular una venta descuenta el total de los KPIs y la fila queda `ANULADA`.
- [x] 2.4 Mostrar en Contabilidad un aviso visible cuando `errors.contabilidad` exista (por ejemplo, base sin migrar), sin bloquear el resto de la pantalla. Verificar apagando el backend de ventas o usando una base sin `003_ventas` y confirmando que el panel sigue cargando.

## 3. Limpieza del repositorio

- [x] 3.1 Eliminar `backend/app/modules/contabilidad/` (placeholder con imports a módulos inexistentes) y verificar que `..\.venv\Scripts\python.exe -c "from app.main import app"` sigue funcionando y que `pytest tests -q` no cambia su resultado.
- [x] 3.2 Sacar `backend/db_ventas.sqlite` del índice con `git rm --cached backend/db_ventas.sqlite` (sin borrar el archivo local), agregar `backend/db_ventas.sqlite` al `.gitignore` y verificar con `git status --short` que ya no aparece como staged.

## 4. Verificación de integración

- [x] 4.1 Aplicar `alembic upgrade head` sobre la base de trabajo y correr `pytest tests/modules/ventas -q` y `pytest tests -q` completos. Verificar que no hay fallos ni tests omitidos por import.
- [x] 4.2 Levantar backend y `npm run dev`, entrar como `admin@cafedefinca.com`, confirmar que Contabilidad muestra los totales de ventas confirmadas (no los pedidos entregados) y la tabla "Ventas registradas". Registrar una venta por Swagger sobre un pedido `ENTREGADO`, refrescar y verificar que suma; anularla desde la UI y verificar que deja de sumar. Confirmar que la tarjeta "Ventas del Mes" del Dashboard coincide.

## Workflow follow-up

- Ejecutar `openspec validate 004-ventas-contabilidad --strict` y `openspec validate --specs`.
- Archivar el cambio una vez aprobado el resultado y verificar el spec principal de `ventas`.
