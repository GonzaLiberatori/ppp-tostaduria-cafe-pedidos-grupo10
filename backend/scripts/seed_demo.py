#!/usr/bin/env python
"""
Seed script para poblar la BD con datos de demo (basados en mockData.js).
Ejecutar: python backend/scripts/seed_demo.py
"""
import sys
import os
from decimal import Decimal
from datetime import datetime, date

# Agregar path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.security import get_password_hash

# Import all models to register them with Base.metadata
from app.modules.auth import models as auth_models
from app.modules.clientes import models as clientes_models
from app.modules.inventario import models as inventario_models
from app.modules.gastos import models as gastos_models
from app.modules.pedidos import models as pedidos_models


def get_database_url():
    """Obtiene la URL de BD desde argumentos o settings."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return settings.DATABASE_URL


# Datos de demo (basados en frontend/src/data/mockData.js)

CLIENTES_DEMO = [
    {
        "id": 1,
        "nombre": "Cafetería El Aroma",
        "tipo": "B2B",
        "kilos_comprados": 120,
        "tiene_deuda": True,
        "monto_deuda": Decimal("45000"),
        "telefono": "+54 11 4567-8901",
        "email": "pedidos@elaroma.com.ar",
        "direccion": "Av. Corrientes 1234, CABA",
    },
    {
        "id": 2,
        "nombre": "Distribuidora Café Sur",
        "tipo": "B2B",
        "kilos_comprados": 500,
        "tiene_deuda": False,
        "monto_deuda": Decimal("0"),
        "telefono": "+54 11 3210-5555",
        "email": "compras@cafesur.com.ar",
        "direccion": "Ruta 3 Km 45, La Matanza",
    },
    {
        "id": 3,
        "nombre": "María González",
        "tipo": "B2C",
        "kilos_comprados": 5,
        "tiene_deuda": False,
        "monto_deuda": Decimal("0"),
        "telefono": "+54 9 11 6789-0123",
        "email": "maria.gonzalez@email.com",
        "direccion": "Palermo, CABA",
    },
    {
        "id": 4,
        "nombre": "Restaurant La Mesita",
        "tipo": "B2B",
        "kilos_comprados": 80,
        "tiene_deuda": True,
        "monto_deuda": Decimal("120000"),
        "telefono": "+54 11 4455-6677",
        "email": "gerencia@lamesita.com.ar",
        "direccion": "San Telmo, CABA",
    },
    {
        "id": 5,
        "nombre": "Juan Pérez",
        "tipo": "B2C",
        "kilos_comprados": 2,
        "tiene_deuda": False,
        "monto_deuda": Decimal("0"),
        "telefono": "+54 9 11 3344-5566",
        "email": "juan.perez@email.com",
        "direccion": "Belgrano, CABA",
    },
]

STOCK_DEMO = [
    # Café Verde
    {
        "id": 1,
        "tipo": "verde",
        "variedad": "Arábica Bourbon",
        "origen": "Colombia - Huila",
        "precio_kg": Decimal("8500"),
        "lote_principal": "LOTE-2026-001",
        "bolsas": [
            {"id": "b1", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-01-15T10:00:00", "lote_ref": "LOTE-2026-001-A"},
            {"id": "b2", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-01-15T10:00:00", "lote_ref": "LOTE-2026-001-B"},
            {"id": "b3", "estado": "abierta", "kilos": Decimal("30"), "fecha_creacion": "2026-01-15T10:00:00", "lote_ref": "LOTE-2026-001-C"},
        ],
    },
    {
        "id": 2,
        "tipo": "verde",
        "variedad": "Arábica Typica",
        "origen": "Brasil - Minas Gerais",
        "precio_kg": Decimal("7200"),
        "lote_principal": "LOTE-2026-002",
        "bolsas": [
            {"id": "b4", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-01-20T10:00:00", "lote_ref": "LOTE-2026-002-A"},
            {"id": "b5", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-01-20T10:00:00", "lote_ref": "LOTE-2026-002-B"},
            {"id": "b6", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-01-20T10:00:00", "lote_ref": "LOTE-2026-002-C"},
            {"id": "b7", "estado": "abierta", "kilos": Decimal("20"), "fecha_creacion": "2026-01-20T10:00:00", "lote_ref": "LOTE-2026-002-D"},
        ],
    },
    {
        "id": 3,
        "tipo": "verde",
        "variedad": "Robusta",
        "origen": "Vietnam - Dak Lak",
        "precio_kg": Decimal("4800"),
        "lote_principal": "LOTE-2026-003",
        "bolsas": [
            {"id": "b8", "estado": "cerrada", "kilos": Decimal("60"), "fecha_creacion": "2026-02-01T10:00:00", "lote_ref": "LOTE-2026-003-A"},
            {"id": "b9", "estado": "abierta", "kilos": Decimal("40"), "fecha_creacion": "2026-02-01T10:00:00", "lote_ref": "LOTE-2026-003-B"},
        ],
    },
    # Café Tostado
    {
        "id": 4,
        "tipo": "tostado",
        "variedad": "Arábica Bourbon - Tueste Medio",
        "origen": "Colombia - Huila",
        "precio_kg": Decimal("18500"),
        "lote_principal": "TST-2026-001",
        "bolsas": [
            {"id": "b10", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-01"},
            {"id": "b11", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-02"},
            {"id": "b12", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-03"},
            {"id": "b13", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-04"},
            {"id": "b14", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-05"},
            {"id": "b15", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-06"},
            {"id": "b16", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-07"},
            {"id": "b17", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-08"},
            {"id": "b18", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-09"},
            {"id": "b19", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-10"},
            {"id": "b20", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-11"},
            {"id": "b21", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-12"},
            {"id": "b22", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-13"},
            {"id": "b23", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-14"},
            {"id": "b24", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-15"},
            {"id": "b25", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-16"},
            {"id": "b26", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-17"},
            {"id": "b27", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-18"},
            {"id": "b28", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-19"},
            {"id": "b29", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-20"},
            {"id": "b30", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-21"},
            {"id": "b31", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-22"},
            {"id": "b32", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-23"},
            {"id": "b33", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-24"},
            {"id": "b34", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-25"},
            {"id": "b35", "estado": "abierta", "kilos": Decimal("0.5"), "fecha_creacion": "2026-02-10T10:00:00", "lote_ref": "TST-2026-001-26"},
        ],
    },
    {
        "id": 5,
        "tipo": "tostado",
        "variedad": "Blend Casa - Tueste Oscuro",
        "origen": "Brasil + Colombia",
        "precio_kg": Decimal("16200"),
        "lote_principal": "TST-2026-002",
        "bolsas": [
            {"id": "b36", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-01"},
            {"id": "b37", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-02"},
            {"id": "b38", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-03"},
            {"id": "b39", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-04"},
            {"id": "b40", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-05"},
            {"id": "b41", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-06"},
            {"id": "b42", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-07"},
            {"id": "b43", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-08"},
            {"id": "b44", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-09"},
            {"id": "b45", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-10"},
            {"id": "b46", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-11"},
            {"id": "b47", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-12"},
            {"id": "b48", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-13"},
            {"id": "b49", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-14"},
            {"id": "b50", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-15"},
            {"id": "b51", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-16"},
            {"id": "b52", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-17"},
            {"id": "b53", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-18"},
            {"id": "b54", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-19"},
            {"id": "b55", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-20"},
            {"id": "b56", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-21"},
            {"id": "b57", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-22"},
            {"id": "b58", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-23"},
            {"id": "b59", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-24"},
            {"id": "b60", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-25"},
            {"id": "b61", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-26"},
            {"id": "b62", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-27"},
            {"id": "b63", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-28"},
            {"id": "b64", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-29"},
            {"id": "b65", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-30"},
            {"id": "b66", "estado": "abierta", "kilos": Decimal("0.5"), "fecha_creacion": "2026-02-12T10:00:00", "lote_ref": "TST-2026-002-31"},
        ],
    },
    {
        "id": 6,
        "tipo": "tostado",
        "variedad": "Arábica Typica - Tueste Claro",
        "origen": "Brasil - Minas Gerais",
        "precio_kg": Decimal("19800"),
        "lote_principal": "TST-2026-003",
        "bolsas": [
            {"id": "b67", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-01"},
            {"id": "b68", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-02"},
            {"id": "b69", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-03"},
            {"id": "b70", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-04"},
            {"id": "b71", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-05"},
            {"id": "b72", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-06"},
            {"id": "b73", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-07"},
            {"id": "b74", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-08"},
            {"id": "b75", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-09"},
            {"id": "b76", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-10"},
            {"id": "b77", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-11"},
            {"id": "b78", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-12"},
            {"id": "b79", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-13"},
            {"id": "b80", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-14"},
            {"id": "b81", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-15"},
            {"id": "b82", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-16"},
            {"id": "b83", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-17"},
            {"id": "b84", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-18"},
            {"id": "b85", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-19"},
            {"id": "b86", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-20"},
            {"id": "b87", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-21"},
            {"id": "b88", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-22"},
            {"id": "b89", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-23"},
            {"id": "b90", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-24"},
            {"id": "b91", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-25"},
            {"id": "b92", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-26"},
            {"id": "b93", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-27"},
            {"id": "b94", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-28"},
            {"id": "b95", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-29"},
            {"id": "b96", "estado": "cerrada", "kilos": Decimal("1"), "fecha_creacion": "2026-02-14T10:00:00", "lote_ref": "TST-2026-003-30"},
        ],
    },
]

PEDIDOS_DEMO = [
    {
        "id": 1,
        "fecha": "2026-02-10T10:00:00",
        "estado": "Entregado",
        "cliente_id": 1,
        "items": [
            {"stock_id": 4, "variedad": "Arábica Bourbon - Tueste Medio", "kilos": Decimal("20"), "precio_kg": Decimal("18500")},
            {"stock_id": 5, "variedad": "Blend Casa - Tueste Oscuro", "kilos": Decimal("10"), "precio_kg": Decimal("16200")},
        ],
        "medio_contacto": "WhatsApp",
        "observaciones": "Entrega en local antes de las 10am",
        "total": Decimal("532000"),
    },
    {
        "id": 2,
        "fecha": "2026-02-12T10:00:00",
        "estado": "Listo",
        "cliente_id": 2,
        "items": [
            {"stock_id": 4, "variedad": "Arábica Bourbon - Tueste Medio", "kilos": Decimal("50"), "precio_kg": Decimal("18500")},
            {"stock_id": 6, "variedad": "Arábica Typica - Tueste Claro", "kilos": Decimal("30"), "precio_kg": Decimal("19800")},
        ],
        "medio_contacto": "Email",
        "observaciones": "Factura A requerida",
        "total": Decimal("1519000"),
    },
    {
        "id": 3,
        "fecha": "2026-02-14T10:00:00",
        "estado": "Pendiente",
        "cliente_id": 3,
        "items": [
            {"stock_id": 5, "variedad": "Blend Casa - Tueste Oscuro", "kilos": Decimal("2"), "precio_kg": Decimal("16200")},
            {"stock_id": 6, "variedad": "Arábica Typica - Tueste Claro", "kilos": Decimal("1"), "precio_kg": Decimal("19800")},
        ],
        "medio_contacto": "Presencial",
        "observaciones": "Retira en tostaduría",
        "total": Decimal("52200"),
    },
    {
        "id": 4,
        "fecha": "2026-02-15T10:00:00",
        "estado": "Pendiente",
        "cliente_id": 4,
        "items": [
            {"stock_id": 4, "variedad": "Arábica Bourbon - Tueste Medio", "kilos": Decimal("40"), "precio_kg": Decimal("18500")},
        ],
        "medio_contacto": "Teléfono",
        "observaciones": "Urgente - fin de semana",
        "total": Decimal("740000"),
    },
    {
        "id": 5,
        "fecha": "2026-02-16T10:00:00",
        "estado": "Entregado",
        "cliente_id": 5,
        "items": [
            {"stock_id": 5, "variedad": "Blend Casa - Tueste Oscuro", "kilos": Decimal("1"), "precio_kg": Decimal("16200")},
            {"stock_id": 4, "variedad": "Arábica Bourbon - Tueste Medio", "kilos": Decimal("1"), "precio_kg": Decimal("18500")},
        ],
        "medio_contacto": "WhatsApp",
        "observaciones": "",
        "total": Decimal("34700"),
    },
]

GASTOS_DEMO = [
    {
        "id": 1,
        "fecha": "2026-01-15T10:00:00",
        "categoria": "Producción",
        "descripcion": "Compra café verde - Lote 001",
        "monto": Decimal("1275000"),
    },
    {
        "id": 2,
        "fecha": "2026-01-18T10:00:00",
        "categoria": "Producción",
        "descripcion": "Gas y electricidad tueste enero",
        "monto": Decimal("85000"),
    },
    {
        "id": 3,
        "fecha": "2026-01-20T10:00:00",
        "categoria": "Operativo",
        "descripcion": "Alquiler tostaduría enero",
        "monto": Decimal("180000"),
    },
    {
        "id": 4,
        "fecha": "2026-01-25T10:00:00",
        "categoria": "Marketing",
        "descripcion": "Publicidad Instagram/Facebook",
        "monto": Decimal("45000"),
    },
    {
        "id": 5,
        "fecha": "2026-02-01T10:00:00",
        "categoria": "Producción",
        "descripcion": "Compra café verde - Lote 002",
        "monto": Decimal("1440000"),
    },
    {
        "id": 6,
        "fecha": "2026-02-05T10:00:00",
        "categoria": "Operativo",
        "descripcion": "Mantenimiento tostadora",
        "monto": Decimal("120000"),
    },
    {
        "id": 7,
        "fecha": "2026-02-10T10:00:00",
        "categoria": "Operativo",
        "descripcion": "Alquiler tostaduría febrero",
        "monto": Decimal("180000"),
    },
    {
        "id": 8,
        "fecha": "2026-02-12T10:00:00",
        "categoria": "Producción",
        "descripcion": "Bolsas y etiquetado",
        "monto": Decimal("65000"),
    },
]


def seed(database_url: str = None):
    """Ejecuta el seed completo usando SQL directo para máxima compatibilidad."""
    if database_url is None:
        database_url = get_database_url()
    
    print(f"[SEED] Conectando a: {database_url}")
    
    engine = create_engine(database_url)
    
    # Crear tablas si no existen (antes de conectar para SQLite)
    Base.metadata.create_all(bind=engine)
    print("[OK] Tablas creadas/verificadas")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Usuarios (auth)
            print("[SEED] Creando usuarios...")
            conn.execute(text("""
                INSERT INTO usuarios (id, username, email, hashed_password, rol, activo) VALUES
                (1, 'admin', 'admin@cafedefinca.com', :hash_admin, 'admin', true),
                (2, 'operador', 'operador@cafedefinca.com', :hash_op, 'operador', true)
            """), {
                'hash_admin': get_password_hash("admin123"),
                'hash_op': get_password_hash("operador123"),
            })
            
            # 2. Clientes
            print("[SEED] Creando clientes...")
            now = datetime.now().isoformat()
            for c in CLIENTES_DEMO:
                conn.execute(text("""
                    INSERT INTO clientes (id, nombre, tipo, kilos_comprados, tiene_deuda, monto_deuda, telefono, email, direccion, creado_en)
                    VALUES (:id, :nombre, :tipo, :kilos, :tiene_deuda, :deuda, :tel, :email, :dir, :creado)
                """), {
                    'id': c['id'], 'nombre': c['nombre'], 'tipo': c['tipo'],
                    'kilos': c['kilos_comprados'], 'tiene_deuda': c['tiene_deuda'],
                    'deuda': float(c['monto_deuda']), 'tel': c['telefono'],
                    'email': c['email'], 'dir': c['direccion'], 'creado': now,
                })
            
            # 3. Stock
            print("[SEED] Creando stock...")
            for s in STOCK_DEMO:
                # Insert stock
                conn.execute(text("""
                    INSERT INTO stock (id, tipo, variedad, origen, precio_kg, lote_principal, fecha_ingreso, created_at, updated_at)
                    VALUES (:id, :tipo, :var, :origen, :precio, :lote, :now, :now, :now)
                """), {
                    'id': s['id'], 'tipo': s['tipo'], 'var': s['variedad'],
                    'origen': s['origen'], 'precio': float(s['precio_kg']), 'lote': s['lote_principal'],
                    'now': now,
                })
                
                # Insert bolsas
                for b in s['bolsas']:
                    conn.execute(text("""
                        INSERT INTO bolsas (id, stock_id, estado, kilos, fecha_creacion, lote_ref, created_at, updated_at)
                        VALUES (:id, :stock_id, :estado, :kilos, :fecha, :lote_ref, :now, :now)
                    """), {
                        'id': b['id'], 'stock_id': s['id'], 'estado': b['estado'],
                        'kilos': float(b['kilos']), 'fecha': b['fecha_creacion'], 'lote_ref': b['lote_ref'],
                        'now': now,
                    })
            
            # 4. Pedidos
            print("[SEED] Creando pedidos...")
            for p in PEDIDOS_DEMO:
                conn.execute(text("""
                    INSERT INTO pedidos (id, cliente_id, fecha, estado, medio_contacto, observaciones, total, idempotency_key, creado_en)
                    VALUES (:id, :cliente_id, :fecha, :estado, :medio, :obs, :total, :idem, :creado)
                """), {
                    'id': p['id'], 'cliente_id': p['cliente_id'], 'fecha': p['fecha'],
                    'estado': p['estado'], 'medio': p['medio_contacto'],
                    'obs': p['observaciones'], 'total': float(p['total']),
                    'idem': f"seed_{p['id']}", 'creado': p['fecha'],
                })
                
                item_id = p['id'] * 100  # Base para IDs de items
                for idx, item in enumerate(p['items']):
                    item_id = item_id + idx + 1
                    conn.execute(text("""
                        INSERT INTO pedido_items (id, pedido_id, stock_id, variedad, kilos, precio_kg, subtotal, created_at)
                        VALUES (:id, :pid, :sid, :var, :kilos, :precio, :subtotal, :now)
                    """), {
                        'id': item_id,
                        'pid': p['id'], 'sid': item['stock_id'], 'var': item['variedad'],
                        'kilos': float(item['kilos']), 'precio': float(item['precio_kg']),
                        'subtotal': float(item['kilos'] * item['precio_kg']),
                        'now': now,
                    })
                
                # Historial de estado inicial
                hist_id = p['id'] * 1000  # Base para IDs de historial
                conn.execute(text("""
                    INSERT INTO pedido_estado_historial (id, pedido_id, estado_anterior, estado_nuevo, usuario_id, timestamp)
                    VALUES (:id, :pid, NULL, :estado, 1, :ts)
                """), {'id': hist_id, 'pid': p['id'], 'estado': p['estado'], 'ts': p['fecha']})
                
                # Si entregado y B2B, actualizar deuda cliente
                if p['estado'] == 'Entregado':
                    cliente = next((c for c in CLIENTES_DEMO if c['id'] == p['cliente_id']), None)
                    if cliente and cliente['tipo'] == 'B2B':
                        conn.execute(text("""
                            UPDATE clientes SET monto_deuda = monto_deuda + :total WHERE id = :cid
                        """), {'total': float(p['total']), 'cid': p['cliente_id']})
            
            # 5. Gastos
            print("[SEED] Creando gastos...")
            for g in GASTOS_DEMO:
                conn.execute(text("""
                    INSERT INTO gastos (id, fecha, categoria, descripcion, monto, created_at)
                    VALUES (:id, :fecha, :cat, :desc, :monto, :now)
                """), {
                    'id': g['id'], 'fecha': g['fecha'], 'cat': g['categoria'],
                    'desc': g['descripcion'], 'monto': float(g['monto']), 'now': now,
                })
            
            trans.commit()
            print("[OK] Seed completado exitosamente!")
            
        except Exception as e:
            trans.rollback()
            print(f"[ERROR] Error en seed: {e}")
            raise


if __name__ == "__main__":
    seed(get_database_url())