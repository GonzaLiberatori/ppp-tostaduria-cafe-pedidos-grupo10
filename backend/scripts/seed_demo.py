#!/usr/bin/env python
"""Puebla la base con datos de demo reproducibles.

El script es idempotente: cada entidad se busca por su clave natural (correo,
código de lote, clave de idempotencia del pedido o combinación de gasto) y solo
se crea si no existe. Correrlo dos veces no duplica filas ni pisa consumos de
stock.

Uso:
    python scripts/seed_demo.py

Las credenciales de acceso quedan documentadas en ``CUENTAS_DEMO``. El panel
trabaja con contratos planos, así que el stock de café tostado usa el precio
base del catálogo (``precio_por_kg_verde``): el modelo guarda un único precio
por origen y el panel lo muestra tanto en verde como en tostado.
"""

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

# Agregar la raíz del backend al path para poder ejecutar el script directo.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.modules.auth.models import Cuenta, UserRole
from app.modules.clientes.models import Cliente, Empleado, Persona, TipoCliente
from app.modules.gastos.models import Gasto
from app.modules.inventario.models import (
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    LoteEstado,
    LoteTipo,
    TipoDeCafe,
)
from app.modules.pedidos.models import (
    DetallePedido,
    EstadoPedido,
    MetodoDespacho,
    Pedido,
    PedidoEstadoHistorial,
)


CUENTAS_DEMO: list[dict[str, Any]] = [
    {
        "correo": "admin@cafedefinca.com",
        "clave": "admin123",
        "rol": UserRole.ADMINISTRADOR,
        "nombre": "Ana",
        "apellido": "Administradora",
        "telefono": None,
    },
    {
        "correo": "operario@cafedefinca.com",
        "clave": "operario123",
        "rol": UserRole.OPERARIO,
        "nombre": "Oscar",
        "apellido": "Operario",
        "telefono": "+54 11 4000-1001",
        "empleado": {
            "fecha_de_contratacion": date(2024, 3, 1),
            "fecha_de_nacimiento": date(1990, 7, 12),
            "salario": Decimal("950000"),
        },
    },
    {
        "correo": "cajero@cafedefinca.com",
        "clave": "cajero123",
        "rol": UserRole.CAJERO,
        "nombre": "Carla",
        "apellido": "Cajera",
        "telefono": "+54 11 4000-1002",
        "empleado": {
            "fecha_de_contratacion": date(2025, 1, 15),
            "fecha_de_nacimiento": date(1994, 11, 3),
            "salario": Decimal("880000"),
        },
    },
]

CLIENTES_DEMO: list[dict[str, Any]] = [
    {
        "nombre": "Cafetería",
        "apellido": "El Aroma",
        "email": "pedidos@elaroma.com.ar",
        "telefono": "+54 11 4567-8901",
        "tipo": TipoCliente.MAYORISTA,
        "direccion": "Av. Corrientes 1234, CABA",
        "saldo": Decimal("45000"),
        "limite": Decimal("200000"),
        "fecha_alta": datetime(2025, 6, 15, 10, 0),
    },
    {
        "nombre": "Distribuidora Café",
        "apellido": "Sur",
        "email": "compras@cafesur.com.ar",
        "telefono": "+54 11 3210-5555",
        "tipo": TipoCliente.MAYORISTA,
        "direccion": "Ruta 3 Km 45, La Matanza",
        "saldo": Decimal("0"),
        "limite": Decimal("500000"),
        "fecha_alta": datetime(2025, 3, 22, 10, 0),
    },
    {
        "nombre": "María",
        "apellido": "González",
        "email": "maria.gonzalez@email.com",
        "telefono": "+54 9 11 6789-0123",
        "tipo": TipoCliente.CONSUMIDOR_FINAL,
        "direccion": "Palermo, CABA",
        "saldo": Decimal("0"),
        "limite": None,
        "fecha_alta": datetime(2026, 1, 10, 10, 0),
        # Esta persona es la dueña del acceso al portal de clientes.
        "correo_cuenta": "cliente@cafedefinca.com",
        "clave_cuenta": "cliente123",
    },
    {
        "nombre": "Restaurant La",
        "apellido": "Mesita",
        "email": "gerencia@lamesita.com.ar",
        "telefono": "+54 11 4455-6677",
        "tipo": TipoCliente.MAYORISTA,
        "direccion": "San Telmo, CABA",
        "saldo": Decimal("120000"),
        "limite": Decimal("150000"),
        "fecha_alta": datetime(2025, 9, 1, 10, 0),
    },
    {
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan.perez@email.com",
        "telefono": "+54 9 11 3344-5566",
        "tipo": TipoCliente.CONSUMIDOR_FINAL,
        "direccion": "Belgrano, CABA",
        "saldo": Decimal("0"),
        "limite": None,
        "fecha_alta": datetime(2026, 2, 1, 10, 0),
    },
]

