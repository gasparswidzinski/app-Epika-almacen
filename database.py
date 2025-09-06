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

    # Tabla sectores (si no existe)
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

    # Tabla movimientos (historial)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        tipo TEXT NOT NULL,
        cambio INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        fecha TEXT NOT NULL,
        detalles TEXT,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Tabla ventas (mantenemos la columna 'cliente' por compatibilidad)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        tipo_pago TEXT NOT NULL,
        estado TEXT NOT NULL,
        total REAL NOT NULL,
        efectivo_recibido REAL,
        vuelto REAL,
        cliente TEXT
    )
    """)

    # Si no existe la columna cliente_id la agregamos (migración)
    cur.execute("PRAGMA table_info(ventas)")
    cols = [r[1] for r in cur.fetchall()]
    if "cliente_id" not in cols:
        try:
            cur.execute("ALTER TABLE ventas ADD COLUMN cliente_id INTEGER")
        except Exception:
            pass

    # Tabla items de venta
    cur.execute("""
    CREATE TABLE IF NOT EXISTS venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(venta_id) REFERENCES ventas(id),
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Tabla clientes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT,
        direccion TEXT,
        notas TEXT
    )
    """)

    # Tabla cobros (cuando se cobran ventas pendientes)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cobros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        cliente_id INTEGER,
        fecha TEXT,
        monto REAL,
        tipo_pago TEXT,
        FOREIGN KEY(venta_id) REFERENCES ventas(id),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)

    # Semillas sectores (si no existen)
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

# Alias
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
        return 0.0
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT margen FROM sectores WHERE id=?", (id_sector,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0.0

# -----------------------------
# MOVIMIENTOS
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
    margen = obtener_margen_sector(sector_id)
    precio = round((costo or 0.0) + ((costo or 0.0) * (margen or 0.0)), 2)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO productos (codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, movimientos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, 0))
    producto_id = cur.lastrowid
    conn.commit()
    conn.close()

    agregar_movimiento(producto_id, "INGRESO", cantidad, precio, detalles="Alta/Ingreso inicial")
    return producto_id

def agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id=None, codigo_barras=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cantidad, costo, sector_id FROM productos WHERE codigo = ?", (codigo,))
    row = cur.fetchone()

    if row:
        producto_id = row[0]
        new_cant = (row[1] or 0) + cantidad
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
    precio = round((costo or 0.0) + ((costo or 0.0) * (margen or 0.0)), 2)

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
# STOCK / VENTAS
# -----------------------------
def modificar_stock(producto_id, cantidad_cambio, detalles=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT cantidad, precio FROM productos WHERE id=?", (producto_id,))
    prod = cur.fetchone()
    if not prod:
        conn.close()
        return False

    nueva = (prod[0] or 0) + cantidad_cambio
    if nueva < 0:
        conn.close()
        return False

    cur.execute("UPDATE productos SET cantidad=? WHERE id=?", (nueva, producto_id))
    conn.commit()
    conn.close()

    tipo = "VENTA" if cantidad_cambio < 0 else "INGRESO"
    agregar_movimiento(producto_id, tipo, cantidad_cambio, prod[1] or 0.0, detalles=detalles)
    return True

# -----------------------------
# CLIENTES (nueva funcionalidad FASE 2)
# -----------------------------
def agregar_cliente(nombre, telefono="", direccion="", notas=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO clientes (nombre, telefono, direccion, notas) VALUES (?, ?, ?, ?)",
                (nombre, telefono, direccion, notas))
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return cid

def editar_cliente(cid, nombre, telefono="", direccion="", notas=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE clientes SET nombre=?, telefono=?, direccion=?, notas=? WHERE id=?",
                (nombre, telefono, direccion, notas, cid))
    conn.commit()
    conn.close()

def eliminar_cliente(cid):
    conn = get_connection()
    cur = conn.cursor()
    # OJO: si hay ventas asociadas, dejar la referencia o prevenir eliminación según política
    cur.execute("DELETE FROM clientes WHERE id=?", (cid,))
    conn.commit()
    conn.close()

def obtener_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, telefono, direccion, notas FROM clientes ORDER BY nombre")
    data = cur.fetchall()
    conn.close()
    return data

def obtener_clientes_con_saldo():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.nombre, COALESCE(SUM(v.total),0) as deuda, COUNT(v.id) as cant_pendientes
        FROM clientes c
        LEFT JOIN ventas v ON v.cliente_id = c.id AND v.estado='PENDIENTE'
        GROUP BY c.id
        ORDER BY deuda DESC
    """)
    data = cur.fetchall()
    conn.close()
    return data

