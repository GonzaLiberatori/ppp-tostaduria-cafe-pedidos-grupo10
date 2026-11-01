# Spec Delta: Ventas

## ADDED Requirements

### Requirement: Venta a crédito pendiente de cobro

Una venta a pagaré DEBE nacer en estado `PENDIENTE_COBRO` con una `fecha_vencimiento` calculada sumando a la fecha de entrega el plazo pactado, que solo puede ser 30, 60 o 90 días. Mientras siga pendiente, la venta DEBE contar como facturada y no como cobrada.

#### Scenario: Vencimiento según el plazo pactado

- **WHEN** se registra una venta a pagaré con plazo de 60 días
- **THEN** la venta queda `PENDIENTE_COBRO` y su vencimiento es la fecha de entrega más 60 días

#### Scenario: Venta pendiente no suma como cobrada

- **WHEN** una venta está `PENDIENTE_COBRO`
- **THEN** su total cuenta como facturado y no aparece en la cobranza ni en los totales cobrados por método de pago

#### Scenario: Venta pendiente sin fecha de cobro

- **WHEN** una venta está `PENDIENTE_COBRO`
- **THEN** la venta no tiene fecha de cobro registrada

#### Scenario: Plazo fuera de los admitidos

- **WHEN** se intenta registrar una venta a pagaré con un plazo distinto de 30, 60 o 90 días
- **THEN** el sistema responde 422 por validación de entrada y no registra la venta

### Requirement: Cobro de una venta pendiente

El sistema DEBE permitir marcar cobrada una venta `PENDIENTE_COBRO` indicando el método real con el que se cobró. La venta DEBE pasar a `CONFIRMADA`, registrar la fecha de cobro y conservar total y comprobante, y sus pagos DEBEN quedar con el método informado.

#### Scenario: Cobro exitoso

- **WHEN** un usuario autorizado marca cobrada una venta `PENDIENTE_COBRO` indicando el método
- **THEN** la venta queda `CONFIRMADA`, registra la fecha de cobro, actualiza el método de sus pagos y descuenta la deuda del cliente

#### Scenario: Cobro de una venta ya cobrada

- **WHEN** se intenta cobrar una venta `CONFIRMADA`
- **THEN** el sistema responde 409 y no modifica la venta

#### Scenario: Cobro de una venta anulada

- **WHEN** se intenta cobrar una venta `ANULADA`
- **THEN** el sistema responde 409 y no modifica la venta

#### Scenario: Venta inexistente

- **WHEN** se intenta cobrar una venta que no existe
- **THEN** el sistema responde 404

#### Scenario: Cobro sin método de pago

- **WHEN** se intenta cobrar una venta pendiente sin indicar el método
- **THEN** el sistema responde 422 por validación de entrada

### Requirement: Saldo por cobrar

El sistema DEBE devolver las ventas `PENDIENTE_COBRO` con comprobante, cliente, total, fecha de entrega y fecha de vencimiento, señalando las que están vencidas, junto con el total por cobrar del conjunto.

#### Scenario: Listado de pendientes

- **WHEN** se consulta el saldo por cobrar y existen ventas pendientes
- **THEN** el sistema devuelve cada pendiente con su vencimiento y el total por cobrar

#### Scenario: Venta vencida señalada

- **WHEN** una venta pendiente tiene fecha de vencimiento anterior a hoy
- **THEN** la respuesta la marca como vencida

#### Scenario: Ventas cobradas o anuladas excluidas

- **WHEN** un pedido tuvo una venta pendiente que luego se cobró o se anuló
- **THEN** esa venta no aparece en el saldo por cobrar

#### Scenario: Sin pendientes

- **WHEN** no hay ventas pendientes de cobro
- **THEN** el sistema devuelve una lista vacía y total por cobrar en cero, sin error

### Requirement: Facturación y cobranza mensual

El resumen mensual DEBE contar como facturada toda venta no anulada, incluidas las pendientes de cobro, y DEBE sumar por método de pago solo los pagos de ventas ya cobradas. El sistema DEBE informar además la cobranza agrupada por mes de cobro, con independencia del mes de facturación.

#### Scenario: Mes con ventas pendientes

- **WHEN** un mes tiene una venta cobrada y una venta a pagaré sin cobrar
- **THEN** el total facturado del mes incluye ambas y los totales cobrados por método solo incluyen la cobrada

#### Scenario: Cobro de un pagaré en otro mes

- **WHEN** una venta facturada en un mes se cobra en el mes siguiente
- **THEN** la cobranza aparece en el mes en que se cobró y la facturación sigue en el mes de la venta