TIPOS_DE_CAFE_DEMO: list[dict[str, Any]] = [
    {
        "variedad": "Arábica Bourbon",
        "pais": "Colombia",
        "region": "Huila",
        "organico": True,
        "precio": Decimal("18500"),
    },
    {
        "variedad": "Arábica Typica",
        "pais": "Brasil",
        "region": "Minas Gerais",
        "organico": False,
        "precio": Decimal("19800"),
    },
    {
        "variedad": "Robusta",
        "pais": "Vietnam",
        "region": "Dak Lak",
        "organico": False,
        "precio": Decimal("12500"),
    },
]

BLEND_DEMO: dict[str, Any] = {
    "nombre": "Blend Casa",
    "descripcion": "Brasil + Colombia",
    "precio": Decimal("16200"),
    "composicion": [("Arábica Bourbon", Decimal("60")), ("Arábica Typica", Decimal("40"))],
}

# (variedad, tipo, código, kilos, estado, fecha de ingreso)
LOTES_DEMO: list[tuple[str, LoteTipo, str, Decimal, LoteEstado, datetime]] = [
    ("Arábica Bourbon", LoteTipo.VERDE, "LOTE-2026-001-A", Decimal("60"), LoteEstado.CERRADO, datetime(2026, 1, 15, 10, 0)),
    ("Arábica Bourbon", LoteTipo.VERDE, "LOTE-2026-001-B", Decimal("60"), LoteEstado.CERRADO, datetime(2026, 1, 15, 10, 0)),
    ("Arábica Bourbon", LoteTipo.VERDE, "LOTE-2026-001-C", Decimal("30"), LoteEstado.ABIERTO, datetime(2026, 1, 15, 10, 0)),
    ("Arábica Typica", LoteTipo.VERDE, "LOTE-2026-002-A", Decimal("60"), LoteEstado.CERRADO, datetime(2026, 1, 20, 10, 0)),
    ("Arábica Typica", LoteTipo.VERDE, "LOTE-2026-002-B", Decimal("60"), LoteEstado.CERRADO, datetime(2026, 1, 20, 10, 0)),
    ("Arábica Typica", LoteTipo.VERDE, "LOTE-2026-002-C", Decimal("20"), LoteEstado.ABIERTO, datetime(2026, 1, 20, 10, 0)),
    ("Robusta", LoteTipo.VERDE, "LOTE-2026-003-A", Decimal("60"), LoteEstado.CERRADO, datetime(2026, 2, 1, 10, 0)),
    ("Robusta", LoteTipo.VERDE, "LOTE-2026-003-B", Decimal("40"), LoteEstado.ABIERTO, datetime(2026, 2, 1, 10, 0)),
    ("Arábica Bourbon", LoteTipo.TOSTADO, "TST-2026-001-01", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 10, 10, 0)),
    ("Arábica Bourbon", LoteTipo.TOSTADO, "TST-2026-001-02", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 10, 10, 0)),
    ("Arábica Bourbon", LoteTipo.TOSTADO, "TST-2026-001-03", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 10, 10, 0)),
    ("Arábica Bourbon", LoteTipo.TOSTADO, "TST-2026-001-04", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 10, 10, 0)),
    ("Arábica Bourbon", LoteTipo.TOSTADO, "TST-2026-001-05", Decimal("20"), LoteEstado.ABIERTO, datetime(2026, 2, 10, 10, 0)),
    ("Arábica Typica", LoteTipo.TOSTADO, "TST-2026-002-01", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 14, 10, 0)),
    ("Arábica Typica", LoteTipo.TOSTADO, "TST-2026-002-02", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 14, 10, 0)),
    ("Arábica Typica", LoteTipo.TOSTADO, "TST-2026-002-03", Decimal("20"), LoteEstado.ABIERTO, datetime(2026, 2, 14, 10, 0)),
    ("Blend Casa", LoteTipo.TOSTADO, "TST-2026-003-01", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 12, 10, 0)),
    ("Blend Casa", LoteTipo.TOSTADO, "TST-2026-003-02", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 12, 10, 0)),
    ("Blend Casa", LoteTipo.TOSTADO, "TST-2026-003-03", Decimal("20"), LoteEstado.CERRADO, datetime(2026, 2, 12, 10, 0)),
    ("Blend Casa", LoteTipo.TOSTADO, "TST-2026-003-04", Decimal("20"), LoteEstado.ABIERTO, datetime(2026, 2, 12, 10, 0)),
    ("Robusta", LoteTipo.TOSTADO, "TST-2026-004-01", Decimal("15"), LoteEstado.ABIERTO, datetime(2026, 2, 18, 10, 0)),
]

