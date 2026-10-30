# Proposal

## Why

El módulo **Pedidos y Ventas** es el núcleo comercial del MVP 1. Actualmente el backend está completamente vacío (todos los archivos .py de todos los módulos tienen 0 líneas) mientras que el frontend ya tiene una UI completa y funcional (vista tabla, vista Kanban, formulario con preview FIFO, filtros, estados) que opera contra mock data en localStorage. Necesitamos implementar el backend real para que la demo funcione end-to-end con persistencia real en **MySQL**, transacciones ACID, y integración con Inventario (stock café tostado) y Clientes (cuenta corriente).

## What Changes

- **Nuevo módulo backend `pedidos`**: Models, Schemas, CRUD, Services, Router siguiendo la arquitectura vertical slice del proyecto
- **Modelos de datos**: `Pedido`, `PedidoItem`, `PedidoEstadoHistorial` con relaciones a `Cliente` y `Stock` (café tostado)
- **API REST**: CRUD completo + cambio de estado + listado con filtros
- **Lógica de negocio transaccional**: Crear pedido → validar stock → consumir FIFO → actualizar cuenta corriente → todo en una transacción
- **Integración con módulos existentes**: `inventario` (stock tostado, consumo FIFO), `clientes` (cuenta corriente, límite crédito), `envios` (generación automática desde jobs programados) — **solo consumo de sus services, no implementación**
- **Tests de servicios**: Casos críticos de transacción, idempotencia, FIFO, cuenta corriente
- **Setup MySQL**: Configuración de BD, requirements, Alembic para MySQL

## Capabilities

### New Capabilities

- `pedidos`: Gestión completa del ciclo de vida de pedidos (crear, listar, detalle, actualizar estado, eliminar) con consumo de stock FIFO y actualización de cuenta corriente del cliente
- `pedidos/estado`: Máquina de estados del pedido (Pendiente → Listo → Entregado) con reglas de transición y efectos colaterales (stock, cuenta corriente)

### Modified Capabilities

*No hay specs existentes en el proyecto; todos son nuevos.*

## Impact

- **Backend**: `app/modules/pedidos/` (5 archivos), `app/core/config.py`, `app/core/database.py`, `app/main.py` (registro router)
- **Base de datos**: Migración Alembic **MySQL-compatible** para tablas `pedidos`, `pedido_items`, `pedido_estado_historial` + FK a `clientes`, `stock` (inventario)
- **Dependencias**: `requirements.txt` → reemplazar `psycopg2-binary` por `mysqlclient==2.2.4` (o `pymysql==1.1.1`)
- **Frontend**: `DataContext.jsx` → reemplazar localStorage por llamadas HTTP al backend (ya preparado con la misma interfaz)
- **Tests**: `backend/tests/modules/pedidos/test_services.py` (transacciones, FIFO, idempotencia, cuenta corriente)