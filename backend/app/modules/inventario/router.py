from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, case

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.inventario.models import Stock, Bolsa
from app.modules.inventario.schemas import (
    StockCreate,
    StockUpdate,
    StockRead,
    StockListRead,
    BolsaCreate,
    BolsaRead,
)
from app.modules.auth.models import Usuario


router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.post(
    "/",
    response_model=StockRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear stock (café verde o tostado)",
)
def crear_stock(
    dto: StockCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stock = Stock(**dto.model_dump())
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


@router.get(
    "/",
    response_model=List[StockListRead],
    summary="Listar stock con totales",
)
def listar_stock(
    tipo: Optional[str] = Query(None, pattern="^(verde|tostado)$"),
    search: Optional[str] = Query(None, description="Buscar por variedad, origen, lote"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Subquery para agregados de bolsas
    bolsas_agg = (
        select(
            Bolsa.stock_id,
            func.count(Bolsa.id).label("total_bolsas"),
            func.coalesce(func.sum(Bolsa.kilos), 0).label("total_kilos"),
        )
        .group_by(Bolsa.stock_id)
        .subquery()
    )
    
    stmt = (
        select(
            Stock,
            bolsas_agg.c.total_bolsas,
            bolsas_agg.c.total_kilos,
        )
        .outerjoin(bolsas_agg, Stock.id == bolsas_agg.c.stock_id)
    )
    
    if tipo:
        stmt = stmt.where(Stock.tipo == tipo)
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            Stock.variedad.ilike(search_term) |
            Stock.origen.ilike(search_term) |
            Stock.lote_principal.ilike(search_term)
        )
    
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    results = db.execute(stmt).all()
    
    # Construir respuesta manualmente para incluir agregados
    response = []
    for stock, total_bolsas, total_kilos in results:
        response.append(StockListRead(
            id=stock.id,
            tipo=stock.tipo,
            variedad=stock.variedad,
            origen=stock.origen,
            precio_kg=stock.precio_kg,
            lote_principal=stock.lote_principal,
            total_bolsas=total_bolsas or 0,
            total_kilos=total_kilos or 0,
        ))
    
    return response


@router.get(
    "/{stock_id}",
    response_model=StockRead,
    summary="Obtener stock con bolsas",
)
def obtener_stock(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stmt = select(Stock).options(selectinload(Stock.bolsas)).where(Stock.id == stock_id)
    stock = db.execute(stmt).scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock no encontrado")
    
    return stock


@router.patch(
    "/{stock_id}",
    response_model=StockRead,
    summary="Actualizar stock",
)
def actualizar_stock(
    stock_id: int,
    dto: StockUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stock = db.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock no encontrado")
    
    update_data = dto.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)
    
    db.commit()
    db.refresh(stock)
    return stock


@router.delete(
    "/{stock_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar stock",
)
def eliminar_stock(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stock = db.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock no encontrado")
    
    db.delete(stock)
    db.commit()


# Bolsas endpoints
@router.post(
    "/{stock_id}/bolsas",
    response_model=BolsaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar bolsa a stock",
)
def agregar_bolsa(
    stock_id: int,
    dto: BolsaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    stock = db.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock no encontrado")
    
    # Generar ID único para la bolsa
    from uuid import uuid4
    bolsa_id = f"b{uuid4().hex[:8]}"
    
    bolsa = Bolsa(
        id=bolsa_id,
        stock_id=stock_id,
        **dto.model_dump()
    )
    db.add(bolsa)
    db.commit()
    db.refresh(bolsa)
    return bolsa