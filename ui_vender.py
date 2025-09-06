from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QLineEdit, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem,
    QFormLayout, QDialogButtonBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
import database


class FormularioPOS(QDialog):
    def __init__(self, parent=None, producto_preseleccionado=None):
        super().__init__(parent)
        self.setWindowTitle("Punto de Venta - Registrar Venta")
        self.resize(780, 520)

        self.cart = []

        layout = QVBoxLayout()

        # Cliente selector
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        cliente_layout.addWidget(self.combo_cliente)
        self.btn_nuevo_cliente = QPushButton("➕ Nuevo")
        cliente_layout.addWidget(self.btn_nuevo_cliente)
        layout.addLayout(cliente_layout)
        self.btn_nuevo_cliente.clicked.connect(self._crear_cliente_rapido)
        self._cargar_clientes()

        # Buscador por código, nombre o barcode
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar (Código / Nombre / Barcode):"))
        self.input_buscar = QLineEdit()
        search_layout.addWidget(self.input_buscar)
        self.btn_buscar = QPushButton("Buscar")
        search_layout.addWidget(self.btn_buscar)
        layout.addLayout(search_layout)

        # Conexiones búsqueda (scanner + botón)
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._buscar_producto)
        self.btn_buscar.clicked.connect(self._buscar_producto)
        self.input_buscar.returnPressed.connect(self._buscar_producto)
        self.input_buscar.textChanged.connect(self._on_text_changed)

        # Tabla carrito
        self.table_cart = QTableWidget()
        self.table_cart.setColumnCount(5)
        self.table_cart.setHorizontalHeaderLabels(["Producto ID", "Código", "Nombre", "Cantidad", "Precio Unit."])
        layout.addWidget(self.table_cart)

        # Agregar manualmente cantidad
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Cantidad a agregar:"))
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 10000)
        self.spin_cant.setValue(1)
        add_layout.addWidget(self.spin_cant)
        self.btn_agregar = QPushButton("➕ Agregar al carrito")
        add_layout.addWidget(self.btn_agregar)
        layout.addLayout(add_layout)
        self.btn_agregar.clicked.connect(self._agregar_al_carrito)

        # Tipo de pago
        pay_layout = QHBoxLayout()
        pay_layout.addWidget(QLabel("Tipo de pago:"))
        self.combo_pago = QComboBox()
        for t in ["Efectivo", "Transferencia", "QR", "Pendiente"]:
            self.combo_pago.addItem(t)
        pay_layout.addWidget(self.combo_pago)

        pay_layout.addWidget(QLabel("Monto recibido (si efectivo):"))
        self.input_recibido = QLineEdit()
        self.input_recibido.setPlaceholderText("0.00")
        pay_layout.addWidget(self.input_recibido)

        layout.addLayout(pay_layout)

        # Totales y botones
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        bottom.addWidget(self.lbl_total)
        self.btn_confirm = QPushButton("✅ Confirmar Venta")
        self.btn_confirm.setShortcut(QKeySequence("F10"))
        bottom.addWidget(self.btn_confirm)
        self.btn_cancel = QPushButton("❌ Cancelar")
        bottom.addWidget(self.btn_cancel)
        layout.addLayout(bottom)

        self.setLayout(layout)

        # Conexiones principales
        self.btn_confirm.clicked.connect(self._confirmar_venta)
        self.btn_cancel.clicked.connect(self.reject)
        self.combo_pago.currentIndexChanged.connect(self._on_pago_change)
        self.input_recibido.textChanged.connect(self._calcular_vuelto)

        self._ultimo_producto = None

        # 🔧 FIX: evitar que Enter dispare botones por defecto
        self.btn_nuevo_cliente.setAutoDefault(False)
        self.btn_buscar.setAutoDefault(False)
        self.btn_agregar.setAutoDefault(False)
        self.btn_confirm.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)

        # Producto preseleccionado (primer escaneo desde ui_main)
        if producto_preseleccionado:
            try:
                pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = producto_preseleccionado
                if int(cantidad) > 0:
                    self._ultimo_producto = {
                        "id": pid, "codigo": codigo, "nombre": nombre,
                        "stock": int(cantidad), "precio": float(precio)
                    }
                    self._agregar_al_carrito(cant_override=1, clear_search=False)
            except Exception:
                pass
        
        QTimer.singleShot(0, self.input_buscar.setFocus)

    # ---------------- Clientes ----------------
    def _cargar_clientes(self):
        self.combo_cliente.clear()
        self.combo_cliente.addItem("(Sin cliente)", None)
        for c in database.obtener_clientes():
            self.combo_cliente.addItem(c[1], c[0])

    def _crear_cliente_rapido(self):
        d = QDialog(self)
        d.setWindowTitle("Crear cliente")
        form = QFormLayout(d)
        inp_nombre = QLineEdit()
        inp_telefono = QLineEdit()
        inp_direccion = QLineEdit()
        inp_notas = QLineEdit()
        form.addRow("Nombre:", inp_nombre)
        form.addRow("Teléfono:", inp_telefono)
        form.addRow("Dirección:", inp_direccion)
        form.addRow("Notas:", inp_notas)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        form.addRow(buttons)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        if d.exec():
            nombre = inp_nombre.text().strip()
            if not nombre:
                QMessageBox.warning(self, "Cliente", "El nombre es obligatorio")
                return
            telefono = inp_telefono.text().strip()
            direccion = inp_direccion.text().strip()
            notas = inp_notas.text().strip()
            cid = database.agregar_cliente(nombre, telefono, direccion, notas)
            self._cargar_clientes()
            idx = self.combo_cliente.findData(cid)
            if idx >= 0:
                self.combo_cliente.setCurrentIndex(idx)

    # ---------------- Scanner / Búsqueda ----------------
    def _on_text_changed(self, texto):
        if texto.strip():
            self._scan_timer.start(250)

    def _buscar_producto(self):
        q = self.input_buscar.text().strip()
        if not q:
            return

        productos = database.obtener_productos()
        encontrado = None
        for p in productos:
            pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = p
            codigo = str(codigo or "").strip().lower()
            codigo_barras = str(codigo_barras or "").strip().lower()
            nombre = str(nombre or "").strip().lower()
            if q.lower() == codigo or q.lower() == codigo_barras or q.lower() in nombre:
                encontrado = p
                break

        if encontrado:
            self._ultimo_producto = {
                "id": encontrado[0], "codigo": encontrado[1], "nombre": encontrado[2],
                "stock": int(encontrado[3]), "precio": float(encontrado[6])
            }
            QApplication.beep()
            self._agregar_al_carrito(cant_override=1, clear_search=True)
        else:
            QApplication.beep()
            QApplication.beep()
            self._alta_rapida_producto(codigo_barras=q)
            prod = database.obtener_producto_por_barcode(q)
            if prod:
                self._ultimo_producto = {
                    "id": prod[0], "codigo": prod[1], "nombre": prod[2],
                    "stock": int(prod[3]), "precio": float(prod[6]) if len(prod) > 6 else 0.0
                }
                self._agregar_al_carrito(cant_override=1, clear_search=True)
            else:
                QMessageBox.information(self, "Alta rápida", "Producto creado, pero no se pudo recuperar para agregar al carrito. Vuelva a escanear.")

        self.input_buscar.clear()
        self.input_buscar.setFocus()

    # ---------------- Alta rápida ----------------
    def _alta_rapida_producto(self, codigo_barras=""):
        d = QDialog(self)
        d.setWindowTitle("Alta rápida de producto")
        f = QFormLayout(d)
        inp_codigo = QLineEdit()
        inp_codigo.setText(codigo_barras)
        inp_nombre = QLineEdit()
        inp_cantidad = QSpinBox()
        inp_cantidad.setRange(0, 100000)
        inp_cantidad.setValue(1)
        inp_costo = QLineEdit()
        sectores = database.obtener_sectores()
        combo_sector = QComboBox()
        for s in sectores:
            combo_sector.addItem(s[1], s[0])
        f.addRow("Código (barcode):", inp_codigo)
        f.addRow("Nombre:", inp_nombre)
        f.addRow("Cantidad inicial:", inp_cantidad)
        f.addRow("Costo:", inp_costo)
        f.addRow("Sector:", combo_sector)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        f.addRow(buttons)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        if d.exec():
            codigo = inp_codigo.text().strip()
            nombre = inp_nombre.text().strip()
            cantidad = int(inp_cantidad.value())
            try:
                costo = float(inp_costo.text()) if inp_costo.text().strip() != "" else 0.0
            except:
                QMessageBox.warning(self, "Costo", "Costo inválido")
                return
            sector_id = combo_sector.currentData() if combo_sector.currentIndex() >= 0 else None
            if not codigo or not nombre:
                QMessageBox.warning(self, "Datos", "Código y nombre son obligatorios")
                return
            database.agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras=codigo)
            QMessageBox.information(self, "Producto", f"Producto '{nombre}' agregado/actualizado")
            return  # 👈 no cerrar el POS

    # ---------------- Carrito ----------------
    def _agregar_al_carrito(self, cant_override=None, clear_search=False):
        if not self._ultimo_producto:
            QMessageBox.warning(self, "Agregar", "Primero buscá un producto")
            return
        cant = int(self.spin_cant.value()) if cant_override is None else int(cant_override)
        if cant <= 0:
            QMessageBox.warning(self, "Cantidad", "Cantidad inválida")
            return
        if cant > self._ultimo_producto["stock"]:
            QMessageBox.warning(self, "Stock", f"Stock insuficiente ({self._ultimo_producto['stock']})")
            return
        for it in self.cart:
            if it["producto_id"] == self._ultimo_producto["id"]:
                it["cantidad"] += cant
                break
        else:
            self.cart.append({
                "producto_id": self._ultimo_producto["id"],
                "codigo": self._ultimo_producto["codigo"],
                "nombre": self._ultimo_producto["nombre"],
                "cantidad": cant,
                "precio_unitario": self._ultimo_producto.get("precio", 0)
            })
        QApplication.beep()
        self._refrescar_carrito()
        if clear_search:
            self.input_buscar.clear()
            # 👇 no resetear self._ultimo_producto, así se puede usar en próximos escaneos

    def _refrescar_carrito(self):
        self.table_cart.setRowCount(len(self.cart))
        for r, it in enumerate(self.cart):
            self.table_cart.setItem(r, 0, QTableWidgetItem(str(it["producto_id"])))
            self.table_cart.setItem(r, 1, QTableWidgetItem(it["codigo"]))
            self.table_cart.setItem(r, 2, QTableWidgetItem(it["nombre"]))
            self.table_cart.setItem(r, 3, QTableWidgetItem(str(it["cantidad"])))
            self.table_cart.setItem(r, 4, QTableWidgetItem(f"{it['precio_unitario']:.2f}"))
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
        self.lbl_total.setText(f"Total: ${total:,.2f}")
        self._calcular_vuelto()

    # ---------------- Pago ----------------
    def _on_pago_change(self):
        tipo = self.combo_pago.currentText()
        if tipo == "Efectivo":
            self.input_recibido.setEnabled(True)
            self.input_recibido.setFocus()
        else:
            self.input_recibido.setEnabled(False)
            self.input_recibido.clear()
        self._calcular_vuelto()

    def _calcular_vuelto(self):
        try:
            recibido = float(self.input_recibido.text()) if self.input_recibido.text().strip() != "" else None
        except:
            recibido = None
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
        if recibido is not None:
            vuelto = recibido - total
            if vuelto < 0:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Falta: ${abs(vuelto):,.2f}")
                self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: red;")
            else:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Vuelto: ${vuelto:,.2f}")
                self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: green;")
        else:
            self.lbl_total.setText(f"Total: ${total:,.2f}")
            self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")

    def _confirmar_venta(self):
        if not self.cart:
            QMessageBox.warning(self, "Carrito vacío", "Agregá productos antes de confirmar")
            return
        tipo_pago = self.combo_pago.currentText()
        recibido = None
        try:
            recibido = float(self.input_recibido.text()) if self.input_recibido.text().strip() != "" else None
        except:
            QMessageBox.warning(self, "Efectivo", "Monto recibido inválido")
            return

        cliente_id = self.combo_cliente.currentData()
        if tipo_pago == "Pendiente" and cliente_id is None:
            QMessageBox.warning(self, "Cliente requerido", "Debés seleccionar un cliente para ventas pendientes (fiado).")
            return

        items = [{"producto_id": it["producto_id"], "cantidad": it["cantidad"], "precio_unitario": it["precio_unitario"]} for it in self.cart]
        ok, res = database.registrar_venta(items, tipo_pago, cliente=cliente_id, efectivo_recibido=recibido)
        if ok:
            venta_id = res
            total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
            vuelto = (recibido - total) if recibido is not None else None
            QMessageBox.information(self, "Venta registrada", f"Venta ID {venta_id} registrada.\nTotal: ${total:,.2f}\nTipo: {tipo_pago}\nVuelto: {vuelto if vuelto is not None else '-'}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error al vender", f"No se pudo registrar: {res}")

    def obtener_carrito(self):
        return self.cart

    def _buscar_si_completo(self, texto: str):
        texto = texto.strip()
        if len(texto) >= 6:
            self._buscar_producto()
    
    def agregar_producto_externo(self, prod):
        try:
            pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = prod
            if int(cantidad) > 0:
                self._ultimo_producto = {
                    "id": pid, "codigo": codigo, "nombre": nombre,
                    "stock": int(cantidad), "precio": float(precio)
                }
                self._agregar_al_carrito(cant_override=1, clear_search=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo agregar producto: {e}")
    
        def showEvent(self, e):   ### NUEVO
            super().showEvent(e)
            # aseguramos que siempre tome el foco al mostrarse
            self.activateWindow()
            self.raise_()
            self.input_buscar.setFocus()
