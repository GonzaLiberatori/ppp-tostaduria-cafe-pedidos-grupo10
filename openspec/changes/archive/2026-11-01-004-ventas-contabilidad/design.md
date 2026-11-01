# Design: Integración de ventas con Contabilidad

## Context

Ver `proposal.md` para la motivación. Estado actual que condiciona el diseño (verificado en el código):

- `ventas` ya expone `GET /api/v1/ventas` (listado con filtros), `GET /api/v1/ventas/resumen` (arqueo de un rango), `GET /api/v1/ventas/{id}`, `GET /api/v1/ventas/comprobante/{numero}` y `POST /api/v1/ventas/{id}/anular`. El RBAC vive en `ventas/router.py` (`ROLES_CONSULTA`, `ROLES_REGISTRO`, `ROLES_ANULACION`).
- `ventas/crud.py` ya tiene `totales_generales` y `totales_por_metodo`, ambos filtran `estado == CONFIRMADA` y aplican `_filtrar_por_fechas`.
- `VentaListRead` devuelve `numero_comprobante`, `fecha`, `estado`, `total`, `cliente_nombre` y `metodos_de_pago`, suficiente para la tabla.
- `frontend/src/context/DataContext.jsx:296-326` calcula la contabilidad mensual sumando `pedido.total` de pedidos `Entregado`; `getTotalesGenerales()` deriva de ahí. `Dashboard.jsx:44-48` y `Contabilidad.jsx:52-55` consumen esos helpers.
- `frontend/src/services/api.js` no tiene ninguna función de ventas.
- `Contabilidad.jsx` es admin-only (`App.jsx:87-91`), usa `Table`, `Badge`, `Modal`, `Input` y `Select` reutilizables.
- La carga inicial de `DataContext` usa `Promise.all`; si una promesa falla, todo el panel queda sin datos y con error.
- `backend/app/modules/contabilidad/__init__.py` importa módulos inexistentes y no está registrado en `main.py`.
- Base SQLite; head de Alembic `003_ventas`; `backend/db.sqlite` está en `57cf7419baaf` (sin tablas de ventas).

## Goals / Non-Goals

**Goals:**

- Serie mensual de ventas confiables (sin anuladas) expuesta por el módulo dueño.
- Contabilidad y Dashboard con los mismos números, sin duplicar el cálculo en dos lugares.
- Detalle de ventas con anulación desde Contabilidad, respetando RBAC.
- No romper el panel si el endpoint nuevo falla (base sin migrar).

**Non-Goals:**

- Alta de ventas desde la UI.
- Mover la lógica de gastos o de pedidos.
- Crear un módulo `contabilidad` nuevo o un endpoint que componga ventas + gastos en el backend.
- Paginación server-side en la tabla de ventas.

## Decisions

### 1. El agregado mensual vive en `ventas`, no en un módulo de contabilidad

`crud.resumen_por_mes` hace dos consultas agrupadas: una por mes (`count`, `sum(total)`) y otra por mes + método de pago (join a `PagoVenta`), ambas sobre `VentaComercial.estado == CONFIRMADA`. `services.resumen_mensual` las combina en una lista.

**Por qué:** `ventas` es el dueño del dato y ya tiene la regla de exclusión de anuladas. Un módulo `contabilidad` que importe `ventas.services` y `gastos.services` sería más "puro", pero suma una capa y toca un placeholder roto que nadie usa. Si más adelante la contabilidad necesita combinar varias fuentes en el backend, ese módulo se crea con una razón concreta.

**Alternativas descartadas:** agregar en el front trayendo todas las ventas (duplica la regla de anuladas y no escala con `limit=500`); crear `contabilidad` ahora (fuera de alcance y sin consumidores).

### 2. Agrupación con `strftime` de SQLite

`func.strftime('%Y-%m', VentaComercial.fecha)` como clave de agrupación. El proyecto es SQLite por decisión de `core/config.py`; la consulta se aísla en `crud.py` para que un cambio de motor solo obligue a reescribir esa función.

**Alternativa descartada:** traer las ventas y agrupar en Python; más simple de portar, pero mueve datos de más y mezcla acceso a datos con presentación.

### 3. Endpoint `GET /ventas/resumen-mensual` antes de `/{venta_id}`

Se declara junto a `/resumen` y `/comprobante/...`, antes de la ruta por id, para que "resumen-mensual" no se interprete como identificador. Roles: `ROLES_CONSULTA` (Administrador, Cajero, Operario). Devuelve una lista ordenada por mes descendente.

Respuesta por mes:

