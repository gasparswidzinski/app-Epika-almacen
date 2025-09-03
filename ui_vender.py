# ui_vender.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QLineEdit, QMessageBox
from PySide6.QtCore import Qt

class FormularioVenta(QDialog):
    def __init__(self, producto, parent=None):
        """
        producto: dict {id, codigo, nombre, stock, precio}
        """
        super().__init__(parent)
        self.setWindowTitle("Registrar Venta")
        self.setModal(True)
        self.producto = producto

        layout = QVBoxLayout()

        lbl_nombre = QLabel(f"🛒 {producto['nombre']}")
        lbl_nombre.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(lbl_nombre, alignment=Qt.AlignCenter)

        lbl_info = QLabel(f"Stock disponible: {producto['stock']} unidades\nPrecio unitario: ${producto['precio']:.2f}")
        layout.addWidget(lbl_info, alignment=Qt.AlignCenter)

        box = QHBoxLayout()
        box.addWidget(QLabel("Cantidad:"))
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, producto['stock'] if producto['stock'] > 0 else 1)
        self.spin_cant.setValue(1)
        self.spin_cant.valueChanged.connect(self._actualizar_total)
        box.addWidget(self.spin_cant)
        layout.addLayout(box)

        # Si pago en efectivo queremos registrar monto recibido y volver
        pay_box = QHBoxLayout()
        pay_box.addWidget(QLabel("Monto recibido (opcional, efectivo):"))
        self.input_recibido = QLineEdit()
        self.input_recibido.setPlaceholderText("0.00")
        pay_box.addWidget(self.input_recibido)
        layout.addLayout(pay_box)

        self.lbl_total = QLabel()
        self.lbl_vuelto = QLabel()
        self.lbl_total.setStyleSheet("font-weight:bold; color:green;")
        layout.addWidget(self.lbl_total, alignment=Qt.AlignCenter)
        layout.addWidget(self.lbl_vuelto, alignment=Qt.AlignCenter)
        self._actualizar_total()

        btns = QHBoxLayout()
        self.btn_ok = QPushButton("✅ Confirmar")
        self.btn_cancel = QPushButton("❌ Cancelar")
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.setLayout(layout)

        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_cancel.clicked.connect(self.reject)
        self.input_recibido.textChanged.connect(self._actualizar_vuelto)

    def _actualizar_total(self):
        cantidad = self.spin_cant.value()
        total = cantidad * self.producto['precio']
        self.lbl_total.setText(f"Total: ${total:,.2f}")
        self._actualizar_vuelto()

    def _actualizar_vuelto(self):
        recibido_text = self.input_recibido.text().strip()
        try:
            recibido = float(recibido_text) if recibido_text != "" else None
        except:
            recibido = None
        total = self.spin_cant.value() * self.producto['precio']
        if recibido is not None:
            vuelto = recibido - total
            if vuelto < 0:
                self.lbl_vuelto.setText(f"Falta: ${abs(vuelto):,.2f}")
            else:
                self.lbl_vuelto.setText(f"Vuelto: ${vuelto:,.2f}")
        else:
            self.lbl_vuelto.setText("")

    def _on_ok(self):
        # Validación básica
        if self.spin_cant.value() <= 0:
            QMessageBox.warning(self, "Cantidad", "La cantidad debe ser mayor a 0")
            return
        # guardamos cantidad y monto recibido (puede estar vacío)
        self.accept()

    def obtener_cantidad(self):
        return self.spin_cant.value()

    def obtener_recibido(self):
        txt = self.input_recibido.text().strip()
        try:
            return float(txt) if txt != "" else None
        except:
            return None
