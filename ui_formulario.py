from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtGui import QIntValidator, QDoubleValidator

class FormularioProducto(QDialog):
    def __init__(self, parent=None, datos=None):
        super().__init__(parent)
        self.setWindowTitle("Producto")
        self.resize(320, 220)

        layout = QVBoxLayout()

        # Código
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Código o escanear con lector")
        layout.addWidget(QLabel("Código"))
        layout.addWidget(self.input_codigo)

        # Nombre
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Nombre del producto")
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.input_nombre)

        # Cantidad
        self.input_cantidad = QLineEdit()
        self.input_cantidad.setPlaceholderText("0")
        self.input_cantidad.setValidator(QIntValidator(0, 10**9, self))
        layout.addWidget(QLabel("Cantidad"))
        layout.addWidget(self.input_cantidad)

        # Precio
        self.input_precio = QLineEdit()
        self.input_precio.setPlaceholderText("0.00")
        val_precio = QDoubleValidator(0.0, 10**12, 2, self)
        val_precio.setNotation(QDoubleValidator.StandardNotation)
        self.input_precio.setValidator(val_precio)
        layout.addWidget(QLabel("Precio"))
        layout.addWidget(self.input_precio)

        # Botones
        botones = QHBoxLayout()
        self.btn_guardar = QPushButton("✅ Guardar")
        self.btn_cancelar = QPushButton("❌ Cancelar")
        botones.addWidget(self.btn_guardar)
        botones.addWidget(self.btn_cancelar)
        layout.addLayout(botones)

        self.setLayout(layout)

        # Conexiones
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

        # Precarga para edición
        if datos:
            self.input_codigo.setText(str(datos.get("codigo", "")))
            self.input_nombre.setText(datos.get("nombre", ""))
            self.input_cantidad.setText(str(datos.get("cantidad", "")))
            self.input_precio.setText(str(datos.get("precio", "")))

    def obtener_datos(self):
        return {
            "codigo": self.input_codigo.text().strip(),
            "nombre": self.input_nombre.text().strip(),
            "cantidad": self.input_cantidad.text().strip(),
            "precio": self.input_precio.text().strip()
        }
