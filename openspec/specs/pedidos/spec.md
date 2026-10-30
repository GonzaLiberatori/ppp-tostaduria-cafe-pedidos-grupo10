# pedidos Specification

## Purpose
Gestiona el ciclo de vida completo de pedidos de cafe tostado: creacion, listado, detalle, actualizacion de estado y eliminacion, con consumo automatico de stock FIFO y actualizacion de cuenta corriente del cliente.

## Requirements

### Requirement: Crear pedido con validacion de stock y consumo FIFO
El sistema DEBE permitir crear un pedido especificando cliente, items (variedad de cafe tostado, kilos, precio/kg), medio de contacto y observaciones. Al crear, el sistema DEBE validar stock suficiente, consumir kilos usando FIFO (bolsas abiertas primero, luego cerradas por fecha de creacion), calcular total, y actualizar la cuenta corriente del cliente si es B2B, todo en una unica transaccion ACID.

#### Scenario: Creacion exitosa con stock suficiente
- **WHEN** usuario crea pedido con items que tienen stock disponible
- **THEN** sistema crea pedido con estado Pendiente, consume stock FIFO, calcula total, actualiza cuenta corriente si B2B, y retorna pedido creado con ID

#### Scenario: Rechazo por stock insuficiente
- **WHEN** usuario crea pedido solicitando mas kilos de los disponibles en stock
- **THEN** sistema rechaza la creacion con error 409 indicando stock disponible por variedad

#### Scenario: Consumo FIFO correcto (abiertas primero, luego cerradas por antiguedad)
- **WHEN** se crea pedido que consume kilos de una variedad con bolsas abiertas y cerradas
- **THEN** sistema consume primero de bolsas abiertas (mas antiguas primero), luego de cerradas (mas antiguas primero), y actualiza estado de bolsas (cerrada -> abierta si se consume parcialmente)

### Requirement: Listar pedidos con filtros y paginacion
El sistema DEBE permitir listar pedidos con filtros opcionales por estado (Pendiente/Listo/Entregado), cliente, rango de fechas, y busqueda por texto (nombre cliente, medio contacto, observaciones), con paginacion y ordenamiento por fecha descendente.

#### Scenario: Listado basico sin filtros
- **WHEN** usuario solicita listado de pedidos
- **THEN** sistema retorna lista paginada ordenada por fecha descendente con datos basicos (id, fecha, cliente, estado, items count, kilos totales, total, medio contacto)

#### Scenario: Filtrado por estado y cliente
- **WHEN** usuario filtra por estado=Listo y cliente_id=X
- **THEN** sistema retorna solo pedidos que coincidan con ambos criterios

### Requirement: Obtener detalle completo de pedido
El sistema DEBE retornar el detalle completo de un pedido incluyendo todos los items con variedad, kilos, precio/kg, subtotal, y datos del cliente.

#### Scenario: Detalle de pedido existente
- **WHEN** usuario solicita detalle de pedido valido
- **THEN** sistema retorna pedido con items expandidos y datos del cliente

#### Scenario: Pedido inexistente
- **WHEN** usuario solicita detalle de ID inexistente
- **THEN** sistema retorna error 404

### Requirement: Actualizar campos editables de pedido
El sistema DEBE permitir actualizar observaciones, medio de contacto y estado (ver requisito separado de transicion de estado) de un pedido existente. No DEBE permitir modificar items, cliente, fecha o total tras la creacion.

#### Scenario: Actualizacion de observaciones y medio contacto
- **WHEN** usuario actualiza observaciones y medio de contacto de pedido Pendiente
- **THEN** sistema persiste cambios y retorna pedido actualizado

#### Scenario: Intento de modificar items de pedido existente
- **WHEN** usuario intenta cambiar items de un pedido ya creado
- **THEN** sistema rechaza con error 400 (items inmutables post-creacion)

### Requirement: Eliminar pedido solo en estado Pendiente
El sistema DEBE permitir eliminar un pedido solo si su estado es Pendiente. Al eliminar, DEBE revertir el consumo de stock FIFO (restaurar kilos a bolsas originales) y revertir cuenta corriente si B2B, todo en una transaccion.

#### Scenario: Eliminacion exitosa de pedido Pendiente
- **WHEN** usuario elimina pedido en estado Pendiente
- **THEN** sistema elimina pedido, restaura stock FIFO, revierte cuenta corriente si B2B

#### Scenario: Rechazo al eliminar pedido no Pendiente
- **WHEN** usuario intenta eliminar pedido en estado Listo o Entregado
- **THEN** sistema rechaza con error 409 (solo Pendiente eliminable)

### Requirement: Idempotencia en creacion de pedidos
El sistema DEBE garantizar que reintentos de la misma peticion de creacion (mismo cliente, mismos items, misma fecha) no dupliquen pedidos ni consuman stock dos veces, usando clave de idempotencia (cliente_id + hash de items + fecha) o restriccion unica en BD.

#### Scenario: Reintento de peticion identica
- **WHEN** misma peticion de creacion se envia dos veces (red reintento)
- **THEN** sistema retorna el mismo pedido existente en el segundo intento, sin duplicar ni consumir stock extra
