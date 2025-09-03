# ui_formulario.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QComboBox, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt
import database

class FormularioProducto(QDialog):
    def __init__(self, parent=None, producto=None):
        super().__init__(parent)
        self.setWindowTitle("Formulario de Producto")
        self.resize(420, 380)
        self.producto = producto  # si viene: tupla desde db (id, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movimientos)

        layout = QVBoxLayout()

        # Código
        layout.addWidget(QLabel("Código:"))
        self.input_codigo = QLineEdit()
        layout.addWidget(self.input_codigo)

        # Nombre
        layout.addWidget(QLabel("Nombre:"))
        self.input_nombre = QLineEdit()
        layout.addWidget(self.input_nombre)

        # Cantidad
        layout.addWidget(QLabel("Cantidad:"))
        self.input_cantidad = QSpinBox()
        self.input_cantidad.setRange(0, 10**9)
        layout.addWidget(self.input_cantidad)

        # Costo
        layout.addWidget(QLabel("Costo (lo que pagás):"))
        self.input_costo = QLineEdit()
        self.input_costo.setPlaceholderText("0.00")
        layout.addWidget(self.input_costo)

        # Sector
        layout.addWidget(QLabel("Sector:"))
        self.combo_sector = QComboBox()
        self._cargar_sectores()
        layout.addWidget(self.combo_sector)

        # Precio (auto)
        layout.addWidget(QLabel("Precio (calculado):"))
        self.input_precio = QLineEdit()
        self.input_precio.setReadOnly(True)
        layout.addWidget(self.input_precio)

        # Código de barras
        layout.addWidget(QLabel("Código de Barras:"))
        self.input_codigobarras = QLineEdit()
        layout.addWidget(self.input_codigobarras)

        # Botones
        btns = QHBoxLayout()
        self.btn_guardar = QPushButton("✅ Guardar")
        self.btn_cancelar = QPushButton("❌ Cancelar")
        btns.addWidget(self.btn_guardar)
        btns.addWidget(self.btn_cancelar)
        layout.addLayout(btns)

        self.setLayout(layout)

        # Conexiones
        self.input_costo.textChanged.connect(self._actualizar_precio)
        self.combo_sector.currentIndexChanged.connect(self._actualizar_precio)
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)

        # Si es edición, precargar
        if self.producto:
            # producto: (id, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movimientos)
            self.input_codigo.setText(str(self.producto[1]))
            self.input_nombre.setText(str(self.producto[2]))
            self.input_cantidad.setValue(int(self.producto[3]))
            self.input_costo.setText(str(self.producto[4] if self.producto[4] is not None else "0"))
            if self.producto[5]:
                # buscar sector por nombre
                idx = self.combo_sector.findText(self.producto[5])
                if idx >= 0:
                    self.combo_sector.setCurrentIndex(idx)
            self.input_precio.setText(str(self.producto[6] if self.producto[6] is not None else "0"))
            self.input_codigobarras.setText(str(self.producto[7] if self.producto[7] is not None else ""))

    def _cargar_sectores(self):
        self.combo_sector.clear()
        sectores = database.obtener_sectores()
        for s in sectores:
            # s = (id, nombre, margen)
            self.combo_sector.addItem(f"{s[1]} ({int(s[2]*100)}%)", s[0])

    def _actualizar_precio(self):
        try:
            costo = float(self.input_costo.text()) if self.input_costo.text().strip() != "" else 0.0
            sector_id = self.combo_sector.currentData()
            margen = database.obtener_margen_sector(sector_id)
            precio = round(costo + (costo * margen), 2)
            self.input_precio.setText(str(precio))
        except Exception:
            self.input_precio.setText("")

    def _guardar(self):
        try:
            codigo = self.input_codigo.text().strip()
            nombre = self.input_nombre.text().strip()
            cantidad = int(self.input_cantidad.value())
            costo = float(self.input_costo.text()) if self.input_costo.text().strip() != "" else 0.0
            sector_id = self.combo_sector.currentData()
            cod_barras = self.input_codigobarras.text().strip()

            if not codigo or not nombre:
                QMessageBox.warning(self, "Validación", "Código y Nombre son obligatorios.")
                return

            if self.producto:
                database.editar_producto(self.producto[0], codigo, nombre, cantidad, costo, sector_id, cod_barras)
            else:
                database.agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id, cod_barras)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el producto:\n{e}")
