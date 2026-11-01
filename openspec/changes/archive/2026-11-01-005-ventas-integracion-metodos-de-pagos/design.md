# Design: Integración de métodos de pago y cobranza

## Contexto

004 dejó la venta como un registro manual posterior a la entrega: `POST /ventas/` exige pedido `ENTREGADO`, pagos que suman el total y nace siempre `CONFIRMADA`. La deuda B2B la maneja `pedidos` en `LISTO → ENTREGADO`, sin mirar el medio de pago, así que una entrega cobrada en efectivo genera deuda igual.

005 invierte el disparador: la venta nace en la entrega, con la condición de pago elegida en ese momento, y `ventas` pasa a administrar la deuda de las ventas a pagaré. `Contabilidad` distingue facturado de cobrado.

Decisiones ya tomadas con el usuario:

1. "Ventas Totales" mide **facturado**; la cobranza es un KPI aparte.
2. La venta **nace al entregar**.
3. El estado de la venta a pagaré es **`PENDIENTE_COBRO`**.
4. La condición de pago se elige **al marcar entregado**.
5. El vencimiento usa **plazos fijos** de 30, 60 o 90 días.
6. **`ventas` maneja la deuda** B2B.
7. Cobranza y "por cobrar" viven **dentro de Contabilidad**.

## Modelo de datos

### `venta_comercial`

| Columna | Cambio | Detalle |
|---|---|---|
| `estado` | valor nuevo | `VentaEstado.PENDIENTE_COBRO` además de `CONFIRMADA` y `ANULADA` |
| `fecha_vencimiento` | nueva, `DateTime` NULL | solo en ventas a pagaré; `fecha` + plazo |
| `cobrada_en` | nueva, `DateTime` NULL | momento del cobro; NULL mientras esté pendiente |

Estados y significado:

- `PENDIENTE_COBRO`: facturada y con deuda viva. Cuenta como facturado, no como cobrado.
- `CONFIRMADA`: cobrada. En las ventas al contado `cobrada_en = fecha`.
- `ANULADA`: sin efecto contable ni sobre la deuda.

### Índice de venta vigente

`ux_venta_comercial_pedido_vigente` pasa de `WHERE estado = 'CONFIRMADA'` a `WHERE estado IN ('CONFIRMADA', 'PENDIENTE_COBRO')`. Sin esto, un pedido con venta a pagaré podría recibir una segunda venta al contado y duplicar deuda y facturación.

### Migración `004_ventas_cobranza`

`down_revision = "003_ventas"`:

1. `op.add_column("venta_comercial", sa.Column("fecha_vencimiento", sa.DateTime(), nullable=True))`
2. `op.add_column("venta_comercial", sa.Column("cobrada_en", sa.DateTime(), nullable=True))`
3. `op.drop_index("ux_venta_comercial_pedido_vigente", ...)` y recreación con el nuevo `sqlite_where`.
4. `downgrade` simétrico: restaura el índice anterior, borra las columnas y deja las filas `PENDIENTE_COBRO` en `CONFIRMADA` antes de borrar `cobrada_en` (si no, quedarían ventas sin fecha de cobro).

No hace falta recrear el enum: en `003_ventas` los enums se crearon con `sa.Enum(...)` sin `create_constraint`, así que SQLite guarda un `VARCHAR` con el nombre del miembro y no hay `CHECK` que ampliar. No se toca el enum `MetodoPago`.

## Condición de pago sin migrar `pedidos`

La condición no se persiste como columna propia: se deduce de la venta.

| Condición | Estado inicial | `fecha_vencimiento` | Pago | Deuda B2B |
|---|---|---|---|---|
| Contado | `CONFIRMADA` | NULL | método real elegido | no |
| Pagaré | `PENDIENTE_COBRO` | `fecha + plazo` | `CREDITO` | sí |

El contrato de entrada del panel (`PATCH /pedidos/panel/{id}`) agrega tres campos opcionales, en camelCase como el resto del panel:

- `condicionPago`: `CONTADO` | `PAGARE`.
- `metodoPago`: `MetodoPago`, requerido cuando la condición es `CONTADO`.
- `plazoDias`: `30` | `60` | `90`, requerido cuando la condición es `PAGARE`.

`CondicionPago` y la validación del plazo viven en `ventas/schemas.py`; `pedidos` solo los reenvía. Así `pedidos` no gana columnas, ni migración, ni un enum nuevo.

