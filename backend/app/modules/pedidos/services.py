from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import hashlib
import json
import uuid

from app.modules.pedidos import models, schemas, crud
from app.modules.auth.models import Cuenta


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

    def _generar_idempotency_key(self, cliente_id: int, detalles: List[schemas.DetallePedidoCreate], fecha: datetime) -> str:
        """Generar clave de idempotencia: SHA256(cliente_id + items_sorted_json + fecha_date)"""
        items_json = json.dumps([
            {
                "tipo_de_cafe_id": d.tipo_de_cafe_id,
                "blend_id": d.blend_id,
                "molienda_id": d.molienda_id,
                "perfil_de_tostado_id": d.perfil_de_tostado_id,
                "cantidad_kg": str(d.cantidad_kg)
            }
            for d in sorted(detalles, key=lambda x: (x.tipo_de_cafe_id or 0, x.blend_id or 0))
        ], sort_keys=True)
        
        fecha_str = fecha.date().isoformat()
        raw = f"{cliente_id}|{items_json}|{fecha_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _consumir_stock_fifo(self, tipo_de_cafe_id: Optional[int], blend_id: Optional[int], cantidad: Decimal) -> List[dict]:
        """Consumir stock FIFO y retornar detalle de consumo para rollback.

        Se consideran tanto los lotes abiertos como los cerrados: una bolsa
        sellada se abre en el momento de descontar, porque el panel de stock
        nace con todas las bolsas cerradas.
        """
        if tipo_de_cafe_id:
            lotes = self.db.query(models.Lote).filter(
                models.Lote.tipo_de_cafe_id == tipo_de_cafe_id,
                models.Lote.tipo == "TOSTADO",
                models.Lote.estado.in_(["ABIERTO", "CERRADO"]),
                models.Lote.kg_disponibles > 0,
            ).order_by(models.Lote.fecha_vencimiento).all()
        elif blend_id:
            lotes = self.db.query(models.Lote).filter(
                models.Lote.blend_id == blend_id,
                models.Lote.tipo == "TOSTADO",
                models.Lote.estado.in_(["ABIERTO", "CERRADO"]),
                models.Lote.kg_disponibles > 0,
            ).order_by(models.Lote.fecha_vencimiento).all()
        else:
            raise ValueError("Debe especificar tipo_de_cafe_id o blend_id")
        
        if not lotes:
            raise ValueError("No hay lotes disponibles")
        
        consumo_detalle = []
        restante = cantidad
        
        for lote in lotes:
            if restante <= 0:
                break
            
            if lote.kg_disponibles >= restante:
                lote.kg_disponibles -= restante
                consumo_detalle.append({"lote_id": lote.id, "kg_consumidos": restante})
                restante = Decimal("0")
            else:
                consumo_detalle.append({"lote_id": lote.id, "kg_consumidos": lote.kg_disponibles})
                restante -= lote.kg_disponibles
                lote.kg_disponibles = Decimal("0")
            
            if lote.kg_disponibles == 0:
                lote.estado = "CERRADO"
            else:
                lote.estado = "ABIERTO"
        
        if restante > 0:
            raise ValueError("Stock insuficiente")
        
        self.db.commit()
        return consumo_detalle

    def _restaurar_stock_fifo(self, consumo_detalle: List[dict]):
        """Restaurar stock exacto usando el detalle de consumo"""
        for consumo in consumo_detalle:
            lote = self.db.query(models.Lote).filter(models.Lote.id == consumo["lote_id"]).first()
            if lote:
                lote.kg_disponibles += consumo["kg_consumidos"]
                if lote.estado == "CERRADO" and lote.kg_disponibles > 0:
                    lote.estado = "ABIERTO"
        self.db.commit()

    def _validar_transicion_estado(self, estado_actual: str, nuevo_estado: str) -> bool:
        """Validar si la transición de estado es permitida"""
        transiciones_validas = {
            "PENDIENTE": ["LISTO"],
            "LISTO": ["PENDIENTE", "ENTREGADO"],
            "ENTREGADO": ["LISTO"]
        }
        return nuevo_estado in transiciones_validas.get(estado_actual, [])

    def _es_cliente_b2b(self, cliente_id: int) -> bool:
        """Verificar si el cliente es B2B (Mayorista)"""
        cliente = crud.get_cliente(self.db, cliente_id)
        if not cliente:
            return False
        return cliente.es_b2b

    def _ajustar_cuenta_corriente(self, cliente_id: int, delta: Decimal):
        """Ajustar cuenta corriente del cliente (solo B2B)"""
        cliente = crud.get_cliente(self.db, cliente_id)
        if cliente and cliente.es_b2b:
            cliente.saldo_cuenta_corriente += delta
            self.db.commit()

    def _registrar_historial_estado(self, pedido_id: int, estado_anterior: Optional[str], estado_nuevo: str, usuario_id: Optional[int] = None):
        """Registrar cambio de estado en el historial"""
        crud.create_estado_historial(self.db, pedido_id, estado_anterior, estado_nuevo, usuario_id=None)

    def crear_pedido_completo(self, pedido_data: schemas.PedidoCreate, empleado_persona_id: Optional[int] = None) -> models.Pedido:
        """Crear un pedido con sus detalles, validando stock disponible y calculando totales.

        ``empleado_persona_id`` es opcional para permitir el autoservicio del
        portal de clientes, donde no hay un empleado que registre la venta.
        """
        # Validar que el cliente existe
        cliente = crud.get_cliente(self.db, pedido_data.cliente_persona_id)
        if not cliente:
            raise ValueError("Cliente no encontrado")
        
        # Validar que el empleado existe, solo si se indicó uno
        if empleado_persona_id is not None:
            empleado = self.db.query(models.Empleado).filter(models.Empleado.persona_id == empleado_persona_id).first()
            if not empleado:
                raise ValueError("Empleado no encontrado")
        
        # Validar y calcular detalles
        detalles_calculados = self._validar_y_calcular_detalles(pedido_data.detalles)
        total = sum(d["subtotal"] for d in detalles_calculados)
        
        # Idempotencia: generar o usar clave
        idempotency_key = pedido_data.idempotency_key
        if not idempotency_key:
            idempotency_key = self._generar_idempotency_key(
                pedido_data.cliente_persona_id, 
                pedido_data.detalles, 
                pedido_data.fecha
            )
        
        # Verificar idempotencia
        existing = crud.get_pedido_by_idempotency_key(self.db, idempotency_key)
        if existing:
            return existing
        
        # Validar stock para cada detalle (total disponible entre todos los lotes FIFO)
        for i, detalle in enumerate(pedido_data.detalles):
            if detalle.tipo_de_cafe_id:
                total_disponible = self.db.query(func.sum(models.Lote.kg_disponibles)).filter(
                    models.Lote.tipo_de_cafe_id == detalle.tipo_de_cafe_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado.in_(["ABIERTO", "CERRADO"]),
                    models.Lote.kg_disponibles > 0
                ).scalar() or Decimal("0")
                if total_disponible < detalle.cantidad_kg:
                    raise ValueError(f"Stock insuficiente para tipo de café {detalle.tipo_de_cafe_id}")
            
            if detalle.blend_id:
                total_disponible = self.db.query(func.sum(models.Lote.kg_disponibles)).filter(
                    models.Lote.blend_id == detalle.blend_id,
                    models.Lote.tipo == "TOSTADO",
                    models.Lote.estado.in_(["ABIERTO", "CERRADO"]),
                    models.Lote.kg_disponibles > 0
                ).scalar() or Decimal("0")
                if total_disponible < detalle.cantidad_kg:
                    raise ValueError(f"Stock insuficiente para blend {detalle.blend_id}")
        
        # Crear el pedido con total calculado
        pedido_con_total = schemas.PedidoCreate(
            fecha=pedido_data.fecha,
            metodo_de_despacho=pedido_data.metodo_de_despacho,
            estado=pedido_data.estado,
            total=sum(d["subtotal"] for d in self._validar_y_calcular_detalles(pedido_data.detalles)),
            idempotency_key=idempotency_key,
            medio_contacto=pedido_data.medio_contacto,
            observaciones=pedido_data.observaciones,
            cliente_persona_id=pedido_data.cliente_persona_id,
            empleado_persona_id=empleado_persona_id,
            detalles=[schemas.DetallePedidoCreate(**d) for d in self._validar_y_calcular_detalles(pedido_data.detalles)]
        )
        
        db_pedido = crud.create_pedido(self.db, pedido_con_total)
        
        # Consumir stock FIFO y guardar detalle para posible rollback
        consumo_total = []
        for i, detalle in enumerate(pedido_data.detalles):
            if detalle.tipo_de_cafe_id:
                consumo = self._consumir_stock_fifo(detalle.tipo_de_cafe_id, None, detalle.cantidad_kg)
                consumo_total.extend(consumo)
            
            if detalle.blend_id:
                consumo = self._consumir_stock_fifo(None, detalle.blend_id, detalle.cantidad_kg)
                consumo_total.extend(consumo)
        
        # Guardar detalle de consumo en el pedido para posible rollback
        # (en producción se guardaría en una tabla separada)
        
        # Registrar historial de estado inicial
        self._registrar_historial_estado(db_pedido.id, None, "PENDIENTE")
        
        return db_pedido

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

    def _consumir_stock_fifo_detalle(self, detalle: schemas.DetallePedidoCreate) -> List[dict]:
        """Consumir stock FIFO para un detalle y retornar detalle de consumo"""
        if detalle.tipo_de_cafe_id:
            return self._consumir_stock_fifo(detalle.tipo_de_cafe_id, None, detalle.cantidad_kg)
        elif detalle.blend_id:
            return self._consumir_stock_fifo(None, detalle.blend_id, detalle.cantidad_kg)
        return []

    def actualizar_pedido(self, pedido_id: int, pedido_update: schemas.PedidoUpdate, detalles: Optional[List[schemas.DetallePedidoCreate]] = None, usuario_id: Optional[int] = None) -> Optional[models.Pedido]:
        """Actualizar un pedido, recalculando totales si se envían nuevos detalles"""
        db_pedido = crud.get_pedido(self.db, pedido_id)
        if not db_pedido:
            return None
        
        estado_anterior = db_pedido.estado
        
        # Si se envían nuevos detalles, validar y recalcular
        if detalles is not None:
            # Validar que el cliente existe
            cliente = crud.get_cliente(self.db, db_pedido.cliente_persona_id)
            if not cliente:
                raise ValueError("Cliente no encontrado")
            
            # Validar y calcular nuevos detalles
            detalles_calculados = self._validar_y_calcular_detalles(detalles)
            total = sum(d["subtotal"] for d in detalles_calculados)
            
            # Validar stock para los nuevos detalles
            for i, detalle in enumerate(detalles):
                if detalle.tipo_de_cafe_id:
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
            
            # Devolver stock anterior
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
            for d in self._validar_y_calcular_detalles(detalles):
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
            db_pedido.total = sum(d["subtotal"] for d in self._validar_y_calcular_detalles(detalles))
        
        # Actualizar campos simples
        update_data = pedido_update.model_dump(exclude_unset=True)
        nuevo_estado = update_data.get("estado", db_pedido.estado)
        
        # Si hay cambio de estado, validar transición
        if "estado" in update_data and update_data["estado"] != estado_anterior:
            if not self._validar_transicion_estado(estado_anterior, nuevo_estado):
                raise ValueError(f"Transición inválida: {estado_anterior} -> {nuevo_estado}")
            
            # Registrar historial de estado
            self._registrar_historial_estado(pedido_id, estado_anterior, nuevo_estado)
            
            # Efectos laterales: cuenta corriente B2B
            if estado_anterior == "LISTO" and nuevo_estado == "ENTREGADO":
                if self._es_cliente_b2b(db_pedido.cliente_persona_id):
                    self._ajustar_cuenta_corriente(db_pedido.cliente_persona_id, db_pedido.total)
            elif estado_anterior == "ENTREGADO" and nuevo_estado == "LISTO":
                if self._es_cliente_b2b(db_pedido.cliente_persona_id):
                    self._ajustar_cuenta_corriente(db_pedido.cliente_persona_id, -db_pedido.total)
        
        for field, value in update_data.items():
            setattr(db_pedido, field, value)
        
        self.db.commit()
        self.db.refresh(db_pedido)
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

    def _devolver_stock_lotes(self, lotes: List[models.Lote], cantidad: Decimal):
        """Devolver stock a lotes distribuyendo en orden inverso al consumo (LIFO para rollback de FIFO)"""
        # Ordenar lotes por fecha_vencimiento ASC (orden de consumo FIFO)
        # Para rollback, procesar en orden inverso (LIFO para rollback de FIFO)
        lotes_ordenados = sorted(lotes, key=lambda l: l.fecha_vencimiento, reverse=True)
        
        restante = cantidad
        for lote in lotes_ordenados:
            if restante <= 0:
                break
            
            # Calcular cuánto se puede restaurar en este lote (hasta su capacidad original)
            capacidad_restauracion = lote.kg_reales - lote.kg_disponibles
            if capacidad_restauracion <= 0:
                continue
            
            # Si el lote estaba CERRADO y sin stock, reabrirlo
            if lote.estado == "CERRADO" and lote.kg_disponibles == 0:
                lote.estado = "ABIERTO"
            
            # Restaurar lo que se pueda en este lote
            a_restaurar = min(restante, capacidad_restauracion)
            lote.kg_disponibles += a_restaurar
            restante -= a_restaurar
        
        # Si sobra cantidad después de restaurar todos los lotes, agregar al último lote disponible
        if restante > 0 and lotes:
            # Buscar el último lote con espacio disponible
            for lote in reversed(lotes):
                if lote.estado == "CERRADO" and lote.kg_disponibles == 0:
                    lote.estado = "ABIERTO"
                lote.kg_disponibles += restante
                break
        
        self.db.commit()

    def eliminar_pedido(self, pedido_id: int) -> bool:
        """Eliminar un pedido y devolver stock si está PENDIENTE"""
        db_pedido = crud.get_pedido(self.db, pedido_id)
        if not db_pedido:
            return False
        
        if db_pedido.estado != "PENDIENTE":
            raise ValueError("Solo se pueden eliminar pedidos en estado PENDIENTE")
        
        # Devolver stock
        detalles = crud.get_detalles_by_pedido(self.db, pedido_id)
        for det in detalles:
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
        
        # Eliminar historial
        self.db.query(models.PedidoEstadoHistorial).filter(models.PedidoEstadoHistorial.pedido_id == pedido_id).delete()
        
        # Eliminar detalles
        self.db.query(models.DetallePedido).filter(models.DetallePedido.pedido_id == pedido_id).delete()
        
        # Eliminar pedido
        self.db.delete(db_pedido)
        self.db.commit()
        return True

    def cambiar_estado_pedido(self, pedido_id: int, nuevo_estado: str, usuario_id: Optional[int] = None) -> Optional[models.Pedido]:
        """Cambiar estado del pedido con validación de transiciones"""
        db_pedido = crud.get_pedido(self.db, pedido_id)
        if not db_pedido:
            return None
        
        estado_anterior = db_pedido.estado
        
        if not self._validar_transicion_estado(estado_anterior, nuevo_estado):
            raise ValueError(f"Transición inválida: {estado_anterior} -> {nuevo_estado}")
        
        # Actualizar estado
        db_pedido.estado = nuevo_estado
        
        # Registrar historial
        self._registrar_historial_estado(pedido_id, estado_anterior, nuevo_estado, usuario_id)
        
        # Efectos laterales: cuenta corriente B2B
        if estado_anterior == "LISTO" and nuevo_estado == "ENTREGADO":
            if self._es_cliente_b2b(db_pedido.cliente_persona_id):
                self._ajustar_cuenta_corriente(db_pedido.cliente_persona_id, db_pedido.total)
        elif estado_anterior == "ENTREGADO" and nuevo_estado == "LISTO":
            if self._es_cliente_b2b(db_pedido.cliente_persona_id):
                self._ajustar_cuenta_corriente(db_pedido.cliente_persona_id, -db_pedido.total)
        
        self.db.commit()
        self.db.refresh(db_pedido)
        return db_pedido

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

    def obtener_todos_pedidos(self, skip: int = 0, limit: int = 100, estado: Optional[str] = None, cliente_persona_id: Optional[int] = None, fecha_desde: Optional[datetime] = None, fecha_hasta: Optional[datetime] = None, q: Optional[str] = None) -> List[models.Pedido]:
        return crud.get_pedidos_con_filtros(self.db, skip, limit, estado, cliente_persona_id, None, None, None)

    def obtener_pedido_por_id(self, pedido_id: int) -> Optional[models.Pedido]:
        return crud.get_pedido_with_full_info(self.db, pedido_id)


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


