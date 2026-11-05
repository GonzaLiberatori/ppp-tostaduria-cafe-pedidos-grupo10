# Diagramas de actividad y secuencia — Módulo Ventas

> **Documento fuente para que una IA genere los `.drawio`.**
> No es un documento de casos de uso: cada flujo trae la **especificación mecánica**
> de su diagrama de **secuencia** (lifelines, mensajes, fragmentos) y de su
> diagrama de **actividad** (particiones, decisiones, guardas).
> Módulo: `backend/app/modules/ventas/` · Prefijo: `/api/v1/ventas`

---

# PARTE I — Convenciones de dibujo

## 1. Diagrama de actividad

| Elemento | Forma en draw.io | Uso en este documento |
|---|---|---|
| Nodo inicial | `Inicio` — círculo negro relleno | Una sola vez, en la calle del actor. |
| Acción | `Acción` — rectángulo redondeado | Cada fila de tipo `ACCIÓN`. |
| Decisión | Rombo | Filas de tipo `DECISIÓN`; las salidas llevan **guarda entre corchetes**. |
| Merge | Rombo | Solo cuando dos ramas se vuelven a unir. |
| Fork / Join | `Barra` negra gruesa | Solo para la validación de los pagos en paralelo nominal (ver D-03). |
| Nodo final | `Fin` — círculo con anillo | Uno por cada estado terminal (incluidos los de error). |
| Partición | `Calle` (swimlane) horizontal | Una por participante de la sección 3. |
| Nota | `Nota` | Para `commit`, `rollback` y referencias a otro diagrama. |

**Reglas:**
- Las acciones se numeran `A1, A2, …` para poder referenciarlas.
- Toda arista que sale de un rombo **debe** tener guarda. Si el flujo puede fallar, la guarda de error es obligatoria.
- El `commit` y el `rollback` se dibujan como acciones propias dentro de la calle del servicio que los ejecuta, nunca implícitos.
- Los diagramas de actividad de este documento son **de un solo flujo**: no mezclar alta y cobro en el mismo dibujo.

## 2. Diagrama de secuencia

| Elemento | Forma en draw.io | Uso |
|---|---|---|
| Línea de vida | `Lifeline` con etiqueta `NombreClase` | Una por participante de la sección 3, en ese orden de izquierda a derecha. |
| Mensaje sincrónico | Flecha **sólida**, punta rellena | Todo mensaje de la columna `Mensaje`. |
| Retorno | Flecha **discontinua**, punta abierta | Toda fila de la columna `Retorno`. |
| Activación | Barra vertical | Desde el primer mensaje recibido hasta su retorno. |
| Fragmento combinado | Rectángulo con pestaña pentagonal | `alt`, `opt`, `loop` según las tablas de fragmentos. |
| Creación de objeto | Flecha con `<<create>>` | Solo `VentaComercial`, `PagoVenta`, `VentaComercialHistorial`. |

**Reglas:**
- Numerar los mensajes `1, 2, 3, …` en el orden de la tabla. Los mensajes internos de un servicio invocado se numeran `5.1, 5.2, …`.
- Los nombres de los mensajes son las **firmas reales del código**. No traducirlos ni inventar métodos.
- Toda llamada a `commit()` y `rollback()` de SQLAlchemy se dibuja como mensaje explícito hacia la línea de vida `Session`.
- Los errores de dominio **no** son mensajes: son retornos con un `alt` que termina en `HTTP 4xx`.

## 3. Participantes oficiales (nombres exactos)

| # | Etiqueta de lifeline / calle | Tipo | Origen en el código |
|---|---|---|---|
| P1 | `Panel React` | Actor/UI | `frontend/src/pages/` + `context/DataContext.jsx` |
| P2 | `Router Ventas` | Control | `ventas/router.py` |
| P3 | `VentaService` | Control | `ventas/services.py` |
| P4 | `crud` | DAO | `ventas/crud.py` |
| P5 | `Session` | Infra | SQLAlchemy `Session` |
| P6 | `SQLite` | Datos | Base de datos |
| P7 | `clientes.services` | Servicio externo | `ajustar_saldo_cuenta_corriente`, `obtener_cliente` |
| P8 | `Router Pedidos` | Control | `pedidos/router.py` |
| P9 | `PedidoService` | Control | `pedidos/services.py::cambiar_estado_pedido` |

> D-01 y D-02 son los únicos que incluyen `P8` y `P9`. En el resto, `P9` aparece solo como nota.

---

# PARTE II — Inventario de diagramas a generar

| ID | Flujo | Secuencia | Actividad | Criticidad |
|---|---|:---:|:---:|---|
| **D-01** | Confirmar entrega → venta al contado | ✔ | ✔ | Alta — cruza 3 módulos |
| **D-02** | Confirmar entrega → venta a pagaré B2B | ✔ | ✔ | Alta — mueve deuda |
| **D-03** | Alta manual `POST /ventas/` (pagos mixtos) | ✔ | ✔ | Alta — validaciones |
| **D-04** | Cobrar pagaré | ✔ | ✔ | Alta — descuenta deuda |
| **D-05** | Anular venta | ✔ | ✔ | Alta — revierte deuda |
| **D-06** | Listar ventas con filtros | ✔ | ✔ | Media |
| **D-07** | Consultas de contabilidad y cobranza | ✔ | ✔ | Media |
| **D-08** | Revertir entrega `ENTREGADO → LISTO` | ✔ | ✔ | Alta — cruza `pedidos` ↔ `ventas` |

Orden recomendado de generación: **D-04 → D-05 → D-03 → D-01 → D-02 → D-08 → D-06 → D-07**
(los tres primeros son los más simples y sirven de plantilla de estilo; D-08 va después de D-05 porque lo necesita como precondición).

---

# PARTE III — Especificaciones

---

## D-01 · Confirmar entrega y generar venta al contado

