# main.py
import sys, os, shutil
from datetime import datetime
from PySide6.QtWidgets import QApplication
import database
from ui_main import MainWindow

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

