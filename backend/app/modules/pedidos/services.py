from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from app.modules.pedidos import models, schemas, crud
from app.modules.auth.models import Cuenta, UserRole


class PedidoService:
    def __init__(self, db: Session):
        self.db = db

    def _calcular_precio_kg(self, detalle: schemas.DetallePedidoCreate) -> Decimal:
        """Calcular precio por kg según tipo de café, blend, molienda y perfil de tostado"""
        precio_base = Decimal("0")
        
        if detalle.tipo_de_cafe_id:
            tipo_cafe = crud.get_tipo_de_cafe(self.db, detalle.tipo_de_cafe_id)
            if not tipo_cafe:
                raise ValueError(f"Tipo de café {detalle.tipo_de_cafe_id} no encontrado")
            precio_base = tipo_cafe.precio_por_kg_verde
        elif detalle.blend_id:
            blend = crud.get_blend(self.db, detalle.blend_id)
            if not blend:
                raise ValueError(f"Blend {detalle.blend_id} no encontrado")
            precio_base = blend.precio_por_kg_verde
        else:
            raise ValueError("Debe especificar tipo_de_cafe_id o blend_id")
        
        # Agregar valor de molienda
        if detalle.molienda_id:
            molienda = crud.get_molienda(self.db, detalle.molienda_id)
            if not molienda:
                raise ValueError(f"Molienda {detalle.molienda_id} no encontrada")
            precio_base += molienda.valor_agregado_por_kg
        
        # Agregar valor de perfil de tostado
        if detalle.perfil_de_tostado_id:
            perfil = crud.get_perfil_de_tostado(self.db, detalle.perfil_de_tostado_id)
            if not perfil:
                raise ValueError(f"Perfil de tostado {detalle.perfil_de_tostado_id} no encontrado")
            precio_base += perfil.valor_agregado_por_kg
        
        return precio_base

    def _validar_y_calcular_detalles(self, detalles: List[schemas.DetallePedidoCreate]) -> List[dict]:
        """Validar detalles y calcular subtotales"""
        detalles_calculados = []
        for detalle in detalles:
            precio_kg = self._calcular_precio_kg(detalle)
            subtotal = precio_kg * detalle.cantidad_kg
            
            detalles_calculados.append({
                "cantidad_kg": detalle.cantidad_kg,
                "subtotal": subtotal,
                "tipo_de_cafe_id": detalle.tipo_de_cafe_id,
                "blend_id": detalle.blend_id,
                "molienda_id": detalle.molienda_id,
                "perfil_de_tostado_id": detalle.perfil_de_tostado_id
            })
        return detalles_calculados

    def crear_pedido_completo(self, pedido_data: schemas.PedidoCreate, empleado_persona_id: int) -> models.Pedido:
        """Crear un pedido con sus detalles, validando stock disponible y calculando totales"""
        # Validar que el cliente existe
        cliente = crud.get_cliente(self.db, pedido_data.cliente_persona_id)
        if not cliente:
            raise ValueError("Cliente no encontrado")
        
        # Validar que el empleado existe
        empleado = crud.get_empleado(self.db, empleado_persona_id)
        if not empleado:
            raise ValueError("Empleado no encontrado")
        
        # Validar y calcular detalles
        detalles_calculados = self._validar_y_calcular_detalles(pedido_data.detalles)
        total = sum(d["subtotal"] for d in detalles_calculados)
        
        # Validar stock para cada detalle
        for i, detalle in enumerate(pedido_data.detalles):
            if detalle.tipo_de_cafe_id:
                lotes = self.db.query(models.Lote).filter(
                    models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado == "ABIERTO",
                    models.Lote.kg_disponibles >= detalle.cantidad_kg
                ).all()
                if not lotes:
                    raise ValueError(f"Stock insuficiente para tipo de café {detalle.tipo_de_cafe_id}")
            
            if detalle.blend_id:
                lotes = self.db.query(models.Lote).filter(
                    models.Lote.blend_id == detalle.blend_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado == "ABIERTO",
                    models.Lote.kg_disponibles >= detalle.cantidad_kg
                ).all()
                if not lotes:
                    raise ValueError(f"Stock insuficiente para blend {detalle.blend_id}")
        
        # Crear el pedido con total calculado
        pedido_con_total = schemas.PedidoCreate(
            fecha=pedido_data.fecha,
            metodo_de_despacho=pedido_data.metodo_de_despacho,
            estado=pedido_data.estado,
            total=total,
            cliente_persona_id=pedido_data.cliente_persona_id,
            empleado_persona_id=pedido_data.empleado_persona_id,
            detalles=[schemas.DetallePedidoCreate(**d) for d in detalles_calculados]
        )
        
        db_pedido = crud.create_pedido(self.db, pedido_con_total)
        
        # Descontar stock
        for i, detalle in enumerate(pedido_data.detalles):
            if detalle.tipo_de_cafe_id:
                lotes = self.db.query(models.Lote).filter(
                    models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado == "ABIERTO"
                ).order_by(models.Lote.fecha_vencimiento).all()
                self._descontar_stock_lotes(lotes, detalle.cantidad_kg)
            
            if detalle.blend_id:
                lotes = self.db.query(models.Lote).filter(
                    models.Lote.blend_id == detalle.blend_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado == "ABIERTO"
                ).order_by(models.Lote.fecha_vencimiento).all()
                self._descontar_stock_lotes(lotes, detalle.cantidad_kg)
        
        return db_pedido

    def _descontar_stock_lotes(self, lotes: List[models.Lote], cantidad: Decimal):
        """Descontar stock de lotes usando FIFO (primero en vencer, primero en salir)"""
        restante = cantidad
        for lote in lotes:
            if restante <= 0:
                break
            if lote.kg_disponibles >= restante:
                lote.kg_disponibles -= restante
                restante = Decimal("0")
            else:
                restante -= lote.kg_disponibles
                lote.kg_disponibles = Decimal("0")
            if lote.kg_disponibles == 0:
                lote.estado = "CERRADO"
        self.db.commit()

    def actualizar_pedido(self, pedido_id: int, pedido_update: schemas.PedidoUpdate, detalles: Optional[List[schemas.DetallePedidoCreate]] = None) -> Optional[models.Pedido]:
        """Actualizar un pedido, recalculando totales si se envían nuevos detalles"""
        db_pedido = crud.get_pedido(self.db, pedido_id)
        if not db_pedido:
            return None
        
        # Si se envían nuevos detalles, validar y recalcular
        if detalles is not None:
            # Validar que el cliente existe
            cliente = crud.get_cliente(self.db, db_pedido.cliente_persona_id)
            if not cliente:
                raise ValueError("Cliente no encontrado")
            
            # Validar y calcular nuevos detalles
            detalles_calculados = self._validar_y_calcular_detalles(detalles)
            total = sum(d["subtotal"] for d in detalles_calculados)
            
            # Validar stock para los nuevos detalles (excluyendo stock ya reservado por este pedido)
            for i, detalle in enumerate(detalles):
                if detalle.tipo_de_cafe_id:
                    # Obtener stock disponible + lo que ya tiene reservado este pedido
                    stock_reservado = self.db.query(models.DetallePedido).filter(
                        models.DetallePedido.pedido_id == pedido_id,
                        models.DetallePedido.tipo_de_cafe_id == detalle.tipo_de_cafe_id
                    ).with_entities(models.DetallePedido.cantidad_kg).scalar() or Decimal("0")
                    
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado == "ABIERTO",
                        models.Lote.kg_disponibles + stock_reservado >= detalle.cantidad_kg
                    ).all()
                    if not lotes:
                        raise ValueError(f"Stock insuficiente para tipo de café {detalle.tipo_de_cafe_id}")
                
                if detalle.blend_id:
                    stock_reservado = self.db.query(models.DetallePedido).filter(
                        models.DetallePedido.pedido_id == pedido_id,
                        models.DetallePedido.blend_id == detalle.blend_id
                    ).with_entities(models.DetallePedido.cantidad_kg).scalar() or Decimal("0")
                    
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.blend_id == detalle.blend_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado == "ABIERTO",
                        models.Lote.kg_disponibles + stock_reservado >= detalle.cantidad_kg
                    ).all()
                    if not lotes:
                        raise ValueError(f"Stock insuficiente para blend {detalle.blend_id}")
            
            # Devolver stock anterior (siempre, no solo si está PENDIENTE)
            detalles_anteriores = crud.get_detalles_by_pedido(self.db, pedido_id)
            for det in detalles_anteriores:
                if det.tipo_de_cafe_id:
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.tipo_de_cafe_id == det.tipo_de_cafe_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado.in_(["ABIERTO", "CERRADO"])
                    ).order_by(models.Lote.fecha_vencimiento.desc()).all()
                    self._devolver_stock_lotes(lotes, det.cantidad_kg)
                
                if det.blend_id:
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.blend_id == det.blend_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado.in_(["ABIERTO", "CERRADO"])
                    ).order_by(models.Lote.fecha_vencimiento.desc()).all()
                    self._devolver_stock_lotes(lotes, det.cantidad_kg)
            
            # Eliminar detalles antiguos
            self.db.query(models.DetallePedido).filter(models.DetallePedido.pedido_id == pedido_id).delete()
            
            # Crear nuevos detalles
            for d in detalles_calculados:
                db_detalle = models.DetallePedido(**d, pedido_id=pedido_id)
                self.db.add(db_detalle)
            
            # Descontar stock de los nuevos detalles
            for i, detalle in enumerate(detalles):
                if detalle.tipo_de_cafe_id:
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado == "ABIERTO"
                    ).order_by(models.Lote.fecha_vencimiento).all()
                    self._descontar_stock_lotes(lotes, detalle.cantidad_kg)
                
                if detalle.blend_id:
                    lotes = self.db.query(models.Lote).filter(
                        models.Lote.blend_id == detalle.blend_id,
                        models.Lote.tipo == "TOSTADO",
                        models.Lote.estado == "ABIERTO"
                    ).order_by(models.Lote.fecha_vencimiento).all()
                    self._descontar_stock_lotes(lotes, detalle.cantidad_kg)
            
            # Actualizar total
            db_pedido.total = total
        
        # Actualizar campos simples
        update_data = pedido_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pedido, field, value)
        
        self.db.commit()
        self.db.refresh(db_pedido)
        return db_pedido

    def _devolver_stock_lotes(self, lotes: List[models.Lote], cantidad: Decimal):
        """Devolver stock a lotes usando LIFO"""
        restante = cantidad
        for lote in lotes:
            if restante <= 0:
                break
            if lote.estado == "CERRADO" and lote.kg_disponibles == 0:
                lote.estado = "ABIERTO"
            lote.kg_disponibles += restante
            restante = Decimal("0")
        self.db.commit()

    def eliminar_pedido(self, pedido_id: int) -> bool:
        """Eliminar un pedido y devolver stock si está PENDIENTE"""
        return crud.delete_pedido(self.db, pedido_id)

    def cambiar_estado_pedido(self, pedido_id: int, nuevo_estado: str) -> Optional[models.Pedido]:
        """Cambiar estado del pedido"""
        estados_validos = ["PENDIENTE", "LISTO", "ENTREGADO"]
        if nuevo_estado not in estados_validos:
            raise ValueError(f"Estado inválido. Debe ser uno de: {estados_validos}")
        
        pedido = crud.update_pedido(self.db, pedido_id, schemas.PedidoUpdate(estado=nuevo_estado))
        return pedido

    def obtener_pedidos_cliente(self, cliente_persona_id: int) -> List[models.Pedido]:
        return crud.get_pedidos_by_cliente_with_info(self.db, cliente_persona_id)

    def obtener_pedidos_pendientes(self) -> List[models.Pedido]:
        from sqlalchemy.orm import joinedload
        return self.db.query(models.Pedido).options(
            joinedload(models.Pedido.cliente).joinedload(models.Cliente.persona)
        ).filter(models.Pedido.estado == "PENDIENTE").all()

    def obtener_pedidos_listos(self) -> List[models.Pedido]:
        from sqlalchemy.orm import joinedload
        return self.db.query(models.Pedido).options(
            joinedload(models.Pedido.cliente).joinedload(models.Cliente.persona)
        ).filter(models.Pedido.estado == "LISTO").all()

    def obtener_todos_pedidos(self, skip: int = 0, limit: int = 100) -> List[models.Pedido]:
        return crud.get_pedidos_with_clientes(self.db, skip, limit)

    def obtener_pedido_por_id(self, pedido_id: int) -> Optional[models.Pedido]:
        return crud.get_pedido_with_cliente(self.db, pedido_id)


