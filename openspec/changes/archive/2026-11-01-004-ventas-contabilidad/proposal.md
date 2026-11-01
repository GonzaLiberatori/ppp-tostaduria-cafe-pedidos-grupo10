# Proposal: Integración de ventas con Contabilidad

## Why

La pantalla **Contabilidad** es el único lugar del panel donde se ven "ventas", pero hoy no usa el módulo `ventas`: `DataContext.getContabilidadMensual()` suma `pedido.total` de los pedidos en estado `Entregado` y lo cruza con `/gastos`. Consecuencias concretas:

- Registrar una venta no mueve ningún número de la pantalla.
- Anular una venta no descuenta nada.
- Un pedido entregado sin cobrar suma como si se hubiera cobrado.
- El arqueo por método de pago que ya expone `/ventas/resumen` no se ve en ningún lado.

Además, `backend/app/modules/contabilidad/__init__.py` importa `models`, `schemas`, `crud`, `services` y `router`, que no existen en ese directorio. No rompe el arranque solo porque `main.py` no lo importa, pero es un placeholder muerto que confunde sobre dónde vive la contabilidad.

Este cambio conecta la pantalla con el cobro real y deja la contabilidad de ventas dentro del módulo `ventas`, sin tocar gastos, pedidos ni inventario.

## What Changes

- **Nuevo endpoint `GET /api/v1/ventas/resumen-mensual`**: serie agregada por mes calendario con cantidad de ventas, total facturado y totales por método de pago, filtrable por rango y excluyendo las ventas `ANULADA`. Roles habilitados: Administrador, Cajero y Operario (los mismos de consulta).
- **Contabilidad alimentada por ventas**: los KPIs (Ventas Totales, Ganancia Neta Total, Mes Actual), la Evolución Mensual, la Ganancia Neta por Mes y el Resumen Contable Mensual pasan a calcularse con las ventas confirmadas + los gastos existentes. La forma de los datos que consume `Contabilidad.jsx` se conserva, así que la pantalla no se reescribe.
- **Bloque "Ventas registradas"** en Contabilidad: comprobante, fecha, cliente, métodos de pago, total y estado, ordenado por fecha descendente, con acción **Anular** para Administrador (motivo + confirmación) y refresco de KPIs y serie mensual.
- **Exportar Contabilidad** usa el mismo resumen mensual ya alimentado por ventas.
- **Limpieza**: se elimina el placeholder roto `backend/app/modules/contabilidad/` y se saca del índice `backend/db_ventas.sqlite` (el archivo local se conserva).
- **Sin cambios de contrato** en los endpoints existentes de `ventas`, `pedidos`, `gastos` ni `inventario`. No hay migración de base: el resumen es solo lectura.

### Fuera de alcance

- Alta de ventas desde la UI (botón "Cobrar" en Pedidos). Las ventas se siguen registrando por API/Swagger o por el flujo que exista.
- Cambios en el CRUD de gastos, en pedidos o en inventario.
- Conciliación de deuda B2B: sigue siendo responsabilidad de `pedidos`.
- Arqueo por método como pantalla propia: el endpoint ya existe; se muestra solo si el diseño lo incluye como bloque del resumen.

## Capabilities

### New Capabilities

Ninguna. La pantalla es un consumidor de comportamiento que ya existe (consulta, detalle y anulación) más el resumen mensual que se agrega a `ventas`.

### Modified Capabilities

- `ventas`: se agrega el requisito de **resumen mensual** de ventas (agregado por mes calendario, con cantidad, total facturado y totales por método, excluyendo anuladas) para alimentar la contabilidad del panel.

## Impact

- **Backend**: `app/modules/ventas/crud.py` (agregado por mes), `services.py`, `schemas.py`, `router.py` y `tests/modules/ventas/`. Sin migración.
- **Frontend**: `src/services/api.js` (resumen mensual y anulación), `src/context/DataContext.jsx` (fuente de la contabilidad mensual y refresco), `src/pages/Contabilidad.jsx` (tabla de ventas y anulación). `Dashboard.jsx` no cambia de código, pero su tarjeta "Ventas del Mes" pasa a mostrar ventas reales por compartir `getContabilidadMensual()`.
- **Limpieza**: eliminación de `backend/app/modules/contabilidad/` y `git rm --cached backend/db_ventas.sqlite`.
- **API**: un endpoint nuevo de solo lectura; ningún contrato existente cambia.
- **Datos**: los números de Contabilidad cambian de semántica (pedidos entregados → ventas confirmadas). Un pedido entregado sin venta deja de sumar y una venta anulada deja de sumar; es el comportamiento buscado, pero hay que comunicarlo al equipo.
- **Base de datos**: `backend/db.sqlite` sigue en la revisión `57cf7419baaf`; para probar hay que aplicar `alembic upgrade head` (migración `003_ventas`) o usar una base ya migrada.
