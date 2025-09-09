# ui_login.py
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox
import database

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión")
        self.resize(300, 150)

        form = QFormLayout(self)

        self.input_user = QLineEdit()
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)

        form.addRow("Usuario:", self.input_user)
        form.addRow("Contraseña:", self.input_pass)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)

        buttons.accepted.connect(self._login)
        buttons.rejected.connect(self.reject)

        self.rol = None  # se guarda el rol al validar
        
        # 🎨 Estilos para hacer el login más lindo
        self.setStyleSheet("""
            QDialog {
                background-color: #f7f7f7;
                border-radius: 12px;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #aaa;
                border-radius: 8px;
                background: white;
            }
            QDialogButtonBox QPushButton {
                padding: 6px 12px;
                border-radius: 8px;
                background-color: #0078d7;
                color: white;
                font-weight: bold;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #005a9e;
            }
        """)

    def _login(self):
        user = self.input_user.text().strip()
        pwd = self.input_pass.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Login", "Ingrese usuario y contraseña")
            return

        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT rol FROM usuarios WHERE usuario=? AND password=?", (user, pwd))
        row = cur.fetchone()
        conn.close()

        if row:
            self.rol = row[0]
            self.usuario = user 
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos")