**Disparador:** `PATCH /api/v1/pedidos/panel/{id}` con `estado: "Entregado"`, `condicionPago: "CONTADO"`, `metodoPago`.
**Transacción:** abierta por `PedidoService`; el `commit` es de `pedidos`.
**Resultado:** pedido `ENTREGADO` + venta `CONFIRMADA` + sin deuda.

### D-01.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Pedidos` → `PedidoService` → `VentaService` · `registrar_venta_de_entrega` → `crud` → `Session` → `SQLite` → `clientes.services`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Pedidos | `PATCH /pedidos/panel/{id}` `{estado, condicionPago, metodoPago}` | sync |
| 2 | Router Pedidos → Router Pedidos | `get_current_user(token)` → `Cuenta` | interno |
| 3 | Router Pedidos → PedidoService | `cambiar_estado_pedido(pedido_id, "ENTREGADO", usuario_id, condicion_pago, metodo_de_pago, cuenta_id)` | sync |
| 4 | PedidoService → crud | **`pedidos`** `crud.get_pedido(db, pedido_id)` | sync |
| 5 | PedidoService → PedidoService | `_validar_transicion_estado("LISTO", "ENTREGADO")` | interno |
| 6 | PedidoService → VentaService | `registrar_venta_de_entrega(db, pedido, CONTADO, metodo_de_pago, plazo_dias, cuenta_id)` | sync |
| 6.1 | VentaService → crud | `obtener_vigente_por_pedido(db, pedido.id)` → `None` | sync |
| 6.2 | VentaService → clientes.services | `obtener_cliente(db, pedido.cliente_persona_id)` → `tipo` | sync |
| 6.3 | VentaService → VentaService | `_facturacion_por_defecto(...)` → `Factura A` si B2B, si no `Consumidor Final` | interno |
| 6.4 | VentaService → VentaService | `_persistir_venta(estado=CONFIRMADA, cobrada_en=ahora, pagos=[(metodo, total, ARS, None)])` | interno |
| 6.4.1 | `_persistir_venta` → crud | `crear_venta(db, VentaComercial)` | sync |
| 6.4.2 | crud → Session | `db.add(venta)` + `db.flush()` | sync |
| 6.4.3 | Session → SQLite | `INSERT venta_comercial` → `id` | sync |
| 6.4.4 | `_persistir_venta` → `_generar_comprobante` | `f"V-{fecha:%Y%m}-{id:06d}"` | interno |
| 6.4.5 | `_persistir_venta` → crud | `actualizar_venta(db, venta)` → `flush` → `UPDATE numero_comprobante` | sync |
| 6.4.6 | `_persistir_venta` → crud | `crear_historial(db, Historial(None → CONFIRMADA, motivo, cuenta_id))` → `INSERT` | sync |
| 6.4.7 | `_persistir_venta` → crud | **`loop`** `[por cada pago]` `crear_pago(db, PagoVenta)` → `INSERT pago_venta` | loop |
| 7 | PedidoService → PedidoService | `db_pedido.estado = "ENTREGADO"` | interno |
| 8 | PedidoService → PedidoService | `_registrar_historial_estado(...)` → `INSERT pedido_estado_historial` | sync |
| 9 | PedidoService → Session | `db.commit()` | sync |
| 10 | PedidoService → Session | `db.refresh(db_pedido)` | sync |
| 11 | PedidoService → Router Pedidos | `Pedido` actualizado | **retorno** |
| 12 | Router Pedidos → Panel React | `200 OK` + pedido | **retorno** |

**Fragmentos:**

| Fragmento | Condición (guarda) | Contenido |
|---|---|---|
| `opt` | `[condicion_pago == null]` | `raise CondicionDePagoRequerida` → `422`. Ocurre entre **3** y **6**. |
| `alt` | `[IntegrityError en flush]` | `_traducir_integrity_error` → `VentaDuplicada` (`409`) o `ComprobanteDuplicado` (`409`). Se lanza desde **6.4.2**. |
| `alt` | `[cualquier excepción]` | `PedidoService` ejecuta `self.db.rollback()` y relanza. El pedido **queda en `LISTO`**, sin venta y sin deuda. |

> **Nota de dibujo:** el `rollback` está en `PedidoService`, **no** en `VentaService`.
> `registrar_venta_de_entrega` nunca hace `commit` ni `rollback`.

### D-01.b — Diagrama de actividad

Particiones: `Panel React` · `Router Pedidos` · `PedidoService` · `VentaService` · `crud / Session`

| Nodo | Partición | Tipo | Etiqueta | Guardas salientes |
|---|---|---|---|---|
| A1 | Panel React | INICIO | — | — |
| A2 | Panel React | ACCIÓN | Abrir modal "Confirmar entrega" | — |
| A3 | Panel React | ACCIÓN | Elegir condición, método, ver total | — |
| A4 | Router Pedidos | DECISIÓN | ¿`condicion_pago` informada? | `[no]` → A5 · `[sí]` → A6 |
| A5 | Router Pedidos | FIN | `422 CondicionDePagoRequerida` | — |
| A6 | PedidoService | ACCIÓN | `validar transición LISTO → ENTREGADO` | — |
| A7 | PedidoService | DECISIÓN | ¿Transición válida? | `[no]` → A8 · `[sí]` → A9 |
| A8 | PedidoService | FIN | `422 TransicionInvalida` | — |
| A9 | VentaService | DECISIÓN | ¿Ya hay venta vigente? | `[sí]` → A10 · `[no]` → A11 |
| A10 | VentaService | FIN | `409 VentaDuplicada` → `rollback` | — |
| A11 | VentaService | ACCIÓN | Calcular facturación según tipo de cliente | — |
| A12 | VentaService | ACCIÓN | Crear venta + `flush` (obtener `id`) | — |
| A13 | VentaService | ACCIÓN | Generar comprobante `V-AAAAMM-######` | — |
| A14 | VentaService | ACCIÓN | Registrar historial `NULL → CONFIRMADA` | — |
| A15 | VentaService | ACCIÓN | Registrar pago con método real (bucle) | — |
| A16 | PedidoService | ACCIÓN | `pedido.estado = ENTREGADO` + historial de estado | — |
| A17 | PedidoService | ACCIÓN | `commit()` | — |
| A18 | PedidoService | FIN | `200 OK` con pedido entregado | — |

