from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from app.modules.pedidos import models, schemas


# Pais
def get_pais(db: Session, pais_id: int) -> Optional[models.Pais]:
    return db.query(models.Pais).filter(models.Pais.id == pais_id).first()


def get_paises(db: Session, skip: int = 0, limit: int = 100) -> List[models.Pais]:
    return db.query(models.Pais).offset(skip).limit(limit).all()


def create_pais(db: Session, pais: schemas.PaisCreate) -> models.Pais:
    db_pais = models.Pais(**pais.model_dump())
    db.add(db_pais)
    db.commit()
    db.refresh(db_pais)
    return db_pais


# Region
def get_region(db: Session, region_id: int) -> Optional[models.Region]:
    return db.query(models.Region).filter(models.Region.id == region_id).first()


def get_regiones(db: Session, skip: int = 0, limit: int = 100) -> List[models.Region]:
    return db.query(models.Region).offset(skip).limit(limit).all()


def create_region(db: Session, region: schemas.RegionCreate) -> models.Region:
    db_region = models.Region(**region.model_dump())
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region


# Variedad
def get_variedad(db: Session, variedad_id: int) -> Optional[models.Variedad]:
    return db.query(models.Variedad).filter(models.Variedad.id == variedad_id).first()


def get_variedades(db: Session, skip: int = 0, limit: int = 100) -> List[models.Variedad]:
    return db.query(models.Variedad).offset(skip).limit(limit).all()


def create_variedad(db: Session, variedad: schemas.VariedadCreate) -> models.Variedad:
    db_variedad = models.Variedad(**variedad.model_dump())
    db.add(db_variedad)
    db.commit()
    db.refresh(db_variedad)
    return db_variedad


# TipoDeCafe
def get_tipo_de_cafe(db: Session, tipo_id: int) -> Optional[models.TipoDeCafe]:
    return db.query(models.TipoDeCafe).filter(models.TipoDeCafe.id == tipo_id).first()


def get_tipos_de_cafe(db: Session, skip: int = 0, limit: int = 100) -> List[models.TipoDeCafe]:
    return db.query(models.TipoDeCafe).offset(skip).limit(limit).all()


def create_tipo_de_cafe(db: Session, tipo: schemas.TipoDeCafeCreate) -> models.TipoDeCafe:
    db_tipo = models.TipoDeCafe(**tipo.model_dump())
    db.add(db_tipo)
    db.commit()
    db.refresh(db_tipo)
    return db_tipo


# Blend
def get_blend(db: Session, blend_id: int) -> Optional[models.Blend]:
    return db.query(models.Blend).filter(models.Blend.id == blend_id).first()


def get_blends(db: Session, skip: int = 0, limit: int = 100) -> List[models.Blend]:
    return db.query(models.Blend).offset(skip).limit(limit).all()


def create_blend(db: Session, blend: schemas.BlendCreate) -> models.Blend:
    db_blend = models.Blend(**blend.model_dump())
    db.add(db_blend)
    db.commit()
    db.refresh(db_blend)
    return db_blend


# Molienda
def get_molienda(db: Session, molienda_id: int) -> Optional[models.Molienda]:
    return db.query(models.Molienda).filter(models.Molienda.id == molienda_id).first()


def get_moliendas(db: Session, skip: int = 0, limit: int = 100) -> List[models.Molienda]:
    return db.query(models.Molienda).offset(skip).limit(limit).all()


def create_molienda(db: Session, molienda: schemas.MoliendaCreate) -> models.Molienda:
    db_molienda = models.Molienda(**molienda.model_dump())
    db.add(db_molienda)
    db.commit()
    db.refresh(db_molienda)
    return db_molienda


# PerfilDeTostado
def get_perfil_de_tostado(db: Session, perfil_id: int) -> Optional[models.PerfilDeTostado]:
    return db.query(models.PerfilDeTostado).filter(models.PerfilDeTostado.id == perfil_id).first()


def get_perfiles_de_tostado(db: Session, skip: int = 0, limit: int = 100) -> List[models.PerfilDeTostado]:
    return db.query(models.PerfilDeTostado).offset(skip).limit(limit).all()


def create_perfil_de_tostado(db: Session, perfil: schemas.PerfilDeTostadoCreate) -> models.PerfilDeTostado:
    db_perfil = models.PerfilDeTostado(**perfil.model_dump())
    db.add(db_perfil)
    db.commit()
    db.refresh(db_perfil)
    return db_perfil


# OrdenTueste
def get_orden_tueste(db: Session, orden_id: int) -> Optional[models.OrdenTueste]:
    return db.query(models.OrdenTueste).filter(models.OrdenTueste.id == orden_id).first()


