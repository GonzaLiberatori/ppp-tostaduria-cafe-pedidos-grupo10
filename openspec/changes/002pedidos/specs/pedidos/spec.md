# Spec Delta: Módulo de Pedidos (002pedidos)

## Purpose
Implementar el ciclo de vida completo de pedidos para demo: creación con validación FIFO, listado filtrado, detalle con auditoría, máquina de estados con reversiones controladas, eliminación con rollback, e idempotencia.

## ADDED Requirements

### Requirement: Crear pedido con validación FIFO e idempotencia
El sistema DEBE permitir crear un pedido especificando cliente, items (tipo de café/blend, kilos, molienda, perfil), método de despacho y observaciones. Al crear:
- Validar stock suficiente consumiendo FIFO (lotes abiertos por fecha vencimiento)
- Calcular total y subtotales automáticamente (precio base + molienda + perfil)
- Generar/aplicar `idempotency_key` (header o SHA256(cliente+items+fecha))
- Crear `PedidoEstadoHistorial` inicial (estado: Pendiente)
- Todo en una transacción ACID

#### Scenario: Creación exitosa con stock suficiente
- **WHEN** usuario crea pedido con items que tienen stock disponible
- **THEN** sistema crea pedido con estado Pendiente, consume stock FIFO, calcula total, registra historial, retorna pedido con ID

#### Scenario: Rechazo por stock insuficiente
- **WHEN** usuario crea pedido solicitando más kilos de los disponibles
- **THEN** sistema rechaza con error 409 indicando stock disponible por item

#### Scenario: Idempotencia - reintento de petición idéntica
- **WHEN** misma petición (mismo cliente, items, fecha) se envía dos veces
- **THEN** sistema retorna el mismo pedido existente en el segundo intento (200 OK), sin duplicar ni consumir stock extra

### Requirement: Listar pedidos con filtros y paginación
El sistema DEBE permitir listar pedidos con filtros opcionales:
- Por estado (Pendiente, Listo, Entregado)
- Por cliente (ID)
- Por rango de fechas (desde/hasta)
- Búsqueda por texto (cliente, método contacto, observaciones)
Con paginación (page, size) y ordenamiento por fecha descendente.

#### Scenario: Listado básico sin filtros
- **WHEN** usuario solicita listado de pedidos
- **THEN** sistema retorna lista paginada ordenada por fecha descendente con: id, fecha, cliente, estado, items_count, kilos_totales, total, metodo_contacto

#### Scenario: Filtrado combinado
- **WHEN** usuario filtra por estado=Listo y cliente_id=X
- **THEN** sistema retorna solo pedidos que coincidan con ambos criterios

### Requirement: Obtener detalle completo de pedido
El sistema DEBE retornar el detalle completo incluyendo:
- Datos del pedido (id, fecha, estado, total, metodo_despacho, observaciones)
- Items expandidos (variedad/blend, kilos, precio/kg, subtotal, molienda, perfil)
- Datos del cliente (nombre, tipo, dirección, teléfono)
- Historial de estados (timestamp, estado_anterior, estado_nuevo, usuario)

#### Scenario: Detalle de pedido existente
- **WHEN** usuario solicita detalle de pedido válido
- **THEN** sistema retorna pedido con items, cliente e historial

#### Scenario: Pedido inexistente
- **WHEN** usuario solicita detalle de ID inexistente
- **THEN** sistema retorna error 404

### Requirement: Máquina de estados con auditoría
El sistema DEBE implementar transiciones validadas:
- PENDIENTE -> LISTO (preparación completada)
- LISTO -> PENDIENTE (cancelar preparación)
- LISTO -> ENTREGADO (entrega confirmada) - **Actualiza cuenta corriente B2B**
- ENTREGADO -> LISTO (corrección error) - **Revierte cuenta corriente B2B**

Cada transición DEBE:
- Validar que la transición es permitida
- Registrar en `PedidoEstadoHistorial` (timestamp, usuario, estado_anterior, estado_nuevo)
- Ejecutar efectos laterales (cuenta corriente) en la misma transacción

#### Scenario: Avance Pendiente -> Listo
- **WHEN** usuario cambia estado de Pendiente a Listo
- **THEN** sistema actualiza estado, registra historial, NO modifica stock ni cuenta corriente

#### Scenario: Entrega a cliente B2B actualiza cuenta corriente
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2B
- **THEN** sistema actualiza estado a Entregado, registra historial, suma total a `saldo_cuenta_corriente` del cliente

#### Scenario: Reversión Entregado -> Listo (cliente B2B)
- **WHEN** usuario cambia estado de Entregado a Listo para cliente B2B
- **THEN** sistema actualiza estado a Listo, registra historial, resta total de `saldo_cuenta_corriente`

#### Scenario: Rechazo transición inválida
- **WHEN** usuario intenta Pendiente -> Entregado (saltando Listo)
- **THEN** sistema rechaza con error 409 (transición no permitida)

### Requirement: Eliminar pedido con rollback FIFO
El sistema DEBE permitir eliminar un pedido SOLO si su estado es Pendiente. Al eliminar:
- Revertir consumo FIFO restaurando kilos exactos a lotes originales
- Eliminar historial de estados
- Eliminar items y pedido
- Todo en una transacción

#### Scenario: Eliminación exitosa de pedido Pendiente
- **WHEN** usuario elimina pedido en estado Pendiente
- **THEN** sistema elimina pedido, restaura stock FIFO exacto, elimina historial

#### Scenario: Rechazo al eliminar pedido no Pendiente
- **WHEN** usuario intenta eliminar pedido en estado Listo o Entregado
- **THEN** sistema rechaza con error 409 (solo Pendiente eliminable)

### Requirement: Cuenta corriente B2B
El modelo `Cliente` DEBE tener:
- `saldo_cuenta_corriente` (Numeric, default 0)
- `es_b2b` (Boolean, derivado de `tipo == 'Mayorista'`)
- Solo actualizar en transiciones a/desde ENTREGADO

#### Scenario: Entrega B2B incrementa deuda
- **WHEN** pedido de cliente Mayorista pasa a Entregado
- **THEN** `saldo_cuenta_corriente += total_pedido`

#### Scenario: Reversión B2B decrementa deuda
- **WHEN** pedido de cliente Mayorista vuelve de Entregado a Listo
- **THEN** `saldo_cuenta_corriente -= total_pedido`

#### Scenario: Cliente Consumidor Final no afecta cuenta corriente
- **WHEN** pedido de cliente Consumidor Final cambia estado
- **THEN** NO modifica `saldo_cuenta_corriente`

## MODIFIED Requirements

### Requirement: Modelo Pedido existente
Se MODIFICA para agregar:
- `idempotency_key` (String(64), UNIQUE, nullable, indexado)
- `medio_contacto` (String(50), nullable)
- `observaciones` (Text, nullable)
- Relación `historial_estados` con `PedidoEstadoHistorial`

### Requirement: Modelo Cliente existente
Se MODIFICA para agregar:
- `saldo_cuenta_corriente` (Numeric(12,2), default 0)
- `es_b2b` (Boolean, computed: tipo == 'Mayorista')

## REMOVED Requirements
Ninguno.