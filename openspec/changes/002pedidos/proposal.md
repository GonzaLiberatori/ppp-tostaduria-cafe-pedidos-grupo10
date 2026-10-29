# Propuesta: Módulo de Pedidos para Demo (002pedidos)

## Resumen
Implementar el módulo completo de gestión de pedidos para una demo, incluyendo creación, listado, detalle, actualización de estados y eliminación, con validación de stock FIFO, idempotencia, auditoría de estados y cuenta corriente B2B.

## Alcance
- **Creación de pedidos**: Validación de stock, consumo FIFO, cálculo automático de totales, idempotencia
- **Listado y detalle**: Filtros por estado, cliente, fecha; vista completa con items y cliente
- **Estados**: Máquina de estados Pendiente <-> Listo <-> Entregado con auditoría completa
- **Eliminación**: Solo pedidos Pendiente, con rollback de stock
- **Cuenta corriente**: Actualización automática para clientes B2B al entregar/retornar

## Fuera de alcance
- Pasarelas de pago
- Notificaciones push/email
- Reportes avanzados
- Frontend (ya existe, solo adaptar DataContext)

## Criterios de aceptación
1. POST /api/v1/pedidos crea pedido con stock FIFO y idempotencia
2. GET /api/v1/pedidos lista con filtros y paginación
3. GET /api/v1/pedidos/{id} retorna detalle con items, cliente e historial
4. PATCH /api/v1/pedidos/{id}/estado valida transiciones y audita
5. DELETE /api/v1/pedidos/{id} solo si Pendiente, revierte stock
6. Tests pasan en verde con SQLite en memoria