#### Scenario: Cobranza sin movimientos

- **WHEN** se consulta la cobranza de un mes sin cobros
- **THEN** el sistema devuelve el mes con total cobrado en cero o no lo devuelve, sin error

#### Scenario: Ventas anuladas excluidas

- **WHEN** un mes contiene una venta `ANULADA`
- **THEN** esa venta no suma en la facturación, ni en la cobranza, ni en los totales por método

## MODIFIED Requirements

### Requirement: Registrar la venta de un pedido entregado

El sistema DEBE permitir registrar una venta indicando el pedido, el tipo de facturación, la condición de pago y al menos un pago. La venta toma como importe el total del pedido y queda asociada al usuario que la registra. Nace `CONFIRMADA` si es al contado y `PENDIENTE_COBRO` si es a pagaré. Solo se admiten pedidos en estado `ENTREGADO` sin venta vigente.

#### Scenario: Registro exitoso

- **WHEN** un usuario autorizado registra una venta al contado sobre un pedido `ENTREGADO` sin venta vigente
- **THEN** el sistema crea la venta `CONFIRMADA` con su número de comprobante, guarda los pagos y devuelve la venta con su identificador

#### Scenario: Registro a pagaré

- **WHEN** un usuario autorizado registra una venta a pagaré a 30 días sobre un pedido entregado a un cliente Mayorista
- **THEN** el sistema crea la venta `PENDIENTE_COBRO` con su vencimiento, guarda el pago y suma el total a la cuenta corriente del cliente

#### Scenario: Pagaré a un cliente que no es Mayorista

- **WHEN** se intenta registrar una venta a pagaré para un cliente que no es Mayorista
- **THEN** el sistema responde 409 indicando que ese cliente no tiene cuenta corriente y no crea la venta

#### Scenario: Pedido inexistente

- **WHEN** se intenta registrar una venta para un pedido que no existe
- **THEN** el sistema responde 404 y no crea ningún registro

#### Scenario: Pedido no vendible

- **WHEN** se intenta registrar una venta sobre un pedido en estado `PENDIENTE` o `LISTO`
- **THEN** el sistema responde 409 indicando que el pedido todavía no fue entregado y no modifica ningún dato

#### Scenario: Registro no altera el estado del pedido

- **WHEN** se registra una venta sobre un pedido `ENTREGADO`
- **THEN** el pedido sigue en estado `ENTREGADO` y su historial de estados no recibe ninguna entrada

### Requirement: Venta vigente única por pedido

Un pedido DEBE tener como máximo una venta vigente, considerando vigentes los estados `CONFIRMADA` y `PENDIENTE_COBRO`. El sistema DEBE rechazar un segundo registro mientras la venta anterior siga vigente, incluso ante dos solicitudes concurrentes.

#### Scenario: Segundo registro rechazado

- **WHEN** se registra una venta para un pedido que ya tiene una venta `CONFIRMADA`
- **THEN** el sistema responde 409 y conserva la venta original sin duplicar pagos

#### Scenario: Segundo registro con una venta pendiente de cobro

- **WHEN** se registra una venta para un pedido cuya venta está `PENDIENTE_COBRO`
- **THEN** el sistema responde 409 y conserva la venta pendiente sin duplicar la deuda

#### Scenario: Registro con la venta anterior anulada

- **WHEN** la venta de un pedido fue anulada y se registra una venta nueva para ese mismo pedido
- **THEN** el sistema la acepta y la nueva venta recibe un comprobante propio

### Requirement: Consulta de ventas con filtros

El sistema DEBE permitir listar ventas por rango de fechas, estado, método de pago y cliente, con paginación y orden por fecha descendente. Cada fila DEBE informar comprobante, fecha, cliente, total, estado, métodos de pago utilizados y, cuando corresponda, la fecha de vencimiento.

#### Scenario: Listado por rango de fechas

- **WHEN** se consultan las ventas entre dos fechas
- **THEN** el sistema devuelve solo las ventas del rango, con comprobante, fecha, cliente, total, estado y métodos de pago utilizados

#### Scenario: Filtrado combinado

- **WHEN** se filtra por estado `ANULADA` y por cliente
- **THEN** el sistema devuelve solo las ventas que cumplen ambos criterios

#### Scenario: Filtro por método de pago

- **WHEN** se filtra por método `EFECTIVO`
- **THEN** el sistema devuelve solo las ventas con al menos un pago en ese método

#### Scenario: Filtro por ventas pendientes de cobro

