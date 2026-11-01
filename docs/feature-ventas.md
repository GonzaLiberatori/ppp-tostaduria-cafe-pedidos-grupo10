# Feature Ventas: documentación técnica y funcional

> **Estado:** módulo implementado en el árbol de trabajo, con migraciones
> `003_ventas` y `004_ventas_cobranza`, y cubierto por pruebas de schemas, CRUD,
> servicios y router.
>
> **Alcance de los cambios:** `003` agregó el módulo `ventas` sin tocar el resto.
> `004` sumó contabilidad y cobranza. `005` integra los métodos de pago al panel
> de pedidos: la venta nace al confirmar la entrega, la condición de pago
> (`CONTADO` / `PAGARE`) se elige en ese momento, la deuda B2B la administra
> `ventas` y la cobranza se consulta dentro de Contabilidad.

| Dato | Valor |
|---|---|
| Módulo backend | `backend/app/modules/ventas/` |
| Cambios OpenSpec | `openspec/changes/003ventas/`, `004-ventas-contabilidad/`, `005-ventas-integracion-metodos-de-pagos/` |
| Specs delta | `specs/ventas/spec.md` de cada cambio |
| Migraciones | `003_ventas.py` y `004_ventas_cobranza.py` |
| Pruebas | `backend/tests/modules/ventas/` |
| Prefijo HTTP | `/api/v1/ventas` |
| Etiqueta Swagger | `Ventas` |

## Índice

