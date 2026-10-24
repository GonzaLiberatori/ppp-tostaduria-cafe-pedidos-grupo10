import sqlite3
import os

DB_PATH = "db.sqlite"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")

# 1. Tabla: cuenta
cursor.execute("""
CREATE TABLE IF NOT EXISTS cuenta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rol TEXT NOT NULL CHECK (rol IN ('Cliente', 'Administrador', 'Cajero', 'Operario')),
    correo TEXT NOT NULL UNIQUE,
    clave TEXT NOT NULL
);
""")

# 2. Tabla: persona
cursor.execute("""
CREATE TABLE IF NOT EXISTS persona (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    CUIT TEXT UNIQUE,
    telefono TEXT NOT NULL UNIQUE,
    cuenta_id INTEGER,
    FOREIGN KEY (cuenta_id) REFERENCES cuenta(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 3. Tabla: cliente
cursor.execute("""
CREATE TABLE IF NOT EXISTS cliente (
    persona_id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('Mayorista', 'Consumidor Final')),
    direccion_de_entrega TEXT,
    FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 4. Tabla: empleado
cursor.execute("""
CREATE TABLE IF NOT EXISTS empleado (
    persona_id INTEGER PRIMARY KEY,
    fecha_de_contratacion DATE NOT NULL,
    fecha_de_nacimiento DATE NOT NULL,
    salario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (persona_id) REFERENCES persona(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 5. Tabla: pais
cursor.execute("""
CREATE TABLE IF NOT EXISTS pais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);
""")

# 6. Tabla: region
cursor.execute("""
CREATE TABLE IF NOT EXISTS region (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    pais_id INTEGER NOT NULL,
    FOREIGN KEY (pais_id) REFERENCES pais(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 7. Tabla: variedad
cursor.execute("""
CREATE TABLE IF NOT EXISTS variedad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);
""")

# 8. Tabla: tipo_de_cafe
cursor.execute("""
CREATE TABLE IF NOT EXISTS tipo_de_cafe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organico INTEGER NOT NULL CHECK (organico IN (0, 1)),
    precio_por_kg_verde DECIMAL(10,2) NOT NULL,
    region_id INTEGER NOT NULL,
    variedad_id INTEGER NOT NULL,
    FOREIGN KEY (region_id) REFERENCES region(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (variedad_id) REFERENCES variedad(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 9. Tabla: blend
cursor.execute("""
CREATE TABLE IF NOT EXISTS blend (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    precio_por_kg_verde DECIMAL(10,2) NOT NULL,
    Descripcion TEXT NOT NULL
);
""")

# 10. Tabla: blend_has_tipo_de_cafe
cursor.execute("""
CREATE TABLE IF NOT EXISTS blend_has_tipo_de_cafe (
    blend_id INTEGER NOT NULL,
    tipo_de_cafe_id INTEGER NOT NULL,
    porcentaje DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (blend_id, tipo_de_cafe_id),
    FOREIGN KEY (blend_id) REFERENCES blend(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (tipo_de_cafe_id) REFERENCES tipo_de_cafe(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 11. Tabla: molienda
cursor.execute("""
CREATE TABLE IF NOT EXISTS molienda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL UNIQUE,
    valor_agregado_por_kg DECIMAL(10,2) NOT NULL DEFAULT 0
);
""")

# 12. Tabla: perfil_de_tostado
cursor.execute("""
CREATE TABLE IF NOT EXISTS perfil_de_tostado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante TEXT NOT NULL,
    valor_agregado_por_kg DECIMAL(10,2) NOT NULL DEFAULT 0
);
""")

# 13. Tabla: orden_tueste
cursor.execute("""
CREATE TABLE IF NOT EXISTS orden_tueste (
    id INTEGER PRIMARY KEY,
    fecha_tueste DATETIME NOT NULL,
    kg_gastados DECIMAL(10,2) NOT NULL,
    kg_obtenidos DECIMAL(10,2) NOT NULL,
    perfil_de_tostado_id INTEGER NOT NULL,
    FOREIGN KEY (perfil_de_tostado_id) REFERENCES perfil_de_tostado(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 14. Tabla: lote
cursor.execute("""
CREATE TABLE IF NOT EXISTS lote (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('VERDE', 'TOSTADO')),
    estado TEXT NOT NULL CHECK (estado IN ('CERRADO', 'ABIERTO')),
    fecha_vencimiento DATETIME NOT NULL,
    humedad DECIMAL(5,2) NOT NULL,
    kg_disponibles DECIMAL(10,2) NOT NULL,
    kg_reales DECIMAL(10,2) NOT NULL,
    ubicacion_fisica TEXT NOT NULL,
    observaciones TEXT,
    tipo_de_cafe_id INTEGER,
    blend_id INTEGER,
    orden_tueste_id INTEGER,
    FOREIGN KEY (tipo_de_cafe_id) REFERENCES tipo_de_cafe(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (blend_id) REFERENCES blend(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (orden_tueste_id) REFERENCES orden_tueste(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 15. Tabla: pedido
cursor.execute("""
CREATE TABLE IF NOT EXISTS pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATETIME NOT NULL,
    metodo_de_despacho TEXT NOT NULL CHECK (metodo_de_despacho IN ('Retiro en local', 'Envio propio', 'Transporte externo')),
    estado TEXT NOT NULL CHECK (estado IN ('PENDIENTE', 'LISTO', 'ENTREGADO')),
    total DECIMAL(10,2) NOT NULL,
    cliente_persona_id INTEGER NOT NULL,
    empleado_persona_id INTEGER NOT NULL,
    FOREIGN KEY (cliente_persona_id) REFERENCES cliente(persona_id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (empleado_persona_id) REFERENCES empleado(persona_id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 16. Tabla: detalle_pedido
cursor.execute("""
CREATE TABLE IF NOT EXISTS detalle_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cantidad_kg DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    pedido_id INTEGER NOT NULL,
    tipo_de_cafe_id INTEGER,
    blend_id INTEGER,
    molienda_id INTEGER,
    perfil_de_tostado_id INTEGER,
    FOREIGN KEY (pedido_id) REFERENCES pedido(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (tipo_de_cafe_id) REFERENCES tipo_de_cafe(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (blend_id) REFERENCES blend(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (molienda_id) REFERENCES molienda(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (perfil_de_tostado_id) REFERENCES perfil_de_tostado(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

# 17. Tabla: pago
cursor.execute("""
CREATE TABLE IF NOT EXISTS pago (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metodo_de_pago TEXT NOT NULL CHECK (metodo_de_pago IN ('EFECTIVO', 'CREDITO', 'DEBITO', 'TRANSFERENCIA', 'MERCADO_PAGO', 'CHEQUE', 'OTRO')),
    porcentaje_pagado DECIMAL(5,2) NOT NULL,
    moneda TEXT NOT NULL CHECK (moneda IN ('ARS', 'USD', 'EUR', 'BRL')),
    aclaracion TEXT
);
""")

# 18. Tabla: venta
cursor.execute("""
CREATE TABLE IF NOT EXISTS venta (
    id INTEGER PRIMARY KEY,
    fecha DATETIME NOT NULL,
    facturacion TEXT NOT NULL CHECK (facturacion IN ('Factura A', 'Consumidor Final', 'Ticket', 'No requiere')),
    pedido_id INTEGER NOT NULL,
    pago_id INTEGER NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedido(id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY (pago_id) REFERENCES pago(id) ON DELETE NO ACTION ON UPDATE NO ACTION
);
""")

conn.commit()
conn.close()
print(f"Base de datos SQLite creada en: {DB_PATH}")