# Design: Módulo de Ventas (003ventas)

## Context

Estado actual que condiciona el diseño (verificado en el código):

- `pedidos/models.py` ya define `MetodoPago`, `Moneda`, `Facturacion` y las tablas `pago` (con `porcentaje_pagado`) y `venta` (con `pago_id`, `id` sin autoincrement). Ningún flujo las crea y no existe CRUD que las use.
- `Pedido.venta` es una relación con string `"Venta"`; cualquier clase nueva llamada `Venta` en otro módulo produciría ambigüedad en el registry de SQLAlchemy.
- `Pedido.total` (`Numeric(10,2)`) se calcula al crear el pedido y no cambia después.
- `EstadoPedido` usa los valores `PENDIENTE`, `LISTO`, `ENTREGADO`.
- `pedidos/services.py` imputa la deuda B2B al pasar a `ENTREGADO` y la revierte al volver a `LISTO`, y descuenta stock por FIFO al crear el pedido.
- `Cuenta` (`auth/models.py`) tiene `rol: UserRole` (`Administrador`, `Cajero`, `Operario`, `Cliente`) y `correo` único. `TokenData` solo transporta `email` y `core/deps.get_current_user` descarta el rol.
- El backend corre sobre SQLite (`core/config.py`) con Alembic; el head actual es `57cf7419baaf`.
- `pedidos/router.py` usa `Optional` y `datetime` sin importarlos: `app.main` no importa y `tests/conftest.py` (que hace `import app.main`) impide recolectar cualquier test.

**Restricción de alcance:** no se modifica el comportamiento ni el código de `pedidos`, `clientes`, `inventario`, `auth` ni `core`, salvo las cuatro líneas imprescindibles para que la aplicación arranque y el router nuevo quede expuesto.

## Goals / Non-Goals

**Goals:**

- Registrar el cobro de un pedido entregado con uno o varios pagos, en una transacción única.
- Consultar, auditar y anular ventas sin borrar datos.
- Arqueo de caja por método de pago para un rango de fechas.
- Cero cambios de comportamiento en los módulos existentes.

**Non-Goals:**

- Imputar o revertir deuda en `Cliente.saldo_cuenta_corriente` (lo sigue haciendo `pedidos`).
- Descontar o reponer stock de café tostado (lo sigue haciendo `pedidos`).
- Cambiar el ciclo de vida del pedido, sus estados o sus endpoints.
- Pasarela de pago, reintegro real de dinero, nota de crédito fiscal, tipo de cambio.
- Frontend de ventas.
- Reutilizar o migrar las tablas heredadas `venta` / `pago`.

## Decisions

### 1. Módulo propio con nombres de tabla distintos

`app/modules/ventas/` con `models.py`, `schemas.py`, `crud.py`, `services.py`, `router.py`. Las entidades se llaman `VentaComercial`, `PagoVenta` y `VentaComercialHistorial`, sobre las tablas `venta_comercial`, `pago_venta` y `venta_comercial_historial`.

El renombre no es cosmético: `pedidos.models` ya mapea las clases `Venta` y `Pago` y usa `relationship("Venta")` por string. Declarar otra clase `Venta` dispara `Multiple classes found for path "Venta"` al configurar los mapeos, y reutilizar la tabla `venta` obligaría a reescribirla, que es exactamente lo que este alcance evita.

**Alternativas:** mover `Venta`/`Pago` a ventas y reexportar desde pedidos → cumple la spec original pero edita tres archivos del compañero. Descartado por decisión de alcance.

### 2. Los enums se importan, no se redefinen

`ventas/models.py` hace `from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda`. Es una lectura: no modifica ni registra nada nuevo. Redefinir los enums duplicaría los valores de `SQLEnum` y cualquier cambio futuro en pedidos dejaría los dos módulos inconsistentes.

### 3. La venta se registra sobre un pedido `ENTREGADO`

No dispara ni revierte transiciones. El operario entrega desde el panel de pedidos como hoy, y después (o en el mismo momento) registra el cobro en ventas. Esto es lo que permite no tocar `pedidos/services.py`.