# -----------------------------
# VENTAS
# -----------------------------
def registrar_venta(items, tipo_pago, cliente=None, efectivo_recibido=None):
    """
    items: list of dicts: {"producto_id": id, "cantidad": n, "precio_unitario": p}
    tipo_pago: 'Efectivo'|'Transferencia'|'QR'|'Pendiente'
    cliente: None | cliente_id (int) | cliente_nombre (str)
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        total = round(sum(it["cantidad"] * it["precio_unitario"] for it in items), 2)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado = "PAGADO" if tipo_pago != "Pendiente" else "PENDIENTE"
        vuelto = None

        # resolver cliente: obtener cliente_id y cliente_text
        cliente_id = None
        cliente_text = ""
        if cliente is not None:
            if isinstance(cliente, int):
                cliente_id = cliente
                cur.execute("SELECT nombre FROM clientes WHERE id=?", (cliente_id,))
                r = cur.fetchone()
                cliente_text = r[0] if r else ""
            else:
                # string
                cliente_text = str(cliente)

        # Iniciar transacción
        cur.execute("BEGIN")
        cur.execute("""
            INSERT INTO ventas (fecha, tipo_pago, estado, total, efectivo_recibido, vuelto, cliente, cliente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (fecha, tipo_pago, estado, total, efectivo_recibido, vuelto, cliente_text, cliente_id))
        venta_id = cur.lastrowid

        # procesar items: verificar stock y descontar
        for it in items:
            pid = it["producto_id"]
            cant = it["cantidad"]
            precio_unit = it["precio_unitario"]
            subtotal = round(cant * precio_unit, 2)

            # verificar stock actual
            cur.execute("SELECT cantidad, precio FROM productos WHERE id=?", (pid,))
            prod = cur.fetchone()
            if not prod:
                raise Exception(f"Producto id {pid} no encontrado")
            current = prod[0] or 0
            if current - cant < 0:
                raise Exception(f"Stock insuficiente para {pid}")

            # descontar stock
            cur.execute("UPDATE productos SET cantidad=? WHERE id=?", (current - cant, pid))

            # insertar item
            cur.execute("""
                INSERT INTO venta_items (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (venta_id, pid, cant, precio_unit, subtotal))

            # registrar movimiento tipo VENTA (cantidad negativa)
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cambio, precio_unitario, fecha, detalles) VALUES (?, ?, ?, ?, ?, ?)",
                        (pid, "VENTA", -cant, precio_unit, fecha, f"Venta ID {venta_id}"))

        conn.commit()
        conn.close()
        return True, venta_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def obtener_ventas(fecha_inicio=None, fecha_fin=None, estado=None):
    conn = get_connection()
    cur = conn.cursor()
    q = """
        SELECT v.id, v.fecha, v.tipo_pago, v.estado, v.total, v.efectivo_recibido, v.vuelto,
               COALESCE(c.nombre, v.cliente) as cliente
        FROM ventas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        WHERE 1=1
    """
    params = []
    if fecha_inicio and fecha_fin:
        q += " AND date(v.fecha) BETWEEN date(?) AND date(?)"
        params.extend([fecha_inicio, fecha_fin])
    if estado:
        q += " AND v.estado = ?"
        params.append(estado)
    q += " ORDER BY v.fecha DESC"
    cur.execute(q, tuple(params))
    data = cur.fetchall()
    conn.close()
    return data

def obtener_items_venta(venta_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT vi.id, vi.producto_id, p.nombre, vi.cantidad, vi.precio_unitario, vi.subtotal
        FROM venta_items vi
        JOIN productos p ON p.id = vi.producto_id
        WHERE vi.venta_id = ?
    """, (venta_id,))
    data = cur.fetchall()
    conn.close()
    return data

def obtener_ventas_pendientes():
    return obtener_ventas(estado="PENDIENTE")

