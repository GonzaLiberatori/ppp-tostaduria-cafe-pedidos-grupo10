# Diseño Técnico: Módulo de Pedidos (Demo)

## Contexto
Backend FastAPI + SQLAlchemy + SQLite para demo. Arquitectura vertical slice: cada módulo tiene router, schemas, crud, services, models.

## Base de Datos
- **SQLite** (`sqlite:///./demo.db` para desarrollo, `sqlite:///:memory:` para tests)
- **Alembic** para migraciones
- **Tablas nuevas**:
  - `pedido_estado_historial` - Auditoría de cambios de estado
  - `pedido` - Agregar `idempotency_key` (UNIQUE)

## Modelos (SQLAlchemy)

### Pedido
```python
class Pedido(Base):
    __tablename__ = "pedido"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, nullable=False)
    metodo_de_despacho = Column(String(50), nullable=False)
    estado = Column(Enum(EstadoPedido), nullable=False, default=EstadoPedido.PENDIENTE)
    total = Column(Numeric(10, 2), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    observaciones = Column(Text, nullable=True)
    medio_contacto = Column(String(50), nullable=True)
    cliente_persona_id = Column(Integer, ForeignKey("cliente.persona_id"), nullable=False)
    empleado_persona_id = Column(Integer, ForeignKey("empleado.persona_id"), nullable=False)
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="pedidos")
    empleado = relationship("Empleado", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")
    historial_estados = relationship("PedidoEstadoHistorial", back_populates="pedido", cascade="all, delete-orphan")
```

### DetallePedido (LineaPedido)
```python
class DetallePedido(Base):
    __tablename__ = "detalle_pedido"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cantidad_kg = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    tipo_de_cafe_id = Column(Integer, ForeignKey("tipo_de_cafe.id"), nullable=True)
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    molienda_id = Column(Integer, ForeignKey("molienda.id"), nullable=True)
    perfil_de_tostado_id = Column(Integer, ForeignKey("perfil_de_tostado.id"), nullable=True)
    
    pedido = relationship("Pedido", back_populates="detalles")
```

### PedidoEstadoHistorial
```python
class PedidoEstadoHistorial(Base):
    __tablename__ = "pedido_estado_historial"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False, index=True)
    estado_anterior = Column(Enum(EstadoPedido), nullable=True)
    estado_nuevo = Column(Enum(EstadoPedido), nullable=False)
    usuario_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    
    pedido = relationship("Pedido", back_populates="historial_estados")
```

## Machine de Estados

```
PENDIENTE <-> LISTO <-> ENTREGADO
```

Transiciones válidas:
- PENDIENTE -> LISTO (preparación completada)
- LISTO -> PENDIENTE (cancelar preparación)
- LISTO -> ENTREGADO (entrega confirmada) - **Actualiza cuenta corriente B2B**
- ENTREGADO -> LISTO (corrección error) - **Revierte cuenta corriente B2B**

## Idempotencia
- Header `Idempotency-Key` (opcional)
- Si no se provee: `SHA256(cliente_id + sorted(items_json) + fecha_date)`
- Clave única en `pedido.idempotency_key`

## Stock FIFO
- Consumir lotes `TOSTADO` y `ABIERTO` ordenados por `fecha_vencimiento` ASC
- Retornar detalle de consumo por lote para rollback exacto

## Cuenta Corriente
- Campo `saldo_cuenta_corriente` en `Cliente`
- Campo `es_b2b` en `Cliente` (derivado de `tipo`)
- Solo actualizar en transiciones a/desde `ENTREGADO` para clientes B2B

## Endpoints REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/v1/pedidos | Crear pedido |
| GET | /api/v1/pedidos | Listar con filtros (estado, cliente, fecha) + paginación |
| GET | /api/v1/pedidos/{id} | Detalle completo (items, cliente, historial) |
| PATCH | /api/v1/pedidos/{id} | Actualizar campos editables (estado, metodo, obs) |
| PATCH | /api/v1/pedidos/{id}/estado | Transición de estado validada |
| DELETE | /api/v1/pedidos/{id} | Eliminar (solo Pendiente) |
| GET | /api/v1/pedidos/cliente/{cliente_id} | Pedidos por cliente |

## Servicios (Capa de Negocio)

### PedidoService
- `crear_pedido(dto, user_id, session)` - Valida stock, consume FIFO, calcula total, idempotencia, historial
- `cambiar_estado(pedido_id, nuevo_estado, user_id, session)` - Valida transición, efectos laterales, historial
- `eliminar_pedido(pedido_id, session)` - Solo Pendiente, rollback FIFO
- `get_pedidos_con_filtros(filtros, pagination, session)`

### StockService (inventario - mínima implementación)
- `consumir_fifo(stock_id, kilos, session)` -> (consumo_detalle, faltante)
- `restaurar_fifo(consumo_detalle, session)`

### ClienteService (clientes - mínima implementación)
- `ajustar_cuenta_corriente(cliente_id, delta, session)`
- `get_by_id_con_tipo(cliente_id, session)` -> (cliente, es_b2b)

## Transacciones
Todas las operaciones de negocio en `services.py` dentro de una sola transacción (commit/rollback automático).

## Tests
- SQLite en memoria (`sqlite:///:memory:`) en `conftest.py`
- Tests de servicios: transacciones, FIFO, idempotencia, state machine
- Tests de router: TestClient para endpoints