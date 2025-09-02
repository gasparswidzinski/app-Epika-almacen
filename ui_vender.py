from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton
)
from PySide6.QtCore import Qt


class FormularioVenta(QDialog):
    def __init__(self, producto, parent=None):
        """
        producto: diccionario con {id, codigo, nombre, stock, precio}
        """
        super().__init__(parent)
        self.setWindowTitle("Registrar Venta")
        self.setModal(True)
        self.producto = producto

        layout = QVBoxLayout()

        # Nombre del producto
        lbl_nombre = QLabel(f"🛒 {producto['nombre']}")
        lbl_nombre.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(lbl_nombre, alignment=Qt.AlignCenter)

        # Info stock y precio
        lbl_info = QLabel(
            f"Stock disponible: {producto['stock']} unidades\n"
            f"Precio unitario: ${producto['precio']:.2f}"
        )
        lbl_info.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(lbl_info, alignment=Qt.AlignCenter)

        # Cantidad
        box_layout = QHBoxLayout()
        box_layout.addWidget(QLabel("Cantidad a vender:"))
        self.input_cantidad = QSpinBox()
        self.input_cantidad.setRange(1, producto['stock'])
        self.input_cantidad.setValue(1)
        self.input_cantidad.valueChanged.connect(self._actualizar_total)
        box_layout.addWidget(self.input_cantidad)
        layout.addLayout(box_layout)

        # Total
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
        layout.addWidget(self.lbl_total, alignment=Qt.AlignCenter)
        self._actualizar_total()

        # Botones
        botones = QHBoxLayout()
        btn_ok = QPushButton("✅ Confirmar")
        btn_cancel = QPushButton("❌ Cancelar")
        botones.addWidget(btn_ok)
        botones.addWidget(btn_cancel)
        layout.addLayout(botones)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        self.setLayout(layout)

    def _actualizar_total(self):
        cantidad = self.input_cantidad.value()
        total = cantidad * self.producto['precio']
        self.lbl_total.setText(f"Total: ${total:,.2f}")

    def obtener_cantidad(self):
        return self.input_cantidad.value()
