# Feature Ventas: documentación técnica y funcional

> **Estado:** módulo implementado en el árbol de trabajo, con migración propia y
> cubierto por pruebas de schemas, CRUD, servicios y router.
>
> **Alcance del cambio:** se agrega el módulo `ventas` sin modificar la lógica ni
> el comportamiento de `pedidos`, `clientes`, `inventario`, `auth` ni `core`. Los
> únicos archivos compartidos que se tocaron son `pedidos/router.py` (dos líneas
> de imports), `main.py` (registro del router) y `alembic/env.py` (import de los
> modelos nuevos).

| Dato | Valor |
|---|---|
| Módulo backend | `backend/app/modules/ventas/` |
| Cambio OpenSpec | `openspec/changes/003ventas/` |
| Spec delta | `openspec/changes/003ventas/specs/ventas/spec.md` |
| Migración | `backend/alembic/versions/003_ventas.py` (`003_ventas`, revises `57cf7419baaf`) |
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

El módulo de ventas registra el **cobro** de un pedido que ya fue entregado. No
reemplaza al módulo de pedidos: lo complementa en un flujo de dos pasos.

1. **Entrega (módulo `pedidos`)**: el pedido avanza a `ENTREGADO`. En ese momento
   `pedidos` ya descontó el stock al crear el pedido y ya imputó la deuda del
   cliente mayorista a su cuenta corriente.
2. **Cobro (módulo `ventas`)**: el cajero registra la venta indicando el tipo de
   facturación y uno o varios pagos. La suma de los pagos debe coincidir con el
   total del pedido. La venta queda `CONFIRMADA` con un número de comprobante
   propio.

La venta se puede **anular de forma lógica**: pasa a `ANULADA`, conserva su
comprobante y sus pagos, y la respuesta devuelve el `pedido_id` para que la
reversión de la entrega (stock y saldo) se gestione manualmente desde el panel de
pedidos.

---

## 2. Alcance

### 2.1 Incluido

- Registro del cobro de un pedido `ENTREGADO`.
- Pagos únicos o mixtos (varios métodos sobre la misma venta).
- Comprobante único con formato `V-AAAAMM-######`.
- Venta vigente única por pedido, respaldada por un índice único parcial.
- Anulación lógica con motivo, usuario y marca de tiempo.
- Listado con filtros por fecha, estado, método de pago, cliente y texto.
- Arqueo de caja por método de pago.
- Detalle por identificador y por comprobante.
- Auditoría propia en `venta_comercial_historial`.

### 2.2 Fuera de alcance

- Mover stock o reponerlo al anular (sigue siendo de `pedidos`/`inventario`).
- Imputar o revertir deuda en la cuenta corriente (sigue siendo de `pedidos`).
- Integración real con pasarelas de pago: solo se guarda el método y el monto.
- Facturación electrónica y numeración fiscal.
- Devoluciones o notas de crédito.
- Notificaciones al cliente.
- Frontend del módulo (el cambio es solo backend).

---

## 3. Arquitectura

Vertical slice con las capas habituales del proyecto. Cada capa tiene una única
responsabilidad y la comunicación con otros módulos es siempre de lectura.

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
| `estado` | Enum `ventaestado` | `CONFIRMADA` o `ANULADA`. |
| `total` | Numeric(10,2) | Copia del `pedido.total` al confirmar. |
| `numero_comprobante` | String(20) | Único, índice único. Se completa tras el `flush`. |
| `cuenta_id` | Integer FK `cuenta.id` | Usuario que registró la venta. |
| `creada_en` | DateTime | Marca de creación. |
| `anulada_en` | DateTime | Se completa al anular. |

Índice único parcial:

```sql
CREATE UNIQUE INDEX ux_venta_comercial_pedido_vigente
    ON venta_comercial (pedido_id)
    WHERE estado = 'CONFIRMADA';
```

El `WHERE` es lo que permite volver a vender un pedido cuya venta anterior fue
anulada: la unicidad solo aplica a la venta vigente.

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
| `estado_nuevo` | Enum `ventaestado` | `CONFIRMADA` o `ANULADA`. |
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

Es la misma convención que ya usa el módulo de pedidos, porque los enums se
importan desde ahí.

---

## 5. Reglas de negocio

### 5.1 Registro (`VentaService.registrar_venta`)

1. El pedido debe existir (si no, `404`).
2. El pedido debe estar en estado `ENTREGADO` (si no, `409`). El estado del pedido
   no se modifica y no se agrega ninguna entrada a `pedido_estado_historial`.
3. El pedido no debe tener otra venta `CONFIRMADA` (si no, `409`).
4. La suma de los pagos debe ser exactamente igual a `pedido.total` (si no, `409`
   informando la diferencia). Cada monto debe ser mayor que cero (`422`).
5. Se crea la venta con `total = pedido.total`, se hace `flush` para obtener el
   `id`, se genera el comprobante `V-AAAAMM-######`, se guarda el historial de
   alta y luego los pagos.