**Salida de error común:** cualquier excepción de A9…A16 salta a un nodo `rollback()` en la partición `PedidoService` y de ahí a un `FIN` de error. Dibujar **una sola** arista de excepción que agrupe esas acciones, rotulada `[excepción]`.

---

## D-02 · Confirmar entrega y generar venta a pagaré (B2B)

**Disparador:** mismo `PATCH`, con `condicionPago: "PAGARE"`, `plazoDias ∈ {30, 60, 90}`.
**Diferencia con D-01:** la venta nace `PENDIENTE_COBRO` y **suma deuda** a la cuenta corriente.

### D-02.a — Diagrama de secuencia

Lifelines: idénticas a D-01 + `clientes.services` activo (ya no es solo lectura).

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1–6 | — | Idénticos a D-01 | — |
| 6.1 | VentaService → crud | `obtener_vigente_por_pedido` → `None` | sync |
| 6.2 | VentaService → VentaService | `_validar_plazo(plazo_dias)` → `30 \| 60 \| 90` | interno |
| 6.3 | VentaService → VentaService | `fecha_vencimiento = datetime.now() + timedelta(days=plazo)` | interno |
| 6.4 | VentaService → VentaService | `estado = PENDIENTE_COBRO`, `cobrada_en = None` | interno |
| 6.5 | VentaService → VentaService | `_sumar_deuda_de_pagare(db, pedido, total)` | interno |
| 6.5.1 | `_sumar_deuda_de_pagare` → clientes.services | `obtener_cliente(db, pedido.cliente_persona_id)` → `cliente` | sync |
| 6.5.2 | `_sumar_deuda_de_pagare` | `alt [cliente.tipo != "B2B"]` → `raise PagareNoPermitido` | alt |
| 6.5.3 | `_sumar_deuda_de_pagare` → clientes.services | `ajustar_saldo_cuenta_corriente(db, cliente_id, +total)` → `UPDATE cuenta corriente` | sync |
| 6.6 | VentaService → VentaService | `_persistir_venta(pagos=[(CREDITO, total, ARS, None)], estado=PENDIENTE_COBRO)` | interno |
| 6.6.1–6.6.7 | — | Idénticos a D-01 (**referenciar el fragmento, no repetirlo**) | — |
| 7–12 | — | Idénticos a D-01 | — |

**Fragmentos:**

| Fragmento | Guarda | Efecto |
|---|---|---|
| `alt` | `[plazo_dias not in (30, 60, 90)]` | `422 PlazoInvalido`. Se valida **dos veces**: Pydantic (`VentaCreate`, solo en D-03) y `_validar_plazo` en el servicio. |
| `alt` | `[cliente.tipo != "B2B"]` | `409 PagareNoPermitido` → `rollback` → pedido queda `LISTO`. |
| `alt` | `[excepción]` | `rollback` completo: **ni venta ni deuda**. La deuda y la venta viven en la misma transacción, por eso no puede quedar una sin la otra. |

### D-02.b — Diagrama de actividad

Idéntico a D-01.b con estos reemplazos:

- **A11** → `Validar cliente B2B y plazo`
- **A12** → `DECISIÓN ¿cliente es B2B?` con `[no]` → `409 PagareNoPermitido` + `rollback` · `[sí]` → `A13`
- **A13** → `Ajustar saldo del cliente (+total)`
- **A14** → `Crear venta PENDIENTE_COBRO con fecha_vencimiento`
- **A15** → `Registrar pago CREDITO por el total`
- **A18** → `200 OK` con pedido entregado y deuda registrada

> La rama de deuda (`clientes.services`) debe aparecer **dentro** de la calle `VentaService` como llamada a un participante externo, o en una calle propia si el diagrama se hace de nivel arquitectónico. No dibujarla después del `commit`.

---

## D-03 · Alta manual de venta (`POST /ventas/`)

**Disparador:** `POST /api/v1/ventas/` · Roles: Administrador, Cajero.
**Uso:** solo pedidos `ENTREGADO` heredados. Admite **pagos mixtos**.
**Transacción:** propia de `VentaService` (este flujo **sí** hace `commit`).