- `mes`: `AAAA-MM`
- `cantidad_ventas`: entero
- `total_facturado`: decimal
- `totales_por_metodo`: reutiliza `ResumenPorMetodo`

Solo aparecen meses con al menos una venta confirmada. El front une esos meses con los meses de gastos, así que un mes con gastos y sin ventas sigue mostrándose con ventas en cero (comportamiento actual de la pantalla).

### 4. `DataContext` conserva la forma y aísla el fallo

Se agregan dos estados: `resumenVentasMensual` y `ventas`. Las promesas nuevas se resuelven con `.catch(() => [])` dentro del `Promise.all` existente, y el error se guarda en `errors.contabilidad`. Así, si `backend/db.sqlite` no tiene la migración `003_ventas`, el resto del panel sigue cargando y Contabilidad muestra un aviso en vez de dejar toda la aplicación vacía.

`getContabilidadMensual()` mantiene la salida `{ mes, ventasTotales, gastosTotales, gananciaNeta }`: toma `ventasTotales` de `resumenVentasMensual`, `gastosTotales` de `/gastos`, une los meses de ambas fuentes y ordena descendente. `getTotalesGenerales()` no cambia. Por eso `Contabilidad.jsx` y `Dashboard.jsx` no necesitan reescribir sus gráficos ni sus tablas.

**Alternativa descartada:** que cada página consulte `/ventas` por su cuenta; duplicaría fetch y podría mostrar números distintos entre Dashboard y Contabilidad.

### 5. Tabla de ventas con anulación en Contabilidad

Se reutiliza `GET /ventas/?limit=100` (más reciente primero) y `POST /ventas/{id}/anular`. La tabla muestra comprobante, fecha, cliente, métodos, total y estado. La acción **Anular** abre el `Modal` existente, exige un motivo y, al confirmar, llama a `anularVenta` y refresca tanto el listado como el resumen mensual.

El filtrado por estado y la búsqueda por cliente/comprobante se hacen en el cliente sobre las 100 ventas cargadas, igual que el detalle de gastos. Paginar en el servidor queda como mejora posterior.

**Por qué no un modal de alta:** registrar una venta exige elegir un pedido `ENTREGADO` y repartir pagos; ese flujo pertenece a Pedidos y está fuera de alcance.

### 6. Limpieza del placeholder y del archivo staged

Se elimina `backend/app/modules/contabilidad/` (solo contiene un `__init__.py` que importa módulos inexistentes y no lo importa nadie). Se saca del índice `backend/db_ventas.sqlite` con `git rm --cached`, sin borrar el archivo local.

**Riesgo de coordinación:** si un compañero está trabajando en ese módulo, hay que avisarle antes de borrarlo. La alternativa mínima es dejar el `__init__.py` vacío; se prefiere borrar para no simular un módulo que no existe.

## Risks / Trade-offs

- [Cambia la semántica de los números] → "Ventas Totales" pasa de pedidos entregados a ventas confirmadas; los valores bajan si hay entregas sin cobrar. Mitigación: documentarlo en el resumen del cambio y avisar al equipo antes de la demo.
- [Base sin migrar] → `/ventas/resumen-mensual` falla con "no such table". Mitigación: las promesas de ventas se aíslan con `catch`, Contabilidad muestra un aviso y el runbook indica `alembic upgrade head`.
- [Agrupación no portable] → `strftime` es de SQLite. Mitigación: la consulta queda aislada en `crud.resumen_por_mes`.
- [Ventas registradas fuera de la ventana de 100] → la tabla no las muestra. Mitigación: filtros de la API ya existen; paginación server-side como mejora.
- [Dashboard cambia sin pedirlo] → su tarjeta "Ventas del Mes" usa el mismo helper. Se acepta por consistencia; si se quisiera aislar, habría que duplicar el cálculo.
- [Borrar el placeholder] → puede pisar trabajo ajeno. Mitigación: confirmar con el equipo; el cambio es reversible por git.

## Migration Plan

1. Backend: agregar `crud.resumen_por_mes`, `services.resumen_mensual`, schemas y la ruta; tests del módulo.
2. Frontend: `api.js`, `DataContext`, tabla y anulación en `Contabilidad.jsx`.
3. Limpieza: borrar el placeholder de contabilidad y sacar `db_ventas.sqlite` del índice.
4. Verificación: `alembic upgrade head` sobre la base de trabajo, `pytest tests/modules/ventas -q`, backend + `npm run dev`, login admin, Contabilidad con ventas reales y anulación.

Rollback: revertir los archivos de código; no hay migración que deshacer. Las ventas y gastos existentes no se modifican.

## Open Questions

Ninguna pendiente.
