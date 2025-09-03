# database.py
import sqlite3
from datetime import datetime

DB_NAME = "almacen.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

# -----------------------------
# Inicialización / migración
# -----------------------------
def inicializar_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabla sectores
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sectores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        margen REAL NOT NULL
    )
    """)

    # Tabla productos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 0,
        costo REAL DEFAULT 0,
        sector_id INTEGER,
        precio REAL DEFAULT 0,
        codigo_barras TEXT,
        movimientos INTEGER DEFAULT 0,
        FOREIGN KEY(sector_id) REFERENCES sectores(id)
    )
    """)

    # Tabla movimientos (historial detallado)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        tipo TEXT NOT NULL,        -- 'INGRESO','VENTA','EDIT','ELIM','REEMBOLSO'
        cambio INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        fecha TEXT NOT NULL,
        detalles TEXT,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Tabla ventas (para fases siguientes / compatibilidad)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        tipo_pago TEXT,
        estado TEXT,
        total REAL,
        efectivo_recibido REAL,
        vuelto REAL,
        cliente TEXT
    )
    """)

    # Tabla venta_items (para fases siguientes)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        cantidad INTEGER,
        precio_unitario REAL,
        subtotal REAL,
        FOREIGN KEY(venta_id) REFERENCES ventas(id),
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Semillas de sectores por defecto
    default = [
        ("Fiambreria", 0.60),
        ("Panaderia", 0.40),
        ("Lacteos", 0.35),
        ("Almacen", 0.30)
    ]
    for nombre, margen in default:
        try:
            cur.execute("INSERT INTO sectores (nombre, margen) VALUES (?, ?)", (nombre, margen))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

# Alias por compatibilidad
init_db = inicializar_db

# -----------------------------
# SECTORES
# -----------------------------
def obtener_sectores():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, margen FROM sectores ORDER BY nombre")
    data = cur.fetchall()
    conn.close()
    return data

def agregar_sector(nombre, margen):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO sectores (nombre, margen) VALUES (?, ?)", (nombre, margen))
    conn.commit()
    conn.close()

def editar_sector(id_sector, nombre, margen):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE sectores SET nombre=?, margen=? WHERE id=?", (nombre, margen, id_sector))
    conn.commit()
    conn.close()

def eliminar_sector(id_sector):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sectores WHERE id=?", (id_sector,))
    conn.commit()
    conn.close()

def obtener_margen_sector(id_sector):
    if id_sector is None:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT margen FROM sectores WHERE id=?", (id_sector,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

# -----------------------------
# MOVIMIENTOS (historial)
# -----------------------------
def agregar_movimiento(producto_id, tipo, cambio, precio_unitario, detalles=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movimientos (producto_id, tipo, cambio, precio_unitario, fecha, detalles) VALUES (?, ?, ?, ?, ?, ?)",
        (producto_id, tipo, cambio, precio_unitario, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detalles)
    )
    conn.commit()
    conn.close()

def obtener_movimientos(limit=100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, p.nombre, m.tipo, m.cambio, m.precio_unitario, m.fecha, m.detalles
        FROM movimientos m
        LEFT JOIN productos p ON p.id = m.producto_id
        ORDER BY m.id DESC
        LIMIT ?
    """, (limit,))
    data = cur.fetchall()
    conn.close()
    return data

# -----------------------------
# PRODUCTOS
# -----------------------------
def agregar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras):
    # calcula precio según margen del sector
    margen = obtener_margen_sector(sector_id)
    precio = round(costo + (costo * margen), 2) if costo is not None else 0.0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO productos (codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, movimientos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, 0))
    producto_id = cur.lastrowid
    conn.commit()
    conn.close()

    # registrar movimiento de ingreso
    agregar_movimiento(producto_id, "INGRESO", cantidad, precio, detalles="Alta/Ingreso inicial")
    return producto_id

def agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id=None, codigo_barras=""):
    """
    Compatibilidad: si existe un producto con el mismo codigo -> suma cantidad (ingreso).
    Si no existe -> crea nuevo producto. Calcula precio por sector.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cantidad, costo, sector_id FROM productos WHERE codigo = ?", (codigo,))
    row = cur.fetchone()

    if row:
        producto_id = row[0]
        new_cant = (row[1] or 0) + cantidad
        # si se pasa costo/sector, actualizarlos; si no, mantener
        costo_final = costo if costo is not None else (row[2] or 0)
        sector_final = sector_id if sector_id is not None else row[3]

        margen = obtener_margen_sector(sector_final)
        precio = round(costo_final + (costo_final * margen), 2) if costo_final is not None else 0.0

        cur.execute("UPDATE productos SET cantidad=?, costo=?, sector_id=?, precio=?, codigo_barras=? WHERE id=?",
                    (new_cant, costo_final, sector_final, precio, codigo_barras, producto_id))
        conn.commit()
        conn.close()

        agregar_movimiento(producto_id, "INGRESO", cantidad, precio, detalles="Ingreso por import/alta")
        return producto_id
    else:
        conn.close()
        return agregar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras)

def editar_producto(id_producto, codigo, nombre, cantidad, costo, sector_id, codigo_barras):
    margen = obtener_margen_sector(sector_id)
    precio = round(costo + (costo * margen), 2) if costo is not None else 0.0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE productos
        SET codigo=?, nombre=?, cantidad=?, costo=?, sector_id=?, precio=?, codigo_barras=?
        WHERE id=?
    """, (codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, id_producto))
    conn.commit()
    conn.close()

    agregar_movimiento(id_producto, "EDIT", 0, precio, detalles="Edición de producto")

def eliminar_producto(id_producto):
    # obtener datos antes de eliminar para movimiento
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nombre, precio FROM productos WHERE id=?", (id_producto,))
    row = cur.fetchone()
    cur.execute("DELETE FROM productos WHERE id=?", (id_producto,))
    conn.commit()
    conn.close()

    if row:
        agregar_movimiento(id_producto, "ELIM", 0, row[1] if row[1] else 0, detalles=f"Eliminado: {row[0]}")

def obtener_productos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.codigo, p.nombre, p.cantidad, p.costo,
               COALESCE(s.nombre, '') as sector, p.precio, COALESCE(p.codigo_barras, ''), p.movimientos
        FROM productos p
        LEFT JOIN sectores s ON p.sector_id = s.id
        ORDER BY p.nombre COLLATE NOCASE
    """)
    data = cur.fetchall()
    conn.close()
    return data

# -----------------------------
# STOCK / VENTAS (compatibilidad)
# -----------------------------
def modificar_stock(producto_id, cantidad_cambio, descripcion=""):
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener datos actuales del producto (cantidad, nombre y precio)
    cursor.execute("SELECT cantidad, nombre, precio FROM productos WHERE id=?", (producto_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return False

    nueva_cantidad = prod[0] + cantidad_cambio
    if nueva_cantidad < 0:
        conn.close()
        return False  # no puede quedar negativo

    # Actualizar cantidad en productos
    cursor.execute("UPDATE productos SET cantidad=? WHERE id=?", (nueva_cantidad, producto_id))
    conn.commit()
    conn.close()

    # Registrar movimiento usando la función ya existente
    agregar_movimiento(
        producto_id=producto_id,
        tipo="VENTA" if cantidad_cambio < 0 else "INGRESO",
        cambio=cantidad_cambio,
        precio_unitario=prod[2] if prod[2] is not None else 0.0,
        detalles=descripcion if descripcion else f"Cambio de stock: {cantidad_cambio}"
    )

    return True

def obtener_ventas(fecha_inicio, fecha_fin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.codigo, p.nombre, m.cambio, m.precio_unitario, m.fecha
        FROM movimientos m
        JOIN productos p ON p.id = m.producto_id
        WHERE m.tipo = 'VENTA' AND date(m.fecha) BETWEEN date(?) AND date(?)
        ORDER BY m.fecha ASC
    """, (fecha_inicio, fecha_fin))
    data = cur.fetchall()
    conn.close()
    return data
