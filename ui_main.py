# ui_main.py
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

        # toolbar
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # acciones
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

        # central widget
        central = QWidget()
        main_layout = QHBoxLayout(central)

        # left panel
        left_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔎 Buscar:"))
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Código, Nombre o Código de Barras...")
        search_layout.addWidget(self.input_buscar)
        self.chk_bajo_stock = QCheckBox("Solo bajo stock (≤5)")
        search_layout.addWidget(self.chk_bajo_stock)
        left_layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        left_layout.addWidget(self.table)

        main_layout.addLayout(left_layout, stretch=3)

        # right panel - historial
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("📜 Historial"))
        self.historial = QTextEdit()
        self.historial.setReadOnly(True)
        right_layout.addWidget(self.historial)
        main_layout.addLayout(right_layout, stretch=1)

        self.setCentralWidget(central)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("✅ Aplicación iniciada")

        # inicializar cache
        self._productos_cache = []
        self.actualizar_tabla()
        self.actualizar_historial()

        # conexiones
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

        # atajos
        self.act_agregar.setShortcut(QKeySequence("F1"))
        self.act_vender.setShortcut(QKeySequence("F2"))
        self.act_editar.setShortcut(QKeySequence("F3"))
        self.act_eliminar.setShortcut(QKeySequence("Delete"))

    # -------------------------
    # carga de productos / tabla
    # -------------------------
    def _cargar_productos(self):
        self._productos_cache = database.obtener_productos()
        return self._productos_cache

    def actualizar_tabla(self):
        productos = self._cargar_productos()
        self._pintar_tabla(productos)

    def _pintar_tabla(self, productos):
        # columnas: id, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movimientos
        headers = ["ID", "Código", "Nombre", "Cantidad", "Costo", "Sector", "Precio", "Código Barras", "Movs"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(productos))

        for r, prod in enumerate(productos):
            for c, val in enumerate(prod):
                item = QTableWidgetItem(str(val))
                if c == 3:  # cantidad
                    try:
                        cant = int(val)
                        if cant <= 5:
                            item.setForeground(QColor("red"))
                        if cant == 0:
                            item.setForeground(QColor("#777777"))
                    except:
                        pass
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        # ordenar por nombre (col 2)
        try:
            self.table.sortItems(2)
        except:
            pass

    def aplicar_filtros(self):
        texto = self.input_buscar.text().strip().lower()
        solo_bajo = self.chk_bajo_stock.isChecked()
        filtrados = []
        for prod in self._productos_cache:
            _id, codigo, nombre, cantidad, costo, sector, precio, codigobarras, movs = prod
            ok_text = True
            if texto:
                ok_text = (texto in str(codigo).lower()) or (texto in str(nombre).lower()) or (texto in str(codigobarras).lower())
            ok_bajo = True
            if solo_bajo:
                try:
                    ok_bajo = int(cantidad) <= 5
                except:
                    ok_bajo = False
            if ok_text and ok_bajo:
                filtrados.append(prod)
        self._pintar_tabla(filtrados)

    # -------------------------
    # historial
    # -------------------------
    def actualizar_historial(self):
        movs = database.obtener_movimientos(200)
        self.historial.clear()
        for mid, nombre, tipo, cambio, precio_unit, fecha, detalles in movs:
            etiqueta = tipo
            if tipo == "INGRESO":
                etiqueta = "✅ Ingreso"
            elif tipo == "VENTA":
                etiqueta = "🛒 Venta"
            elif tipo == "EDIT":
                etiqueta = "✏️ Editado"
            elif tipo == "ELIM":
                etiqueta = "❌ Eliminado"
            elif tipo == "REEMBOLSO":
                etiqueta = "↩️ Reembolso"
            linea = f"[{fecha}] {etiqueta}: {nombre} ({cambio}) ${precio_unit} {('- '+detalles) if detalles else ''}"
            self.historial.append(linea)

    # -------------------------
    # CRUD productos
    # -------------------------
    def abrir_formulario(self):
        dialog = FormularioProducto(self)
        if dialog.exec():
            # después de aceptar, recargar
            self.actualizar_tabla()
            self.actualizar_historial()
            self.aplicar_filtros()
            self.status.showMessage("✅ Producto agregado/actualizado", 4000)

    def editar_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Seleccioná un producto para editar", 4000)
            return
        prod = (
            int(self.table.item(fila,0).text()),   # id
            self.table.item(fila,1).text(),        # codigo
            self.table.item(fila,2).text(),        # nombre
            int(self.table.item(fila,3).text()),   # cantidad
            float(self.table.item(fila,4).text()) if self.table.item(fila,4).text() else 0.0,  # costo
            self.table.item(fila,5).text(),        # sector (nombre)
            float(self.table.item(fila,6).text()) if self.table.item(fila,6).text() else 0.0,  # precio
            self.table.item(fila,7).text() if self.table.item(fila,7) else "",               # codigo_barras
            self.table.item(fila,8).text() if self.table.item(fila,8) else ""                # movimientos
        )
        dialog = FormularioProducto(self, producto=prod)
        if dialog.exec():
            self.actualizar_tabla()
            self.actualizar_historial()
            self.aplicar_filtros()
            self.status.showMessage("✏️ Producto editado", 4000)

    def eliminar_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Seleccioná un producto para eliminar", 4000)
            return
        nombre = self.table.item(fila,2).text()
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar {nombre}?")
        if confirm == QMessageBox.Yes:
            pid = int(self.table.item(fila,0).text())
            database.eliminar_producto(pid)
            self.actualizar_tabla()
            self.actualizar_historial()
            self.aplicar_filtros()
            self.status.showMessage("❌ Producto eliminado", 4000)

    # -------------------------
    # Vender (versión simple / ticket)
    # -------------------------
    def vender_producto(self):
        fila = self.table.currentRow()
        if fila < 0:
            self.status.showMessage("⚠ Seleccioná un producto para vender", 4000)
            return

        producto = {
            "id": int(self.table.item(fila, 0).text()),
            "codigo": self.table.item(fila, 1).text(),
            "nombre": self.table.item(fila, 2).text(),
            "stock": int(self.table.item(fila, 3).text()),
            "precio": float(self.table.item(fila, 6).text())
        }

        dialog = FormularioVenta(producto, self)
        if dialog.exec():
            cantidad = dialog.obtener_cantidad()
            recibido = dialog.obtener_recibido()
            if cantidad > producto["stock"]:
                self.status.showMessage("❌ Stock insuficiente", 4000)
                return
            ok = database.modificar_stock(producto["id"], -cantidad)
            if ok:
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                total = cantidad * producto["precio"]
                self.status.showMessage(f"🛒 Vendidas {cantidad} de {producto['nombre']} | Total: ${total:,.2f}", 8000)
                self.historial.append(f"💵 Venta: {cantidad} x {producto['nombre']} = ${total:,.2f}")
                # si ingresó efectivo, mostrar vuelto
                if recibido is not None:
                    vuelto = recibido - total
                    self.status.showMessage(f"💵 Recibido: ${recibido:,.2f} | Vuelto: ${vuelto:,.2f}", 8000)

    # -------------------------
    # Importar / Exportar Excel
    # -------------------------
    def exportar_excel(self):
        productos = database.obtener_productos()
        df = pd.DataFrame(productos, columns=[
            "ID", "Código", "Nombre", "Cantidad", "Costo", "Sector", "Precio", "Código Barras", "Movimientos"
        ])
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", "stock_exportado.xlsx", "Excel Files (*.xlsx)")
        if not ruta:
            return
        with pd.ExcelWriter(ruta, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Stock", index=False)
            worksheet = writer.sheets["Stock"]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        self.status.showMessage(f"✅ Exportado a {ruta}", 4000)

    def importar_excel(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Excel", "", "Excel Files (*.xlsx)")
        if not ruta:
            return
        try:
            df = pd.read_excel(ruta)
            cols = [c.strip().lower() for c in df.columns]

            # detectar nombres posibles
            code_col = None
            for opt in ["codigo", "código", "code"]:
                if opt in cols:
                    code_col = df.columns[cols.index(opt)]
                    break
            name_col = None
            for opt in ["nombre", "name"]:
                if opt in cols:
                    name_col = df.columns[cols.index(opt)]
                    break
            qty_col = None
            for opt in ["cantidad", "qty", "quantity"]:
                if opt in cols:
                    qty_col = df.columns[cols.index(opt)]
                    break

            # campos opcionales
            costo_col = None
            sector_col = None
            barras_col = None
            for i, c in enumerate(cols):
                if c in ("costo", "cost"):
                    costo_col = df.columns[i]
                if c == "sector":
                    sector_col = df.columns[i]
                if c in ("codigo barras", "codigo_barras", "codigo de barras", "barcode"):
                    barras_col = df.columns[i]

            if not (code_col and name_col and qty_col):
                QMessageBox.warning(self, "Columnas faltantes", "El Excel debe contener al menos: Código, Nombre y Cantidad.")
                return

            # cargar sectores actuales
            sectores = database.obtener_sectores()
            sector_map = {s[1]: s[0] for s in sectores}

            # procesar filas
            for _, row in df.iterrows():
                codigo = str(row[code_col]).strip()
                nombre = str(row[name_col]).strip()
                cantidad = int(row[qty_col]) if not pd.isna(row[qty_col]) else 0
                costo = float(row[costo_col]) if (costo_col and not pd.isna(row[costo_col])) else 0.0
                sector_nombre = str(row[sector_col]).strip() if (sector_col and not pd.isna(row[sector_col])) else "Almacen"
                codigo_barras = str(row[barras_col]).strip() if (barras_col and not pd.isna(row[barras_col])) else ""

                # crear sector si no existe (margen por defecto 30%)
                if sector_nombre not in sector_map:
                    database.agregar_sector(sector_nombre, 0.30)
                    sectores = database.obtener_sectores()
                    sector_map = {s[1]: s[0] for s in sectores}

                sector_id = sector_map.get(sector_nombre)
                # usar agregar_o_actualizar para compatibilidad
                database.agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras)

            self.actualizar_tabla()
            self.actualizar_historial()
            self.status.showMessage("📥 Importación finalizada", 4000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar: {e}")

    # -------------------------
    # Reportes simples
    # -------------------------
    def generar_reporte_ventas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Generar reporte de ventas")
        vbox = QVBoxLayout(dlg)
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
        ok.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)
        if dlg.exec():
            fi = date_ini.date().toString("yyyy-MM-dd")
            ff = date_fin.date().toString("yyyy-MM-dd")
            ventas = database.obtener_ventas(fi, ff)
            if not ventas:
                self.status.showMessage("ℹ️ No se encontraron ventas", 4000)
                return
            df = pd.DataFrame(ventas, columns=["Código", "Nombre", "Cantidad", "Precio", "Fecha"])
            total_unidades = sum(abs(int(v[2])) for v in ventas)
            total_dinero = sum(abs(int(v[2])) * float(v[3]) for v in ventas)
            df.loc[len(df.index)] = ["", "TOTAL", total_unidades, total_dinero, ""]
            ruta, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", "reporte_ventas.xlsx", "Excel Files (*.xlsx)")
            if ruta:
                with pd.ExcelWriter(ruta, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Ventas", index=False)
                    ws = writer.sheets["Ventas"]
                    for i, col in enumerate(df.columns):
                        max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                        ws.set_column(i, i, max_len)
                self.status.showMessage(f"📊 Reporte guardado en {ruta}", 5000)

    def imprimir_bajo_stock(self):
        productos = [p for p in self._productos_cache if int(p[3]) <= 5]
        if not productos:
            self.status.showMessage("ℹ️ No hay productos con bajo stock", 4000)
            return
        df = pd.DataFrame(productos, columns=["ID", "Código", "Nombre", "Cantidad", "Costo", "Sector", "Precio", "Código Barras", "Movimientos"])
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar bajo stock", "bajo_stock.xlsx", "Excel Files (*.xlsx)")
        if ruta:
            with pd.ExcelWriter(ruta, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name="BajoStock", index=False)
                ws = writer.sheets["BajoStock"]
                for i, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    ws.set_column(i, i, max_len)
            self.status.showMessage(f"🖨 Guardado: {ruta}", 4000)