# El precio de cada ítem se toma del catálogo para que el total sea coherente.
PEDIDOS_DEMO: list[dict[str, Any]] = [
    {
        "clave": "seed-demo-1",
        "fecha": datetime(2026, 2, 10, 10, 0),
        "estado": EstadoPedido.ENTREGADO,
        "cliente_email": "pedidos@elaroma.com.ar",
        "medio_contacto": "WhatsApp",
        "observaciones": "Entrega en local antes de las 10am",
        "items": [("Arábica Bourbon", Decimal("20")), ("Blend Casa", Decimal("10"))],
    },
    {
        "clave": "seed-demo-2",
        "fecha": datetime(2026, 2, 12, 10, 0),
        "estado": EstadoPedido.LISTO,
        "cliente_email": "compras@cafesur.com.ar",
        "medio_contacto": "Email",
        "observaciones": "Factura A requerida",
        "items": [("Arábica Bourbon", Decimal("50")), ("Arábica Typica", Decimal("30"))],
    },
    {
        "clave": "seed-demo-3",
        "fecha": datetime(2026, 2, 14, 10, 0),
        "estado": EstadoPedido.PENDIENTE,
        "cliente_email": "maria.gonzalez@email.com",
        "medio_contacto": "Presencial",
        "observaciones": "Retira en tostaduría",
        "items": [("Blend Casa", Decimal("2")), ("Arábica Typica", Decimal("1"))],
    },
    {
        "clave": "seed-demo-4",
        "fecha": datetime(2026, 2, 15, 10, 0),
        "estado": EstadoPedido.PENDIENTE,
        "cliente_email": "gerencia@lamesita.com.ar",
        "medio_contacto": "Teléfono",
        "observaciones": "Urgente - fin de semana",
        "items": [("Arábica Bourbon", Decimal("40"))],
    },
    {
        "clave": "seed-demo-5",
        "fecha": datetime(2026, 2, 16, 10, 0),
        "estado": EstadoPedido.ENTREGADO,
        "cliente_email": "juan.perez@email.com",
        "medio_contacto": "WhatsApp",
        "observaciones": "",
        "items": [("Blend Casa", Decimal("1")), ("Arábica Bourbon", Decimal("1"))],
    },
]

