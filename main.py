import sys, os, shutil
from datetime import datetime
from PySide6.QtWidgets import QApplication
import database
from ui_main import MainWindow

def respaldo_automatico():
    if not os.path.exists("backups"):
        os.makedirs("backups")
    fecha = datetime.now().strftime("%Y-%m-%d")
    destino = f"backups/almacen_{fecha}.db"
    if not os.path.exists(destino):  # solo un backup por día
        shutil.copy("almacen.db", destino)

if __name__ == "__main__":
    database.init_db()
    respaldo_automatico()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
