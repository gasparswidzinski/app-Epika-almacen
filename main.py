# main.py
import sys, os, shutil
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMessageBox
import database
from ui_main import MainWindow
from ui_login import LoginDialog
from ui_usuarios import UsuarioForm

# (limpieza) quitamos imports duplicados de os, shutil

def respaldo_automatico():
    import os, shutil
    from database import DATA_DIR, DB_PATH
    backups_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d")
    destino = os.path.join(backups_dir, f"almacen_{fecha}.db")
    if not os.path.exists(destino) and os.path.exists(DB_PATH):
        shutil.copy(DB_PATH, destino)

if __name__ == "__main__":
    # (robustez) si hay un fallo en inicializar_db, avisamos y salimos prolijamente
    try:
        database.inicializar_db()  # crea/migra DB y tablas
    except Exception as e:
        # aún no tenemos QApplication; usamos print y salimos
        print("Error inicializando base de datos:", e)
        sys.exit(1)

    # Garantizamos la carpeta de datos (útil para backup u "abrir carpeta de datos")
    os.makedirs(database.DATA_DIR, exist_ok=True)

    # Backup del día antes de abrir UI
    respaldo_automatico()

    app = QApplication(sys.argv)

    # 🔑 diálogo de login
    login = LoginDialog()
    if login.exec() != LoginDialog.Accepted:
        sys.exit(0)

    window = MainWindow()
    window.rol_actual = login.rol

    # 👤 Primer inicio: sólo admin + developer presentes → pedir crear admin propio
    try:
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios")
        cant_usuarios = cur.fetchone()[0]
        conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Base de datos", f"Error consultando usuarios:\n{e}")
        sys.exit(1)

    if cant_usuarios == 2 and login.rol == "admin":
        QMessageBox.information(
            None,
            "Primer inicio",
            "Estás entrando por primera vez con el usuario admin.\n\n"
            "Debés crear tu usuario administrador personalizado antes de continuar."
        )

        while True:
            dlg = UsuarioForm(window)  # (mejora) parent para centrar y bloquear fondo
            if dlg.exec():
                user, pwd, rol = dlg.get_data()
                if not user or not pwd:
                    QMessageBox.warning(None, "Error", "Usuario y contraseña no pueden estar vacíos.")
                    continue
                if rol != "admin":
                    QMessageBox.warning(None, "Error", "El primer usuario personalizado debe ser administrador.")
                    continue
                try:
                    database.agregar_usuario(user, pwd, rol)  # guarda hasheado
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
                # (misma lógica que tenías) obliga a crear el usuario
                QMessageBox.warning(None, "Obligatorio", "Debés crear un usuario para continuar.")

    window.aplicar_permisos()
    window.show()
    sys.exit(app.exec())
