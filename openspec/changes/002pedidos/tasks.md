# Tasks: Módulo de Pedidos Demo (002pedidos)

## Fase 0: Configuración Base y OpenSpec

- [x] **T0.1** Configurar Alembic `target_metadata` en `backend/alembic/env.py`
- [x] **T0.2** Crear `backend/tests/conftest.py` con fixtures SQLite en memoria
- [x] **T0.3** Implementar modelos mínimos en `backend/app/modules/inventario/models.py` (Stock) y `backend/app/modules/clientes/models.py` (Cliente con saldo_cuenta_corriente)
- [x] **T0.4** Crear `openspec/specs/pedidos/spec.md` sincronizando desde delta

## Fase 1: Modelos Core y Migración

- [x] **T1.1** Agregar `PedidoEstadoHistorial`, `idempotency_key`, `medio_contacto`, `observaciones` en `backend/app/modules/pedidos/models.py`
- [x] **T1.2** Generar migración inicial: `alembic revision --autogenerate -m "Initial: pedidos, historial, stock, cliente cuenta corriente"`
- [x] **T1.3** Aplicar migración: `alembic upgrade head`
- [x] **T1.5** Verificar migración: `alembic check`

## Fase 2: Esquemas Pydantic

- [ ] **T2.1** Completar `backend/app/modules/pedidos/schemas.py`:
  - `LineaPedidoCreate`, `LineaPedidoRead`
  - `PedidoCreate` (con items, idempotency_key opcional)
  - `PedidoUpdate` (solo estado, metodo_despacho, observaciones)
  - `PedidoDetailRead` (con items, cliente, historial_estados)
  - `PedidoListRead` (campos básicos para listado)
  - `PedidoEstadoHistorialRead`, `EstadoPedidoEnum`
  - Validaciones: `kilos > 0`, `precio_kg > 0`, `estado` en enum

## Fase 3: Capa CRUD

- [ ] **T3.1** Implementar en `backend/app/modules/pedidos/crud.py`:
  - `create_pedido`, `get_pedido`, `get_pedidos_con_filtros`, `update_pedido`, `delete_pedido`
  - `create_pedido_items_bulk`, `create_estado_historial`
  - `get_pedido_by_idempotency_key`
  - CRUD para `PedidoEstadoHistorial`

## Fase 4: Servicios (Lógica de Negocio)

- [ ] **T4.1** `PedidoService.crear_pedido` en `backend/app/modules/pedidos/services.py`:
  - Calcular idempotency_key (header o SHA256)
  - Verificar idempotencia
  - Validar stock FIFO (consumir lotes por fecha_vencimiento ASC)
  - Calcular total y subtotales
  - Crear pedido + items + historial (Pendiente)
  - Transacción ACID

- [ ] **T4.2** `PedidoService.cambiar_estado`:
  - Validar transiciones permitidas
  - Efectos laterales: cuenta corriente B2B (Entregado/Listo)
  - Registrar `PedidoEstadoHistorial`
  - Transacción ACID

- [ ] **T4.3** `PedidoService.eliminar_pedido`:
  - Solo si estado == Pendiente
  - Rollback FIFO exacto
  - Eliminar historial + items + pedido
  - Transacción ACID

- [ ] **T4.4** `StockService.consumir_fifo` / `restaurar_fifo` (en pedidos/services.py para demo)
- [ ] **T4.5** `ClienteService.ajustar_cuenta_corriente` / `get_by_id_con_tipo` (en pedidos/services.py para demo)

## Fase 5: Router HTTP

- [ ] **T5.1** Completar `backend/app/modules/pedidos/router.py`:
  - `POST /api/v1/pedidos` (crear con idempotency_key header)
  - `GET /api/v1/pedidos` (filtros + paginación)
  - `GET /api/v1/pedidos/{id}` (detalle con items, cliente, historial)
  - `PATCH /api/v1/pedidos/{id}` (campos editables)
  - `PATCH /api/v1/pedidos/{id}/estado` (transición validada)
  - `DELETE /api/v1/pedidos/{id}` (solo Pendiente)
  - `GET /api/v1/pedidos/cliente/{cliente_id}`

- [ ] **T5.2** Verificar registro en `backend/app/main.py`

## Fase 6: Tests

- [ ] **T6.1** `backend/tests/conftest.py`: fixtures `db_session` (SQLite memoria), `client` (TestClient), `auth_headers`
- [ ] **T6.2** `backend/tests/modules/pedidos/test_crud.py`: CRUD puro con mocks
- [ ] **T6.3** `backend/tests/modules/pedidos/test_services.py`:
  - Transacciones, FIFO, idempotencia, state machine, cuenta corriente
- [ ] **T6.4** `backend/tests/modules/pedidos/test_router.py`: TestClient endpoints
- [ ] **T6.5** Ejecutar suite completa: `pytest backend/tests/ -v`

## Fase 7: Verificación Demo

- [ ] **T7.1** Levantar servidor: `uvicorn backend.app.main:app --reload`
- [ ] **T7.2** Flujo manual end-to-end en Swagger `/docs`
- [ ] **T7.3** Suite completa: `pytest backend/tests/ -v` todo verde
- [ ] **T7.4** Sincronizar spec final: `openspec sync` (o manual)

---