El alta manual `POST /ventas/` reusa el mismo contrato y, por compatibilidad con 004, si no se envía `condicionPago` se asume `CONTADO` con el método del primer pago.

## Transacción de la entrega

La operación "confirmar entrega" es un caso de uso de `pedidos`; por eso el commit es único y queda en `PedidoService.cambiar_estado_pedido`. `ventas` expone una función que participa de esa transacción y no commitea:

```text
PedidoService.cambiar_estado_pedido(pedido_id, "ENTREGADO", condicion)
  ├─ valida transición y condición de pago
  ├─ ventas.services.registrar_venta_de_entrega(db, pedido, condicion, cuenta_id)
  │    ├─ valida B2B para pagaré y plazo en {30,60,90}
  │    ├─ crea VentaComercial + PagoVenta + historial
  │    └─ si es pagaré: clientes.services.ajustar_saldo_cuenta_corriente(db, cliente, +total)
  ├─ estado = ENTREGADO + historial de estado
  └─ db.commit()   (o rollback completo si algo falla)
```

`registrar_venta_de_entrega` no commitea: es la contraparte de `ajustar_saldo_cuenta_corriente` en `clientes`. `POST /ventas/` sigue usando `registrar_venta`, que sí commitea porque ahí la operación es la venta misma. La distinción se documenta en el docstring del módulo, igual que ya hace `ventas/services.py` con su frontera transaccional.

### Un solo funnel de estados

Hoy `pedidos/services.py` duplica los efectos laterales en `cambiar_estado_pedido` (panel) y en `actualizar_pedido` (endpoint legado). 005 elimina el bloque de cuenta corriente de ambos y hace que `actualizar_pedido` delegue la transición en `cambiar_estado_pedido`. Consecuencia: un único lugar crea ventas, ajusta deuda y valida la reversión.

### Reversión `ENTREGADO → LISTO`

Si el pedido tiene venta vigente (`CONFIRMADA` o `PENDIENTE_COBRO`) se responde 409 (`PedidoConVentaVigente`) con el mensaje que indica anular la venta primero. Es un cambio de comportamiento **BREAKING**: antes la reversión restaba la deuda y dejaba la venta huérfana.

Sin venta vigente la reversión no toca la cuenta corriente: la deuda ya no vive en `pedidos`.

## Deuda B2B en `ventas`

`clientes/services.py` gana una función pública sin commit:

```python
def ajustar_saldo_cuenta_corriente(db: Session, cliente_id: int, delta: Decimal) -> Decimal
```

Reglas:

| Evento | Deuda |
|---|---|
| Venta a pagaré creada | `+total` |
| Venta a pagaré cobrada | `-total` |
| Venta a pagaré anulada | `-total` |
| Venta al contado (alta, cobro o anulación) | sin cambios |
| Reversión de entrega sin venta vigente | sin cambios |

Se mantiene la regla de que solo los clientes `es_b2b` tienen cuenta corriente: un pagaré a un cliente B2C se rechaza con 409.

## Cobro de una venta pendiente

`POST /ventas/{id}/cobrar` (Administrador y Cajero), cuerpo `{metodo_de_pago, aclaracion?}`:

1. La venta debe existir (404) y estar `PENDIENTE_COBRO` (409 si `CONFIRMADA` o `ANULADA`).
2. `estado = CONFIRMADA`, `cobrada_en = now`.
3. El pago `CREDITO` que representaba el pagaré se actualiza al método real y a la aclaración recibida. Se actualiza, no se agrega: la invariante "la suma de los pagos es igual al total" se mantiene y el arqueo por método queda correcto.
4. Se descuenta la deuda y se registra historial (`PENDIENTE_COBRO → CONFIRMADA`).
5. Todo en una transacción con `commit` en el servicio.

No se admite cobro parcial ni múltiples cobros por venta: eso requiere la tabla de cobros (ver "Fuera de alcance").

## Agregaciones y endpoints

| Endpoint | Roles | Contenido |
|---|---|---|
| `GET /ventas/resumen-mensual` | admin, cajero, operario | facturado por mes de venta (`estado != ANULADA`) + cobrado por método (solo `CONFIRMADA`) |
| `GET /ventas/cobranza-mensual` | admin, cajero, operario | cobranza por mes de `cobrada_en` + totales por método |
| `GET /ventas/por-cobrar` | admin, cajero, operario | pendientes con vencimiento, marca de vencida y total por cobrar |
| `POST /ventas/{id}/cobrar` | admin, cajero | cobro de una venta pendiente |

