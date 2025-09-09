# main.py
import sys, os, shutil
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMessageBox
import database
from ui_main import MainWindow
from ui_login import LoginDialog
from ui_usuarios import UsuarioForm


def respaldo_automatico():
    if not os.path.exists("backups"):
        os.makedirs("backups")
    fecha = datetime.now().strftime("%Y-%m-%d")
    destino = os.path.join("backups", f"almacen_{fecha}.db")
    if not os.path.exists(destino):
        # Copiamos la DB si existe
        if os.path.exists("almacen.db"):
            shutil.copy("almacen.db", destino)
        else:
            # si no existe aún la DB (primera ejecución), no hacemos nada
            pass


if __name__ == "__main__":
    # inicializar DB (crea tablas, semillas)
    database.inicializar_db()
    respaldo_automatico()
    app = QApplication(sys.argv)
    
    # 🔑 mostrar login antes de abrir la app
    login = LoginDialog()
    if login.exec() != LoginDialog.Accepted:
        sys.exit(0)
    
    window = MainWindow()
    window.rol_actual = login.rol

    # 👤 Si es el primer inicio solo con admin
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    cant_usuarios = cur.fetchone()[0]
    conn.close()

    if cant_usuarios == 2 and login.rol == "admin":
        QMessageBox.information(
            None,
            "Primer inicio",
            "Estás entrando por primera vez con el usuario admin.\n\n"
            "Debés crear tu usuario administrador personalizado antes de continuar."
        )

        while True:
            dlg = UsuarioForm()
            if dlg.exec():
                user, pwd, rol = dlg.get_data()
                if not user or not pwd:
                    QMessageBox.warning(None, "Error", "Usuario y contraseña no pueden estar vacíos.")
                    continue
                if rol != "admin":
                    QMessageBox.warning(None, "Error", "El primer usuario personalizado debe ser administrador.")
                    continue
                try:
                    database.agregar_usuario(user, pwd, rol)
                    QMessageBox.information(
                        None,
                        "Usuario creado",
                        f"✅ Usuario '{user}' creado correctamente.\n\nAhora podés usar la aplicación con tu nueva cuenta."
                    )
                    break
                except Exception as e:
                    QMessageBox.critical(None, "Error", f"No se pudo crear el usuario:\n{e}")
                    continue
            else:
                QMessageBox.warning(None, "Obligatorio", "Debés crear un usuario para continuar.")

    window.aplicar_permisos()
    window.show()
    sys.exit(app.exec())
