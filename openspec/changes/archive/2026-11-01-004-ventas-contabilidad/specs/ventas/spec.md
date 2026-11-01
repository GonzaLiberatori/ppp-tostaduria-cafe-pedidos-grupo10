# Spec Delta: Ventas

## ADDED Requirements

### Requirement: Resumen mensual de ventas

El sistema DEBE devolver, para un rango de fechas opcional, un resumen agregado por mes calendario de las ventas, con la cantidad de ventas, el total facturado y el total cobrado por cada método de pago. Las ventas en estado `ANULADA` NO DEBEN sumar en ningún total ni cantidad.

#### Scenario: Agrupación por mes calendario

- **WHEN** se solicita el resumen mensual y existen ventas confirmadas en dos meses distintos
- **THEN** el sistema devuelve una fila por mes, identificada como `AAAA-MM`, con la cantidad de ventas y el total facturado de ese mes

#### Scenario: Ventas anuladas excluidas

- **WHEN** un mes contiene una venta `ANULADA` junto a ventas `CONFIRMADA`
- **THEN** la venta anulada no suma en la cantidad, ni en el total facturado, ni en los totales por método de pago

#### Scenario: Totales por método de pago del mes

- **WHEN** un mes tiene ventas cobradas con efectivo y con transferencia
- **THEN** el resumen de ese mes informa el monto cobrado con cada método, sumando únicamente los pagos de las ventas confirmadas

#### Scenario: Mes sin ventas vigentes

- **WHEN** un mes solo tiene ventas anuladas o no tiene ventas
- **THEN** ese mes no aparece en la respuesta

#### Scenario: Rango sin ventas

- **WHEN** se solicita el resumen de un rango sin ventas
- **THEN** el sistema devuelve una lista vacía, sin error

#### Scenario: Rango de fechas opcional

- **WHEN** se solicita el resumen sin fechas
- **THEN** el sistema agrega todas las ventas vigentes registradas

#### Scenario: Consulta autorizada

- **WHEN** un usuario con rol Administrador, Cajero u Operario solicita el resumen mensual
- **THEN** el sistema responde 200 con la serie agregada

#### Scenario: Cliente sin acceso

- **WHEN** un usuario con rol Cliente solicita el resumen mensual
- **THEN** el sistema responde 403

#### Scenario: Solicitud sin token

- **WHEN** se solicita el resumen mensual sin token válido
- **THEN** el sistema responde 401