### D-03.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Ventas` → `VentaService` → `crud` → `Session` → `SQLite` → `clientes.services`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 0 | Panel React → Router Ventas | `POST /ventas/` body `VentaCreate` | sync |
| 0.1 | Router Ventas → Router Ventas | Pydantic `VentaCreate.validar_condicion_de_pago()` | interno |
| 1 | Router Ventas → Router Ventas | `get_cuenta_actual(token)` → `Cuenta` (lee rol en la base) | interno |
| 2 | Router Ventas → Router Ventas | `_exigir_rol(cuenta, (ADMINISTRADOR, CAJERO))` | interno |
| 3 | Router Ventas → VentaService | `registrar_venta(datos, cuenta_id)` | sync |
| 4 | VentaService → crud | `obtener_pedido(db, datos.pedido_id)` | sync |
| 5 | VentaService | `alt [pedido is None]` → `404 PedidoNoEncontrado` | alt |
| 6 | VentaService | `alt [pedido.estado != "ENTREGADO"]` → `409 PedidoNoVendible` | alt |
| 7 | VentaService → crud | `obtener_vigente_por_pedido(db, pedido.id)` | sync |
| 8 | VentaService | `alt [vigente is not None]` → `409 VentaDuplicada` | alt |
| 9 | VentaService → VentaService | `total = Decimal(pedido.total)`; `pagado = Σ pagos.monto` | interno |
| 10 | VentaService | `alt [pagado != total]` → `409 PagosNoCuadran(total, pagado)` | alt |
| 11 | VentaService | `alt [condicion_pago == PAGARE]` → **rama pagaré** | alt/else |
| 11.1 | VentaService | `_validar_plazo(plazo_dias)` → `422 PlazoInvalido` si no ∈ {30,60,90} | interno |
| 11.2 | VentaService → clientes.services | `ajustar_saldo_cuenta_corriente(db, cliente_id, +total)` | sync |
| 11.3 | VentaService | `estado = PENDIENTE_COBRO`, `fecha_vencimiento = ahora + plazo` | interno |
| 11.4 | VentaService | `else` → `estado = CONFIRMADA`, `cobrada_en = ahora`, `fecha_vencimiento = None` | interno |
| 12 | VentaService → VentaService | `_persistir_venta(...)` — **ver D-01 pasos 6.4.1 a 6.4.7** | interno |
| 13 | VentaService → Session | `db.commit()` | sync |
| 14 | VentaService → VentaService | `obtener_venta(venta.id)` → `_a_detalle` | interno |
| 14.1 | `_a_detalle` → crud | `obtener_pedido(db, venta.pedido_id)` + `obtener_persona(db, pedido.cliente_persona_id)` | sync |
| 15 | VentaService → Router Ventas | `VentaDetailRead` | **retorno** |
| 16 | Router Ventas → Panel React | `201 Created` | **retorno** |

**Fragmentos obligatorios:**

| Fragmento | Guarda | Resultado |
|---|---|---|
| `alt` | `[body inválido]` | `422` automático de FastAPI, **antes** de llegar al router (paso 0.1). |
| `alt` | `[rol no habilitado]` | `403` en el paso 2. |
| `alt` | `[PAGARE y plazo fuera de {30,60,90}]` | `422 PlazoInvalido` (paso 11.1). |
| `alt` | `[excepción]` | `self.db.rollback()` en `VentaService`, luego relanza. **Único flujo donde el rollback es de `ventas`**. |

### D-03.b — Diagrama de actividad

Particiones: `Panel React` · `Router Ventas` · `VentaService` · `crud / Session`

Cadena lineal de decisiones — **no** usar fork/join, las validaciones son secuenciales:

```
A1 INICIO (Panel React)
A2 enviar POST /ventas/  →  A3 [Pydantic] ¿VentaCreate válido? --[no]--> FIN 422
A4 [Router] ¿rol ∈ {Admin, Cajero}? --[no]--> FIN 403
A5 [VentaService] ¿pedido existe? --[no]--> FIN 404
A6 ¿pedido.estado == ENTREGADO? --[no]--> FIN 409 PedidoNoVendible
A7 ¿venta vigente? --[sí]--> FIN 409 VentaDuplicada
A8 Σ pagos == pedido.total? --[no]--> FIN 409 PagosNoCuadran
A9 ¿condicion_pago == PAGARE? --[sí]--> A10 ¿plazo ∈ {30,60,90}? --[no]--> FIN 422
                                        A11 ¿cliente B2B? --[no]--> FIN 409
                                        A12 saldo +total
                                        A13 venta PENDIENTE_COBRO
                             --[no]--> A14 venta CONFIRMADA (cobrada_en = ahora)
A15 crear venta + comprobante + historial
A16 [loop] registrar cada pago
A17 commit()
A18 cargar detalle (_a_detalle)
A19 FIN 201
```

**Nota para el dibujante:** si el diagrama debe mostrar atomicidad, agregar después de `A15/A16` un rombo `¿falló alguna escritura?` con `[sí]` → `rollback()` → `FIN 500`. Es la única forma de que el diagrama de actividad exprese el `try/except` del código.

---

## D-04 · Cobrar un pagaré

**Disparador:** `POST /api/v1/ventas/{id}/cobrar` · Roles: Administrador, Cajero.
**Resultado:** `PENDIENTE_COBRO → CONFIRMADA`, deuda descontada.

### D-04.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Ventas` → `VentaService` → `crud` → `Session` → `SQLite` → `clientes.services`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Ventas | `POST /ventas/{id}/cobrar` `{metodo_de_pago, aclaracion}` | sync |
| 2 | Router Ventas | `get_cuenta_actual` + `_exigir_rol(ADMINISTRADOR, CAJERO)` | interno |
| 3 | Router Ventas → VentaService | `cobrar_venta(venta_id, datos, cuenta_id)` | sync |
| 4 | VentaService → crud | `obtener_por_id(db, venta_id)` | sync |
| 5 | VentaService | `alt [venta is None]` → `404 VentaNoEncontrada` | alt |
| 6 | VentaService | `alt [venta.estado != PENDIENTE_COBRO]` → `409 VentaNoPendienteDeCobro` | alt |
| 7 | VentaService → crud | `obtener_pedido(db, venta.pedido_id)` | sync |
| 8 | VentaService | `alt [pedido is None]` → `404 PedidoNoEncontrado` | alt |
| 9 | VentaService → VentaService | `venta.estado = CONFIRMADA`; `venta.cobrada_en = datetime.now()` | interno |
| 10 | VentaService → crud | `actualizar_venta(db, venta)` → `flush` → `UPDATE venta_comercial` | sync |
| 11 | VentaService → VentaService | **`loop`** `[por cada pago en venta.pagos]` → `pago.metodo_de_pago = datos.metodo_de_pago`; `pago.aclaracion = datos.aclaracion` | loop |
| 12 | VentaService → crud | `crear_historial(db, Historial(PENDIENTE_COBRO → CONFIRMADA, "Cobro de la venta a pagaré", cuenta_id))` | sync |
| 13 | VentaService → clientes.services | `ajustar_saldo_cuenta_corriente(db, pedido.cliente_persona_id, -total)` | sync |
| 14 | VentaService → Session | `db.commit()` | sync |
| 15 | VentaService → VentaService | `obtener_venta(venta_id)` → `_a_detalle` | interno |
| 16 | VentaService → Router Ventas | `VentaDetailRead` | **retorno** |
| 17 | Router Ventas → Panel React | `200 OK` | **retorno** |

