# Proposal: Integración de métodos de pago y cobranza

## Why

Hoy la venta solo existe si alguien la carga a mano después de entregar, y el pedido no registra cómo se cobra. Al entregar, `pedidos` suma el total a la cuenta corriente de todo cliente B2B sin mirar el medio, así que una entrega cobrada en efectivo genera deuda igual. El negocio vende a pagaré a 30/60/90 días y necesita distinguir lo facturado de lo cobrado sin cargar la venta a mano ni inventar deuda.

## What Changes

- **La entrega genera la venta.** Al pasar un pedido de `Listo` a `Entregado` se crea la venta en la misma transacción. La condición de pago se elige en ese momento, no al crear el pedido.
- **Condición de pago en la entrega:** contado (efectivo, transferencia, débito, Mercado Pago, cheque al día) o pagaré con plazo fijo de 30, 60 o 90 días. Un cliente B2C no puede entregarse a pagaré.
- **Nuevo estado de venta `PENDIENTE_COBRO`** con `fecha_vencimiento` y `cobrada_en`. La venta a pagaré nace pendiente y pasa a `CONFIRMADA` cuando se cobra. **BREAKING**: `VentaEstado` gana un valor y el índice único parcial `ux_venta_comercial_pedido_vigente` se amplía a los estados vigentes.
- **La deuda B2B pasa a `ventas`.** Solo la venta a pagaré suma a `saldo_cuenta_corriente`; al cobrarse o anularse se revierte. `pedidos` deja de tocar la cuenta corriente.
- **`POST /ventas/{id}/cobrar`** (Administrador y Cajero) para marcar cobrada una venta pendiente, eligiendo el medio real con el que se cobró.
- **Facturado y cobranza separados:** `GET /ventas/resumen-mensual` sigue midiendo facturación e incorpora las ventas pendientes; nuevos `GET /ventas/cobranza-mensual` (por fecha de cobro) y `GET /ventas/por-cobrar` (saldo pendiente con vencimientos).
- **BREAKING**: revertir `Entregado` a `Listo` se rechaza con 409 si el pedido tiene una venta vigente; hay que anular la venta primero.
- **Contabilidad** suma los KPI "Cobranza del mes" y "Por cobrar", la tabla de pendientes con acción "Marcar cobrado" y el badge de estado pendiente. **Pedidos** suma el modal "Confirmar entrega" con la condición de pago.
- El alta manual `POST /ventas/` se mantiene para pedidos entregados sin venta (histórico y correcciones).

## Capabilities

### New Capabilities

Ninguna: el comportamiento nuevo pertenece a capacidades existentes.

### Modified Capabilities

- `ventas`: registro con condición de pago, estado `PENDIENTE_COBRO`, cobro, deuda B2B, facturación vs cobranza, consulta de pendientes y autorización del cobro.
- `pedidos/estado`: la transición `Listo → Entregado` crea la venta y condiciona la deuda al medio; la reversión a `Listo` se bloquea si hay venta vigente.

## Impact

- **Backend `ventas`**: `models.py` (`VentaEstado`, `fecha_vencimiento`, `cobrada_en`, índice parcial), `schemas.py`, `crud.py` (filtros del resumen, cobranza, por cobrar), `services.py` (alta por entrega, cobro, anulación con reversión de deuda), `router.py` (endpoints nuevos) y migración Alembic.
- **Backend `pedidos`**: `schemas.PedidoPanelUpdate` gana la condición de pago; `services.cambiar_estado_pedido` deja de ajustar la cuenta corriente y delega en `ventas`; `actualizar_pedido` reutiliza ese funnel; error nuevo 409 al revertir una entrega vendida.
- **Backend `clientes`**: función pública de ajuste de saldo para que `ventas` mueva la deuda sin importar `crud` ajeno.
- **Frontend**: `Pedidos.jsx` (modal de entrega), `Contabilidad.jsx` (KPIs, tabla por cobrar, acción cobrar, filtros y badges), `DataContext.jsx` y `services/api.js`.
- **Datos**: migración sobre `venta_comercial` (dos columnas y un índice). No se tocan `inventario` ni `auth`, y no se modifica el enum `MetodoPago` (el pagaré usa `CREDITO`).
- **Docs**: `docs/feature-ventas.md` y `docs/feature-pedidos.md`.
