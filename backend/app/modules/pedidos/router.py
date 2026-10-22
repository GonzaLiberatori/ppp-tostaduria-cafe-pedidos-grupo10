from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.pedidos.services import PedidoService
from app.modules.pedidos.schemas import (
    PedidoCreate,
    PedidoUpdate,
    PedidoRead,
    PedidoDetailRead,
    PedidoListRead,
    EstadoPedidoEnum,
    PedidoEstadoHistorialRead,
)
from app.modules.auth.models import Usuario


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])
pedido_service = PedidoService()


@router.post(
    "/",
    response_model=PedidoDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo pedido",
    description="Crea un pedido validando stock, consumiendo FIFO y actualizando cuenta corriente B2B.",
)
def crear_pedido(
    dto: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Crea un nuevo pedido."""
    try:
        pedido = pedido_service.crear_pedido(dto, current_user.id, db)
        db.commit()
        return pedido
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno")


@router.get(
    "/",
    response_model=List[PedidoListRead],
    summary="Listar pedidos con filtros",
    description="Lista paginada de pedidos con filtros opcionales por estado, cliente, fechas y búsqueda.",
)
def listar_pedidos(
    estado: Optional[EstadoPedidoEnum] = Query(None, description="Filtrar por estado"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por ID de cliente"),
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Búsqueda por texto (cliente, contacto, observaciones)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista pedidos con filtros y paginación."""
    pedidos, total = pedido_service.get_pedidos_con_filtros(
        estado=estado,
        cliente_id=cliente_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        search=search,
        page=page,
        page_size=page_size,
        session=db,
    )
    # Agregar headers de paginación
    return pedidos


@router.get(
    "/cliente/{cliente_id}",
    response_model=List[PedidoListRead],
    summary="Pedidos por cliente",
    description="Retorna todos los pedidos de un cliente específico.",
)
def listar_pedidos_por_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Obtiene todos los pedidos de un cliente."""
    pedidos, _ = pedido_service.get_pedidos_con_filtros(
        cliente_id=cliente_id,
        page=1,
        page_size=1000,
        session=db,
    )
    return pedidos


@router.get(
    "/{pedido_id}",
    response_model=PedidoDetailRead,
    summary="Obtener detalle de pedido",
    description="Retorna el detalle completo de un pedido incluyendo items y cliente.",
)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Obtiene el detalle de un pedido."""
    pedido = pedido_service.get_pedido_detalle(pedido_id, db)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    return pedido


@router.patch(
    "/{pedido_id}",
    response_model=PedidoDetailRead,
    summary="Actualizar pedido",
    description="Actualiza campos editables: medio_contacto, observaciones. No permite cambiar items, cliente, fecha o total.",
)
def actualizar_pedido(
    pedido_id: int,
    dto: PedidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Actualiza campos editables de un pedido."""
    from app.modules.pedidos.crud import get_pedido as crud_get_pedido, update_pedido as crud_update_pedido
    
    pedido = crud_get_pedido(db, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    
    # Solo permitir actualizar campos editables
    update_data = dto.model_dump(exclude_unset=True)
    if "estado" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use el endpoint PATCH /pedidos/{id}/estado para cambiar estado"
        )
    
    try:
        pedido = crud_update_pedido(db, pedido=pedido, **update_data)
        db.commit()
        return pedido
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno")


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoDetailRead,
    summary="Cambiar estado de pedido",
    description="Cambia el estado validando transiciones permitidas. Efectos: Entregado suma a cuenta corriente B2B; reversión resta.",
)
def cambiar_estado(
    pedido_id: int,
    nuevo_estado: EstadoPedidoEnum,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Cambia el estado de un pedido."""
    try:
        pedido = pedido_service.cambiar_estado(pedido_id, nuevo_estado, current_user.id, db)
        db.commit()
        return pedido
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno")


@router.delete(
    "/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar pedido",
    description="Elimina un pedido solo si está en estado Pendiente. Revierte stock FIFO y cuenta corriente B2B.",
)
def eliminar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Elimina un pedido (solo Pendiente)."""
    try:
        pedido_service.eliminar_pedido(pedido_id, db)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno")