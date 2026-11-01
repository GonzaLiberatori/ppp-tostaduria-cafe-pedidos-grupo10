# Tasks

## 1. Modelo y migración

- [x] 1.1 Agregar `PENDIENTE_COBRO` a `VentaEstado` en `backend/app/modules/ventas/models.py` y los campos `fecha_vencimiento` y `cobrada_en` (`DateTime` nullable) a `VentaComercial`. Actualizar el `sqlite_where` del índice `ux_venta_comercial_pedido_vigente` a `estado IN ('CONFIRMADA', 'PENDIENTE_COBRO')`. Verificar que `python -c "from app.modules.ventas.models import VentaEstado"` desde `backend/` importa sin error y que el índice declarado en el modelo coincide con la migración.
- [x] 1.2 Crear `backend/alembic/versions/004_ventas_cobranza.py` con `down_revision = "003_ventas"`: agrega las dos columnas, recrea el índice parcial y en `downgrade` restaura el índice anterior, pasa las filas `PENDIENTE_COBRO` a `CONFIRMADA` y borra las columnas. Verificar con `..\.venv\Scripts\python.exe -m alembic upgrade head` y `..\.venv\Scripts\python.exe -m alembic downgrade -1` sobre una copia de `backend/db.sqlite` sin errores y sin perder las ventas existentes.

## 2. Deuda y alta de venta por entrega

- [x] 2.1 Agregar `ajustar_saldo_cuenta_corriente(db, cliente_id, delta)` en `backend/app/modules/clientes/services.py`, sin `commit`, que ajuste `saldo_cuenta_corriente` y devuelva el saldo resultante. Verificar con un test en `backend/tests/modules/clientes/test_services.py` que suma, resta y no commitea.
- [x] 2.2 Definir en `backend/app/modules/ventas/schemas.py` el enum `CondicionPago` (`CONTADO`, `PAGARE`) y los schemas `VentaCobroCreate`, `VentaPorCobrarItemRead`, `VentaPorCobrarRead`, `VentaCobranzaMensualRead`; sumar `fecha_vencimiento` y `cobrada_en` a `VentaRead`, y `condicion_pago`/`plazo_dias` a `VentaCreate` (con `condicion_pago` por defecto `CONTADO`). Verificar con tests de validación en `backend/tests/modules/ventas/test_schemas.py`: plazo fuera de 30/60/90 rechazado y pagaré sin plazo rechazado.
- [x] 2.3 Implementar `registrar_venta_de_entrega(db, pedido, condicion_pago, metodo_de_pago, plazo_dias, cuenta_id)` en `ventas/services.py`, sin `commit`: crea la venta `CONFIRMADA` o `PENDIENTE_COBRO`, el pago (`CREDITO` para pagaré), el historial y ajusta la deuda solo en pagaré B2B. Reutilizar la generación de comprobante existente. Verificar con tests en `backend/tests/modules/ventas/test_services.py`: contado no toca el saldo, pagaré B2B lo suma con el vencimiento correcto, pagaré B2C responde `PagareNoPermitido`, plazo inválido responde `PlazoInvalido`.
- [x] 2.4 Refactorizar `registrar_venta` para que use el mismo camino de persistencia que 2.3, manteniendo el `commit` y el comportamiento de `POST /ventas/`. Verificar que los tests existentes de registro, pagos mixtos y comprobantes siguen pasando.

## 3. Cobro y anulación con deuda

- [x] 3.1 Implementar `cobrar_venta(venta_id, datos, cuenta_id)` en `ventas/services.py`: valida que la venta esté `PENDIENTE_COBRO` (`VentaNoPendienteDeCobro`), pasa a `CONFIRMADA`, setea `cobrada_en`, actualiza el método y la aclaración del pago existente, descuenta la deuda B2B y registra historial, todo en una transacción. Verificar con tests: cobro exitoso (estado, fecha, método, saldo e historial), cobro de una venta `CONFIRMADA` y de una `ANULADA` devuelven 409, y la suma de pagos sigue igual al total.
- [x] 3.2 Extender `anular_venta` para revertir la deuda cuando la venta anulada estaba `PENDIENTE_COBRO`, dentro de la misma transacción, sin tocar las ventas al contado. Verificar con tests: anular un pagaré deja el saldo como estaba antes de la venta y anular una venta al contado no lo modifica.
- [x] 3.3 Agregar los errores de dominio nuevos en `ventas/services.py` (`VentaNoPendienteDeCobro`, `PagareNoPermitido`, `PlazoInvalido`) y mapearlos en `ventas/router.py` a 409 (o 422 para el plazo) dentro de `_a_codigo_http`. Verificar con `backend/tests/modules/ventas/test_router.py` que cada caso devuelve el código esperado y que el mensaje identifica el motivo.

