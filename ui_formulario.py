# ui_formulario.py
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
import database

class FormularioProducto(QDialog):
    """
    Formulario simple para crear/editar productos.
    Parámetros:
      producto: tuple/row opcional (id, codigo, nombre, cantidad, costo, sector_nombre, precio, codigo_barras, movs)
      codigo_barras: si se pasa, lo precarga en el campo correspondiente (útil para scanner)
    """
    def __init__(self, parent=None, producto=None, codigo_barras=""):
        super().__init__(parent)
        self.setWindowTitle("Agregar/Editar Producto")
        self.resize(420, 320)
        self.producto = producto

        form = QFormLayout(self)

        self.input_codigo = QLineEdit()
        form.addRow("Código interno:", self.input_codigo)

        self.input_nombre = QLineEdit()
        form.addRow("Nombre:", self.input_nombre)

        self.input_cantidad = QSpinBox()
        self.input_cantidad.setRange(0, 1000000)
        form.addRow("Cantidad inicial:", self.input_cantidad)

        self.input_costo = QLineEdit()
        self.input_costo.setPlaceholderText("0.00")
        form.addRow("Costo (lo que pagás):", self.input_costo)

        self.input_sector = QComboBox()
        try:
            sectores = database.obtener_sectores()
            for s in sectores:
                # s is (id, nombre, margen)
                sid = s[0]
                sname = s[1]
                self.input_sector.addItem(sname, sid)
        except Exception:
            pass
        form.addRow("Sector:", self.input_sector)

        self.input_codigobarras = QLineEdit()
        form.addRow("Código de Barras:", self.input_codigobarras)

        # Si se pasa un producto para editar, poblar campos
        if producto:
            try:
                # producto como tupla: (id, codigo, nombre, cantidad, costo, sector_nombre, precio, codigo_barras, movs)
                self.input_codigo.setText(str(producto[1] or ""))
                self.input_nombre.setText(str(producto[2] or ""))
                try:
                    self.input_cantidad.setValue(int(producto[3]))
                except:
                    pass
                try:
                    self.input_costo.setText(str(producto[4] if producto[4] is not None else ""))
                except:
                    pass
                try:
                    cb = str(producto[7] or "")
                    self.input_codigobarras.setText(cb)
                except:
                    pass
                # intentar seleccionar sector si producto[5] es nombre
                try:
                    sector_nombre = producto[5] if len(producto) > 5 else None
                except:
                    sector_nombre = None
                if sector_nombre:
                    idx = self.input_sector.findText(str(sector_nombre))
                    if idx >= 0:
                        self.input_sector.setCurrentIndex(idx)
            except Exception:
                pass

        # si se pasó codigo_barras (desde scanner), precargar
        if codigo_barras:
            self.input_codigobarras.setText(str(codigo_barras))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        try:
            buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
            buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        except Exception:
            pass
        form.addRow(buttons)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

    def _on_accept(self):
        codigo = self.input_codigo.text().strip()
        nombre = self.input_nombre.text().strip()
        if not codigo or not nombre:
            QMessageBox.warning(self, "Validación", "Código y Nombre son obligatorios.")
            return
        try:
            cantidad = int(self.input_cantidad.value())
        except:
            cantidad = 0
        try:
            txt_costo = self.input_costo.text().strip().replace(",", ".")
            costo = float(txt_costo) if txt_costo != "" else 0.0
        except:
            QMessageBox.warning(self, "Costo", "Costo inválido")
            return
        sector_id = self.input_sector.currentData() if self.input_sector.currentIndex() >= 0 else None
        cod_barras_txt = (self.input_codigobarras.text() or "").strip()
        cod_barras = cod_barras_txt if cod_barras_txt != "" else None

        try:
            database.agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras=cod_barras)
            QMessageBox.information(self, "Producto", "Producto guardado correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el producto:\n{e}")