6. Un único `commit`. Ante cualquier excepción, `rollback` completo: no queda
   venta, ni pagos, ni comprobante consumido. Una carrera entre dos registros
   simultáneos la corta el índice único parcial y se traduce a `409`; cualquier
   otra violación de integridad se informa como tal (por ejemplo, un comprobante
   ya asignado devuelve `409` con ese motivo), sin rotularse como venta duplicada.

### 5.2 Anulación (`VentaService.anular_venta`)

1. La venta debe existir (`404`) y no estar ya anulada (`409`).
2. Se marca `estado = ANULADA`, `anulada_en` y se agrega la entrada de historial
   con el motivo y la cuenta que la ejecutó.
3. Se conservan comprobante y pagos: la anulación es lógica, no borra nada.
4. La respuesta incluye `pedido_id` para que la reversión de la entrega se haga
   desde el módulo de pedidos, que es el dueño del stock y del saldo.
5. Un único `commit` con `rollback` ante error.

### 5.3 Consultas

- **Listado**: filtros por `fecha_desde`, `fecha_hasta`, `estado`,
  `metodo_de_pago`, `cliente_persona_id` y texto libre `q` (comprobante, nombre o
  apellido del cliente). Orden por fecha descendente y luego por id, con
  `skip`/`limit`. Los joins a `pedido` y `persona` son externos: una venta cuyo
  pedido o cliente ya no exista sigue apareciendo (con cliente `null`) en lugar
  de desaparecer del listado, igual que en el detalle.
- **Resumen de arqueo**: cantidad de ventas `CONFIRMADA`, total facturado y total
  por método de pago. Las ventas `ANULADA` no suman. Un rango sin ventas devuelve
  ceros, no error.
- **Detalle**: por `id` o por `numero_comprobante`, con pagos, historial, estado
  del pedido y nombre del cliente.

---

## 6. Autorización

El token JWT solo transporta el correo. La dependencia `get_cuenta_actual` lee la
`Cuenta` por `correo` y resuelve el rol en la base; `core/deps.py` no se modifica.

| Operación | Endpoints | Roles habilitados |
|---|---|---|
| Registrar venta | `POST /ventas/` | Administrador, Cajero |
| Anular venta | `POST /ventas/{id}/anular` | Administrador |
| Consultar | `GET /ventas/`, `/resumen`, `/comprobante/{n}`, `/{id}` | Administrador, Cajero, Operario |

Sin token válido: `401`. Con un rol no habilitado: `403`. Un usuario Cliente no
accede a ningún endpoint del módulo.

---

## 7. API HTTP

Todas las rutas cuelgan de `/api/v1/ventas` y aparecen en `/docs` con la etiqueta
`Ventas`.

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| `POST` | `/ventas/` | Registra el cobro de un pedido entregado. | `201`, `401`, `403`, `404`, `409`, `422` |
| `GET` | `/ventas/` | Lista ventas con filtros y paginación. | `200`, `401`, `403`, `422` |
| `GET` | `/ventas/resumen` | Arqueo por método de pago. | `200`, `401`, `403` |
| `GET` | `/ventas/comprobante/{numero_comprobante}` | Detalle por comprobante. | `200`, `401`, `403`, `404` |
| `GET` | `/ventas/{venta_id}` | Detalle por identificador. | `200`, `401`, `403`, `404` |
| `POST` | `/ventas/{venta_id}/anular` | Anulación lógica con motivo. | `200`, `401`, `403`, `404`, `409`, `422` |

`/resumen` y `/comprobante/...` se declaran antes de `/{venta_id}` para que no se
interpreten como identificadores.

### 7.1 Registrar una venta

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
  "pedido_estado": "ENTREGADO",
  "cliente_nombre": "B2B Test",
  "pagos": [
    { "metodo_de_pago": "EFECTIVO", "monto": "30000.00", "moneda": "ARS" },
    { "metodo_de_pago": "TRANSFERENCIA", "monto": "15000.00", "moneda": "ARS" }
  ],
  "historial": [
    {
      "estado_anterior": null,
      "estado_nuevo": "CONFIRMADA",
      "motivo": "Registro de la venta",
      "timestamp": "2026-10-30T10:15:00"
    }
  ]
}
```

### 7.2 Anular una venta

```http
POST /api/v1/ventas/7/anular
Authorization: Bearer <token>
Content-Type: application/json