GASTOS_DEMO: list[dict[str, Any]] = [
    {"fecha": datetime(2026, 1, 15, 10, 0), "categoria": "Producción", "descripcion": "Compra café verde - Lote 001", "monto": Decimal("1275000")},
    {"fecha": datetime(2026, 1, 18, 10, 0), "categoria": "Producción", "descripcion": "Gas y electricidad tueste enero", "monto": Decimal("85000")},
    {"fecha": datetime(2026, 1, 20, 10, 0), "categoria": "Operativo", "descripcion": "Alquiler tostaduría enero", "monto": Decimal("180000")},
    {"fecha": datetime(2026, 1, 25, 10, 0), "categoria": "Marketing", "descripcion": "Publicidad Instagram/Facebook", "monto": Decimal("45000")},
    {"fecha": datetime(2026, 2, 1, 10, 0), "categoria": "Producción", "descripcion": "Compra café verde - Lote 002", "monto": Decimal("1440000")},
    {"fecha": datetime(2026, 2, 5, 10, 0), "categoria": "Operativo", "descripcion": "Mantenimiento tostadora", "monto": Decimal("120000")},
    {"fecha": datetime(2026, 2, 10, 10, 0), "categoria": "Operativo", "descripcion": "Alquiler tostaduría febrero", "monto": Decimal("180000")},
    {"fecha": datetime(2026, 2, 12, 10, 0), "categoria": "Producción", "descripcion": "Bolsas y etiquetado", "monto": Decimal("65000")},
]


def _crear_cuenta(db: Session, datos: dict[str, Any]) -> Cuenta:
    """Devuelve la cuenta del correo, creándola con su clave si no existe."""
    cuenta = db.query(Cuenta).filter(Cuenta.correo == datos["correo"]).first()
    if cuenta is None:
        cuenta = Cuenta(
            correo=datos["correo"],
            clave=get_password_hash(datos["clave"]),
            rol=datos["rol"],
        )
        db.add(cuenta)
        db.flush()
    return cuenta


def _crear_persona(
    db: Session,
    nombre: str,
    apellido: str,
    email: str,
    telefono: Optional[str],
    cuenta_id: Optional[int] = None,
) -> Persona:
    """Devuelve la persona del correo, creándola si no existe."""
    persona = db.query(Persona).filter(Persona.email == email).first()
    if persona is None:
        persona = Persona(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono,
            cuenta_id=cuenta_id,
        )
        db.add(persona)
        db.flush()
    elif cuenta_id is not None and persona.cuenta_id is None:
        persona.cuenta_id = cuenta_id
        db.flush()
    return persona


def _crear_cliente(
    db: Session, persona: Persona, datos: dict[str, Any]
) -> Cliente:
    """Devuelve el cliente de la persona, creándolo con su cuenta corriente."""
    cliente = db.get(Cliente, persona.id)
    if cliente is None:
        cliente = Cliente(
            persona_id=persona.id,
            tipo=datos["tipo"],
            direccion_de_entrega=datos["direccion"],
            fecha_alta=datos["fecha_alta"],
            saldo_cuenta_corriente=datos["saldo"],
            limite_credito=datos["limite"],
        )
        db.add(cliente)
        db.flush()
    return cliente


def _crear_empleado(
    db: Session, persona: Persona, datos: dict[str, Any]
) -> Empleado:
    """Devuelve el empleado de la persona, creándolo si no existe."""
    empleado = db.get(Empleado, persona.id)
    if empleado is None:
        empleado = Empleado(
            persona_id=persona.id,
            fecha_de_contratacion=datos["fecha_de_contratacion"],
            fecha_de_nacimiento=datos["fecha_de_nacimiento"],
            salario=datos["salario"],
        )
        db.add(empleado)
        db.flush()
    return empleado


def _crear_tipo_de_cafe(db: Session, datos: dict[str, Any]) -> TipoDeCafe:
    """Devuelve el tipo de café por variedad y país."""
    tipo = (
        db.query(TipoDeCafe)
        .filter(
            TipoDeCafe.variedad == datos["variedad"],
            TipoDeCafe.pais == datos["pais"],
        )
        .first()
    )
    if tipo is None:
        tipo = TipoDeCafe(
            organico=datos["organico"],
            precio_por_kg_verde=datos["precio"],
            variedad=datos["variedad"],
            region=datos["region"],
            pais=datos["pais"],
        )
        db.add(tipo)
        db.flush()
    return tipo