def get_ordenes_tueste(db: Session, skip: int = 0, limit: int = 100) -> List[models.OrdenTueste]:
    return db.query(models.OrdenTueste).offset(skip).limit(limit).all()


def create_orden_tueste(db: Session, orden: schemas.OrdenTuesteCreate) -> models.OrdenTueste:
    db_orden = models.OrdenTueste(**orden.model_dump())
    db.add(db_orden)
    db.commit()
    db.refresh(db_orden)
    return db_orden


# Lote
def get_lote(db: Session, lote_id: int) -> Optional[models.Lote]:
    return db.query(models.Lote).filter(models.Lote.id == lote_id).first()


def get_lotes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Lote]:
    return db.query(models.Lote).offset(skip).limit(limit).all()


def get_lotes_disponibles(db: Session, tipo: str = "TOSTADO") -> List[models.Lote]:
    return db.query(models.Lote).filter(
        models.Lote.tipo == tipo,
        models.Lote.estado == "ABIERTO",
        models.Lote.kg_disponibles > 0
    ).all()


def create_lote(db: Session, lote: schemas.LoteCreate) -> models.Lote:
    db_lote = models.Lote(**lote.model_dump())
    db.add(db_lote)
    db.commit()
    db.refresh(db_lote)
    return db_lote


def update_lote_stock(db: Session, lote_id: int, kg_usados: Decimal) -> Optional[models.Lote]:
    lote = get_lote(db, lote_id)
    if lote and lote.kg_disponibles >= kg_usados:
        lote.kg_disponibles -= kg_usados
        db.commit()
        db.refresh(lote)
    return lote


# Persona
def get_persona(db: Session, persona_id: int) -> Optional[models.Persona]:
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def get_persona_by_cuit(db: Session, cuit: str) -> Optional[models.Persona]:
    return db.query(models.Persona).filter(models.Persona.CUIT == cuit).first()


def get_persona_by_telefono(db: Session, telefono: str) -> Optional[models.Persona]:
    return db.query(models.Persona).filter(models.Persona.telefono == telefono).first()


def get_personas(db: Session, skip: int = 0, limit: int = 100) -> List[models.Persona]:
    return db.query(models.Persona).offset(skip).limit(limit).all()


def create_persona(db: Session, persona: schemas.PersonaCreate) -> models.Persona:
    db_persona = models.Persona(**persona.model_dump())
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


# Cliente
def get_cliente(db: Session, persona_id: int) -> Optional[models.Cliente]:
    return db.query(models.Cliente).filter(models.Cliente.persona_id == persona_id).first()


def get_clientes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Cliente]:
    return db.query(models.Cliente).offset(skip).limit(limit).all()


def create_cliente(db: Session, cliente: schemas.ClienteCreate) -> models.Cliente:
    db_cliente = models.Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


# Empleado
def get_empleado(db: Session, persona_id: int) -> Optional[models.Empleado]:
    return db.query(models.Empleado).filter(models.Empleado.persona_id == persona_id).first()


def get_empleados(db: Session, skip: int = 0, limit: int = 100) -> List[models.Empleado]:
    return db.query(models.Empleado).offset(skip).limit(limit).all()


def create_empleado(db: Session, empleado: schemas.EmpleadoCreate) -> models.Empleado:
    db_empleado = models.Empleado(**empleado.model_dump())
    db.add(db_empleado)
    db.commit()
    db.refresh(db_empleado)
    return db_empleado


# Pedido
def get_pedido(db: Session, pedido_id: int) -> Optional[models.Pedido]:
    return db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()


def get_pedido_with_cliente(db: Session, pedido_id: int) -> Optional[models.Pedido]:
    from sqlalchemy.orm import joinedload
    return db.query(models.Pedido).options(
        joinedload(models.Pedido.cliente).joinedload(models.Cliente.persona)
    ).filter(models.Pedido.id == pedido_id).first()


def get_pedidos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Pedido]:
    return db.query(models.Pedido).offset(skip).limit(limit).all()


def get_pedidos_with_clientes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Pedido]:
    from sqlalchemy.orm import joinedload
    return db.query(models.Pedido).options(
        joinedload(models.Pedido.cliente).joinedload(models.Cliente.persona)
    ).offset(skip).limit(limit).all()


def get_pedidos_by_cliente(db: Session, cliente_persona_id: int) -> List[models.Pedido]:
    return db.query(models.Pedido).filter(models.Pedido.cliente_persona_id == cliente_persona_id).all()


def get_pedidos_by_cliente_with_info(db: Session, cliente_persona_id: int) -> List[models.Pedido]:
    from sqlalchemy.orm import joinedload
    return db.query(models.Pedido).options(
        joinedload(models.Pedido.cliente).joinedload(models.Cliente.persona)
    ).filter(models.Pedido.cliente_persona_id == cliente_persona_id).all()