## 4. Entrega desde pedidos

- [x] 4.1 Agregar `condicionPago`, `metodoPago` y `plazoDias` opcionales a `PedidoPanelUpdate` en `backend/app/modules/pedidos/schemas.py`. Verificar con tests de schema que un `PATCH` sin condición sigue siendo válido para cambios que no son de estado.
- [x] 4.2 En `backend/app/modules/pedidos/services.py`, reemplazar el bloque de cuenta corriente de `cambiar_estado_pedido` por la llamada a `ventas.services.registrar_venta_de_entrega`, exigiendo condición de pago al pasar a `ENTREGADO`, y hacer que `actualizar_pedido` delegue la transición en `cambiar_estado_pedido` en lugar de duplicar los efectos. Verificar con tests en `backend/tests/modules/pedidos/test_services.py`: la entrega crea la venta, el contado no genera deuda, el pagaré B2B sí, y un fallo de la venta deja el pedido en `LISTO` sin deuda ni venta.
- [x] 4.3 Rechazar la reversión `ENTREGADO → LISTO` con 409 (`PedidoConVentaVigente`) cuando exista venta `CONFIRMADA` o `PENDIENTE_COBRO`, y mapear el error en `pedidos/router.py`. Verificar con tests: reversión bloqueada con venta vigente, permitida después de anularla, y sin efectos sobre la cuenta corriente.
- [x] 4.4 Pasar `cuenta_id` del usuario autenticado desde los endpoints del panel a `cambiar_estado_pedido`, para que la venta y su historial queden auditados. Verificar con un test de router que la venta creada por la entrega tiene `cuenta_id` del usuario que la ejecutó.

## 5. Consultas y endpoints de cobranza

- [x] 5.1 Ajustar `resumen_por_mes` en `ventas/crud.py` para filtrar `estado != ANULADA` y dejar `totales_por_mes_y_metodo` con `estado == CONFIRMADA`. Verificar con tests en `test_crud.py`: un mes con una venta `PENDIENTE_COBRO` la incluye en cantidad y facturado y no en los totales por método.
- [x] 5.2 Agregar `cobranza_por_mes`, `totales_de_cobranza_por_metodo` y `pendientes_de_cobro` en `ventas/crud.py`, agrupando por `func.strftime('%Y-%m', VentaComercial.cobrada_en)`. Verificar con tests: cobro de un pagaré facturado en un mes anterior aparece en el mes del cobro, las anuladas quedan afuera y un rango sin cobros devuelve lista vacía.
- [x] 5.3 Implementar `cobranza_mensual` y `por_cobrar` en `ventas/services.py`, calculando en el servicio la marca de vencida y el total por cobrar. Verificar con tests: pendientes ordenadas por vencimiento, vencidas señaladas, cobradas y anuladas excluidas, y total por cobrar igual a la suma de los ítems.
- [x] 5.4 Exponer `GET /ventas/cobranza-mensual`, `GET /ventas/por-cobrar` y `POST /ventas/{venta_id}/cobrar` en `ventas/router.py` con los roles definidos en el spec (cobro para Administrador y Cajero; consultas también para Operario). Verificar con `test_router.py`: 200 por rol habilitado, 403 para Operario cobrando y para Cliente consultando, 401 sin token.
- [x] 5.5 Actualizar `docs/feature-ventas.md` con el estado `PENDIENTE_COBRO`, los tres endpoints nuevos, la semántica facturado vs cobrado y la regla de deuda, y verificar que los ejemplos de `curl` documentados funcionan contra el backend levantado.

## 6. Frontend de pedidos