1. [Resumen funcional](#1-resumen-funcional)
2. [Alcance](#2-alcance)
3. [Arquitectura](#3-arquitectura)
4. [Modelo de datos](#4-modelo-de-datos)
5. [Reglas de negocio](#5-reglas-de-negocio)
6. [Autorización](#6-autorización)
7. [API HTTP](#7-api-http)
8. [Límites sobre deuda y stock](#8-límites-sobre-deuda-y-stock)
9. [Pruebas](#9-pruebas)
10. [Puesta en marcha](#10-puesta-en-marcha)
11. [Limitaciones y próximos pasos](#11-limitaciones-y-próximos-pasos)
12. [Referencias](#12-referencias)

---

## 1. Resumen funcional

La venta **nace al confirmar la entrega** del pedido. Desde 005 no hay un paso
manual separado de "registrar el cobro": al pasar el pedido de `LISTO` a
`ENTREGADO` el panel pide la condición de pago y `pedidos` delega en `ventas` la
creación de la venta dentro de la misma transacción.

1. **Entrega (módulo `pedidos`)**: el pedido avanza a `ENTREGADO`. `pedidos`
   descuenta el stock al crear el pedido y ahora delega la venta en `ventas`.
2. **Venta (módulo `ventas`)**: según la condición elegida,
   - **Contado**: nace `CONFIRMADA` con la fecha de cobro y el método real.
   - **Pagaré**: nace `PENDIENTE_COBRO`, con vencimiento a 30/60/90 días y un pago
     `CREDITO` que representa la deuda; solo para clientes B2B con cuenta
     corriente. La deuda se suma al saldo del cliente.
3. **Cobro**: cuando el cliente paga el pagaré, se marca cobrada indicando el
   método real. La venta pasa a `CONFIRMADA`, se registra `cobrada_en` y la deuda
   se descuenta.

La venta se puede **anular de forma lógica**: pasa a `ANULADA`, conserva su
comprobante y sus pagos, revierte la deuda si estaba pendiente y la respuesta
devuelve el `pedido_id` para gestionar la reversión de la entrega desde pedidos.

**Facturado no es cobrado.** Los totales de ventas ("Ventas Totales", el resumen
mensual y el Dashboard) miden lo **facturado**: toda venta no anulada, incluidas
las `PENDIENTE_COBRO`. La **cobranza** se consulta aparte y solo cuenta el dinero
que entró (`cobrada_en`).

---

## 2. Alcance

### 2.1 Incluido

- Venta creada automáticamente al confirmar la entrega, con condición de pago
  `CONTADO` o `PAGARE`.
- Alta manual `POST /ventas/` para pedidos `ENTREGADO` heredados, con el mismo
  contrato de condición.
- Ventas `PENDIENTE_COBRO` con vencimiento a 30, 60 o 90 días.
- Cobro de un pagaré con el método real: pasa a `CONFIRMADA` y descuenta la deuda.
- Consulta de **cobranza mensual** y de **saldo por cobrar** (con vencidas).
- Pagos únicos o mixtos (varios métodos sobre la misma venta al contado).
- Comprobante único con formato `V-AAAAMM-######`.
- Venta vigente única por pedido (`CONFIRMADA` o `PENDIENTE_COBRO`), respaldada
  por un índice único parcial.
- Anulación lógica con motivo, usuario y marca de tiempo; revierte la deuda si la
  venta estaba pendiente.
- Listado con filtros por fecha, estado, método de pago, cliente y texto.
- Arqueo de caja por método de pago.
- Detalle por identificador y por comprobante.
- Auditoría propia en `venta_comercial_historial`.

### 2.2 Fuera de alcance

- Mover stock o reponerlo al anular (sigue siendo de `pedidos`/`inventario`).
- Cobros parciales o múltiples cobros por venta: el pagaré se cobra entero.
- Integración real con pasarelas de pago: solo se guarda el método y el monto.
- Facturación electrónica y numeración fiscal.
- Devoluciones o notas de crédito.
- Notificaciones al cliente.

---

## 3. Arquitectura

Vertical slice con las capas habituales del proyecto. Cada capa tiene una única
responsabilidad. `ventas` lee pedidos y escribe en la cuenta corriente del cliente
a través de `clientes.services.ajustar_saldo_cuenta_corriente`, nunca importando
sus routers.

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Modelos | `models.py` | Tablas `venta_comercial`, `pago_venta`, `venta_comercial_historial` y enum `VentaEstado`. |
| Schemas | `schemas.py` | Contratos Pydantic de entrada y salida. |
| Acceso a datos | `crud.py` | Consultas y `add`/`flush`. **Nunca** hace `commit`. |
| Servicios | `services.py` | Reglas de negocio y frontera transaccional (`commit`/`rollback`). |
| Router | `router.py` | HTTP, dependencias y guardas de rol. Sin acceso directo a la sesión. |
| Tareas | — | Este módulo no programa jobs. |

Decisiones relevantes:

- **Tablas propias en lugar de reutilizar las heredadas.** Las tablas `venta` y
  `pago` de `pedidos/models.py` quedaron sin uso y con otra forma. Crear tablas
  nuevas evita colisiones en el registro de SQLAlchemy y deja intacto el mapeo
  heredado, que no se elimina en este cambio.
- **Enums compartidos, no duplicados.** `Facturacion`, `MetodoPago` y `Moneda` se
  importan (solo lectura) desde `app.modules.pedidos.models`, de modo que la API
  expone exactamente los mismos valores. `VentaEstado` es propio del módulo.
- **Sin `relationship` hacia `Pedido`.** La venta referencia el pedido por clave
  foránea y lo lee con `db.get`, sin declarar relación ORM. Así el mapeo de
  ventas no se acopla al de pedidos y no altera su comportamiento.
- **`__init__.py` vacío.** No reexporta el router para no sumar otro eslabón al
  import circular que ya existe entre los paquetes de módulos.

---

## 4. Modelo de datos

### 4.1 `venta_comercial`

| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | Autoincremental. |
| `pedido_id` | Integer FK `pedido.id` | Índice `ix_venta_comercial_pedido_id`. |
| `fecha` | DateTime | Fecha comercial de la venta. |
| `facturacion` | Enum `facturacion` | `FACTURA_A`, `CONSUMIDOR_FINAL`, `TICKET`, `NO_REQUIERE`. |
| `estado` | Enum `ventaestado` | `CONFIRMADA`, `PENDIENTE_COBRO` o `ANULADA`. |
| `total` | Numeric(10,2) | Copia del `pedido.total` al confirmar. |
| `numero_comprobante` | String(20) | Único, índice único. Se completa tras el `flush`. |
| `cuenta_id` | Integer FK `cuenta.id` | Usuario que registró la venta. |
| `creada_en` | DateTime | Marca de creación. |
| `anulada_en` | DateTime | Se completa al anular. |
| `fecha_vencimiento` | DateTime | Solo en pagarés: `fecha` más el plazo pactado. |
| `cobrada_en` | DateTime | Momento en que entró el dinero. `NULL` mientras esté pendiente. |

Índice único parcial:

```sql
CREATE UNIQUE INDEX ux_venta_comercial_pedido_vigente
    ON venta_comercial (pedido_id)
    WHERE estado IN ('CONFIRMADA', 'PENDIENTE_COBRO');
```

El `WHERE` es lo que permite volver a vender un pedido cuya venta anterior fue
anulada: la unicidad solo aplica a la venta vigente, y un pagaré pendiente cuenta
como vigente.

### 4.2 `pago_venta`

| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | Autoincremental. |
| `venta_id` | Integer FK `venta_comercial.id` | Índice `ix_pago_venta_venta_id`. |
| `metodo_de_pago` | Enum `metodopago` | `EFECTIVO`, `CREDITO`, `DEBITO`, `TRANSFERENCIA`, `MERCADO_PAGO`, `CHEQUE`, `OTRO`. |
| `monto` | Numeric(12,2) | Mayor que cero. |
| `moneda` | Enum `moneda` | `ARS` por defecto. |
| `aclaracion` | String(255) | Opcional. |
| `creado_en` | DateTime | Marca de creación. |

### 4.3 `venta_comercial_historial`

| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | Autoincremental. |
| `venta_id` | Integer FK `venta_comercial.id` | Índice `ix_venta_comercial_historial_venta_id`. |
| `estado_anterior` | Enum `ventaestado` | `NULL` en el alta. |
| `estado_nuevo` | Enum `ventaestado` | `PENDIENTE_COBRO`, `CONFIRMADA` o `ANULADA`. |
| `motivo` | String(255) | Texto libre; obligatorio al anular. |
| `cuenta_id` | Integer FK `cuenta.id` | Usuario que ejecutó el cambio. |
| `timestamp` | DateTime | Momento del cambio. |

Los enums se persisten **por nombre** (`FACTURA_A`, `CREDITO`, `CONFIRMADA`), que
es el criterio que ya usan las tablas existentes. En el JSON, en cambio, viaja el
**valor** del miembro, que no siempre coincide con el nombre:

| Enum | Nombre en la base | Valor aceptado y devuelto por la API |
|---|---|---|
| `Facturacion` | `FACTURA_A` | `Factura A` |
| `Facturacion` | `CONSUMIDOR_FINAL` | `Consumidor Final` |
| `Facturacion` | `TICKET` | `Ticket` |
| `Facturacion` | `NO_REQUIERE` | `No requiere` |
| `MetodoPago` | `EFECTIVO` | `EFECTIVO` (igual al nombre) |
| `Moneda` | `ARS` | `ARS` (igual al nombre) |
| `VentaEstado` | `CONFIRMADA` | `CONFIRMADA` (igual al nombre) |
| `VentaEstado` | `PENDIENTE_COBRO` | `PENDIENTE_COBRO` (igual al nombre) |
| `VentaEstado` | `ANULADA` | `ANULADA` (igual al nombre) |

Es la misma convención que ya usa el módulo de pedidos, porque los enums se
importan desde ahí.

---

## 5. Reglas de negocio

### 5.1 Venta al confirmar la entrega

`PedidoService.cambiar_estado_pedido` es el único punto que crea la venta y mueve
la deuda. Al pasar a `ENTREGADO`:

1. Exige la condición de pago: sin ella la entrega no se confirma (`422` en el
   `PATCH` del panel).
2. Llama a `ventas.services.registrar_venta_de_entrega`, que **no** hace `commit`:
   participa de la transacción de pedidos y el commit lo cierra el servicio de
   pedidos.
3. **Contado**: la venta nace `CONFIRMADA`, con `cobrada_en = ahora`, el método
   informado y sin deuda.
4. **Pagaré**: valida que el cliente sea B2B con cuenta corriente (`409` si no),
   la venta nace `PENDIENTE_COBRO` con `fecha_vencimiento = fecha + plazo` y un
   pago `CREDITO` por el total, y suma la deuda al cliente.
5. Si la venta falla, el `rollback` deja el pedido en `LISTO`, sin venta y sin
   deuda. Un pedido nuevo no puede crearse ya entregado: la entrega se confirma
   desde el panel para poder registrar la condición.

`POST /ventas/` sigue existiendo para los pedidos `ENTREGADO` heredados (ventas
creadas antes de 005). Reusa el mismo contrato y, si no se envía
`condicion_pago`, asume `CONTADO` con el método del primer pago.

### 5.2 Cobro de un pagaré (`VentaService.cobrar_venta`)

1. La venta debe existir (`404`) y estar `PENDIENTE_COBRO` (`409` si ya está
   `CONFIRMADA` o `ANULADA`).
2. Pasa a `CONFIRMADA` y registra `cobrada_en`.
3. El pago `CREDITO` que representaba la deuda se **actualiza** al método real y
   la aclaración recibida. No se agrega un pago: la invariante "la suma de los
   pagos es igual al total" se mantiene y el arqueo por método queda correcto.
4. Descuenta la deuda del cliente y registra historial
   (`PENDIENTE_COBRO → CONFIRMADA`), todo en una transacción.

No se admite cobro parcial ni múltiples cobros por venta.

### 5.3 Anulación (`VentaService.anular_venta`)

1. La venta debe existir (`404`) y no estar ya anulada (`409`).
2. Se marca `estado = ANULADA`, `anulada_en` y se agrega la entrada de historial
   con el motivo y la cuenta que la ejecutó.
3. Si estaba `PENDIENTE_COBRO`, se revierte la deuda en la misma transacción. Las
   ventas al contado no tocan el saldo.
4. Se conservan comprobante y pagos: la anulación es lógica, no borra nada.
5. La respuesta incluye `pedido_id` para que la reversión de la entrega se haga
   desde el módulo de pedidos.
6. Un único `commit` con `rollback` ante error.

### 5.4 Deuda y stock

| Evento | Deuda B2B |
|---|---|
| Venta a pagaré creada | `+total` |
| Venta a pagaré cobrada | `-total` |
| Venta a pagaré anulada | `-total` |
| Venta al contado (alta, cobro o anulación) | sin cambios |

La regla "solo un cliente B2B compra a pagaré" se valida en el alta. Las
reversiones funcionan aunque el cliente cambie de tipo después. Toda mutación del
saldo pasa por `clientes.services.ajustar_saldo_cuenta_corriente`.

El stock no cambia nunca desde `ventas`: se descuenta al crear el pedido.

### 5.5 Consultas: facturado vs cobrado

- **Listado**: filtros por `fecha_desde`, `fecha_hasta`, `estado`,
  `metodo_de_pago`, `cliente_persona_id` y texto libre `q`. Orden por fecha
  descendente y luego por id, con `skip`/`limit`. Los joins a `pedido` y `persona`
  son externos para no perder ventas cuyo pedido ya no exista.
- **Resumen de arqueo**: cantidad de ventas **facturadas** (`estado != ANULADA`,
  incluye `PENDIENTE_COBRO`) y total facturado; los totales por método solo suman
  pagos de ventas `CONFIRMADA`, es decir, dinero efectivamente cobrado.
- **Resumen mensual**: serie por mes de `venta_comercial.fecha` con cantidad y
  total facturado de todas las ventas no anuladas, más el cobrado por método de
  las confirmadas. Es la fuente del KPI "Ventas Totales" de Contabilidad y del
  Dashboard.
- **Cobranza mensual** (`GET /ventas/cobranza-mensual`): serie por mes de
  `cobrada_en`, no por la fecha de la venta. Un pagaré facturado en agosto y
  cobrado en septiembre suma en septiembre. Excluye pendientes y anuladas.
- **Por cobrar** (`GET /ventas/por-cobrar`): ventas `PENDIENTE_COBRO` ordenadas
  por vencimiento, con la marca `vencida` calculada con `datetime.now()`, el total
  por cobrar y la cantidad de vencidas.
- **Detalle**: por `id` o por `numero_comprobante`, con pagos, historial, estado
  del pedido y nombre del cliente.

### 5.6 Integración con la pantalla Contabilidad

- **KPIs y series mensuales**: `getContabilidadMensual()` cruza
  `GET /ventas/resumen-mensual` con `GET /gastos`. Los meses con gastos y sin
  ventas se muestran con ventas en cero y viceversa.
- **KPIs de cobranza**: "Cobranza del mes" sale de `GET /ventas/cobranza-mensual`
  y "Por cobrar" de `GET /ventas/por-cobrar`, con el contador de vencidas.
- **Tabla "Por cobrar"**: permite marcar cobrado con `POST /ventas/{id}/cobrar`
  (Administrador y Cajero).
- **Tabla "Ventas registradas"**: usa `GET /ventas/?limit=100`, permite filtrar
  por `PENDIENTE_COBRO` y anular (solo Administrador, también en pendientes).

Consecuencia de semántica: **"Ventas Totales" mide lo facturado, no lo cobrado**.
Un pagaré pendiente suma a Ventas Totales y todavía no a la cobranza. Anular una
venta la saca de ambos.

### 5.7 Frontend del panel

- **`frontend/src/pages/Pedidos.jsx`**: el destino `Entregado` (kanban, botones o
  detalle) abre el modal "Confirmar entrega". Pide condición `Contado`/`Pagaré`,
  método de pago real o plazo de 30/60/90, muestra el total y el vencimiento
  calculado, y deshabilita pagaré para clientes no B2B. La tabla y la tarjeta
  Kanban muestran la condición (`Contado`, `Pagaré · vence …`, `Pagaré cobrado`,
  `Venta anulada`) y el detalle incluye un bloque "Cobro".
- **`frontend/src/pages/Contabilidad.jsx`**: KPIs "Cobranza del mes" y "Por
  cobrar" (con vencidas), tabla "Por cobrar" ordenada por vencimiento con la
  acción "Marcar cobrado" (modal con método real y aclaración), y tabla "Ventas
  registradas" con filtro `PENDIENTE_COBRO`, badge ámbar, columna de vencimiento y
  anulación habilitada también para pendientes.
- **`frontend/src/context/DataContext.jsx`**: carga y refresca `cobranzaMensual`,
  `porCobrar` y `ventas`; `cobrarVenta` y `anularVenta` refrescan además los
  clientes para ver el saldo actualizado. Los errores de cobranza se aíslan en
  `errors.contabilidad`.
- **Permisos**: la pantalla Contabilidad sigue restringida a `admin`, pero la
  acción de cobrar se muestra también a `vendedor` (rol Cajero), que es el otro
  rol habilitado por el backend. Anular queda solo para `admin`.

Si la base no tiene aplicada la migración `004_ventas_cobranza`, los endpoints
nuevos devuelven error. El frontend lo aísla con `errors.contabilidad` y muestra
un aviso sin vaciar el resto del panel.

---

## 6. Autorización

El token JWT solo transporta el correo. La dependencia `get_cuenta_actual` lee la
`Cuenta` por `correo` y resuelve el rol en la base; `core/deps.py` no se modifica.

| Operación | Endpoints | Roles habilitados |
|---|---|---|
| Registrar venta manual | `POST /ventas/` | Administrador, Cajero |
| Cobrar pagaré | `POST /ventas/{id}/cobrar` | Administrador, Cajero |
| Anular venta | `POST /ventas/{id}/anular` | Administrador |
| Consultar | `GET /ventas/`, `/resumen`, `/resumen-mensual`, `/cobranza-mensual`, `/por-cobrar`, `/comprobante/{n}`, `/{id}` | Administrador, Cajero, Operario |

Sin token válido: `401`. Con un rol no habilitado: `403`. Un usuario Cliente no
accede a ningún endpoint del módulo.

---

## 7. API HTTP

Todas las rutas cuelgan de `/api/v1/ventas` y aparecen en `/docs` con la etiqueta
`Ventas`.

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| `POST` | `/ventas/` | Registra la venta de un pedido `ENTREGADO` heredado. | `201`, `401`, `403`, `404`, `409`, `422` |
| `GET` | `/ventas/` | Lista ventas con filtros y paginación. | `200`, `401`, `403`, `422` |
| `GET` | `/ventas/resumen` | Arqueo: facturado y cobrado por método. | `200`, `401`, `403` |
| `GET` | `/ventas/resumen-mensual` | Serie mensual de facturado y cobrado. | `200`, `401`, `403` |
| `GET` | `/ventas/cobranza-mensual` | Cobranza por mes de cobro y método. | `200`, `401`, `403` |
| `GET` | `/ventas/por-cobrar` | Pendientes con vencimiento y total por cobrar. | `200`, `401`, `403` |
| `GET` | `/ventas/comprobante/{numero_comprobante}` | Detalle por comprobante. | `200`, `401`, `403`, `404` |
| `GET` | `/ventas/{venta_id}` | Detalle por identificador. | `200`, `401`, `403`, `404` |
| `POST` | `/ventas/{venta_id}/cobrar` | Cobra un pagaré con el método real. | `200`, `401`, `403`, `404`, `409`, `422` |
| `POST` | `/ventas/{venta_id}/anular` | Anulación lógica con motivo. | `200`, `401`, `403`, `404`, `409`, `422` |

`/resumen`, `/resumen-mensual`, `/cobranza-mensual`, `/por-cobrar` y
`/comprobante/...` se declaran antes de `/{venta_id}` para que no se interpreten
como identificadores.

### 7.1 Venta al confirmar la entrega (desde el panel de pedidos)

La venta no se crea con `POST /ventas/`, sino en el `PATCH` del panel:

```http
PATCH /api/v1/pedidos/panel/12
Authorization: Bearer <token>
Content-Type: application/json

{
  "estado": "Entregado",
  "condicionPago": "PAGARE",
  "plazoDias": 30
}
```

Al contado se envía `"condicionPago": "CONTADO"` y `"metodoPago": "TRANSFERENCIA"`.
La respuesta es el pedido actualizado; la venta queda creada en la misma
transacción y se consulta con `GET /ventas/?cliente_persona_id=...`.

### 7.2 Registrar una venta heredada (manual)

```http
POST /api/v1/ventas/
Authorization: Bearer <token>
Content-Type: application/json

{
  "pedido_id": 12,
  "facturacion": "Ticket",
  "pagos": [
    { "metodo_de_pago": "EFECTIVO", "monto": "30000.00", "moneda": "ARS" },
    {
      "metodo_de_pago": "TRANSFERENCIA",
      "monto": "15000.00",
      "moneda": "ARS",
      "aclaracion": "Transferencia Banco Nación"
    }
  ]
}
```

Respuesta `201` (resumida):

```json
{
  "id": 7,
  "pedido_id": 12,
  "numero_comprobante": "V-202610-000007",
  "fecha": "2026-10-30T10:15:00",
  "facturacion": "Ticket",
  "estado": "CONFIRMADA",
  "total": "45000.00",
  "fecha_vencimiento": null,
  "cobrada_en": "2026-10-30T10:15:00",
  "pedido_estado": "ENTREGADO",
  "cliente_nombre": "B2B Test",
  "pagos": [
    { "metodo_de_pago": "EFECTIVO", "monto": "30000.00", "moneda": "ARS" },
    { "metodo_de_pago": "TRANSFERENCIA", "monto": "15000.00", "moneda": "ARS" }
  ]
}
```

### 7.3 Cobrar un pagaré

```http
POST /api/v1/ventas/7/cobrar
Authorization: Bearer <token>
Content-Type: application/json

{ "metodo_de_pago": "TRANSFERENCIA", "aclaracion": "Transferencia Banco Nación" }
```

La respuesta `200` devuelve la venta con `estado: "CONFIRMADA"`,
`cobrada_en` completo, el pago actualizado al método real y el historial con la
entrada `PENDIENTE_COBRO → CONFIRMADA`. La deuda del cliente queda descontada.

### 7.4 Anular una venta

```http
POST /api/v1/ventas/7/anular
Authorization: Bearer <token>
Content-Type: application/json

{ "motivo": "Cobro cargado dos veces" }
```

La respuesta `200` devuelve la venta con `estado: "ANULADA"`, `anulada_en`
completo, `pedido_id` y la entrada de historial con el motivo. Si la venta estaba
pendiente, la deuda se revierte. Con ese `pedido_id`, el equipo de pedidos revierte
la entrega si corresponde.

### 7.5 Listado, arqueo y cobranza

```http
GET /api/v1/ventas/?fecha_desde=2026-10-01T00:00:00&estado=PENDIENTE_COBRO&limit=50
GET /api/v1/ventas/resumen?fecha_desde=2026-10-30T00:00:00&fecha_hasta=2026-10-30T23:59:59
GET /api/v1/ventas/resumen-mensual?fecha_desde=2026-01-01T00:00:00
GET /api/v1/ventas/cobranza-mensual?fecha_desde=2026-01-01T00:00:00
GET /api/v1/ventas/por-cobrar
```

Respuesta `200` de `/cobranza-mensual`:

```json
[
  {
    "mes": "2026-10",
    "cantidad_cobros": 2,
    "total_cobrado": "75000.00",
    "totales_por_metodo": [
      { "metodo_de_pago": "TRANSFERENCIA", "monto": "45000.00" },
      { "metodo_de_pago": "EFECTIVO", "monto": "30000.00" }
    ]
  }
]
```

Respuesta `200` de `/por-cobrar`:

```json
{
  "items": [
    {
      "venta_id": 9,
      "pedido_id": 14,
      "numero_comprobante": "V-202609-000009",
      "cliente_persona_id": 3,
      "cliente_nombre": "B2B Test",
      "fecha": "2026-09-15T10:00:00",
      "fecha_vencimiento": "2026-10-15T10:00:00",
      "total": "35000.00",
      "vencida": true
    }
  ],
  "total_por_cobrar": "35000.00",
  "cantidad_vencidas": 1
}
```

Un rango sin movimientos devuelve `[]` en las series y un objeto con `items: []`
y `total_por_cobrar: "0"` en `/por-cobrar`.

---

## 8. Límites sobre deuda y stock

- **Stock**: `ventas` no toca `lote`. El descuento ocurre al crear el pedido, con
  criterio FIFO, y vive en `pedidos`/`inventario`. Registrar, cobrar o anular una
  venta no cambia `kg_disponibles`.
- **Cuenta corriente**: desde 005 la deuda B2B la administra `ventas`. La suma al
  registrar un pagaré, la descuenta al cobrarlo y la revierte al anularlo, siempre
  a través de `clientes.services.ajustar_saldo_cuenta_corriente` y dentro de la
  transacción de la operación. Las ventas al contado no la tocan.
- **Estado del pedido**: `ventas` no modifica `pedido.estado` ni escribe en
  `pedido_estado_historial` por sí mismo. La venta de la entrega participa de la
  transacción que abre `pedidos`.
- **Reversión de la entrega**: `ENTREGADO → LISTO` se bloquea con `409`
  (`PedidoConVentaVigente`) si hay venta `CONFIRMADA` o `PENDIENTE_COBRO`. Hay que
  anular la venta primero; después la reversión no toca el saldo.

Ambos límites están cubiertos por pruebas: se comparan los kilos por lote y el
saldo del cliente antes y después de registrar, cobrar y anular.

---

## 9. Pruebas

Ubicación: `backend/tests/modules/ventas/`. Los casos críticos de idempotencia y
transacción se prueban contra `services.py`, no contra el router.

| Archivo | Qué cubre |
|---|---|
| `test_schemas.py` | Montos, enums, motivo, listas vacías, condición de pago, plazos 30/60/90 y contrato de los resúmenes. |
| `test_crud.py` | Búsquedas, filtros, paginación, arqueo, resumen mensual con pendientes, cobranza por mes de cobro y pendientes ordenadas por vencimiento. |
| `test_services.py` | Alta por entrega (contado/pagaré), deuda y vencimiento, pagaré a B2C rechazado, cobro, cobro duplicado, anulación con reversión de deuda, cobranza mensual y saldo por cobrar, atomicidad e invariancia de stock. |
| `test_router.py` | Contratos HTTP y RBAC de todos los endpoints, incluidos `cobrar`, `cobranza-mensual` y `por-cobrar`. |

`conftest.py` del módulo define fixtures de dominio (`pedido_entregado_b2b`,
`pedido_entregado_consumidor`, `venta_confirmada`) y una `db_session` con
`StaticPool`, necesaria porque `TestClient` atiende los requests en otro hilo.

Ejecución:

```bash
cd backend
python -m pytest tests/modules/ventas -q     # solo el módulo
python -m pytest tests -q                    # suite completa
```

---

## 10. Puesta en marcha

1. Aplicar las migraciones:

   ```bash
   cd backend
   python -m alembic upgrade head
   ```

   `003_ventas` crea las tablas y `004_ventas_cobranza` agrega
   `PENDIENTE_COBRO`, `fecha_vencimiento`, `cobrada_en` y amplía el índice
   parcial a `('CONFIRMADA', 'PENDIENTE_COBRO')`.

2. Levantar la API y abrir `/docs`:

   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

3. Flujo mínimo de prueba manual:

   1. Crear un pedido B2B y avanzarlo a `LISTO`.
   2. Entregarlo con `PATCH /api/v1/pedidos/panel/{id}` indicando
      `condicionPago: "PAGARE"` y `plazoDias: 30`.
   3. Verificar la deuda en `GET /api/v1/clientes/...` y la venta en
      `GET /api/v1/ventas/por-cobrar`.
   4. Cobrarla con `POST /api/v1/ventas/{id}/cobrar` y confirmar que sale de
      `/por-cobrar`, suma en `/cobranza-mensual` y baja el saldo del cliente.

---

## 11. Limitaciones y próximos pasos

- **Sin pasarela de pago**: `metodo_de_pago` es informativo, no hay conciliación
  automática ni estados de pago pendientes más allá de `PENDIENTE_COBRO`.
- **Cobro entero**: no hay cobros parciales ni múltiples cobros por venta.
- **Reversión de entrega**: requiere anular la venta vigente primero; la reversión
  no repone stock (el stock se descuenta al crear el pedido).
- **Tablas heredadas**: `venta` y `pago` siguen mapeadas en `pedidos/models.py`
  sin uso. Su eliminación es un cambio aparte.
- **Moneda**: se guarda por pago, pero no hay conversión ni tipo de cambio.

---

## 12. Referencias

- Cambios OpenSpec: `openspec/changes/003ventas/`,
  `openspec/changes/004-ventas-contabilidad/`,
  `openspec/changes/005-ventas-integracion-metodos-de-pagos/`
- Módulo: `backend/app/modules/ventas/`
- Migraciones: `backend/alembic/versions/003_ventas.py` y
  `004_ventas_cobranza.py`
- Pruebas: `backend/tests/modules/ventas/`
- Módulo de pedidos (dueño del stock y de la transición de entrega):
  `docs/feature-pedidos.md`
- Documentación interactiva: `/docs` y `/redoc` con la app levantada.