def get_pedidos_by_estado(db: Session, estado: str) -> List[models.Pedido]:
    return db.query(models.Pedido).filter(models.Pedido.estado == estado).all()


def create_pedido(db: Session, pedido: schemas.PedidoCreate) -> models.Pedido:
    detalles_data = pedido.detalles
    pedido_data = pedido.model_dump(exclude={"detalles"})
    
    db_pedido = models.Pedido(**pedido_data)
    db.add(db_pedido)
    db.flush()
    
    for detalle_data in detalles_data:
        db_detalle = models.DetallePedido(**detalle_data.model_dump(), pedido_id=db_pedido.id)
        db.add(db_detalle)
    
    db.commit()
    db.refresh(db_pedido)
    return db_pedido


def update_pedido(db: Session, pedido_id: int, pedido_update: schemas.PedidoUpdate) -> Optional[models.Pedido]:
    db_pedido = get_pedido(db, pedido_id)
    if db_pedido:
        update_data = pedido_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pedido, field, value)
        db.commit()
        db.refresh(db_pedido)
    return db_pedido


def delete_pedido(db: Session, pedido_id: int) -> bool:
    """Eliminar un pedido y devolver stock si está PENDIENTE"""
    db_pedido = get_pedido(db, pedido_id)
    if not db_pedido:
        return False
    
    # Si el pedido está PENDIENTE, devolver stock a los lotes
    if db_pedido.estado == "PENDIENTE":
        detalles = get_detalles_by_pedido(db, pedido_id)
        for detalle in detalles:
            if detalle.tipo_de_cafe_id:
                lotes = db.query(models.Lote).filter(
                    models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado.in_(["ABIERTO", "CERRADO"])
                ).order_by(models.Lote.fecha_vencimiento.desc()).all()
                _devolver_stock_lotes(lotes, detalle.cantidad_kg)
            
            if detalle.blend_id:
                lotes = db.query(models.Lote).filter(
                    models.Lote.blend_id == detalle.blend_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado.in_(["ABIERTO", "CERRADO"])
                ).order_by(models.Lote.fecha_vencimiento.desc()).all()
                _devolver_stock_lotes(lotes, detalle.cantidad_kg)
    
    # Eliminar detalles primero
    db.query(models.DetallePedido).filter(models.DetallePedido.pedido_id == pedido_id).delete()
    
    # Eliminar pedido
    db.delete(db_pedido)
    db.commit()
    return True


def _devolver_stock_lotes(lotes: List[models.Lote], cantidad: Decimal):
    """Devolver stock a lotes usando LIFO (último en vencer, primero en volver)"""
    restante = cantidad
    for lote in lotes:
        if restante <= 0:
            break
        # Si el lote estaba CERRADO y tenía 0 disponible, reabrirlo
        if lote.estado == "CERRADO" and lote.kg_disponibles == 0:
            lote.estado = "ABIERTO"
        lote.kg_disponibles += restante
        restante = Decimal("0")
    if lotes:
        from sqlalchemy.orm import Session
        # Get session from the first lote
        session = Session.object_session(lotes[0])
        if session:
            session.commit()


# DetallePedido
def get_detalle_pedido(db: Session, detalle_id: int) -> Optional[models.DetallePedido]:
    return db.query(models.DetallePedido).filter(models.DetallePedido.id == detalle_id).first()


def get_detalles_by_pedido(db: Session, pedido_id: int) -> List[models.DetallePedido]:
    return db.query(models.DetallePedido).filter(models.DetallePedido.pedido_id == pedido_id).all()


# Pago
def get_pago(db: Session, pago_id: int) -> Optional[models.Pago]:
    return db.query(models.Pago).filter(models.Pago.id == pago_id).first()


def get_pagos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Pago]:
    return db.query(models.Pago).offset(skip).limit(limit).all()


def create_pago(db: Session, pago: schemas.PagoCreate) -> models.Pago:
    db_pago = models.Pago(**pago.model_dump())
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago


# Venta
def get_venta(db: Session, venta_id: int) -> Optional[models.Venta]:
    return db.query(models.Venta).filter(models.Venta.id == venta_id).first()


def get_ventas(db: Session, skip: int = 0, limit: int = 100) -> List[models.Venta]:
    return db.query(models.Venta).offset(skip).limit(limit).all()


def create_venta(db: Session, venta: schemas.VentaCreate) -> models.Venta:
    db_venta = models.Venta(**venta.model_dump())
    db.add(db_venta)
    db.commit()
    db.refresh(db_venta)
    return db_venta