class StockService:
    def __init__(self, db: Session):
        self.db = db

    def obtener_stock_disponible(self) -> List[models.Lote]:
        return crud.get_lotes_disponibles(self.db)

    def obtener_stock_por_tipo_cafe(self, tipo_de_cafe_id: int) -> List[models.Lote]:
        return self.db.query(models.Lote).filter(
            models.Lote.tipo_de_cafe_id == tipo_de_cafe_id,
            models.Lote.tipo == "TOSTADO",
            models.Lote.estado == "ABIERTO",
            models.Lote.kg_disponibles > 0
        ).all()

    def obtener_stock_por_blend(self, blend_id: int) -> List[models.Lote]:
        return self.db.query(models.Lote).filter(
            models.Lote.blend_id == blend_id,
            models.Lote.tipo == "TOSTADO",
            models.Lote.estado == "ABIERTO",
            models.Lote.kg_disponibles > 0
        ).all()

    def total_kg_disponibles_tipo_cafe(self, tipo_de_cafe_id: int) -> Decimal:
        lotes = self.obtener_stock_por_tipo_cafe(tipo_de_cafe_id)
        return sum(l.kg_disponibles for l in lotes)

    def total_kg_disponibles_blend(self, blend_id: int) -> Decimal:
        lotes = self.obtener_stock_por_blend(blend_id)
        return sum(l.kg_disponibles for l in lotes)


