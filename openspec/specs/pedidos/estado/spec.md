# pedidos/estado Specification

## Purpose
Define la maquina de estados del pedido (Pendiente -> Listo -> Entregado) con reglas de transicion validadas y efectos colaterales automaticos sobre stock y cuenta corriente.

## Requirements

### Requirement: Transicion Pendiente -> Listo (preparacion completada)
El sistema DEBE permitir cambiar estado de Pendiente a Listo indicando que el pedido esta preparado para envio/entrega. Esta transicion NO consume stock adicional (ya se consumo al crear) NI afecta cuenta corriente.

#### Scenario: Avance a Listo exitoso
- **WHEN** usuario cambia estado de pedido Pendiente a Listo
- **THEN** sistema actualiza estado a Listo, registra timestamp de preparacion, no modifica stock ni cuenta corriente

#### Scenario: Rechazo si pedido no esta Pendiente
- **WHEN** usuario intenta poner en Listo un pedido ya Entregado
- **THEN** sistema rechaza con error 409 (transicion invalida)

### Requirement: Transicion Listo -> Entregado (entrega confirmada)
El sistema DEBE permitir cambiar estado de Listo a Entregado confirmando la entrega fisica. Al entregar, si el cliente es B2B con cuenta corriente, el sistema DEBE registrar el cargo en la cuenta corriente del cliente (sumar al monto de deuda) dentro de la misma transaccion.

#### Scenario: Entrega a cliente B2B actualiza cuenta corriente
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2B
- **THEN** sistema actualiza estado a Entregado, registra timestamp de entrega, y suma el total del pedido a la cuenta corriente del cliente (montoDeuda += total)

#### Scenario: Entrega a cliente B2C no afecta cuenta corriente
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2C
- **THEN** sistema actualiza estado a Entregado, registra timestamp, NO modifica cuenta corriente (B2C paga al contado)

#### Scenario: Rechazo si pedido no esta Listo
- **WHEN** usuario intenta entregar un pedido Pendiente (saltandose Listo)
- **THEN** sistema rechaza con error 409 (se requiere pasar por Listo)

### Requirement: Transicion inversa Entregado -> Listo (correccion de error)
El sistema DEBE permitir revertir de Entregado a Listo solo como correccion operativa (ej. marca equivocada). Al revertir, DEBE restar el total de la cuenta corriente del cliente B2B (montoDeuda -= total) en la misma transaccion.

#### Scenario: Reversion de entrega a cliente B2B
- **WHEN** usuario cambia estado de Entregado a Listo para cliente B2B
- **THEN** sistema actualiza estado a Listo, resta el total de la cuenta corriente del cliente

#### Scenario: Reversion de entrega a cliente B2C
- **WHEN** usuario cambia estado de Entregado a Listo para cliente B2C
- **THEN** sistema actualiza estado a Listo, NO modifica cuenta corriente

### Requirement: Transicion inversa Listo -> Pendiente (cancelacion de preparacion)
El sistema DEBE permitir volver de Listo a Pendiente si la preparacion no se completo. NO DEBE haber efectos sobre stock (ya consumido al crear) ni cuenta corriente.

#### Scenario: Retroceso a Pendiente
- **WHEN** usuario cambia estado de Listo a Pendiente
- **THEN** sistema actualiza estado a Pendiente, sin efectos laterales

### Requirement: Historial de cambios de estado auditable
El sistema DEBE registrar automaticamente cada cambio de estado con timestamp, usuario que lo realizo, estado anterior y nuevo estado, accesible en el detalle del pedido.

#### Scenario: Consulta de historial de estados
- **WHEN** usuario ve detalle de pedido
- **THEN** sistema muestra linea de tiempo de cambios de estado con timestamps y usuarios