**Puntos que el diagrama debe hacer visibles:**

| Punto | Cómo se dibuja |
|---|---|
| **No se agrega un pago nuevo** | El paso 11 es un `loop` que **modifica** los pagos existentes (`actualizar`), no un `create`. Si el diagrama muestra un `INSERT pago_venta`, está mal. |
| **Invariante** | Nota al margen: `Σ pagos == venta.total` se mantiene siempre. |
| **Atomicidad** | `alt [excepción]` con `rollback()` antes del paso 14. Deuda y estado cambian juntos o no cambian. |
| **Cobro entero** | No hay fragmento `opt` de monto parcial. El monto nunca viaja en el body. |

### D-04.b — Diagrama de actividad

```
A1 INICIO (Panel React)
A2 "Marcar cobrado" → modal método real + aclaración
A3 ¿rol ∈ {Admin, Cajero}? --[no]--> FIN 403
A4 ¿venta existe? --[no]--> FIN 404
A5 ¿estado == PENDIENTE_COBRO? --[no]--> FIN 409
A6 marcar CONFIRMADA + cobrada_en = ahora
A7 [loop] actualizar método y aclaración de cada pago
A8 registrar historial PENDIENTE_COBRO → CONFIRMADA
A9 ajustar saldo del cliente (-total)
A10 ¿alguna escritura falló? --[sí]--> rollback() --> FIN 500
                          --[no]--> A11 commit()
A12 FIN 200 (venta cobrada)
```

---

## D-05 · Anular una venta

**Disparador:** `POST /api/v1/ventas/{id}/anular` · Rol: **solo Administrador**.
**Resultado:** venta `ANULADA`, historial con motivo, deuda revertida si estaba pendiente.

### D-05.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Ventas` → `VentaService` → `crud` → `Session` → `SQLite` → `clientes.services` *(solo si aplica)*

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Ventas | `POST /ventas/{id}/anular` `{motivo}` | sync |
| 2 | Router Ventas | `_exigir_rol(ADMINISTRADOR)` | interno |
| 3 | Router Ventas → VentaService | `anular_venta(venta_id, datos, cuenta_id)` | sync |
| 4 | VentaService → crud | `obtener_por_id(db, venta_id)` | sync |
| 5 | VentaService | `alt [venta is None]` → `404 VentaNoEncontrada` | alt |
| 6 | VentaService | `alt [venta.estado == ANULADA]` → `409 VentaYaAnulada` | alt |
| 7 | VentaService → crud | `obtener_pedido(db, venta.pedido_id)` | sync |
| 8 | VentaService | `alt [pedido is None]` → `404 PedidoNoEncontrado` | alt |
| 9 | VentaService → VentaService | `estado_anterior = venta.estado` | interno |
| 10 | VentaService → VentaService | `venta.estado = ANULADA`; `venta.anulada_en = ahora` | interno |
| 11 | VentaService → crud | `actualizar_venta(db, venta)` → `flush` | sync |
| 12 | VentaService → crud | `crear_historial(db, Historial(estado_anterior → ANULADA, datos.motivo, cuenta_id))` | sync |
| 13 | VentaService | **`opt`** `[estado_anterior == PENDIENTE_COBRO]` | opt |
| 13.1 | VentaService → clientes.services | `ajustar_saldo_cuenta_corriente(db, cliente_id, -total)` | sync |
| 14 | VentaService → Session | `db.commit()` | sync |
| 15 | VentaService → VentaService | `obtener_venta(venta_id)` → `_a_detalle` | interno |
| 16 | VentaService → Router Ventas | `VentaDetailRead` (incluye `pedido_id`) | **retorno** |
| 17 | Router Ventas → Panel React | `200 OK` | **retorno** |

**Puntos críticos:**

| Punto | Cómo se dibuja |
|---|---|
| **Anulación lógica** | No hay mensaje `delete`. La fila, el comprobante y los pagos se conservan. |
| **Reversión condicional** | El bloque 13 es `opt`, no `alt`: si la venta era al contado, el diagrama **salta** esas líneas sin rama `else`. |
| **Deuda revertida** | Nota: se **resta** porque al crear el pagaré se **sumó**. |
| **Entrega no revertida** | Nota al final: el `pedido_id` del retorno habilita a que `pedidos` revierta `ENTREGADO → LISTO` (flujo de otro módulo; **no dibujarlo acá**). |
| **Stock** | Nota obligatoria: **el stock no se repone** en ningún punto. |

### D-05.b — Diagrama de actividad

```
A1 INICIO (Panel React)
A2 escribir motivo (1..255) → A3 ¿rol == Administrador? --[no]--> FIN 403
A4 ¿venta existe? --[no]--> FIN 404
A5 ¿ya está ANULADA? --[sí]--> FIN 409
A6 guardar estado_anterior
A7 marcar ANULADA + anulada_en
A8 registrar historial con motivo y cuenta
A9 ¿estado_anterior == PENDIENTE_COBRO? --[sí]--> A10 saldo del cliente -total
                                        --[no]--> (merge)
A11 ¿falló alguna escritura? --[sí]--> rollback() --> FIN 500
                            --[no]--> A12 commit()
A13 FIN 200 (venta anulada, pedido_id devuelto)
```

---

## D-06 · Listar ventas con filtros

**Disparador:** `GET /api/v1/ventas/?…` · Roles: Administrador, Cajero, Operario.
**Solo lectura: no hay `commit` ni `rollback`.**

