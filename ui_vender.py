# ui_vender.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QLineEdit, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem, QFileDialog
)
from PySide6.QtCore import Qt
import database

class FormularioPOS(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Punto de Venta - Registrar Venta")
        self.resize(700, 500)

        self.cart = []  # lista de dicts: producto_id, codigo, nombre, cantidad, precio_unitario

        layout = QVBoxLayout()

        # Buscador por código, nombre o barcode
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar (Código / Nombre / Barcode):"))
        self.input_buscar = QLineEdit()
        search_layout.addWidget(self.input_buscar)
        self.btn_buscar = QPushButton("Buscar")
        search_layout.addWidget(self.btn_buscar)
        layout.addLayout(search_layout)

        # Resultado simple: agrego por código exacto o por primer match
        self.btn_buscar.clicked.connect(self._buscar_producto)
        self.input_buscar.returnPressed.connect(self._buscar_producto)

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

        # Efectivo recibido (solo si Efectivo)
        pay_layout.addWidget(QLabel("Monto recibido (si efectivo):"))
        self.input_recibido = QLineEdit()
        self.input_recibido.setPlaceholderText("0.00")
        pay_layout.addWidget(self.input_recibido)

        layout.addLayout(pay_layout)

        # Totales y botones
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        bottom.addWidget(self.lbl_total)
        self.btn_confirm = QPushButton("✅ Confirmar Venta")
        bottom.addWidget(self.btn_confirm)
        self.btn_cancel = QPushButton("❌ Cancelar")
        bottom.addWidget(self.btn_cancel)
        layout.addLayout(bottom)

        self.setLayout(layout)

        # conexiones
        self.btn_confirm.clicked.connect(self._confirmar_venta)
        self.btn_cancel.clicked.connect(self.reject)
        self.combo_pago.currentIndexChanged.connect(self._on_pago_change)
        self.input_recibido.textChanged.connect(self._calcular_vuelto)

        # helper: ultimo resultado de búsqueda
        self._ultimo_producto = None

    def _buscar_producto(self):
        q = self.input_buscar.text().strip().lower()
        if not q:
            QMessageBox.information(self, "Buscar", "Ingresá código, nombre o barcode")
            return
        # buscar por codigo exacto o codigo_barras exacto o nombre contains
        productos = database.obtener_productos()
        encontrado = None
        for p in productos:
            pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = p
            if str(codigo).lower() == q or str(codigo_barras).lower() == q or q in str(nombre).lower():
                encontrado = p
                break
        if encontrado:
            self._ultimo_producto = {
                "id": encontrado[0], "codigo": encontrado[1], "nombre": encontrado[2],
                "stock": int(encontrado[3]), "precio": float(encontrado[6])
            }
            QMessageBox.information(self, "Producto encontrado", f"{self._ultimo_producto['nombre']} — Stock: {self._ultimo_producto['stock']} — Precio: ${self._ultimo_producto['precio']}")
        else:
            QMessageBox.information(self, "No encontrado", "No se encontró el producto")

    def _agregar_al_carrito(self):
        if not self._ultimo_producto:
            QMessageBox.warning(self, "Agregar", "Primero buscá un producto")
            return
        cant = int(self.spin_cant.value())
        if cant <= 0:
            QMessageBox.warning(self, "Cantidad", "Cantidad inválida")
            return
        if cant > self._ultimo_producto["stock"]:
            QMessageBox.warning(self, "Stock", f"Stock insuficiente ({self._ultimo_producto['stock']})")
            return
        # ver si ya en carrito
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
                "precio_unitario": self._ultimo_producto["precio"]
            })
        self._refrescar_carrito()

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

    def _on_pago_change(self):
        tipo = self.combo_pago.currentText()
        if tipo == "Efectivo":
            self.input_recibido.setEnabled(True)
        else:
            self.input_recibido.setEnabled(False)
            self.input_recibido.clear()

    def _calcular_vuelto(self):
        try:
            recibido = float(self.input_recibido.text()) if self.input_recibido.text().strip() != "" else None
        except:
            recibido = None
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
        if recibido is not None:
            vuelto = recibido - total
            # mostrar en etiqueta
            if vuelto < 0:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Falta: ${abs(vuelto):,.2f}")
            else:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Vuelto: ${vuelto:,.2f}")
        else:
            self.lbl_total.setText(f"Total: ${total:,.2f}")

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
        items = []
        for it in self.cart:
            items.append({
                "producto_id": it["producto_id"],
                "cantidad": it["cantidad"],
                "precio_unitario": it["precio_unitario"]
            })
        ok, res = database.registrar_venta(items, tipo_pago, cliente=None, efectivo_recibido=recibido)
        if ok:
            venta_id = res
            total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
            vuelto = (recibido - total) if recibido is not None else None
            QMessageBox.information(self, "Venta registrada", f"Venta ID {venta_id} registrada.\nTotal: ${total:,.2f}\nTipo: {tipo_pago}\nVuelto: {vuelto if vuelto is not None else '-'}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error al vender", f"No se pudo registrar: {res}")

    # Exponer carrito (si se necesita fuera)
    def obtener_carrito(self):
        return self.cart