Consultas nuevas en `ventas/crud.py`, todas con `func.strftime('%Y-%m', ...)` como en 004:

- `cobranza_por_mes`: agrupa por `strftime('%Y-%m', cobrada_en)` con `cobrada_en IS NOT NULL AND estado != ANULADA`.
- `totales_de_cobranza_por_metodo`: une `pago_venta` con las ventas cobradas y agrupa por mes de cobro y método.
- `pendientes_de_cobro`: `estado == PENDIENTE_COBRO`, orden por `fecha_vencimiento` ascendente; la marca de vencida se calcula en el servicio con `datetime.now()` para que el contrato no dependa de la zona horaria de SQLite.

`resumen_por_mes` cambia el filtro a `estado != ANULADA`; `totales_por_mes_y_metodo` conserva `estado == CONFIRMADA`. Eso deja el resumen mensual de 004 con la semántica que ya declara su spec ("solo las ventas anuladas no suman" para facturación; "únicamente los pagos de las ventas confirmadas" para cobrado) sin necesidad de modificar esa capacidad.

## Frontend

### Pedidos

`changeEstado` (kanban y botones) intercepta el destino `Entregado` y abre un modal "Confirmar entrega": condición (contado / pagaré), método de pago o plazo de 30/60/90, y un resumen del total y del vencimiento calculado. Al confirmar envía `{ estado: 'Entregado', condicionPago, metodoPago | plazoDias }` en el mismo `PATCH`. Si el cliente no es B2B, la opción pagaré se muestra deshabilitada con la explicación.

### Contabilidad

- KPIs nuevos: "Cobranza del mes" (de `cobranza-mensual`) y "Por cobrar" (de `por-cobrar`, con contador de vencidas).
- Tabla "Por cobrar" con comprobante, cliente, total, vencimiento, días restantes o atraso y acción "Marcar cobrado" (admin y cajero) que abre un modal con el método real.
- La tabla "Ventas registradas" suma el filtro `PENDIENTE_COBRO`, un badge ámbar y una columna de vencimiento; "Anular" sigue siendo solo para admin y ahora aplica también a las pendientes.
- `DataContext` expone `cobranzaMensual`, `porCobrar`, `refrescarVentas` (que ya refresca ambos) y `cobrarVenta`; `api.js` gana `getCobranzaMensualVentas`, `getPorCobrarVentas` y `cobrarVenta`.
- Los tres endpoints nuevos comparten el aislamiento de errores de 004: si fallan, se muestra el aviso de Contabilidad y el resto del panel sigue funcionando.

El Dashboard no cambia de código: su tarjeta "Ventas del Mes" sigue leyendo el resumen mensual y ahora incluye las ventas pendientes de cobro, que es la semántica de facturado buscada.

## Tests

- `tests/modules/ventas/test_services.py`: alta por entrega al contado y a pagaré (deuda, vencimiento), pagaré a B2C rechazado, plazo inválido, cobro exitoso (método actualizado, deuda descontada, historial), cobro duplicado, cobro de anulada, anulación de pendiente que revierte deuda, invariante de pagos.
- `tests/modules/ventas/test_crud.py`: resumen mensual con pendientes incluidas en facturado, cobrado solo de confirmadas, cobranza por mes de cobro cruzando meses, pendientes excluidas de la cobranza, rango sin movimientos.
- `tests/modules/ventas/test_router.py`: roles de `cobrar`, `por-cobrar` y `cobranza-mensual` (403 para operario en cobro, 403 para cliente, 401 sin token), 409 de cobro repetido.
- `tests/modules/pedidos/test_services.py`: entrega crea la venta en la misma transacción, fallo de la venta deja el pedido en `LISTO` y sin deuda, contado no genera deuda, pagaré B2B sí, reversión bloqueada con venta vigente y permitida después de anularla.

Los casos de transacción e idempotencia se escriben contra `services.py`, no contra los routers.

## Fuera de alcance

- Pagos parciales, señas o cobro antes de entregar.
- Tabla de cobros con varios pagos por venta (modelo B del análisis).
- Cheques diferidos y fechas de vencimiento manuales.
- Bloqueo de nuevas ventas por `limite_credito`.
- Backfill de ventas para pedidos ya entregados sin venta: siguen usando `POST /ventas/`.
- Recordatorios o notificaciones de vencimiento.