### D-06.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Ventas` → `VentaService` → `crud` → `Session` → `SQLite`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Ventas | `GET /ventas/?skip&limit&fecha_desde&fecha_hasta&estado&metodo_de_pago&cliente_persona_id&q` | sync |
| 2 | Router Ventas | `_exigir_rol(ADMINISTRADOR, CAJERO, OPERARIO)` | interno |
| 3 | Router Ventas → VentaService | `listar_ventas(...)` | sync |
| 4 | VentaService → crud | `listar(db, skip, limit, filtros)` | sync |
| 5 | crud → Session | `SELECT venta_comercial LEFT JOIN pedido LEFT JOIN persona … ORDER BY fecha DESC, id` | sync |
| 6 | Session → SQLite | ejecuta la consulta | sync |
| 7 | SQLite → crud | filas `(venta, persona_id, nombre, apellido)` | **retorno** |
| 8 | VentaService → crud | `metodos_por_venta(db, [ids])` | sync |
| 9 | VentaService → VentaService | mapear a `VentaListRead` (`_a_venta_read` + cliente + métodos) | interno |
| 10 | VentaService → Router Ventas | `list[VentaListRead]` | **retorno** |
| 11 | Router Ventas → Panel React | `200 OK` | **retorno** |

**Puntos críticos:**
- Los **joins son externos (`LEFT`)**: una venta cuyo pedido ya no existe **se muestra igual**. Si el diagrama muestra `INNER JOIN`, está mal.
- `limit` está acotado a `500` y `skip ≥ 0`; fuera de rango → `422` (validación de `Query`).
- `q` busca por texto libre; el resto de filtros son exactos. No hay `commit`.

### D-06.b — Diagrama de actividad

```
A1 INICIO (Panel React) → A2 cargar filtros y paginación
A3 ¿rol ∈ {Admin, Cajero, Operario}? --[no]--> FIN 403
A4 ¿parámetros válidos (limit ≤ 500, skip ≥ 0)? --[no]--> FIN 422
A5 aplicar filtros de fecha (rango sobre venta.fecha)
A6 aplicar estado / método / cliente / texto
A7 SELECT con LEFT JOIN a pedido y persona
A8 ORDER BY fecha DESC, id + skip/limit
A9 resolver métodos de pago por venta
A10 FIN 200 (lista)
```

---

## D-07 · Consultas de contabilidad y cobranza

**Disparadores:** `GET /ventas/resumen-mensual`, `GET /ventas/cobranza-mensual`, `GET /ventas/por-cobrar`.
**Solo lectura.** Es el flujo que alimenta la pantalla `Contabilidad.jsx`.

### D-07.a — Diagrama de secuencia (`por-cobrar`, el más representativo)

Lifelines: `Panel React` → `Router Ventas` → `VentaService` → `crud` → `Session` → `SQLite`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Ventas | `GET /ventas/por-cobrar` | sync |
| 2 | Router Ventas | `_exigir_rol(CONSULTA)` | interno |
| 3 | Router Ventas → VentaService | `por_cobrar()` | sync |
| 4 | VentaService → crud | `pendientes_de_cobro(db)` | sync |
| 5 | crud → Session | `SELECT … WHERE estado = 'PENDIENTE_COBRO' ORDER BY fecha_vencimiento` | sync |
| 6 | Session → SQLite | ejecuta | sync |
| 7 | VentaService → VentaService | `ahora = datetime.now()` | interno |
| 8 | VentaService → VentaService | **`loop`** `[por cada pendiente]` → `vencida = vencimiento is not None and vencimiento < ahora` | loop |
| 9 | VentaService → VentaService | `total_por_cobrar = Σ items.total`; `cantidad_vencidas = Σ vencida` | interno |
| 10 | VentaService → Router Ventas | `VentaPorCobrarRead` | **retorno** |
| 11 | Router Ventas → Panel React | `200 OK` | **retorno** |

**Variantes (mismo esqueleto, solo cambia el mensaje 4):**

| Endpoint | Mensaje al `crud` | Salida | Regla clave |
|---|---|---|---|
| `/resumen-mensual` | `resumen_por_mes(...)` + `totales_por_mes_y_metodo(...)` | `list[VentaResumenMensualRead]` | Agrupa por `venta_comercial.fecha`, **incluye `PENDIENTE_COBRO`** (facturado). |
| `/cobranza-mensual` | `cobranza_por_mes(...)` + `totales_de_cobranza_por_metodo(...)` | `list[VentaCobranzaMensualRead]` | Agrupa por **`cobrada_en`**, no por la fecha de la venta. `PENDIENTE_COBRO` **no suma**. |
| `/resumen` | `totales_generales(...)` + `totales_por_metodo(...)` | `VentaResumenRead` | Excluye `ANULADA`; el desglose por método solo cuenta `CONFIRMADA`. |

### D-07.b — Diagrama de actividad (`por-cobrar`)

```
A1 INICIO (Panel React) → A2 abrir Contabilidad
A3 ¿rol ∈ {Admin, Cajero, Operario}? --[no]--> FIN 403
A4 leer pendientes de cobro ordenados por vencimiento
A5 [loop por cada pendiente] → ¿fecha_vencimiento < ahora? --[sí]--> marcar vencida
                                                           --[no]--> no marcar
A6 acumular total_por_cobrar y cantidad_vencidas
A7 FIN 200 (tabla "Por cobrar" + KPI)
```

---

## D-08 · Revertir entrega (`ENTREGADO → LISTO`)

**Disparador:** `PATCH /api/v1/pedidos/panel/{id}` con `estado: "Listo"`.
**Transacción:** abierta por `PedidoService`; el `commit` es de `pedidos`.
**Resultado:** el pedido vuelve a `LISTO` **solo si no tiene venta vigente**. La venta no se borra, no se modifica y el stock no se repone.

> **Este diagrama cruza dos módulos.** `ventas` aporta una única consulta de solo
> lectura (`tiene_venta_vigente`); no hay escritura en el módulo de ventas.
> Es el complemento natural de **D-05**: primero se anula la venta, después se revierte la entrega.