def _crear_blend(
    db: Session, datos: dict[str, Any], tipos: dict[str, TipoDeCafe]
) -> Blend:
    """Devuelve el blend por nombre y completa su composición."""
    blend = db.query(Blend).filter(Blend.nombre == datos["nombre"]).first()
    if blend is None:
        blend = Blend(
            nombre=datos["nombre"],
            precio_por_kg_verde=datos["precio"],
            descripcion=datos["descripcion"],
        )
        db.add(blend)
        db.flush()

    for variedad, porcentaje in datos["composicion"]:
        tipo = tipos[variedad]
        existente = db.get(BlendHasTipoDeCafe, (blend.id, tipo.id))
        if existente is None:
            db.add(
                BlendHasTipoDeCafe(
                    blend_id=blend.id,
                    tipo_de_cafe_id=tipo.id,
                    porcentaje=porcentaje,
                )
            )
    db.flush()
    return blend


def _crear_lote(
    db: Session,
    tipo: LoteTipo,
    codigo: str,
    kilos: Decimal,
    estado: LoteEstado,
    fecha_ingreso: datetime,
    tipo_de_cafe: Optional[TipoDeCafe] = None,
    blend: Optional[Blend] = None,
) -> Lote:
    """Crea el lote si el código no existe y lo devuelve."""
    lote = db.query(Lote).filter(Lote.codigo_lote == codigo).first()
    if lote is None:
        lote = Lote(
            codigo_lote=codigo,
            fecha_ingreso=fecha_ingreso,
            tipo=tipo,
            estado=estado,
            fecha_vencimiento=fecha_ingreso + timedelta(days=365),
            humedad=Decimal("12.00"),
            kg_disponibles=kilos,
            kg_reales=kilos,
            ubicacion_fisica="Depósito principal",
            tipo_de_cafe_id=tipo_de_cafe.id if tipo_de_cafe else None,
            blend_id=blend.id if blend else None,
        )
        db.add(lote)
        db.flush()
    return lote


def _crear_pedido(
    db: Session,
    datos: dict[str, Any],
    clientes: dict[str, Cliente],
    precios: dict[str, Decimal],
    empleado_id: Optional[int],
) -> Pedido:
    """Crea el pedido con sus detalles si la clave de idempotencia no existe."""
    pedido = (
        db.query(Pedido)
        .filter(Pedido.idempotency_key == datos["clave"])
        .first()
    )
    if pedido is not None:
        return pedido

    total = sum(
        (kilos * precios[variedad] for variedad, kilos in datos["items"]),
        Decimal("0"),
    )
    cliente = clientes[datos["cliente_email"]]
    pedido = Pedido(
        fecha=datos["fecha"],
        metodo_de_despacho=MetodoDespacho.RETIRO_LOCAL,
        estado=datos["estado"],
        total=total,
        idempotency_key=datos["clave"],
        medio_contacto=datos["medio_contacto"],
        observaciones=datos["observaciones"] or None,
        cliente_persona_id=cliente.persona_id,
        empleado_persona_id=empleado_id,
    )
    db.add(pedido)
    db.flush()

    for variedad, kilos in datos["items"]:
        db.add(
            DetallePedido(
                cantidad_kg=kilos,
                subtotal=kilos * precios[variedad],
                pedido_id=pedido.id,
                tipo_de_cafe_id=(
                    None
                    if variedad == BLEND_DEMO["nombre"]
                    else db.query(TipoDeCafe)
                    .filter(TipoDeCafe.variedad == variedad)
                    .one()
                    .id
                ),
                blend_id=(
                    db.query(Blend)
                    .filter(Blend.nombre == variedad)
                    .one()
                    .id
                    if variedad == BLEND_DEMO["nombre"]
                    else None
                ),
            )
        )

    db.add(
        PedidoEstadoHistorial(
            pedido_id=pedido.id,
            estado_anterior=None,
            estado_nuevo=datos["estado"],
            usuario_id=None,
            timestamp=datos["fecha"],
        )
    )
    db.flush()
    return pedido