**Alternativas:** registrar la venta en `LISTO` y que ventas mueva el pedido a `ENTREGADO` → obliga a escribir el estado del pedido y su historial desde ventas, duplicando la lógica de transición y el ajuste de deuda. Descartado.

### 4. Ventas no escribe saldo ni stock

`ventas` nunca toca `Cliente.saldo_cuenta_corriente`, `Lote` ni `PedidoEstadoHistorial`. Cada dato sigue teniendo un solo dueño: pedidos (entrega, stock, deuda) y ventas (cobro y comprobante).

Consecuencia aceptada y visible en la spec: la deuda B2B se imputa por el total del pedido sin importar cómo se cobró, y anular la venta no la revierte. Para corregir una entrega el operario debe, en este orden: anular la venta, y luego revertir el pedido a `LISTO` desde el panel (que ya ajusta el saldo).

**Alternativas:** que ventas impute la porción `CREDITO` y revierta al anular → doble deuda cuando el pedido ya pasó por `ENTREGADO`, y escritura cruzada de un modelo ajeno. Descartado.

### 5. Unicidad con índice parcial sobre `CONFIRMADA`

`CREATE UNIQUE INDEX ux_venta_comercial_pedido_vigente ON venta_comercial (pedido_id) WHERE estado = 'CONFIRMADA'`. Un `UNIQUE(pedido_id)` plano impediría volver a vender un pedido cuya venta anterior fue anulada, que es un caso real (cobro mal cargado).

SQLite soporta índices únicos parciales; Alembic los emite con `op.create_index(..., sqlite_where=sa.text("estado = 'CONFIRMADA'"))`. La verificación previa en el servicio da el 409 amable y el índice cubre la carrera.

**Alternativas:** columna `vigente` booleana + `UNIQUE(pedido_id, vigente)` → funciona también en MySQL, pero agrega estado derivado que hay que mantener sincronizado. Anotado como plan B si el equipo migra el motor.

### 6. RBAC resuelto dentro del módulo

`ventas/router.py` define su propia dependencia `get_cuenta_actual`: valida el token con el `get_current_user` existente, toma el `email` del `TokenData` y busca la `Cuenta` por `correo`. Con la `Cuenta` en mano aplica la matriz de roles y la pasa al servicio para guardar `cuenta_id`.

No se modifica `core/deps.py` (no se agrega `require_roles`) ni `auth/schemas.py` (no se agrega `role` a `TokenData`). El costo es una consulta por request autenticado, irrelevante para el volumen del MVP.

**Alternativas:** extender `TokenData` y `core/deps.py` → más limpio a futuro, pero son archivos compartidos. Queda como mejora posterior.

### 7. Frontera transaccional en `services.py`

`VentaService.registrar_venta` y `VentaService.anular_venta` son los únicos puntos con `commit`. `crud.py` solo hace `add`/`flush`/`query`. Ante cualquier excepción el servicio hace `rollback` y traduce el `IntegrityError` del índice parcial a `VentaDuplicada` (409). SQLite serializa las escrituras, así que no hace falta bloqueo explícito.

### 8. Comprobante legible generado dentro de la transacción

`V-{AAAAMM}-{id:06d}`: se hace `flush()` para obtener el `id`, se asigna el comprobante y se hace otro `flush()`. El `UNIQUE` sobre `numero_comprobante` es la garantía final. No se usa una tabla de secuencias: sería más maquinaria y contención de escritura para una demo.

### 9. Lectura del pedido sin acoplarse a su lógica

`venta_comercial.pedido_id` es `ForeignKey("pedido.id")` por string. Para el detalle y el listado, `crud.py` hace `join` a `Pedido` y `Cliente` en modo lectura, y reutiliza `DetallePedido` para mostrar los ítems. No se llama a ningún servicio de pedidos ni se modifica ninguna de sus filas.

### 10. Migración `003_ventas` sobre `57cf7419baaf`

Solo `create_table` de las tres tablas nuevas y `create_index` (incluido el parcial). No hay `batch_alter_table` porque no se altera ninguna tabla existente, y por lo tanto no hay riesgo para los datos del equipo. `downgrade` hace `drop_index` + `drop_table` en orden inverso. Se agrega el import de `ventas.models` en `alembic/env.py` para que `autogenerate` y `check` vean las tablas.

