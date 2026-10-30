from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.gastos.models import Gasto
from app.modules.gastos.schemas import (
    GastoCreate,
    GastoUpdate,
    GastoRead,
)
from app.modules.auth.models import Usuario


router = APIRouter(prefix="/gastos", tags=["Gastos"])


@router.post(
    "/",
    response_model=GastoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear gasto",
)
def crear_gasto(
    dto: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    gasto = Gasto(**dto.model_dump())
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get(
    "/",
    response_model=List[GastoRead],
    summary="Listar gastos con filtros",
)
def listar_gastos(
    categoria: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stmt = select(Gasto)
    
    if categoria:
        stmt = stmt.where(Gasto.categoria == categoria)
    if fecha_desde:
        stmt = stmt.where(func.date(Gasto.fecha) >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(func.date(Gasto.fecha) <= fecha_hasta)
    
    # Ordenar por fecha descendente (más recientes primero)
    stmt = stmt.order_by(Gasto.fecha.desc())
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    gastos = db.execute(stmt).scalars().all()
    return gastos


@router.get(
    "/{gasto_id}",
    response_model=GastoRead,
    summary="Obtener gasto por ID",
)
def obtener_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    gasto = db.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    return gasto


@router.patch(
    "/{gasto_id}",
    response_model=GastoRead,
    summary="Actualizar gasto",
)
def actualizar_gasto(
    gasto_id: int,
    dto: GastoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    gasto = db.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    
    update_data = dto.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gasto, field, value)
    
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete(
    "/{gasto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar gasto",
)
def eliminar_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    gasto = db.get(Gasto, gasto_id)
    if not gasto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    
    db.delete(gasto)
    db.commit()