def _crear_gasto(db: Session, datos: dict[str, Any]) -> None:
    """Crea el gasto si no coincide fecha, categoría y descripción."""
    existente = (
        db.query(Gasto)
        .filter(
            Gasto.fecha == datos["fecha"],
            Gasto.categoria == datos["categoria"],
            Gasto.descripcion == datos["descripcion"],
        )
        .first()
    )
    if existente is None:
        db.add(
            Gasto(
                fecha=datos["fecha"],
                categoria=datos["categoria"],
                descripcion=datos["descripcion"],
                monto=datos["monto"],
            )
        )


def seed() -> None:
    """Ejecuta el seed completo dentro de una única transacción."""
    # ``engine`` se importa para que SQLite aplique el PRAGMA de claves foráneas
    # al crear la sesión; las tablas ya existen por las migraciones.
    _ = engine

    with SessionLocal() as db:
        try:
            # 1. Cuentas y empleados.
            for datos in CUENTAS_DEMO:
                cuenta = _crear_cuenta(db, datos)
                persona = _crear_persona(
                    db,
                    datos["nombre"],
                    datos["apellido"],
                    datos["correo"],
                    datos["telefono"],
                    cuenta_id=cuenta.id,
                )
                if "empleado" in datos:
                    _crear_empleado(db, persona, datos["empleado"])

            # 2. Clientes (incluye el acceso al portal B2C).
            clientes: dict[str, Cliente] = {}
            for datos in CLIENTES_DEMO:
                cuenta_id = None
                if "correo_cuenta" in datos:
                    cuenta = _crear_cuenta(
                        db,
                        {
                            "correo": datos["correo_cuenta"],
                            "clave": datos["clave_cuenta"],
                            "rol": UserRole.CLIENTE,
                        },
                    )
                    cuenta_id = cuenta.id

                persona = _crear_persona(
                    db,
                    datos["nombre"],
                    datos["apellido"],
                    datos["email"],
                    datos["telefono"],
                    cuenta_id=cuenta_id,
                )
                clientes[datos["email"]] = _crear_cliente(db, persona, datos)

            # 3. Catálogo de cafés y blend.
            tipos = {
                datos["variedad"]: _crear_tipo_de_cafe(db, datos)
                for datos in TIPOS_DE_CAFE_DEMO
            }
            blend = _crear_blend(db, BLEND_DEMO, tipos)

            precios: dict[str, Decimal] = {
                datos["variedad"]: datos["precio"]
                for datos in TIPOS_DE_CAFE_DEMO
            }
            precios[BLEND_DEMO["nombre"]] = BLEND_DEMO["precio"]

            # 4. Lotes verdes y tostados.
            for variedad, tipo, codigo, kilos, estado, fecha in LOTES_DEMO:
                if variedad == BLEND_DEMO["nombre"]:
                    _crear_lote(
                        db, tipo, codigo, kilos, estado, fecha, blend=blend
                    )
                else:
                    _crear_lote(
                        db,
                        tipo,
                        codigo,
                        kilos,
                        estado,
                        fecha,
                        tipo_de_cafe=tipos[variedad],
                    )

            # 5. Pedidos: el empleado que los registra es el operario.
            operario = (
                db.query(Persona)
                .filter(Persona.email == "operario@cafedefinca.com")
                .one()
            )
            for datos in PEDIDOS_DEMO:
                _crear_pedido(db, datos, clientes, precios, operario.id)

            # 6. Gastos.
            for datos in GASTOS_DEMO:
                _crear_gasto(db, datos)

            db.commit()
            print("[OK] Seed completado. Credenciales de demo:")
            for datos in CUENTAS_DEMO:
                print(f"     {datos['correo']} / {datos['clave']} ({datos['rol'].value})")
            print("     cliente@cafedefinca.com / cliente123 (Cliente)")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    seed()