def marcar_venta_pagada(venta_id, tipo_pago_nuevo=None, recibido=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT estado, total, cliente_id FROM ventas WHERE id=?", (venta_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Venta no encontrada"
    estado_actual = row[0]
    total = row[1] or 0.0
    cliente_id = row[2]

    if estado_actual == "PAGADO":
        conn.close()
        return False, "Venta ya está pagada"

    nuevo_tipo = tipo_pago_nuevo if tipo_pago_nuevo else "Efectivo"
    vuelto = None
    if recibido is not None:
        vuelto = round(recibido - total, 2)

    cur.execute("UPDATE ventas SET estado=?, tipo_pago=?, efectivo_recibido=?, vuelto=? WHERE id=?",
                ("PAGADO", nuevo_tipo, recibido, vuelto, venta_id))

    # insertar registro de cobro
    cur.execute("INSERT INTO cobros (venta_id, cliente_id, fecha, monto, tipo_pago) VALUES (?, ?, ?, ?, ?)",
                (venta_id, cliente_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, nuevo_tipo))

    conn.commit()
    conn.close()
    return True, "Venta marcada como pagada"

def reembolsar_venta(venta_id, items_to_refund=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, fecha, total FROM ventas WHERE id=?", (venta_id,))
        venta = cur.fetchone()
        if not venta:
            conn.close()
            return False, "Venta no encontrada"

        if items_to_refund is None:
            cur.execute("SELECT id, producto_id, cantidad, precio_unitario, subtotal FROM venta_items WHERE venta_id=?", (venta_id,))
            items = cur.fetchall()
        else:
            placeholders = ",".join("?" for _ in items_to_refund)
            cur.execute(f"SELECT id, producto_id, cantidad, precio_unitario, subtotal FROM venta_items WHERE id IN ({placeholders})", tuple(items_to_refund))
            items = cur.fetchall()

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for itm in items:
            vi_id, pid, cant, precio_unit, subtotal = itm
            cur.execute("SELECT cantidad FROM productos WHERE id=?", (pid,))
            row = cur.fetchone()
            current = row[0] if row else 0
            cur.execute("UPDATE productos SET cantidad=? WHERE id=?", (current + cant, pid))
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cambio, precio_unitario, fecha, detalles) VALUES (?, ?, ?, ?, ?, ?)",
                        (pid, "REEMBOLSO", cant, precio_unit, fecha, f"Reembolso de venta {venta_id}"))

        conn.commit()
        conn.close()
        return True, "Reembolso procesado"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

# -----------------------------
# Reportes: ventas agrupadas por tipo de pago
# -----------------------------
def ventas_resumen_por_tipo(fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    cur = conn.cursor()
    q = "SELECT tipo_pago, SUM(total) as total, COUNT(*) as cantidad FROM ventas WHERE 1=1"
    params = []
    if fecha_inicio and fecha_fin:
        q += " AND date(fecha) BETWEEN date(?) AND date(?)"
        params.extend([fecha_inicio, fecha_fin])
    q += " GROUP BY tipo_pago"
    cur.execute(q, tuple(params))
    data = cur.fetchall()
    conn.close()
    return data

def obtener_ventas_con_detalles():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ventas ORDER BY fecha")
    ventas = cursor.fetchall()

    resultado = []
    for v in ventas:
        venta_id = v[0]
        cursor.execute("""
            SELECT vi.cantidad, vi.precio_unitario, (vi.cantidad * vi.precio_unitario) as subtotal, p.nombre
            FROM venta_items vi
            JOIN productos p ON vi.producto_id = p.id
            WHERE vi.venta_id=?
        """, (venta_id,))
        items = cursor.fetchall()

        # cliente display
        cliente_display = None
        if len(v) >= 9:
            # if cliente_id column exists, prefer lookup
            try:
                cur2 = conn.cursor()
                cur2.execute("SELECT nombre FROM clientes WHERE id=?", (v[8],))
                r = cur2.fetchone()
                if r:
                    cliente_display = r[0]
            except Exception:
                pass
        if not cliente_display:
            cliente_display = v[7] if len(v) >= 8 else ""

        resultado.append({
            "id": v[0],
            "fecha": v[1],
            "tipo_pago": v[2],
            "estado": v[3],
            "total": v[4],
            "recibido": v[5],
            "vuelto": v[6],
            "cliente": cliente_display,
            "items": [
                {"cantidad": it[0], "precio": it[1], "subtotal": it[2], "nombre": it[3]}
                for it in items
            ]
        })

    conn.close()
    return resultado

def obtener_producto_por_barcode(codigo_barras):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.codigo, p.nombre, p.cantidad, p.costo,
               COALESCE(s.nombre, '') as sector, p.precio, COALESCE(p.codigo_barras, ''), p.movimientos
        FROM productos p
        LEFT JOIN sectores s ON p.sector_id = s.id
        WHERE p.codigo_barras = ?
    """, (codigo_barras,))
    prod = cur.fetchone()
    conn.close()
    return prod