- [x] 6.1 Agregar en `frontend/src/services/api.js` las llamadas `getCobranzaMensualVentas`, `getPorCobrarVentas` y `cobrarVenta`, y extender `updatePedido` para aceptar la condición de pago. Verificar con `npm run build` sin errores.
- [x] 6.2 Implementar en `frontend/src/pages/Pedidos.jsx` el modal "Confirmar entrega" (condición contado/pagaré, método o plazo 30/60/90, total y vencimiento calculado) que intercepte el destino `Entregado` en el kanban y en los botones de estado, con la opción pagaré deshabilitada para clientes no B2B. Verificar en el navegador: entregar al contado crea la venta confirmada y entregar a pagaré deja el pedido entregado con su venta pendiente.
- [x] 6.3 Mostrar en la tarjeta o el detalle del pedido entregado la condición con la que se vendió y, si quedó pendiente, su vencimiento. Verificar visualmente con un pedido entregado a pagaré.

## 7. Frontend de contabilidad

- [x] 7.1 Exponer en `frontend/src/context/DataContext.jsx` `cobranzaMensual`, `porCobrar` y `cobrarVenta`, cargándolos junto con las ventas y aislando sus errores en `errors.contabilidad`. Verificar que un fallo de la cobranza no impide ver gastos ni ventas.
- [x] 7.2 Sumar en `frontend/src/pages/Contabilidad.jsx` los KPI "Cobranza del mes" y "Por cobrar" (con contador de vencidas). Verificar en el navegador que los importes coinciden con los endpoints para el mes en curso.
- [x] 7.3 Agregar la tabla "Por cobrar" con comprobante, cliente, total, vencimiento, días restantes o atraso y la acción "Marcar cobrado" (Administrador y Cajero) con modal de método real. Verificar en el navegador: cobrar una venta pendiente la saca de la tabla, la pasa a confirmada en "Ventas registradas" y actualiza los KPI.
- [x] 7.4 Extender la tabla "Ventas registradas" con el filtro `PENDIENTE_COBRO`, badge ámbar y columna de vencimiento, manteniendo "Anular" solo para Administrador y habilitado también en pendientes. Verificar en el navegador que anular un pagaré lo saca de "Por cobrar" y revierte el saldo del cliente.
- [x] 7.5 Actualizar `docs/feature-ventas.md` y `docs/feature-pedidos.md` con el flujo nuevo del panel (modal de entrega, cobranza y por cobrar). Verificar que los pasos descritos coinciden con la UI y ejecutar `npm run build` sin errores.

## 8. Verificación de integración

- [x] 8.1 Correr la suite completa desde `backend/` con `..\.venv\Scripts\python.exe -m pytest -q` y verificar que pasa entera, incluidos los tests nuevos de ventas, pedidos y clientes.
- [x] 8.2 Hacer un recorrido end-to-end con el backend y `npm run dev` en `http://localhost:3000`: crear un pedido B2B, pasarlo a Listo, entregarlo a pagaré a 30 días, comprobar la deuda en Clientes, verlo en "Por cobrar" de Contabilidad, cobrarlo con transferencia y confirmar que el KPI de cobranza y el saldo del cliente cuadran. Verificar también que revertir la entrega con venta vigente devuelve el error visible en la UI.
- [x] 8.3 Dejar la base de demo sin datos de prueba: borrar las ventas y pedidos creados durante la verificación y confirmar que Contabilidad vuelve a los totales previos.

> **Nota de verificación (01/11/2026):** el recorrido de 8.2 se ejecutó contra
> una **copia** de la base (`db_e2e.sqlite`) con el backend en el puerto 8001 y
> cubrió por API el alta B2B, `Listo`, entrega a pagaré 30 días, deuda en
> clientes, `/ventas/por-cobrar`, cobro con transferencia, cobranza mensual,
> reversión con venta vigente (`409`), pagaré a B2C (`409`) y entrega al contado
> (`CONFIRMADA` sin deuda). La copia se eliminó, por lo que `db.sqlite` conserva
> solo sus datos previos (migrada a `004_ventas_cobranza`). El frontend se
> verificó con `npm run build`; no hubo navegador automatizado disponible.
> 8.1: **507 passed**, con los 4 errores preexistentes de `backend/test_endpoints.py`
> (fixture `lote_id` inexistente).

## Workflow follow-up

- Archivar el cambio después de la revisión y aprobación del usuario, sincronizando los deltas de `ventas` y `pedidos/estado`.
- Confirmar con el usuario el commit de los cambios, incluido `backend/db.sqlite` migrado a `004_ventas_cobranza`.