### D-08.a — Diagrama de secuencia

Lifelines: `Panel React` → `Router Pedidos` → `PedidoPanelService` → `PedidoService` → `ventas.services` → `ventas.crud` → `Session` → `SQLite`

| # | Desde → Hacia | Mensaje | Tipo |
|---|---|---|---|
| 1 | Panel React → Router Pedidos | `PATCH /pedidos/panel/{id}` `{estado: "Listo"}` | sync |
| 2 | Router Pedidos | `get_current_user(token)` + `get_panel_service(db)` | interno |
| 3 | Router Pedidos → PedidoPanelService | `actualizar(pedido_id, datos, cuenta_id)` | sync |
| 4 | PedidoPanelService → PedidoPanelService | `crud.get_pedido(db, pedido_id)` → `None` → `404 PedidoNoEncontrado` | sync |
| 5 | PedidoPanelService → PedidoPanelService | `objetivo = estado_canonico(datos.estado)` → `"LISTO"` | interno |
| 6 | PedidoPanelService → PedidoPanelService | `_cambiar_estado(pedido, "LISTO")` | interno |
| 6.1 | `_cambiar_estado` | `alt [actual == objetivo]` → no aplica (`ENTREGADO != LISTO`) | alt |
| 6.2 | `_cambiar_estado` → PedidoService | `_validar_transicion_estado("ENTREGADO", "LISTO")` → `True` | sync |
| 6.3 | `_cambiar_estado` → PedidoService | `cambiar_estado_pedido(pedido_id, "LISTO", usuario_id)` | sync |
| 7 | PedidoService → PedidoService | `estado_anterior = db_pedido.estado` → `"ENTREGADO"` | interno |
| 8 | PedidoService → PedidoService | `_validar_transicion_estado("ENTREGADO", "LISTO")` → `True` | interno |
| 9 | PedidoService | `alt [transición inválida]` → `422 TransicionInvalida` | alt |
| 10 | PedidoService → ventas.services | `tiene_venta_vigente(db, pedido_id)` | sync |
| 10.1 | ventas.services → ventas.crud | `obtener_vigente_por_pedido(db, pedido_id)` | sync |
| 10.2 | ventas.crud → Session | `SELECT venta_comercial WHERE pedido_id = :id AND estado IN ('CONFIRMADA','PENDIENTE_COBRO')` | sync |
| 10.3 | ventas.crud → ventas.services | `VentaComercial \| None` | **retorno** |
| 10.4 | ventas.services → PedidoService | `bool` | **retorno** |
| 11 | PedidoService | **`alt [venta vigente == True]`** → `raise PedidoConVentaVigente(pedido_id)` | alt |
| 11.1 | PedidoService → Session | `db.rollback()` | sync |
| 11.2 | PedidoService → Router Pedidos | excepción → `_a_codigo_http` → `409 Conflict` | **retorno** |
| 12 | PedidoService | `db_pedido.estado = "LISTO"` | interno |
| 13 | PedidoService → PedidoService | `_registrar_historial_estado(pedido_id, "ENTREGADO", "LISTO", usuario_id)` → `INSERT pedido_estado_historial` | sync |
| 14 | PedidoService → Session | `db.commit()` | sync |
| 15 | PedidoService → Session | `db.refresh(db_pedido)` | sync |
| 16 | PedidoService → Router Pedidos | `Pedido` en `LISTO` | **retorno** |
| 17 | Router Pedidos → Panel React | `200 OK` con pedido | **retorno** |

**Puntos críticos:**

| Punto | Cómo se dibuja |
|---|---|
| **Consulta cruzada de solo lectura** | El paso 10 es la **única** interacción con `ventas`. No hay `INSERT`, `UPDATE` ni `DELETE` en la línea de vida de ventas. |
| **Bloqueo, no borrado** | Si hay venta vigente, el diagrama termina en `409`. No existe rama que anule la venta automáticamente. |
| **Precondición real** | Nota: solo se puede revertir después de ejecutar **D-05** (`ANULADA` deja de ser vigente). |
| **Stock** | Nota obligatoria: la reversión **no repone stock**, porque se descontó al crear el pedido. |
| **Rollback** | `PedidoConVentaVigente` se lanza **dentro** del `try`, por lo que el diagrama debe mostrar `rollback()` antes del `409`. |

### D-08.b — Diagrama de actividad

Particiones: `Panel React` · `Router Pedidos` · `PedidoService` · `ventas.services / crud`

| Nodo | Partición | Tipo | Etiqueta | Guardas salientes |
|---|---|---|---|---|
| A1 | Panel React | INICIO | — | — |
| A2 | Panel React | ACCIÓN | Arrastrar tarjeta de Entregado a Listo | — |
| A3 | Router Pedidos | ACCIÓN | Resolver cuenta y servicio del panel | — |
| A4 | PedidoService | DECISIÓN | ¿Pedido existe? | `[no]` → A5 · `[sí]` → A6 |
| A5 | PedidoService | FIN | `404 PedidoNoEncontrado` | — |
| A6 | PedidoService | DECISIÓN | ¿Transición `ENTREGADO → LISTO` permitida? | `[no]` → A7 · `[sí]` → A8 |
| A7 | PedidoService | FIN | `422 TransicionInvalida` | — |
| A8 | ventas.services | ACCIÓN | `obtener_vigente_por_pedido(pedido_id)` | — |
| A9 | PedidoService | DECISIÓN | **¿Hay venta `CONFIRMADA` o `PENDIENTE_COBRO`?** | `[sí]` → A10 · `[no]` → A12 |
| A10 | PedidoService | ACCIÓN | `rollback()` | — |
| A11 | PedidoService | FIN | `409 PedidoConVentaVigente` | — |
| A12 | PedidoService | ACCIÓN | `pedido.estado = "LISTO"` | — |
| A13 | PedidoService | ACCIÓN | Registrar historial de estado | — |
| A14 | PedidoService | ACCIÓN | `commit()` | — |
| A15 | PedidoService | FIN | `200 OK` con pedido en `LISTO` | — |