### 11. Tests aislados en `tests/modules/ventas/`

Se agrega un `conftest.py` propio en esa carpeta que reexporta lo que ya existe en `backend/tests/conftest.py` (pytest combina ambos automáticamente) y suma únicamente fixtures nuevas: `pedido_entregado_b2b` (usa `sample_pedido_b2b_entregado`), `pedido_entregado_consumidor` y `venta_confirmada`. El `conftest.py` compartido no se toca.

Los casos de rollback se simulan con `monkeypatch` sobre `crud.crear_pago` / `crud.crear_historial` para no depender de un motor externo.

### 12. Errores de dominio traducidos en el router

Excepciones en `ventas/services.py`: `VentaNoEncontrada` (404), `PedidoNoVendible` (409), `VentaDuplicada` (409), `PagosNoCuadran` (409 con la diferencia), `VentaYaAnulada` (409). Las validaciones de forma (pagos no vacíos, monto > 0, método y moneda válidos, motivo no vacío) quedan en Pydantic y salen como 422. El router no contiene reglas de negocio.

### 13. API y contratos

- `POST /api/v1/ventas` → 201 `VentaDetailRead`.
- `GET /api/v1/ventas` → listado paginado (`fecha_desde`, `fecha_hasta`, `estado`, `metodo_de_pago`, `cliente_persona_id`, `q`, `skip`, `limit`).
- `GET /api/v1/ventas/resumen` → totales y cantidades por método.
- `GET /api/v1/ventas/{id}` y `GET /api/v1/ventas/comprobante/{numero}`.
- `POST /api/v1/ventas/{id}/anular` → 200 con la venta anulada, incluido `pedido_id`.

Requests: `VentaCreate(pedido_id, facturacion, pagos)`, `PagoCreate(metodo_de_pago, monto, moneda, aclaracion?)`, `VentaAnulacionCreate(motivo)`. El prefijo `/api/v1` lo aporta `main.py`, igual que en el resto de los módulos.

## Risks / Trade-offs

- [Deuda y cobro no conciliados] → un Mayorista que paga en efectivo igual queda con deuda, porque pedidos la imputó por el total. Mitigación: `docs/feature-ventas.md` lo documenta y el resumen de arqueo muestra el cobro real. Conciliar requiere el cambio en pedidos que este alcance excluye.
- [Anulación en dos pasos] → anular la venta no libera al cliente de la deuda; hay que revertir el pedido en el panel. Mitigación: la respuesta de anulación devuelve `pedido_id`.
- [El arreglo de `pedidos/router.py` es de otro archivo] → son dos líneas de imports, sin cambio de lógica, pero sin ellas no se puede correr nada. Se aísla en su propia tarea y se documenta en el proposal.
- [Índice parcial no portable a MySQL] → SQLite lo soporta y es el motor del proyecto. Si se migra el motor, se reemplaza por `UNIQUE(pedido_id, vigente)` sin cambiar el contrato HTTP.
- [Ventas sin pago parcial] → la suma debe dar exacto; no se modelan señas ni saldos a favor. Fuera de alcance por decisión de producto.
- [Acoplamiento de lectura a `pedidos.models`] → si el compañero renombra `Pedido`, `DetallePedido` o `Cliente`, ventas rompe en import. Es un acoplamiento de lectura, mucho menor que editar sus archivos.

## Migration Plan

1. Corregir los imports de `pedidos/router.py` y verificar `python -c "from app.main import app"`.
2. Crear `app/modules/ventas/` con models/schemas/crud/services/router.
3. Generar `alembic/versions/003_ventas.py` e importar `ventas.models` en `alembic/env.py`; verificar `alembic upgrade head` y `alembic downgrade 57cf7419baaf` sobre una base limpia.
4. Registrar el router en `main.py`.
5. Agregar los tests del módulo y correr la suite completa.
6. Rollback: `alembic downgrade 57cf7419baaf` elimina las tres tablas nuevas; no afecta a ninguna tabla existente. Las ventas cargadas se pierden, aceptable para la demo.

## Open Questions

Ninguna pendiente.
