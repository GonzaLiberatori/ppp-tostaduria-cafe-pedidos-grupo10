from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.schemas import TokenData

from app.modules.pedidos import schemas, services


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


# Dependency para servicios
def get_pedido_service(db: Session = Depends(get_db)) -> services.PedidoService:
    return services.PedidoService(db)


def get_stock_service(db: Session = Depends(get_db)) -> services.StockService:
    return services.StockService(db)


def get_catalogo_service(db: Session = Depends(get_db)) -> services.CatalogoService:
    return services.CatalogoService(db)


def get_panel_service(db: Session = Depends(get_db)) -> services.PedidoPanelService:
    return services.PedidoPanelService(db)


# Dependency para usuario autenticado
def get_current_user_required(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    return current_user


# ==================== PEDIDOS ====================

@router.post("/", response_model=schemas.PedidoResponse, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    pedido: schemas.PedidoCreate,
    current_user: TokenData = Depends(get_current_user),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Crear un nuevo pedido con detalles y descontar stock"""
    # El empleado que crea el pedido es el usuario actual
    # Buscar el empleado por email
    from app.modules.pedidos import crud
    from app.modules.auth.models import Cuenta
    from app.modules.pedidos.models import Persona, Empleado
    
    cuenta = service.db.query(Cuenta).filter(Cuenta.correo == current_user.email).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    persona = service.db.query(Persona).filter(Persona.cuenta_id == cuenta.id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    empleado = service.db.query(Empleado).filter(Empleado.persona_id == persona.id).first()
    if not empleado:
        raise HTTPException(status_code=403, detail="El usuario no es un empleado")
    
    try:
        db_pedido = service.crear_pedido_completo(pedido, empleado.persona_id)
        return db_pedido
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.PedidoListRead])
def listar_pedidos(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    cliente_persona_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    q: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Listar todos los pedidos con filtros y paginación"""
    from app.modules.pedidos import crud
    pedidos = crud.get_pedidos_con_filtros(
        service.db, skip, limit, estado, None, None, None, None
    )
    return pedidos


# ==================== PANEL ====================
# Estas rutas van antes de "/{pedido_id}" para que "panel" no se interprete
# como un id numérico.

@router.get("/panel", response_model=List[schemas.PedidoPanelRead])
def listar_pedidos_panel(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoPanelService = Depends(get_panel_service),
):
    """Lista los pedidos con el contrato plano que consume el panel."""
    return service.listar()


@router.get("/panel/cliente/{cliente_id}", response_model=List[schemas.PedidoPanelRead])
def listar_pedidos_panel_cliente(
    cliente_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoPanelService = Depends(get_panel_service),
):
    """Lista los pedidos de un cliente con el contrato plano."""
    return service.listar_por_cliente(cliente_id)


@router.post(
    "/panel",
    response_model=schemas.PedidoPanelRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido_panel(
    datos: schemas.PedidoPanelCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoPanelService = Depends(get_panel_service),
):
    """Crea un pedido desde el panel, descontando stock."""
    try:
        empleado_id = service.resolver_empleado_actual(current_user.email)
        return service.crear(datos, empleado_persona_id=empleado_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/panel/{pedido_id}", response_model=schemas.PedidoPanelRead)
def actualizar_pedido_panel(
    pedido_id: int,
    datos: schemas.PedidoPanelUpdate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoPanelService = Depends(get_panel_service),
):
    """Actualiza un pedido desde el panel."""
    try:
        return service.actualizar(pedido_id, datos)
    except services.PedidoNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/panel/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pedido_panel(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoPanelService = Depends(get_panel_service),
):
    """Elimina un pedido pendiente desde el panel."""
    try:
        service.eliminar(pedido_id)
    except services.PedidoNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pedido_id}", response_model=schemas.PedidoDetailRead)
def obtener_pedido(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Obtener un pedido por ID con items, cliente e historial"""
    pedido = service.obtener_pedido_por_id(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido


@router.patch("/{pedido_id}/estado", response_model=schemas.PedidoResponse)
def cambiar_estado_pedido(
    pedido_id: int,
    estado: str,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Cambiar estado del pedido (PENDIENTE, LISTO, ENTREGADO)"""
    try:
        # Obtener usuario_id del usuario autenticado
        from app.modules.auth.models import Cuenta
        from app.modules.pedidos.models import Persona
        cuenta = service.db.query(Cuenta).filter(Cuenta.correo == current_user.email).first()
        persona = service.db.query(Persona).filter(Persona.cuenta_id == cuenta.id).first() if cuenta else None
        usuario_id = persona.id if persona else None
        
        pedido = service.cambiar_estado_pedido(pedido_id, estado, usuario_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return pedido
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{pedido_id}", response_model=schemas.PedidoDetailRead)
def actualizar_pedido(
    pedido_id: int,
    pedido_update: schemas.PedidoUpdate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Actualizar un pedido (estado, método de despacho, observaciones). No permite cambiar detalles ni totales."""
    try:
        from app.modules.auth.models import Cuenta
        from app.modules.pedidos.models import Persona
        cuenta = service.db.query(Cuenta).filter(Cuenta.correo == current_user.email).first()
        persona = service.db.query(Persona).filter(Persona.cuenta_id == cuenta.id).first() if cuenta else None
        usuario_id = persona.id if persona else None
        
        pedido = service.actualizar_pedido(pedido_id, pedido_update, detalles=None, usuario_id=usuario_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return pedido
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{pedido_id}/con-detalles", response_model=schemas.PedidoDetailRead)
def actualizar_pedido_con_detalles(
    pedido_id: int,
    data: schemas.PedidoUpdateConDetalles,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Actualizar un pedido con nuevos detalles (recalcula totales y ajusta stock)"""
    try:
        from app.modules.auth.models import Cuenta
        from app.modules.pedidos.models import Persona
        cuenta = service.db.query(Cuenta).filter(Cuenta.correo == current_user.email).first()
        persona = service.db.query(Persona).filter(Persona.cuenta_id == cuenta.id).first() if cuenta else None
        usuario_id = persona.id if persona else None
        
        update_data = {}
        if data.estado is not None:
            update_data['estado'] = data.estado
        if data.metodo_de_despacho is not None:
            update_data['metodo_de_despacho'] = data.metodo_de_despacho
        if data.observaciones is not None:
            update_data['observaciones'] = data.observaciones
        if data.medio_contacto is not None:
            update_data['medio_contacto'] = data.medio_contacto
        pedido_update = schemas.PedidoUpdate(**update_data)
        pedido = service.actualizar_pedido(pedido_id, pedido_update, detalles=data.detalles, usuario_id=usuario_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return pedido
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pedido(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Eliminar un pedido. Si está PENDIENTE, devuelve el stock a los lotes."""
    try:
        resultado = service.eliminar_pedido(pedido_id)
        if not resultado:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cliente/{cliente_persona_id}", response_model=List[schemas.PedidoResponse])
def obtener_pedidos_cliente(
    cliente_persona_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Obtener pedidos de un cliente"""
    return service.obtener_pedidos_cliente(cliente_persona_id)


@router.get("/pendientes/", response_model=List[schemas.PedidoResponse])
def obtener_pedidos_pendientes(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Obtener pedidos pendientes"""
    return service.obtener_pedidos_pendientes()


@router.get("/listos/", response_model=List[schemas.PedidoResponse])
def obtener_pedidos_listos(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.PedidoService = Depends(get_pedido_service)
):
    """Obtener pedidos listos para entrega"""
    return service.obtener_pedidos_listos()


# ==================== STOCK ====================

@router.get("/stock/disponible", response_model=List[schemas.LoteResponse])
def obtener_stock_disponible(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.StockService = Depends(get_stock_service)
):
    """Obtener todo el stock disponible (café tostado)"""
    return service.obtener_stock_disponible()


@router.get("/stock/tipo-cafe/{tipo_de_cafe_id}", response_model=List[schemas.LoteResponse])
def obtener_stock_tipo_cafe(
    tipo_de_cafe_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.StockService = Depends(get_stock_service)
):
    """Obtener stock disponible para un tipo de café específico"""
    return service.obtener_stock_por_tipo_cafe(tipo_de_cafe_id)


@router.get("/stock/blend/{blend_id}", response_model=List[schemas.LoteResponse])
def obtener_stock_blend(
    blend_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.StockService = Depends(get_stock_service)
):
    """Obtener stock disponible para un blend específico"""
    return service.obtener_stock_por_blend(blend_id)


@router.get("/stock/tipo-cafe/{tipo_de_cafe_id}/total-kg")
def total_kg_tipo_cafe(
    tipo_de_cafe_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.StockService = Depends(get_stock_service)
):
    """Obtener total de kg disponibles para un tipo de café"""
    total = service.total_kg_disponibles_tipo_cafe(tipo_de_cafe_id)
    return {"tipo_de_cafe_id": tipo_de_cafe_id, "total_kg_disponibles": total}


@router.get("/stock/blend/{blend_id}/total-kg")
def total_kg_blend(
    blend_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.StockService = Depends(get_stock_service)
):
    """Obtener total de kg disponibles para un blend"""
    total = service.total_kg_disponibles_blend(blend_id)
    return {"blend_id": blend_id, "total_kg_disponibles": total}


# ==================== CATÁLOGO ====================

# Tipo de Café
@router.post("/catalogo/tipos-cafe", response_model=schemas.TipoDeCafeResponse, status_code=status.HTTP_201_CREATED)
def crear_tipo_cafe(
    tipo: schemas.TipoDeCafeCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_tipo_cafe(tipo)


@router.get("/catalogo/tipos-cafe", response_model=List[schemas.TipoDeCafeResponse])
def listar_tipos_cafe(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_tipos_cafe()


@router.get("/catalogo/tipos-cafe/{tipo_id}", response_model=schemas.TipoDeCafeResponse)
def obtener_tipo_cafe(
    tipo_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    tipo = crud.get_tipo_de_cafe(service.db, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de café no encontrado")
    return tipo


# Blend
@router.post("/catalogo/blends", response_model=schemas.BlendResponse, status_code=status.HTTP_201_CREATED)
def crear_blend(
    blend: schemas.BlendCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_blend(blend)


@router.get("/catalogo/blends", response_model=List[schemas.BlendResponse])
def listar_blends(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_blends()


@router.get("/catalogo/blends/{blend_id}", response_model=schemas.BlendResponse)
def obtener_blend(
    blend_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    blend = crud.get_blend(service.db, blend_id)
    if not blend:
        raise HTTPException(status_code=404, detail="Blend no encontrado")
    return blend


# Molienda
@router.post("/catalogo/moliendas", response_model=schemas.MoliendaResponse, status_code=status.HTTP_201_CREATED)
def crear_molienda(
    molienda: schemas.MoliendaCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_molienda(molienda)


@router.get("/catalogo/moliendas", response_model=List[schemas.MoliendaResponse])
def listar_moliendas(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_moliendas()


@router.get("/catalogo/moliendas/{molienda_id}", response_model=schemas.MoliendaResponse)
def obtener_molienda(
    molienda_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    molienda = crud.get_molienda(service.db, molienda_id)
    if not molienda:
        raise HTTPException(status_code=404, detail="Molienda no encontrada")
    return molienda


# Perfil de Tostado
@router.post("/catalogo/perfiles-tostado", response_model=schemas.PerfilDeTostadoResponse, status_code=status.HTTP_201_CREATED)
def crear_perfil_tostado(
    perfil: schemas.PerfilDeTostadoCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_perfil_tostado(perfil)


@router.get("/catalogo/perfiles-tostado", response_model=List[schemas.PerfilDeTostadoResponse])
def listar_perfiles_tostado(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_perfiles_tostado()


@router.get("/catalogo/perfiles-tostado/{perfil_id}", response_model=schemas.PerfilDeTostadoResponse)
def obtener_perfil_tostado(
    perfil_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    perfil = crud.get_perfil_de_tostado(service.db, perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil de tostado no encontrado")
    return perfil


# Orden de Tueste
@router.post("/catalogo/ordenes-tueste", response_model=schemas.OrdenTuesteResponse, status_code=status.HTTP_201_CREATED)
def crear_orden_tueste(
    orden: schemas.OrdenTuesteCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_orden_tueste(orden)


@router.get("/catalogo/ordenes-tueste", response_model=List[schemas.OrdenTuesteResponse])
def listar_ordenes_tueste(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_ordenes_tueste()


@router.get("/catalogo/ordenes-tueste/{orden_id}", response_model=schemas.OrdenTuesteResponse)
def obtener_orden_tueste(
    orden_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    orden = crud.get_orden_tueste(service.db, orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de tueste no encontrada")
    return orden


# Lote
@router.post("/catalogo/lotes", response_model=schemas.LoteResponse, status_code=status.HTTP_201_CREATED)
def crear_lote(
    lote: schemas.LoteCreate,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.crear_lote(lote)


@router.get("/catalogo/lotes", response_model=List[schemas.LoteResponse])
def listar_lotes(
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    return service.listar_lotes()


@router.get("/catalogo/lotes/{lote_id}", response_model=schemas.LoteResponse)
def obtener_lote(
    lote_id: int,
    current_user: TokenData = Depends(get_current_user_required),
    service: services.CatalogoService = Depends(get_catalogo_service)
):
    from app.modules.pedidos import crud
    lote = crud.get_lote(service.db, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote