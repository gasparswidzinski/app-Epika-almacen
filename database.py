import sqlite3
from datetime import datetime

DB_NAME = "almacen.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Tabla productos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL,
        movimientos INTEGER DEFAULT 0
    )
    """)

    # Tabla movimientos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        cambio INTEGER NOT NULL,
        precio REAL NOT NULL,
        fecha TEXT NOT NULL,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)
    conn.commit()
    conn.close()

def agregar_o_actualizar_producto(codigo, nombre, cantidad, precio):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id, cantidad, movimientos FROM productos WHERE codigo = ?", (codigo,))
    producto = cur.fetchone()

    if producto:  # existe → actualizar stock
        new_cant = producto[1] + cantidad
        new_movs = producto[2] + 1
        cur.execute("UPDATE productos SET cantidad=?, precio=?, movimientos=? WHERE id=?",
                    (new_cant, precio, new_movs, producto[0]))
        producto_id = producto[0]
    else:  # nuevo producto
        cur.execute("INSERT INTO productos (codigo, nombre, cantidad, precio, movimientos) VALUES (?, ?, ?, ?, ?)",
                    (codigo, nombre, cantidad, precio, 1))
        producto_id = cur.lastrowid

    cur.execute("INSERT INTO movimientos (producto_id, cambio, precio, fecha) VALUES (?, ?, ?, ?)",
                (producto_id, cantidad, precio, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def modificar_stock(producto_id, cambio):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT cantidad, precio, movimientos FROM productos WHERE id=?", (producto_id,))
    prod = cur.fetchone()
    if not prod:
        conn.close()
        return False

    new_cant = prod[0] + cambio
    if new_cant < 0:
        conn.close()
        return False

    cur.execute("UPDATE productos SET cantidad=?, movimientos=? WHERE id=?",
                (new_cant, prod[2]+1, producto_id))
    cur.execute("INSERT INTO movimientos (producto_id, cambio, precio, fecha) VALUES (?, ?, ?, ?)",
                (producto_id, cambio, prod[1], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return True

def eliminar_producto(producto_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM productos WHERE id=?", (producto_id,))
    producto = cur.fetchone()

    cur.execute("DELETE FROM productos WHERE id=?", (producto_id,))

    if producto:
        cur.execute("INSERT INTO movimientos (producto_id, cambio, precio, fecha) VALUES (?, ?, ?, ?)",
                    (producto[0], 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def obtener_productos():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, codigo, nombre, cantidad, precio, movimientos FROM productos")
    data = cur.fetchall()
    conn.close()
    return data

def obtener_movimientos():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.nombre, m.cambio, m.precio, m.fecha
        FROM movimientos m
        JOIN productos p ON p.id = m.producto_id
        ORDER BY m.id DESC LIMIT 10
    """)
    data = cur.fetchall()
    conn.close()
    return data

def editar_producto(id_, nombre, cantidad, precio):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Actualizamos producto
    cur.execute("UPDATE productos SET nombre=?, cantidad=?, precio=? WHERE id=?",
                (nombre, cantidad, precio, id_))

    # Registramos movimiento de edición (cambio=0 solo para dejar registro)
    cur.execute("INSERT INTO movimientos (producto_id, cambio, precio, fecha) VALUES (?, ?, ?, ?)",
                (id_, 0, precio, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def obtener_ventas(fecha_inicio, fecha_fin):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.codigo, p.nombre, m.cambio, m.precio, m.fecha
        FROM movimientos m
        JOIN productos p ON p.id = m.producto_id
        WHERE m.cambio < 0 AND date(m.fecha) BETWEEN date(?) AND date(?)
        ORDER BY m.fecha ASC
    """, (fecha_inicio, fecha_fin))
    data = cur.fetchall()
    conn.close()
    return data