class CatalogoService:
    def __init__(self, db: Session):
        self.db = db

    # Pais
    def crear_pais(self, pais: schemas.PaisCreate) -> models.Pais:
        return crud.create_pais(self.db, pais)

    def listar_paises(self) -> List[models.Pais]:
        return crud.get_paises(self.db)

    # Region
    def crear_region(self, region: schemas.RegionCreate) -> models.Region:
        return crud.create_region(self.db, region)

    def listar_regiones(self) -> List[models.Region]:
        return crud.get_regiones(self.db)

    # Variedad
    def crear_variedad(self, variedad: schemas.VariedadCreate) -> models.Variedad:
        return crud.create_variedad(self.db, variedad)

    def listar_variedades(self) -> List[models.Variedad]:
        return crud.get_variedades(self.db)

    # TipoDeCafe
    def crear_tipo_cafe(self, tipo: schemas.TipoDeCafeCreate) -> models.TipoDeCafe:
        return crud.create_tipo_de_cafe(self.db, tipo)

    def listar_tipos_cafe(self) -> List[models.TipoDeCafe]:
        return crud.get_tipos_de_cafe(self.db)

    # Blend
    def crear_blend(self, blend: schemas.BlendCreate) -> models.Blend:
        return crud.create_blend(self.db, blend)

    def listar_blends(self) -> List[models.Blend]:
        return crud.get_blends(self.db)

    # Molienda
    def crear_molienda(self, molienda: schemas.MoliendaCreate) -> models.Molienda:
        return crud.create_molienda(self.db, molienda)

    def listar_moliendas(self) -> List[models.Molienda]:
        return crud.get_moliendas(self.db)

    # PerfilDeTostado
    def crear_perfil_tostado(self, perfil: schemas.PerfilDeTostadoCreate) -> models.PerfilDeTostado:
        return crud.create_perfil_de_tostado(self.db, perfil)

    def listar_perfiles_tostado(self) -> List[models.PerfilDeTostado]:
        return crud.get_perfiles_de_tostado(self.db)

    # OrdenTueste
    def crear_orden_tueste(self, orden: schemas.OrdenTuesteCreate) -> models.OrdenTueste:
        return crud.create_orden_tueste(self.db, orden)

    def listar_ordenes_tueste(self) -> List[models.OrdenTueste]:
        return crud.get_ordenes_tueste(self.db)

    # Lote
    def crear_lote(self, lote: schemas.LoteCreate) -> models.Lote:
        return crud.create_lote(self.db, lote)

    def listar_lotes(self) -> List[models.Lote]:
        return crud.get_lotes(self.db)