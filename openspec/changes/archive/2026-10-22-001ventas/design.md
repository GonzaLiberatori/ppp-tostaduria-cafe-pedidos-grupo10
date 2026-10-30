# Design

## Context

Ver proposal.md - Why. Resumen: backend vacío, frontend listo con UI completa (tabla, Kanban, formulario FIFO). Arquitectura vertical slice establecida en AGENTS.md: cada módulo con router/schemas/models/crud/services. Comunicación entre módulos SOLO via services. Transacciones ACID en services. FIFO ya implementado en frontend (DataContext.consumirStockFIFO) - replicar en backend. Base de datos: **MySQL** (mysqlclient/pymysql en requirements) según AGENTS.md. El backend está vacío; es el momento de configurar MySQL correctamente.

## Goals / Non-Goals

**Goals:**
- Implementar módulo `pedidos` completo (models, schemas, crud, services, router) listo para demo
- Transacciones ACID en services: crear/eliminar/cambiar estado = una transacción cada uno
- Consumo FIFO de stock (bolsas abiertas primero, luego cerradas por fecha) replicando lógica frontend
- Integración con `inventario` (stock tostado) y `clientes` (cuenta corriente B2B) via services
- Idempotencia en creación (clave única cliente+items+fecha)
- Migración Alembic **MySQL-compatible** para tablas pedidos/pedido_items/pedido_estado_historial
- Tests de services cubriendo transacciones, FIFO, idempotencia, cuenta corriente
- Setup MySQL: requirements, config, database, alembic.ini

**Non-Goals:**
- Pasarelas de pago (mencionado en AGENTS.md pero fuera de demo básica)
- Notificaciones push/email
- Reportes avanzados / analytics
- Frontend: solo adaptar DataContext a HTTP (ya tiene misma interfaz)
- Auth/JWT (módulo auth ya existe, solo usar dependencia get_current_user)
- Implementar services de inventario ni clientes (los consumen, no los crean)

## Decisions

### 1. Modelos SQLAlchemy (pedidos/models.py)
**Decision**: Tres tablas - `pedidos`, `pedido_items`, `pedido_estado_historial` con FKs string-referenciadas a `clientes.id` y `stock.id` (inventario).
**Rationale**: Normalización, items variables por pedido, trazabilidad por variedad, historial auditable. `stock` vive en módulo `inventario` - importar modelo via string FK para evitar circular imports.
**Alternativa**: JSONB para items - descartado por consultas/agregaciones y FK a stock.

### 2. Esquemas Pydantic (pedidos/schemas.py)
**Decision**: Schemas separados: `PedidoCreate`, `PedidoUpdate`, `PedidoItemCreate`, `PedidoRead`, `PedidoDetailRead`, `PedidoListRead`, `EstadoPedidoEnum`, `PedidoEstadoHistorialRead`.
**Rationale**: Validación estricta entrada/salida, documentación OpenAPI automática. `PedidoDetailRead` incluye items anidados + cliente.

### 3. Capa CRUD (pedidos/crud.py)
**Decision**: Solo queries puras sin lógica de negocio. Métodos: create, get, get_multi_con_filtros, update, delete, get_by_idempotency_key, create_pedido_items_bulk, create_estado_historial.
**Rationale**: Separación de responsabilidades. Services orquesta transacciones y lógica.

### 4. Capa Services (pedidos/services.py) - CORAZÓN DEL MÓDULO
**Decision**: Una clase `PedidoService` con métodos transaccionales:
- `crear_pedido()`: valida stock → llama `StockService.consumir_fifo()` (inventario) → crea pedido+items → llama `ClienteService.ajustar_cuenta_corriente()` si B2B (clientes) → registra historial → commit
- `cambiar_estado()`: valida transición → efectos laterales (cuenta corriente en Entregado via `ClienteService`) → registra historial → commit
- `eliminar_pedido()`: solo Pendiente → llama `StockService.restaurar_fifo()` (inventario) → revierte cuenta corriente via `ClienteService` → elimina historial → commit
- `get_pedidos_con_filtros()`: delega a CRUD
**Rationale**: Frontera transaccional única. Otros módulos (envios) importarán `PedidoService` no router ni CRUD. **Consume services de otros módulos, no los implementa**.

### 5. Consumo FIFO en Backend (módulo inventario - lo implementa compañero)
**Decision**: `inventario/services.py` expone `StockService.consumir_fifo(stock_id, kilos, session) -> (consumo_detalle, faltante)` y `StockService.restaurar_fifo(consumo_detalle, session)`. `PedidoService` los invoca.
**Rationale**: DRY - inventario dueño del stock. FIFO: bolsas abiertas (por fecha creación ASC) luego cerradas (por fecha creación ASC). Retorna detalle por bolsa para auditoría y rollback exacto.

### 6. Cuenta Corriente en clientes/services.py (módulo clientes - lo implementa compañero)
**Decision**: `clientes/services.py` expone `ClienteService.ajustar_cuenta_corriente(cliente_id, delta_monto, session)` y `ClienteService.get_by_id_con_tipo(cliente_id, session)`. `PedidoService` los invoca.
**Rationale**: Clientes dueño de cuenta corriente. Pedidos solo delega.

### 7. Idempotencia
**Decision**: Columna `idempotency_key` UNIQUE en `pedidos` (hash SHA256 de cliente_id + items_json + fecha_creacion_date). `crear_pedido` calcula key, busca existente, retorna si existe.
**Rationale**: Simple, a nivel BD, cubre reintentos red. No requiere header externo.

### 8. Historial de Estados
**Decision**: Tabla `pedido_estado_historial` (pedido_id, estado_anterior, estado_nuevo, usuario_id, timestamp). `PedidoService` inserta en cada cambio.
**Rationale**: Auditoría completa, visible en frontend. Bajo overhead.

### 9. Router (pedidos/router.py)
**Decision**: Endpoints REST estándar + `/estado` para transiciones explícitas. Dependencias: `get_db`, `get_current_user` (auth). Response models = schemas de salida.
**Rationale**: Convención REST, OpenAPI auto, fácil testing.

### 10. Migración Alembic
**Decision**: Una migración **MySQL-compatible** que crea `pedidos`, `pedido_items`, `pedido_estado_historial` con FKs, índices, constraints UNIQUE (`idempotency_key`), CHECK (`estado IN ('Pendiente','Listo','Entregado')`). Usar tipos MySQL: BIGINT, DECIMAL(12,2), DATETIME, VARCHAR, ENUM.
**Rationale**: Atómica, reversible, compatible con MySQL.

## Risks / Trade-offs

- [Stock race condition] → Transacción SERIALIZABLE o SELECT FOR UPDATE en `StockService.consumir_fifo`; para demo basta REPEATABLE READ + lock optimista en servicios
- [FIFO drift frontend/backend] → Única fuente de verdad: backend. Frontend solo preview; al guardar, backend recalcula y aplica
- [Cuenta corriente negativa B2B] → Validar límite crédito en `ClienteService.ajustar_cuenta_corriente`; para demo: solo warning, no bloquear
- [Migración datos mock] → Script seed opcional para poblar BD con datos de `mockData.js` al levantar demo
- [Dependencia circular pedidos<->inventario<->clientes] → Services solo importan services de otros módulos, nunca models directamente (usar string imports en FKs)
- [MySQL setup] → Agregar mysqlclient a requirements, configurar config.py, database.py, alembic.ini antes de primera migración