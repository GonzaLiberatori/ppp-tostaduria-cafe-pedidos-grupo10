# Tasks: Módulo de Ventas (003ventas)

> Alcance: módulo `ventas` nuevo. No se modifica la lógica ni el comportamiento de `pedidos`, `clientes`, `inventario`, `auth` ni `core`. Los únicos archivos compartidos que se tocan son `pedidos/router.py` (2 líneas de imports), `main.py` (2 líneas de registro) y `alembic/env.py` (1 línea de import).

## 1. Desbloqueo y registro

- [x] 1.1 En `backend/app/modules/pedidos/router.py`, cambiar `from typing import List` por `from typing import List, Optional` y agregar `from datetime import datetime`. Verificar con `python -c "from app.main import app"` que la aplicación importa (hoy falla con `NameError: name 'Optional' is not defined`).
- [x] 1.2 Crear `backend/app/modules/ventas/__init__.py` vacío (sin reexportar `router`, para no repetir el import circular del resto de los módulos) y verificar con `python -c "import app.modules.ventas"`.
- [x] 1.3 Registrar el router en `backend/app/main.py` (import + `app.include_router(ventas_router, prefix=settings.API_V1_STR)`) y verificar que `GET /openapi.json` incluye las rutas `/api/v1/ventas`.

## 2. Modelos y migración

- [x] 2.1 Crear `backend/app/modules/ventas/models.py` con `VentaComercial` (`venta_comercial`), `PagoVenta` (`pago_venta`), `VentaComercialHistorial` (`venta_comercial_historial`) y el enum `VentaEstado` (`CONFIRMADA`/`ANULADA`); importar `Facturacion`, `MetodoPago` y `Moneda` desde `app.modules.pedidos.models` sin redefinirlos. Verificar con `python -c "from app.modules.ventas.models import VentaComercial, PagoVenta, VentaComercialHistorial"`.
- [x] 2.2 Verificar que no hay colisión de mapeos: con `Base.metadata`, `sqlalchemy.orm.configure_mappers()` debe correr sin `Multiple classes found for path` y `create_all` debe crear las tres tablas nuevas junto a `venta` y `pago`.
- [x] 2.3 Crear `backend/alembic/versions/003_ventas.py` con `down_revision = "57cf7419baaf"`: tres `create_table`, índices de `pedido_id` / `venta_id`, `UNIQUE(numero_comprobante)` y el índice único parcial `ux_venta_comercial_pedido_vigente` con `sqlite_where=text("estado = 'CONFIRMADA'")`. Verificar con `alembic upgrade head` sobre una base limpia y `alembic check` sin diferencias.
- [x] 2.4 Agregar el import de `app.modules.ventas.models` en `backend/alembic/env.py` (1 línea, junto al resto de los módulos) y verificar que `alembic check` sigue sin diferencias.
- [x] 2.5 Verificar el rollback con `alembic downgrade 57cf7419baaf` y confirmar que `venta`, `pago` y el resto de las tablas existentes quedan intactas, y luego `alembic upgrade head`.

## 3. Schemas y CRUD

- [x] 3.1 Implementar `backend/app/modules/ventas/schemas.py`: `PagoCreate` (monto > 0, método y moneda válidos), `VentaCreate` (`pagos` con al menos un elemento), `VentaAnulacionCreate` (motivo no vacío) y las salidas `VentaRead`, `VentaDetailRead`, `VentaListRead`, `VentaResumenRead`. Verificar con `pytest tests/modules/ventas/test_schemas.py` que los casos inválidos dan 422.
- [x] 3.2 Implementar `backend/app/modules/ventas/crud.py` sin `commit`: `crear_venta`, `crear_pago`, `crear_historial`, `obtener_por_id`, `obtener_por_comprobante`, `obtener_vigente_por_pedido`, `listar` (filtros por fecha, estado, método de pago, cliente y texto, con paginación) y `agregar_totales_por_metodo` (excluye `ANULADA`). Verificar con `pytest tests/modules/ventas/test_crud.py` cubriendo filtros combinados y agregados.

## 4. Servicios

- [x] 4.1 Implementar `VentaService.registrar_venta` en `backend/app/modules/ventas/services.py`: validar que el pedido exista y esté `ENTREGADO`, que no tenga venta `CONFIRMADA`, que la suma de pagos coincida con `pedido.total`, generar el comprobante tras `flush()` y hacer un único `commit` con `rollback` ante excepción. Verificar con `pytest tests/modules/ventas/test_services.py` (pago único, pago mixto, pedido inexistente, pedido `LISTO`, duplicado, suma incorrecta).
- [x] 4.2 Implementar `VentaService.anular_venta`: pasar a `ANULADA`, registrar historial con motivo y cuenta, rechazar doble anulación con 409 y devolver el `pedido_id`. Verificar que el pedido sigue `ENTREGADO`, que el stock no cambia y que `saldo_cuenta_corriente` conserva su valor.
- [x] 4.3 Implementar `listar_ventas`, `resumen_arqueo`, `obtener_venta` y `obtener_por_comprobante`, mapeando errores de dominio. Verificar que el resumen excluye anuladas y que un rango vacío devuelve ceros sin error.
- [x] 4.4 Verificar los escenarios de atomicidad con `monkeypatch` sobre `crud.crear_pago` y `crud.crear_historial`: ante excepción no debe quedar la venta ni el comprobante, y la venta original debe seguir `CONFIRMADA`.

## 5. Router, RBAC, tests de integración y documentación

- [x] 5.1 Implementar en `backend/app/modules/ventas/router.py` la dependencia `get_cuenta_actual` (valida con `get_current_user`, busca `Cuenta` por `correo`) y las guardas de rol: registro Administrador/Cajero, anulación solo Administrador, consulta Administrador/Cajero/Operario. Verificar con `pytest tests/modules/ventas/test_router.py` los casos 201/200/401/403/404/409/422.
- [x] 5.2 Agregar `backend/tests/modules/ventas/conftest.py` con las fixtures propias (`pedido_entregado_b2b`, `pedido_entregado_consumidor`, `venta_confirmada`) construidas sobre las fixtures existentes de `backend/tests/conftest.py`, sin modificar ese archivo. Verificar que `pytest tests/modules/ventas -q` recolecta y pasa.
- [x] 5.3 Correr la suite completa con `pytest backend/tests -q` y confirmar que los tests de `pedidos`, `inventario` y `clientes` siguen pasando sin cambios.
- [x] 5.4 Documentar `docs/feature-ventas.md` (modelo, endpoints, flujo de dos pasos, límites de deuda y stock) y verificar que las rutas descritas aparecen en `/docs` al levantar la app.

## Workflow follow-up

- [x] Archivar el cambio con `openspec archive 003ventas` una vez aprobado el resultado y validar con `openspec validate --specs`.
