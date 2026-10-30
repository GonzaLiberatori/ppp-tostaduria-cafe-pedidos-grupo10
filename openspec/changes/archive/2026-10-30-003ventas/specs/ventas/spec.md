# Spec Delta: ventas (003ventas)

## ADDED Requirements

### Requirement: Registrar la venta de un pedido entregado

El sistema DEBE permitir registrar una venta indicando el pedido, el tipo de facturación y al menos un pago. La venta DEBE crearse en estado `CONFIRMADA`, tomar como importe el total del pedido y quedar asociada al usuario que la registra. Solo se admiten pedidos en estado `ENTREGADO`.

#### Scenario: Registro exitoso

- **WHEN** un usuario autorizado registra una venta sobre un pedido `ENTREGADO` sin venta vigente
- **THEN** el sistema crea la venta `CONFIRMADA` con su número de comprobante, guarda los pagos y devuelve la venta con su identificador

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

Un pedido DEBE tener como máximo una venta en estado `CONFIRMADA`. El sistema DEBE rechazar un segundo registro mientras la venta anterior siga vigente, incluso ante dos solicitudes concurrentes.

#### Scenario: Segundo registro rechazado

- **WHEN** se registra una venta para un pedido que ya tiene una venta `CONFIRMADA`
- **THEN** el sistema responde 409 y conserva la venta original sin duplicar pagos

#### Scenario: Registro con la venta anterior anulada

- **WHEN** la venta de un pedido fue anulada y se registra una venta nueva para ese mismo pedido
- **THEN** el sistema la acepta y la nueva venta recibe un comprobante propio

### Requirement: Registro de pagos y validación del total

La venta DEBE aceptar uno o varios pagos, cada uno con método, monto, moneda y aclaración opcional. La suma de los montos DEBE coincidir exactamente con el total del pedido y cada monto DEBE ser mayor que cero.

#### Scenario: Pago único

- **WHEN** se registra una venta con un solo pago por el total del pedido
- **THEN** el sistema guarda el pago y la venta queda saldada

#### Scenario: Pago mixto

- **WHEN** se registra una venta con dos pagos cuyos montos suman el total
- **THEN** el sistema guarda ambos pagos asociados a la misma venta

#### Scenario: Suma incorrecta

- **WHEN** la suma de los pagos difiere del total del pedido
- **THEN** el sistema responde 409 indicando la diferencia y no registra la venta

#### Scenario: Monto inválido

- **WHEN** un pago tiene monto cero o negativo
- **THEN** el sistema responde 422 por validación de entrada y no registra la venta

#### Scenario: Venta sin pagos

- **WHEN** se intenta registrar una venta sin ningún pago
- **THEN** el sistema responde 422 por validación de entrada

### Requirement: Comprobante de venta único

Cada venta DEBE tener un número de comprobante único y legible, generado al confirmarse y consultable por el usuario.

#### Scenario: Comprobante generado

- **WHEN** se confirma una venta
- **THEN** el sistema asigna un comprobante con formato `V-AAAAMM-######` y lo devuelve en la respuesta

#### Scenario: Comprobantes distintos

- **WHEN** se confirman dos ventas
- **THEN** cada una recibe un comprobante distinto y el sistema no admite un comprobante duplicado

### Requirement: Consulta de ventas con filtros

El sistema DEBE permitir listar ventas por rango de fechas, estado, método de pago y cliente, con paginación y orden por fecha descendente.

#### Scenario: Listado por rango de fechas

- **WHEN** se consultan las ventas entre dos fechas
- **THEN** el sistema devuelve solo las ventas del rango, con comprobante, fecha, cliente, total, estado y métodos de pago utilizados

#### Scenario: Filtrado combinado

- **WHEN** se filtra por estado `ANULADA` y por cliente
- **THEN** el sistema devuelve solo las ventas que cumplen ambos criterios

#### Scenario: Filtro por método de pago

- **WHEN** se filtra por método `EFECTIVO`
- **THEN** el sistema devuelve solo las ventas con al menos un pago en ese método

### Requirement: Resumen de arqueo por método de pago

El sistema DEBE devolver, para un rango de fechas, la cantidad de ventas, el total facturado y el total cobrado por cada método de pago, excluyendo las ventas anuladas.