- **WHEN** se filtra por estado `PENDIENTE_COBRO`
- **THEN** el sistema devuelve solo las ventas pendientes, cada una con su fecha de vencimiento

### Requirement: Anulación lógica de la venta

El sistema DEBE anular una venta sin eliminarla físicamente, registrando motivo, usuario y momento de la anulación. Una venta anulada DEBE conservar su comprobante y sus pagos para consulta. Si la venta anulada estaba `PENDIENTE_COBRO`, la anulación DEBE revertir la deuda que había generado en la cuenta corriente del cliente.

#### Scenario: Anulación exitosa

- **WHEN** un usuario autorizado anula una venta indicando un motivo
- **THEN** la venta queda `ANULADA` con su registro de historial, motivo, usuario y fecha de anulación

#### Scenario: Anulación repetida

- **WHEN** se intenta anular una venta ya anulada
- **THEN** el sistema responde 409 y no registra una segunda anulación

#### Scenario: Anulación sin motivo

- **WHEN** se intenta anular una venta sin indicar motivo
- **THEN** el sistema responde 422 por validación de entrada

#### Scenario: Venta inexistente

- **WHEN** se intenta anular una venta que no existe
- **THEN** el sistema responde 404

#### Scenario: La anulación informa el pedido a revertir

- **WHEN** se anula una venta
- **THEN** la respuesta incluye el identificador del pedido asociado para que la reversión de la entrega se gestione en el módulo de pedidos

#### Scenario: Anulación de una venta pendiente revierte la deuda

- **WHEN** se anula una venta `PENDIENTE_COBRO` de un cliente Mayorista
- **THEN** la deuda del cliente se reduce en el total de esa venta y la venta conserva sus pagos

### Requirement: La venta no altera stock ni cuenta corriente

El registro, el cobro y la anulación de una venta NO DEBEN modificar el stock de café tostado. La cuenta corriente del cliente solo se modifica por ventas a pagaré: suma la deuda al registrarse, la revierte al anularse y la descuenta al cobrarse.

#### Scenario: El stock no cambia al vender

- **WHEN** se registra una venta
- **THEN** los kilos disponibles de los lotes de café tostado quedan iguales a como estaban antes del registro

#### Scenario: La anulación no repone stock

- **WHEN** se anula una venta
- **THEN** los kilos disponibles de los lotes de café tostado no cambian

#### Scenario: Venta al contado no genera deuda

- **WHEN** se registra y luego se cobra una venta al contado
- **THEN** el saldo de cuenta corriente del cliente no cambia en ningún momento

#### Scenario: El saldo no cambia al vender ni al anular

- **WHEN** se registra y luego se anula una venta al contado de un cliente Mayorista
- **THEN** `saldo_cuenta_corriente` conserva el valor que tenía antes del registro

#### Scenario: Venta a pagaré genera deuda

- **WHEN** se registra una venta a pagaré de un cliente Mayorista
- **THEN** el saldo de cuenta corriente del cliente aumenta en el total de la venta

#### Scenario: Cobro de un pagaré descuenta la deuda

- **WHEN** se marca cobrada una venta a pagaré
- **THEN** el saldo de cuenta corriente del cliente se reduce en el total de esa venta

### Requirement: Autorización de las operaciones de venta

El sistema DEBE restringir el registro de ventas y el cobro a Administrador y Cajero, la anulación a Administrador y la consulta —incluidos cobranza y saldo por cobrar— a Administrador, Cajero y Operario. Un usuario con rol Cliente NO DEBE acceder a estos endpoints.

#### Scenario: Cajero registra una venta

- **WHEN** un usuario con rol Cajero registra una venta
- **THEN** el sistema la acepta

#### Scenario: Cajero cobra una venta pendiente

- **WHEN** un usuario con rol Cajero marca cobrada una venta pendiente
- **THEN** el sistema la acepta

#### Scenario: Cajero intenta anular

- **WHEN** un usuario con rol Cajero intenta anular una venta
- **THEN** el sistema responde 403

#### Scenario: Operario solo consulta

- **WHEN** un usuario con rol Operario consulta el listado, el resumen, la cobranza o el saldo por cobrar
- **THEN** el sistema responde 200 y, si intenta registrar, cobrar o anular una venta, responde 403

#### Scenario: Cliente consulta ventas

- **WHEN** un usuario con rol Cliente consulta el listado de ventas
- **THEN** el sistema responde 403

#### Scenario: Solicitud sin token

- **WHEN** se llama a cualquier endpoint de ventas sin token válido
- **THEN** el sistema responde 401