{ "motivo": "Cobro cargado dos veces" }
```

La respuesta `200` devuelve la venta con `estado: "ANULADA"`, `anulada_en`
completo, `pedido_id` y la entrada de historial con el motivo. Con ese
`pedido_id`, el equipo de pedidos revierte la entrega si corresponde.

### 7.3 Listado y arqueo

```http
GET /api/v1/ventas/?fecha_desde=2026-10-01T00:00:00&estado=CONFIRMADA&metodo_de_pago=EFECTIVO&limit=50
GET /api/v1/ventas/resumen?fecha_desde=2026-10-30T00:00:00&fecha_hasta=2026-10-30T23:59:59
```

---

## 8. Límites sobre deuda y stock

Este es el punto que más importa al integrar con el trabajo de pedidos:

- **Stock**: `ventas` no toca `lote`. El descuento ocurre al crear el pedido, con
  criterio FIFO, y vive en `pedidos`/`inventario`. Registrar o anular una venta no
  cambia `kg_disponibles`.
- **Cuenta corriente**: `ventas` no toca `cliente.saldo_cuenta_corriente`. La
  deuda del cliente mayorista la imputa `pedidos` al pasar el pedido a
  `ENTREGADO` y la revierte si la entrega vuelve atrás.
- **Estado del pedido**: `ventas` no modifica `pedido.estado` ni escribe en
  `pedido_estado_historial`. Solo lee el estado para validar que sea `ENTREGADO`.
- **Reversión**: anular una venta devuelve `pedido_id` en la respuesta. La
  reversión real (reponer stock, descontar saldo, retroceder el estado) se hace
  desde el panel de pedidos, que es la única fuente de verdad de esas reglas.

Ambos límites están cubiertos por pruebas: se comparan los kilos por lote y el
saldo del cliente antes y después de registrar y de anular.

---

## 9. Pruebas

Ubicación: `backend/tests/modules/ventas/`. Los casos críticos de idempotencia y
transacción se prueban contra `services.py`, no contra el router.

| Archivo | Qué cubre | Casos |
|---|---|---|
| `test_schemas.py` | Validaciones de entrada: montos, enums, motivo, listas vacías. | 15 |
| `test_crud.py` | Búsquedas, filtros combinados, paginación, agregados del arqueo y venta con pedido inexistente. | 23 |
| `test_services.py` | Registro, duplicado, suma incorrecta, anulación, reventa, clasificación de errores de integridad, atomicidad con `monkeypatch`, invariancia de stock y saldo. | 33 |
| `test_router.py` | Contratos HTTP y RBAC: `201/200/401/403/404/409/422`. | 27 |

`conftest.py` del módulo define tres fixtures de dominio
(`pedido_entregado_b2b`, `pedido_entregado_consumidor`, `venta_confirmada`) y una
`db_session` con `StaticPool`, necesaria porque `TestClient` atiende los requests
en otro hilo. Es una fixture local: `backend/tests/conftest.py` no se modifica.

Ejecución:

```bash
cd backend
python -m pytest tests/modules/ventas -q     # solo el módulo
python -m pytest tests -q                    # suite completa
```

---

## 10. Puesta en marcha

1. Aplicar la migración:

   ```bash
   cd backend
   python -m alembic upgrade head
   ```

   La revisión `003_ventas` solo crea tablas nuevas; no altera `venta` ni `pago`.

2. Levantar la API y abrir `/docs`:

   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

   Las cinco rutas de `/api/v1/ventas` (seis operaciones) aparecen bajo la
   etiqueta `Ventas`.

3. Flujo mínimo de prueba manual:

   1. Crear un pedido y avanzarlo a `ENTREGADO` desde `/api/v1/pedidos`.
   2. Registrar la venta con `POST /api/v1/ventas/` y el total exacto.
   3. Consultar `GET /api/v1/ventas/resumen` para ver el arqueo.
   4. Anular con `POST /api/v1/ventas/{id}/anular` y revisar que el resumen ya no
      la cuente.

---

## 11. Limitaciones y próximos pasos

- **Sin frontend**: el cambio es solo backend; la pantalla de caja queda pendiente.
- **Sin pasarela de pago**: `metodo_de_pago` es informativo, no hay conciliación
  automática ni estados de pago pendientes.
- **Reversión manual**: anular una venta no revierte stock ni saldo por diseño. Si
  se necesita automatizar, el caso de uso debe vivir en `pedidos` y ser invocado
  desde su propio servicio.
- **Tablas heredadas**: `venta` y `pago` siguen mapeadas en `pedidos/models.py`
  sin uso. Su eliminación es un cambio aparte, fuera del alcance de este módulo.
- **Moneda**: se guarda por pago, pero no hay conversión ni tipo de cambio; el
  total del pedido se asume en la moneda de la venta.

---

## 12. Referencias

- Cambio OpenSpec: `openspec/changes/003ventas/`
- Spec delta: `openspec/changes/003ventas/specs/ventas/spec.md`
- Módulo: `backend/app/modules/ventas/`
- Migración: `backend/alembic/versions/003_ventas.py`
- Pruebas: `backend/tests/modules/ventas/`
- Módulo de pedidos (dueño de stock y cuenta corriente): `docs/feature-pedidos.md`
- Documentación interactiva: `/docs` y `/redoc` con la app levantada.
