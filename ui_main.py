from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QTextEdit, QFileDialog, QLineEdit, QLabel, QCheckBox,
    QToolBar, QStatusBar, QMessageBox, QDialog, QDateEdit, QPushButton
)
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtCore import Qt, QDate
import pandas as pd
import database
from ui_formulario import FormularioProducto
from ui_vender import FormularioVenta


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Stock - Almacén")
        self.resize(1100, 600)

        # --- Toolbar superior ---
        toolbar = QToolBar("Menú principal")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Acciones con íconos (texto Unicode)
        self.act_agregar = QAction("➕ Agregar (F1)", self)
        self.act_editar = QAction("✏️ Editar (F3)", self)
        self.act_eliminar = QAction("🗑 Eliminar (Del)", self)
        self.act_vender = QAction("🛒 Vender (F2)", self)
        self.act_importar = QAction("📥 Importar Excel", self)
        self.act_exportar = QAction("📤 Exportar Stock", self)
        self.act_reporte = QAction("📊 Reporte ventas", self)
        self.act_bajo_stock = QAction("🖨 Bajo stock", self)

        for act in [self.act_agregar, self.act_editar, self.act_eliminar,
                    self.act_vender, self.act_importar, self.act_exportar,
                    self.act_reporte, self.act_bajo_stock]:
            toolbar.addAction(act)

        # --- Layout central ---
        central = QWidget()
        main_layout = QHBoxLayout(central)

        # Panel izquierdo (tabla + búsqueda + filtro)
        left_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔎 Buscar:"))
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Código o Nombre...")
        search_layout.addWidget(self.input_buscar)
        self.chk_bajo_stock = QCheckBox("Solo bajo stock (≤5)")
        search_layout.addWidget(self.chk_bajo_stock)
        left_layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        left_layout.addWidget(self.table)

        main_layout.addLayout(left_layout, stretch=3)

        # Panel derecho (historial)
        right_layout = QVBoxLayout()
        lbl_historial = QLabel("📜 Historial de movimientos")
        right_layout.addWidget(lbl_historial)
        self.historial = QTextEdit()
        self.historial.setReadOnly(True)
        right_layout.addWidget(self.historial)
        main_layout.addLayout(right_layout, stretch=1)

        self.setCentralWidget(central)

        # --- Barra de estado ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("✅ Aplicación iniciada - Base de datos lista")

        # Inicializar
        self._productos_cache = []
        self.actualizar_tabla()
        self.actualizar_historial()

        # --- Conexiones ---
        self.act_agregar.triggered.connect(self.abrir_formulario)
        self.act_editar.triggered.connect(self.editar_producto)
        self.act_eliminar.triggered.connect(self.eliminar_producto)
        self.act_vender.triggered.connect(self.vender_producto)
        self.act_importar.triggered.connect(self.importar_excel)
        self.act_exportar.triggered.connect(self.exportar_excel)
        self.act_reporte.triggered.connect(self.generar_reporte_ventas)
        self.act_bajo_stock.triggered.connect(self.imprimir_bajo_stock)

        self.input_buscar.textChanged.connect(self.aplicar_filtros)
        self.chk_bajo_stock.toggled.connect(self.aplicar_filtros)

        # Atajos de teclado
        self.act_agregar.setShortcut(QKeySequence("F1"))
        self.act_vender.setShortcut(QKeySequence("F2"))
        self.act_editar.setShortcut(QKeySequence("F3"))
        self.act_eliminar.setShortcut(QKeySequence("Delete"))

    # -----------------------------
    #   Gestión de la tabla
    # -----------------------------
    def _cargar_productos(self):
        self._productos_cache = database.obtener_productos()
        return self._productos_cache

    def actualizar_tabla(self):
        productos = self._cargar_productos()
        self._pintar_tabla(productos)

    def _pintar_tabla(self, productos):
        self.table.setRowCount(len(productos))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Cantidad", "Precio", "Movimientos"])

        for row, prod in enumerate(productos):
            for col, val in enumerate(prod):
                item = QTableWidgetItem(str(val))
                if col == 3:  # Cantidad
                    try:
                        cant = int(val)
                        if cant <= 5:
                            item.setForeground(QColor("red"))
                        if cant == 0:
                            item.setForeground(QColor("#777777"))
                    except:
                        pass
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        # Ordenar automáticamente por Nombre (columna 2)
        self.table.sortItems(2)

    def aplicar_filtros(self):
        texto = self.input_buscar.text().strip().lower()
        solo_bajo = self.chk_bajo_stock.isChecked()

        filtrados = []
        for prod in self._productos_cache:
            _id, codigo, nombre, cantidad, precio, movs = prod
            ok_texto = True
            if texto:
                ok_texto = (texto in str(codigo).lower()) or (texto in str(nombre).lower())

            ok_bajo = True
            if solo_bajo:
                try:
                    ok_bajo = int(cantidad) <= 5
                except:
                    ok_bajo = False

            if ok_texto and ok_bajo:
                filtrados.append(prod)

        self._pintar_tabla(filtrados)

    # -----------------------------
    #   Historial
    # -----------------------------
    def actualizar_historial(self):
        movimientos = database.obtener_movimientos()
        self.historial.clear()
        for nombre, cambio, precio, fecha in movimientos:
            try:
                c = int(cambio)
                p = float(precio)
            except:
                c, p = cambio, precio

            if isinstance(c, int):
                if c > 0:
                    etiqueta = "✅ Ingreso"
                    signo = f"+{c}"
                elif c < 0:
                    etiqueta = "🛒 Venta"
                    signo = f"{c}"
                else:
                    etiqueta = "✏️ Editado" if p and float(p) > 0 else "❌ Eliminado"
                    signo = "0"
            else:
                etiqueta = "ℹ️ Movimiento"
                signo = str(c)

            self.historial.append(f"[{fecha}] {etiqueta}: {nombre} ({signo}) ${precio}")

    # -----------------------------
    #   Operaciones
    # -----------------------------
    def abrir_formulario(self):
        dialog = FormularioProducto(self)
        if dialog.exec():
            datos = dialog.obtener_datos()
            try:
                if not datos["codigo"] or not datos["nombre"]:
                    self.status.showMessage("⚠ Completá Código y Nombre", 5000)
                    return
                database.agregar_o_actualizar_producto(
                    datos["codigo"],
                    datos["nombre"],
                    int(datos["cantidad"]),
                    float(datos["precio"])
                )
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                self.status.showMessage(f"✅ Ingreso: {datos['nombre']} (+{int(datos['cantidad'])})", 5000)
            except ValueError:
                self.status.showMessage("⚠ Error: cantidad y precio deben ser números", 5000)

    def exportar_excel(self):
        productos = database.obtener_productos()
        df = pd.DataFrame(productos, columns=["ID", "Código", "Nombre", "Cantidad", "Precio", "Movimientos"])
        df.to_excel("stock.xlsx", index=False)
        self.status.showMessage("✅ Exportado a stock.xlsx", 5000)

    def importar_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                df = pd.read_excel(file_path)
                requeridas = {"Codigo", "Nombre", "Cantidad", "Precio"}
                if not requeridas.issubset(set(df.columns)):
                    self.status.showMessage("⚠ El Excel debe tener columnas: Codigo, Nombre, Cantidad, Precio", 5000)
                    return
                for _, row in df.iterrows():
                    database.agregar_o_actualizar_producto(
                        str(row["Codigo"]),
                        str(row["Nombre"]),
                        int(row["Cantidad"]),
                        float(row["Precio"])
                    )
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                self.status.showMessage(f"📥 Importado desde {file_path}", 5000)
            except Exception as e:
                self.status.showMessage(f"❌ Error al importar: {e}", 5000)

    def editar_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Selecciona un producto para editar", 5000)
            return

        id_ = int(self.table.item(fila, 0).text())
        datos = {
            "codigo": self.table.item(fila, 1).text(),
            "nombre": self.table.item(fila, 2).text(),
            "cantidad": self.table.item(fila, 3).text(),
            "precio": self.table.item(fila, 4).text()
        }

        dialog = FormularioProducto(self, datos)
        if dialog.exec():
            d = dialog.obtener_datos()
            try:
                database.editar_producto(
                    id_,
                    d["nombre"],
                    int(d["cantidad"]),
                    float(d["precio"])
                )
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                self.status.showMessage(f"✏️ Editado: {d['nombre']}", 5000)
            except ValueError:
                self.status.showMessage("⚠ Error: cantidad y precio deben ser números", 5000)

    def eliminar_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Selecciona un producto para eliminar", 5000)
            return

        nombre = self.table.item(fila, 2).text()
        confirm = QMessageBox.question(self, "Confirmar eliminación",
                                       f"¿Eliminar producto '{nombre}'?")
        if confirm == QMessageBox.Yes:
            id_ = int(self.table.item(fila, 0).text())
            database.eliminar_producto(id_)
            self.actualizar_tabla()
            self.actualizar_historial()
            self.aplicar_filtros()
            self.status.showMessage(f"❌ Eliminado: {nombre}", 5000)

    def vender_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Selecciona un producto para vender", 5000)
            return

        producto = {
            "id": int(self.table.item(fila, 0).text()),
            "codigo": self.table.item(fila, 1).text(),
            "nombre": self.table.item(fila, 2).text(),
            "stock": int(self.table.item(fila, 3).text()),
            "precio": float(self.table.item(fila, 4).text())
        }

        from ui_vender import FormularioVenta
        dialog = FormularioVenta(producto, self)
        if dialog.exec():
            cantidad = dialog.obtener_cantidad()
            if cantidad > producto["stock"]:
                self.status.showMessage("❌ Stock insuficiente", 5000)
                return
            ok = database.modificar_stock(producto["id"], -cantidad)
            if ok:
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                total = cantidad * producto["precio"]

                # Mostrar en barra de estado
                self.status.showMessage(
                    f"🛒 Vendidas {cantidad} de {producto['nombre']} | Total: ${total:,.2f}", 8000
                )

                # Registrar también en historial lateral con el importe total
                self.historial.append(
                    f"💵 Venta: {cantidad} x {producto['nombre']} = ${total:,.2f}"
                )


    # -----------------------------
    #   Reportes
    # -----------------------------
    def generar_reporte_ventas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Generar reporte de ventas")
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Desde:"))
        date_ini = QDateEdit(QDate.currentDate().addDays(-7))
        date_ini.setCalendarPopup(True)
        vbox.addWidget(date_ini)
        vbox.addWidget(QLabel("Hasta:"))
        date_fin = QDateEdit(QDate.currentDate())
        date_fin.setCalendarPopup(True)
        vbox.addWidget(date_fin)
        btns = QHBoxLayout()
        ok = QPushButton("✅ Generar")
        cancel = QPushButton("❌ Cancelar")
        btns.addWidget(ok); btns.addWidget(cancel)
        vbox.addLayout(btns)
        dlg.setLayout(vbox)
        ok.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)

        if dlg.exec():
            fi = date_ini.date().toString("yyyy-MM-dd")
            ff = date_fin.date().toString("yyyy-MM-dd")
            ventas = database.obtener_ventas(fi, ff)
            if not ventas:
                self.status.showMessage("ℹ️ No se encontraron ventas en el rango", 5000)
                return
            df = pd.DataFrame(ventas, columns=["Código", "Nombre", "Cantidad", "Precio", "Fecha"])
            total_unidades = sum(abs(v[2]) for v in ventas)
            total_dinero = sum(abs(v[2]) * v[3] for v in ventas)
            df.loc[len(df.index)] = ["", "TOTAL", total_unidades, total_dinero, ""]
            df.to_excel("reporte_ventas.xlsx", index=False)
            self.status.showMessage(f"📊 Reporte generado: reporte_ventas.xlsx ({fi} → {ff})", 5000)

    def imprimir_bajo_stock(self):
        productos = [p for p in self._productos_cache if int(p[3]) <= 5]
        if not productos:
            self.status.showMessage("ℹ️ No hay productos con bajo stock", 5000)
            return
        df = pd.DataFrame(productos, columns=["ID", "Código", "Nombre", "Cantidad", "Precio", "Movimientos"])
        df.to_excel("bajo_stock.xlsx", index=False)
        self.status.showMessage("🖨 Listado bajo stock generado: bajo_stock.xlsx", 5000)
