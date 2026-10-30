# Proposal

## Why

El ciclo operativo hoy termina en la entrega: el pedido pasa a `ENTREGADO` y ahí se corta la trazabilidad. No queda registro de cómo se cobró, con qué medio, ni un comprobante consultable, así que no se puede hacer arqueo de caja ni corregir una entrega mal cerrada sin tocar datos a mano. Las tablas `venta` y `pago` existen en `pedidos/models.py` pero ningún flujo las usa ni se corresponden con lo que el mostrador necesita (una venta con varios pagos de importe).

Este cambio agrega ese cierre comercial como un módulo propio, **sin modificar el comportamiento ni los archivos de los demás módulos**.

## What Changes

- **Nuevo módulo backend `ventas`** con el vertical slice completo: `models.py`, `schemas.py`, `crud.py`, `services.py`, `router.py`. No importa routers ajenos ni es importado por otros módulos salvo el registro en `main.py`.
- **Modelo propio de venta**: `VentaComercial` 1:N con `PagoVenta` (importe, no porcentaje) y `VentaComercialHistorial` para auditoría. Tablas nuevas (`venta_comercial`, `pago_venta`, `venta_comercial_historial`), separadas de las tablas heredadas `venta`/`pago`, que quedan intactas y sin uso.
- **Registro transaccional del cobro**: `POST /api/v1/ventas` sobre un pedido en estado `ENTREGADO` sin venta vigente; uno o varios pagos cuya suma debe coincidir con el total del pedido; comprobante único `V-AAAAMM-######`.
- **Anulación lógica**: `POST /api/v1/ventas/{id}/anular` marca `ANULADA` con motivo y usuario. No elimina y no reutiliza el comprobante.
- **Consulta y arqueo**: listado filtrable por fecha, estado, método de pago y cliente; resumen de totales y cantidades por método para cierre de caja; consulta por id y por comprobante.
- **RBAC local del módulo**: el rol se resuelve dentro de `ventas/router.py` consultando la cuenta autenticada. No se toca `core/deps.py` ni `auth/schemas.py`.
- **Migración Alembic** `003_ventas` sobre `57cf7419baaf`, sin tocar tablas existentes.

### Límites explícitos de este alcance

Estos tres puntos no son un olvido: son la consecuencia de no modificar los módulos de los demás.

- **La deuda B2B sigue imputándola `pedidos`** al pasar el pedido a `ENTREGADO`. La venta registra el cobro real (incluidos los pagos `CREDITO`) pero **no** escribe `Cliente.saldo_cuenta_corriente`; si lo hiciera, la deuda se duplicaría. Consecuencia aceptada: un cliente Mayorista que paga todo en efectivo igual queda con deuda registrada, porque esa decisión la tomó el flujo de pedidos.
- **La anulación no repone stock.** El stock lo reserva el pedido al crearse y sigue reservado mientras el pedido exista; al anular la venta el pedido no cambia de estado, así que la reserva sigue siendo válida. El stock solo vuelve si se elimina el pedido, y de eso ya se encarga `pedidos` con su propio rollback FIFO.
- **La anulación no revierte la deuda.** La respuesta devuelve el `pedido_id` para que la reversión se haga desde el panel de pedidos (`ENTREGADO -> LISTO`), que ya ajusta el saldo.

## Capabilities

### New Capabilities

- `ventas`: registro del cobro de un pedido entregado, pagos múltiples con validación de total, comprobante único, consulta y arqueo por método de pago, y anulación lógica auditada que no altera stock ni cuenta corriente.

### Modified Capabilities

Ninguna. No se modifican specs de `pedidos`, `pedidos/estado` ni de inventario/clientes.

## Impact

- **Backend (nuevo)**: `app/modules/ventas/` completo y `app/modules/ventas/__init__.py`.
- **Backend (compartido, 5 líneas en total)**:
  - `app/main.py`: import del router + `include_router` (2 líneas).
  - `app/modules/pedidos/router.py`: agregar `Optional` al import de `typing` y `from datetime import datetime` (2 líneas). Sin esto la aplicación no importa y ningún test del backend se recolecta; no cambia ninguna lógica.
  - `alembic/env.py`: import de `ventas.models` (1 línea) para que `autogenerate`/`check` vean las tablas nuevas.
- **Base de datos**: migración `003_ventas` que solo crea tablas nuevas y un índice único parcial; reversible con `downgrade`.
- **API**: endpoints nuevos bajo `/api/v1/ventas`. Ningún endpoint existente cambia de contrato ni de comportamiento.
- **Tests**: `backend/tests/modules/ventas/` nuevo, con `conftest.py` propio que reutiliza las fixtures compartidas ya existentes (`sample_pedido_b2b_entregado`, `sample_pedido_con_stock`, entre otras). No se modifica `tests/conftest.py`.
- **Documentación**: `docs/feature-ventas.md` nuevo. No se modifica `docs/feature-pedidos.md`.