> **A9 es el nodo central del diagrama.** Conviene resaltarlo con color, porque
> representa la única frontera entre los módulos `pedidos` y `ventas`, y la regla
> que impide dejar una venta huérfana sobre un pedido no entregado.

### D-08.c — Secuencia de recuperación (opcional, en el mismo diagrama)

Si el diagrama debe mostrar *cómo* se desbloquea, agregar un fragmento `opt`
previo en el extremo izquierdo con la referencia a D-05:

```
opt [reversión rechazada por 409]
    Panel React → Router Ventas: POST /ventas/{id}/anular {motivo}
    Nota: la venta pasa a ANULADA → deja de ser vigente
    Panel React → Router Pedidos: PATCH /pedidos/panel/{id} {estado: "Listo"}  (reintento)
end
```

No dibujar las dos operaciones como una sola transacción: son **dos requests
independientes**. Si la anulación funciona y la reversión falla, la venta queda
anulada y el pedido sigue `ENTREGADO`, que es un estado consistente.

---

# PARTE IV — Anexos

## A. Mapa de transacciones (dónde se hace `commit` / `rollback`)

| Diagrama | Abre la transacción | `commit` | `rollback` | Quién traduce el error a HTTP |
|---|---|---|---|---|
| D-01 / D-02 | `PedidoService.cambiar_estado_pedido` | `PedidoService` | `PedidoService` | `Router Pedidos` |
| D-03 | `VentaService.registrar_venta` | `VentaService` | `VentaService` | `Router Ventas._a_codigo_http` |
| D-04 | `VentaService.cobrar_venta` | `VentaService` | `VentaService` | `Router Ventas._a_codigo_http` |
| D-05 | `VentaService.anular_venta` | `VentaService` | `VentaService` | `Router Ventas._a_codigo_http` |
| D-08 | `PedidoService.cambiar_estado_pedido` | `PedidoService` | `PedidoService` | `Router Pedidos._a_codigo_http` |
| D-06 / D-07 | — (solo lectura) | no | no | — |

> **No dibujar `commit` en `crud.py` en ningún diagrama.**
> Tampoco en `registrar_venta_de_entrega`, que es el único método de escritura del servicio que no cierra transacción.

## B. Errores de dominio y cómo se dibujan

| Excepción | HTTP | Se origina en | En el diagrama |
|---|---|---|---|
| `PedidoNoEncontrado` | 404 | `registrar_venta`, `cobrar_venta`, `anular_venta` | Nodo final de error |
| `VentaNoEncontrada` | 404 | `cobrar_venta`, `anular_venta`, `obtener_*` | Nodo final de error |
| `PedidoNoVendible` | 409 | `registrar_venta` | Nodo final de error |
| `VentaDuplicada` | 409 | `registrar_venta`, `registrar_venta_de_entrega`, índice `ux_venta_comercial_pedido_vigente` | Nodo final + nota del índice |
| `PagosNoCuadran` | 409 | `registrar_venta` | Nodo final con la diferencia |
| `PagareNoPermitido` | 409 | `_sumar_deuda_de_pagare` | Nodo final |
| `PlazoInvalido` | 422 | `_validar_plazo` | Nodo final |
| `ComprobanteDuplicado` | 409 | `_traducir_integrity_error` | Nodo final |
| `VentaNoPendienteDeCobro` | 409 | `cobrar_venta` | Nodo final |
| `VentaYaAnulada` | 409 | `anular_venta` | Nodo final |
| `CondicionDePagoRequerida` | 422 | `PedidoService` | Nodo final |
| `PedidoConVentaVigente` | 409 | `PedidoService` (`ENTREGADO → LISTO`) | Nodo final en **D-08** |
| `TransicionInvalida` | 422 | `PedidoService._validar_transicion_estado` | Nodo final en **D-08** |

`_a_codigo_http` es un colaborador del router: mapea excepción → código. Dibujarlo como una acción `traducir excepción a HTTP` en la calle `Router Ventas`, no como lifeline.

## C. Reglas para no inventar elementos

1. **Ventas nunca toca stock.** Ningún diagrama de este módulo tiene nodo de descuento o reposición de kilos. El stock se descuenta al **crear el pedido** (FIFO, en `pedidos`).
2. **No hay cobros parciales.** No dibujar `opt [monto < total]`.
3. **No hay pasarela real.** `metodo_de_pago` es un enum informativo: no hay llamada HTTP externa de pago.
4. **No hay devoluciones ni notas de crédito.**
5. **La anulación no borra**: no existe `DELETE FROM venta_comercial` en ningún flujo.
6. **`ventas` no escribe en `pedido`** salvo a través de la transacción que abre `pedidos` (D-01 / D-02). En **D-08** la interacción es **solo de lectura**: `ventas.services.tiene_venta_vigente` consulta y devuelve un booleano, sin modificar nada.
7. **Un pedido tiene como máximo una venta vigente**, garantizado por un índice único parcial en la base. En los diagramas eso se representa como una validación previa **y** como una nota de restricción de BD.

## D. Glosario mínimo

| Término | Significado |
|---|---|
| **Venta vigente** | Estado `CONFIRMADA` o `PENDIENTE_COBRO`. Máximo una por pedido. |
| **Pagaré** | Venta a plazo 30/60/90 días con deuda en la cuenta corriente del cliente B2B. |
| **Facturado** | Toda venta no anulada, **incluye pagarés pendientes**. |
| **Cobrado** | Solo ventas con `cobrada_en` no nulo. |
| **Comprobante** | `V-AAAAMM-######`, único, generado tras el `flush` que asigna el `id`. |
