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
El sistema DEBE permitir cambiar estado de Listo a Entregado confirmando la entrega fisica e indicando la condicion de pago. En la misma transaccion DEBE registrarse la venta del pedido. Solo las ventas a pagare de clientes B2B suman el total a la cuenta corriente; las ventas al contado no generan deuda.

#### Scenario: Entrega a cliente B2B actualiza cuenta corriente
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2B indicando pagare a 30 dias
- **THEN** sistema actualiza estado a Entregado, registra la venta pendiente de cobro con su vencimiento y suma el total del pedido a la cuenta corriente del cliente

#### Scenario: Entrega a cliente B2C no afecta cuenta corriente
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2C al contado
- **THEN** sistema actualiza estado a Entregado, registra la venta confirmada con ese metodo y NO modifica la cuenta corriente del cliente

#### Scenario: Entrega al contado de un cliente B2B no genera deuda
- **WHEN** usuario cambia estado de Listo a Entregado para cliente B2B indicando condicion al contado con metodo transferencia
- **THEN** sistema actualiza estado a Entregado, registra la venta confirmada y NO suma nada a la cuenta corriente del cliente

#### Scenario: Entrega a pagare de cliente B2C rechazada
- **WHEN** usuario intenta entregar a pagare un pedido de un cliente que no es B2B
- **THEN** sistema rechaza la operacion con error 409, no cambia el estado y no registra la venta

#### Scenario: Entrega sin condicion de pago
- **WHEN** usuario intenta pasar un pedido de Listo a Entregado sin indicar condicion de pago
- **THEN** sistema responde 422 por validacion de entrada y el pedido sigue en Listo

#### Scenario: Fallo al registrar la venta
- **WHEN** falla el registro de la venta durante la entrega
- **THEN** el pedido sigue en Listo, no se descuenta deuda y no queda una venta parcial

#### Scenario: Pedido con venta vigente
- **WHEN** usuario intenta entregar un pedido que ya tiene una venta vigente
- **THEN** sistema responde 409 y no duplica la venta

#### Scenario: Rechazo si pedido no esta Listo
- **WHEN** usuario intenta entregar un pedido Pendiente (saltandose Listo)
- **THEN** sistema rechaza con error 409 (se requiere pasar por Listo)

### Requirement: Transicion inversa Entregado -> Listo (correccion de error)
El sistema DEBE permitir revertir de Entregado a Listo solo como correccion operativa (ej. marca equivocada). Si el pedido tiene una venta vigente, la reversion DEBE rechazarse con 409 hasta que esa venta se anule. Sin venta vigente, la reversion no modifica la cuenta corriente.

#### Scenario: Reversion rechazada con venta vigente
- **WHEN** usuario intenta revertir a Listo un pedido entregado cuya venta sigue vigente
- **THEN** sistema responde 409 indicando que primero debe anularse la venta y el pedido sigue en Entregado

#### Scenario: Reversion de entrega a cliente B2B
- **WHEN** usuario revierte a Listo un pedido entregado de un cliente B2B que no tiene venta vigente
- **THEN** sistema actualiza estado a Listo y NO modifica la cuenta corriente del cliente

#### Scenario: Reversion de entrega a cliente B2C
- **WHEN** usuario revierte a Listo un pedido entregado de un cliente B2C
- **THEN** sistema actualiza estado a Listo y NO modifica la cuenta corriente

#### Scenario: Reversion permitida tras anular la venta
- **WHEN** usuario anula la venta del pedido y luego revierte el estado a Listo
- **THEN** sistema actualiza el estado a Listo

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