# ---------------------------------------------------------------------------
# Panel de pedidos: contrato plano sobre el modelo canónico
# ---------------------------------------------------------------------------
class PedidoNoEncontrado(Exception):
    """El id recibido no corresponde a ningún pedido."""

    def __init__(self, pedido_id: int) -> None:
        self.pedido_id = pedido_id
        super().__init__(f"No existe un pedido con id {pedido_id}.")


_ESTADOS_FRONTEND = {
    "pendiente": "PENDIENTE",
    "listo": "LISTO",
    "entregado": "ENTREGADO",
}

_ESTADOS_PANEL = {
    "PENDIENTE": "Pendiente",
    "LISTO": "Listo",
    "ENTREGADO": "Entregado",
}


def estado_canonico(valor: str) -> str:
    """Convierte el estado del panel al valor canónico, sin distinguir mayúsculas."""
    estado = _ESTADOS_FRONTEND.get((valor or "").strip().lower())
    if estado is None:
        raise ValueError("Estado inválido. Debe ser Pendiente, Listo o Entregado.")
    return estado


class PedidoPanelService:
    """Traduce los pedidos del panel al modelo canónico y viceversa."""

    def __init__(self, db: Session):
        self.db = db
        self.pedidos = PedidoService(db)

    # -- Lectura ---------------------------------------------------------
    def _item_a_panel(self, detalle: models.DetallePedido) -> schemas.PedidoPanelItemRead:
        cantidad = detalle.cantidad_kg or Decimal("0")
        precio_kg = (
            (detalle.subtotal / cantidad) if cantidad else Decimal("0")
        )

        if detalle.tipo_de_cafe_id is not None:
            stock_id = f"tc-{detalle.tipo_de_cafe_id}-TOSTADO"
            variedad = (
                detalle.tipo_de_cafe.variedad
                if detalle.tipo_de_cafe is not None
                else f"Tipo de café {detalle.tipo_de_cafe_id}"
            )
        elif detalle.blend_id is not None:
            stock_id = f"bl-{detalle.blend_id}-TOSTADO"
            variedad = (
                detalle.blend.nombre
                if detalle.blend is not None
                else f"Blend {detalle.blend_id}"
            )
        else:
            stock_id = ""
            variedad = "Sin origen"

        return schemas.PedidoPanelItemRead(
            stockId=stock_id,
            variedad=variedad,
            kilos=float(cantidad),
            precioKg=float(precio_kg),
            subtotal=float(detalle.subtotal or 0),
        )

    def _a_panel(self, pedido: models.Pedido) -> schemas.PedidoPanelRead:
        persona = pedido.cliente.persona if pedido.cliente else None
        cliente_nombre = (
            f"{persona.nombre} {persona.apellido}".strip()
            if persona
            else f"Cliente {pedido.cliente_persona_id}"
        )

        return schemas.PedidoPanelRead(
            id=str(pedido.id),
            fecha=pedido.fecha,
            estado=_ESTADOS_PANEL.get(pedido.estado, str(pedido.estado)),
            clienteId=str(pedido.cliente_persona_id),
            clienteNombre=cliente_nombre,
            items=[self._item_a_panel(detalle) for detalle in pedido.detalles],
            medioContacto=pedido.medio_contacto or "",
            observaciones=pedido.observaciones or "",
            total=float(pedido.total or 0),
        )

    def _leer(self, pedido_id: int) -> schemas.PedidoPanelRead:
        pedido = crud.get_pedido_with_full_info(self.db, pedido_id)
        if pedido is None:
            raise PedidoNoEncontrado(pedido_id)
        return self._a_panel(pedido)

    def listar(self) -> List[schemas.PedidoPanelRead]:
        pedidos = crud.get_pedidos_con_filtros(self.db, skip=0, limit=1000)
        return [self._a_panel(pedido) for pedido in pedidos]

    def listar_por_cliente(self, cliente_id: int) -> List[schemas.PedidoPanelRead]:
        pedidos = crud.get_pedidos_con_filtros(
            self.db, skip=0, limit=1000, cliente_persona_id=cliente_id
        )
        return [self._a_panel(pedido) for pedido in pedidos]

    # -- Escritura -------------------------------------------------------
    def _detalle_desde_item(
        self, item: schemas.PedidoPanelItem
    ) -> schemas.DetallePedidoCreate:
        from app.modules.inventario.models import LoteTipo
        from app.modules.inventario.services import parsear_stock_id

        try:
            origen, entidad_id, tipo = parsear_stock_id(item.stockId)
        except Exception:
            raise ValueError(f"Producto de stock inválido: '{item.stockId}'.") from None

        if tipo != LoteTipo.TOSTADO:
            raise ValueError(
                "Solo se puede vender café tostado. "
                f"El producto '{item.stockId}' es café verde."
            )

        if origen == "tc":
            return schemas.DetallePedidoCreate(
                cantidad_kg=item.kilos,
                tipo_de_cafe_id=entidad_id,
            )
        return schemas.DetallePedidoCreate(
            cantidad_kg=item.kilos,
            blend_id=entidad_id,
        )

    def resolver_empleado_actual(self, email: str) -> Optional[int]:
        """Devuelve el empleado vinculado a la cuenta, o ``None`` si es cliente."""
        cuenta = self.db.query(Cuenta).filter(Cuenta.correo == email).first()
        if cuenta is None:
            return None

        persona = (
            self.db.query(models.Persona)
            .filter(models.Persona.cuenta_id == cuenta.id)
            .first()
        )
        if persona is None:
            return None

        empleado = (
            self.db.query(models.Empleado)
            .filter(models.Empleado.persona_id == persona.id)
            .first()
        )
        return empleado.persona_id if empleado else None

    def crear(
        self,
        datos: schemas.PedidoPanelCreate,
        empleado_persona_id: Optional[int] = None,
    ) -> schemas.PedidoPanelRead:
        """Crea el pedido, descuenta stock y aplica el estado pedido."""
        try:
            cliente_id = int(datos.clienteId)
        except (TypeError, ValueError):
            raise ValueError("Cliente inválido.") from None

        objetivo = estado_canonico(datos.estado)
        detalles = [self._detalle_desde_item(item) for item in datos.items]

        pedido_in = schemas.PedidoCreate(
            fecha=datetime.utcnow(),
            metodo_de_despacho="Retiro en local",
            estado="PENDIENTE",
            idempotency_key=f"panel-{uuid.uuid4().hex}",
            medio_contacto=datos.medioContacto or None,
            observaciones=datos.observaciones or None,
            cliente_persona_id=cliente_id,
            empleado_persona_id=empleado_persona_id,
            detalles=detalles,
        )

        pedido = self.pedidos.crear_pedido_completo(pedido_in, empleado_persona_id)

        if objetivo != "PENDIENTE":
            self._cambiar_estado(pedido, objetivo)

        return self._leer(pedido.id)

    def _cambiar_estado(self, pedido: models.Pedido, objetivo: str) -> None:
        """Lleva el pedido al estado objetivo respetando las transiciones.

        El panel permite mover una tarjeta de Pendiente a Entregado (o al
        revés); se pasa por Listo para no saltear la regla de negocio ni los
        efectos sobre la cuenta corriente.
        """
        actual = pedido.estado
        if actual == objetivo:
            return

        if self.pedidos._validar_transicion_estado(actual, objetivo):
            self.pedidos.cambiar_estado_pedido(pedido.id, objetivo)
            return

        intermedio = "LISTO"
        if (
            self.pedidos._validar_transicion_estado(actual, intermedio)
            and self.pedidos._validar_transicion_estado(intermedio, objetivo)
        ):
            self.pedidos.cambiar_estado_pedido(pedido.id, intermedio)
            self.pedidos.cambiar_estado_pedido(pedido.id, objetivo)
            return

        raise ValueError(f"Transición inválida: {actual} -> {objetivo}")

    def actualizar(
        self, pedido_id: int, datos: schemas.PedidoPanelUpdate
    ) -> schemas.PedidoPanelRead:
        """Actualiza cliente, campos simples, ítems y estado."""
        pedido = crud.get_pedido(self.db, pedido_id)
        if pedido is None:
            raise PedidoNoEncontrado(pedido_id)

        campos = datos.model_fields_set

        if "clienteId" in campos and datos.clienteId is not None:
            try:
                nuevo_cliente = int(datos.clienteId)
            except (TypeError, ValueError):
                raise ValueError("Cliente inválido.") from None

            if nuevo_cliente != pedido.cliente_persona_id:
                if pedido.estado != "PENDIENTE":
                    raise ValueError(
                        "Solo se puede cambiar el cliente de un pedido pendiente."
                    )
                if crud.get_cliente(self.db, nuevo_cliente) is None:
                    raise ValueError("Cliente no encontrado.")
                pedido.cliente_persona_id = nuevo_cliente
                self.db.commit()

        simples = {}
        if "medioContacto" in campos:
            simples["medio_contacto"] = (datos.medioContacto or "").strip() or None
        if "observaciones" in campos:
            simples["observaciones"] = (datos.observaciones or "").strip() or None

        if datos.items is not None:
            detalles = [self._detalle_desde_item(item) for item in datos.items]
            self.pedidos.actualizar_pedido(
                pedido_id,
                schemas.PedidoUpdate(**simples),
                detalles=detalles,
            )
        elif simples:
            self.pedidos.actualizar_pedido(
                pedido_id, schemas.PedidoUpdate(**simples)
            )

        if "estado" in campos and datos.estado is not None:
            objetivo = estado_canonico(datos.estado)
            pedido_actualizado = crud.get_pedido(self.db, pedido_id)
            if pedido_actualizado is None:
                raise PedidoNoEncontrado(pedido_id)
            self._cambiar_estado(pedido_actualizado, objetivo)

        return self._leer(pedido_id)

    def eliminar(self, pedido_id: int) -> None:
        """Elimina un pedido pendiente y devuelve su stock."""
        if not self.pedidos.eliminar_pedido(pedido_id):
            raise PedidoNoEncontrado(pedido_id)