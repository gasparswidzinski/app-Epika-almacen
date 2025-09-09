# ui_usuarios.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QLineEdit, QComboBox, QFormLayout, QDialogButtonBox
)
import database

class UsuariosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Usuarios")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Usuario", "Rol"])
        layout.addWidget(self.table)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_nuevo = QPushButton("➕ Nuevo")
        self.btn_editar = QPushButton("✏️ Editar")
        self.btn_borrar = QPushButton("🗑 Eliminar")
        self.btn_cerrar = QPushButton("❌ Cerrar")
        btn_layout.addWidget(self.btn_nuevo)
        btn_layout.addWidget(self.btn_editar)
        btn_layout.addWidget(self.btn_borrar)
        btn_layout.addWidget(self.btn_cerrar)
        layout.addLayout(btn_layout)

        self.btn_cerrar.clicked.connect(self.reject)
        self.btn_nuevo.clicked.connect(self.nuevo_usuario)
        self.btn_editar.clicked.connect(self.editar_usuario)
        self.btn_borrar.clicked.connect(self.borrar_usuario)

        self.cargar_usuarios()

    def cargar_usuarios(self):
        usuarios = database.obtener_usuarios()
        self.table.setRowCount(len(usuarios))
        for r, u in enumerate(usuarios):
            self.table.setItem(r, 0, QTableWidgetItem(str(u[0])))
            self.table.setItem(r, 1, QTableWidgetItem(u[1]))
            self.table.setItem(r, 2, QTableWidgetItem(u[2]))
        self.table.resizeColumnsToContents()

    def nuevo_usuario(self):
        dlg = UsuarioForm(self)
        if dlg.exec():
            user, pwd, rol = dlg.get_data()
            try:
                database.agregar_usuario(user, pwd, rol)
                QMessageBox.information(self, "Usuario", "✅ Usuario creado")
                self.cargar_usuarios()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def editar_usuario(self):
        row = self.table.currentRow()
        if row < 0:
            return
        uid = int(self.table.item(row, 0).text())
        user = self.table.item(row, 1).text()
        rol = self.table.item(row, 2).text()

        dlg = UsuarioForm(self, user, rol)
        if dlg.exec():
            nuevo_user, nuevo_pwd, nuevo_rol = dlg.get_data()
            try:
                database.editar_usuario(uid, nuevo_user, nuevo_pwd, nuevo_rol)
                QMessageBox.information(self, "Usuario", "✅ Usuario actualizado")
                self.cargar_usuarios()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def borrar_usuario(self):
        row = self.table.currentRow()
        if row < 0:
            return
        uid = int(self.table.item(row, 0).text())
        user = self.table.item(row, 1).text()
        if user == "admin":
            QMessageBox.warning(self, "Error", "No se puede eliminar el usuario admin")
            return
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar usuario {user}?")
        if confirm == QMessageBox.Yes:
            try:
                database.eliminar_usuario(uid)
                self.cargar_usuarios()
                QMessageBox.information(self, "Usuario", "🗑 Usuario eliminado")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


class UsuarioForm(QDialog):
    def __init__(self, parent=None, user="", rol="user"):
        super().__init__(parent)
        self.setWindowTitle("Formulario Usuario")
        self.resize(300, 150)

        form = QFormLayout(self)
        self.input_user = QLineEdit(user)
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_rol = QComboBox()
        self.input_rol.addItems(["admin", "user"])
        if rol:
            idx = self.input_rol.findText(rol)
            if idx >= 0:
                self.input_rol.setCurrentIndex(idx)

        form.addRow("Usuario:", self.input_user)
        form.addRow("Contraseña:", self.input_pass)
        form.addRow("Rol:", self.input_rol)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_data(self):
        return (
            self.input_user.text().strip(),
            self.input_pass.text().strip(),
            self.input_rol.currentText()
        )
