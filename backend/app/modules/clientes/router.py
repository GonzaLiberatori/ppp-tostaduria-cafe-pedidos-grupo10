from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.clientes.models import Cliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteUpdate,
    ClienteRead,
    ClienteListRead,
)
from app.modules.auth.models import Usuario


router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post(
    "/",
    response_model=ClienteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
)
def crear_cliente(
    dto: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = Cliente(**dto.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get(
    "/",
    response_model=List[ClienteListRead],
    summary="Listar clientes",
)
def listar_clientes(
    tipo: Optional[str] = Query(None, pattern="^(B2B|B2C)$"),
    search: Optional[str] = Query(None, description="Buscar por nombre, email, teléfono"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stmt = select(Cliente)
    if tipo:
        stmt = stmt.where(Cliente.tipo == tipo)
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            Cliente.nombre.ilike(search_term) |
            Cliente.email.ilike(search_term) |
            Cliente.telefono.ilike(search_term)
        )
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    clientes = db.execute(stmt).scalars().all()
    return clientes


@router.get(
    "/{cliente_id}",
    response_model=ClienteRead,
    summary="Obtener cliente por ID",
)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


@router.patch(
    "/{cliente_id}",
    response_model=ClienteRead,
    summary="Actualizar cliente",
)
def actualizar_cliente(
    cliente_id: int,
    dto: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    
    update_data = dto.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cliente, field, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar cliente",
)
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    
    db.delete(cliente)
    db.commit()