#### Scenario: Arqueo de caja diario

- **WHEN** se solicita el resumen de un día con ventas en efectivo, tarjeta y crédito
- **THEN** el sistema informa el total por método, la cantidad de ventas y el total facturado del día

#### Scenario: Ventas anuladas excluidas

- **WHEN** el rango incluye una venta `ANULADA`
- **THEN** esa venta no suma en la cantidad ni en los totales del resumen

#### Scenario: Rango sin ventas

- **WHEN** se solicita el resumen de un rango sin ventas
- **THEN** el sistema devuelve cantidad cero y totales en cero, sin error

### Requirement: Detalle de venta y consulta por comprobante

El sistema DEBE permitir consultar una venta por identificador o por número de comprobante, incluyendo pedido asociado, cliente, pagos, estado y datos de la anulación.

#### Scenario: Detalle por identificador

- **WHEN** se consulta una venta existente por su identificador
- **THEN** el sistema devuelve la venta con sus pagos y el pedido asociado

#### Scenario: Consulta por comprobante

- **WHEN** se consulta una venta por su número de comprobante
- **THEN** el sistema devuelve el mismo detalle que por identificador

#### Scenario: Venta inexistente

- **WHEN** se consulta un identificador o un comprobante que no existe
- **THEN** el sistema responde 404

### Requirement: Anulación lógica de la venta

El sistema DEBE anular una venta sin eliminarla físicamente, registrando motivo, usuario y momento de la anulación. Una venta anulada DEBE conservar su comprobante y sus pagos para consulta.

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

### Requirement: La venta no altera stock ni cuenta corriente

El registro y la anulación de una venta NO DEBEN modificar el stock de café tostado ni el saldo de cuenta corriente del cliente. El estado del pedido y la deuda asociada siguen siendo responsabilidad del módulo de pedidos.

#### Scenario: El stock no cambia al vender

- **WHEN** se registra una venta
- **THEN** los kilos disponibles de los lotes de café tostado quedan iguales a como estaban antes del registro

#### Scenario: El saldo no cambia al vender ni al anular

- **WHEN** se registra y luego se anula una venta de un cliente Mayorista
- **THEN** `saldo_cuenta_corriente` conserva el valor que le había asignado el módulo de pedidos

#### Scenario: La anulación no repone stock

- **WHEN** se anula una venta
- **THEN** los kilos disponibles de los lotes de café tostado no cambian

### Requirement: Atomicidad del registro y la anulación

El registro y la anulación de una venta DEBEN ejecutarse en una única transacción. Si falla cualquier paso, el sistema DEBE revertir los cambios de venta, pagos e historial, sin dejar registros parciales.

#### Scenario: Fallo al guardar los pagos

- **WHEN** falla la escritura de un pago durante el registro
- **THEN** no queda la venta, ni sus pagos, ni el comprobante consumido

#### Scenario: Fallo al anular

- **WHEN** falla la escritura del historial durante la anulación
- **THEN** la venta sigue `CONFIRMADA` y conserva sus pagos

### Requirement: Autorización de las operaciones de venta

El sistema DEBE restringir el registro de ventas a Administrador y Cajero, la anulación a Administrador y la consulta a Administrador, Cajero y Operario. Un usuario con rol Cliente NO DEBE acceder a estos endpoints.

#### Scenario: Cajero registra una venta

- **WHEN** un usuario con rol Cajero registra una venta
- **THEN** el sistema la acepta

#### Scenario: Cajero intenta anular

- **WHEN** un usuario con rol Cajero intenta anular una venta
- **THEN** el sistema responde 403

#### Scenario: Operario solo consulta

- **WHEN** un usuario con rol Operario consulta el listado y el resumen de ventas
- **THEN** el sistema responde 200 y, si intenta registrar una venta, responde 403

#### Scenario: Cliente consulta ventas

- **WHEN** un usuario con rol Cliente consulta el listado de ventas
- **THEN** el sistema responde 403

#### Scenario: Solicitud sin token

- **WHEN** se llama a cualquier endpoint de ventas sin token válido
- **THEN** el sistema responde 401
