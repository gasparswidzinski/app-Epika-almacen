# ui_main.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QTextEdit, QFileDialog, QLineEdit, QLabel, QCheckBox,
    QToolBar, QStatusBar, QMessageBox, QDialog, QDateEdit, QPushButton,
    QComboBox, QFormLayout
)
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtCore import Qt, QDate, QTimer
import pandas as pd
import database
from ui_formulario import FormularioProducto
from ui_vender import FormularioPOS
import os
import shutil
from PySide6.QtCore import QTimer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Stock - Almacén (Fase 2)")
        self.resize(1200, 650)
        self._pos_dialog = None

        # toolbar
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # acciones
        self.act_agregar = QAction("➕ Agregar (F1)", self)
        self.act_editar = QAction("✏️ Editar (F3)", self)
        self.act_eliminar = QAction("🗑 Eliminar (Del)", self)
        self.act_vender = QAction("🛒 Registrar Venta (F2)", self)
        self.act_importar = QAction("📥 Importar Excel", self)
        self.act_exportar = QAction("📤 Exportar Stock", self)
        self.act_reporte = QAction("📊 Reporte ventas", self)
        self.act_bajo_stock = QAction("🖨 Bajo stock", self)
        self.act_reembolsos = QAction("↩️ Reembolsos", self)
        # NUEVAS acciones
        self.act_clientes = QAction("👥 Clientes", self)
        self.act_pendientes = QAction("🧾 Ventas Pendientes", self)
        self.act_backup = QAction("💾 Backup", self)

        for act in [self.act_agregar, self.act_editar, self.act_eliminar,
                    self.act_vender, self.act_importar, self.act_exportar,
                    self.act_reporte, self.act_bajo_stock, self.act_reembolsos,
                    self.act_clientes, self.act_pendientes, self.act_backup]:
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
        right_layout.addWidget(QLabel("📜 Historial (últimos movimientos)"))
        self.historial = QTextEdit()
        self.historial.setReadOnly(True)
        right_layout.addWidget(self.historial)
        main_layout.addLayout(right_layout, stretch=1)

        self.setCentralWidget(central)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("✅ Aplicación iniciada")

        # inicializar
        self._productos_cache = []
        self.actualizar_tabla()
        self.actualizar_historial()

        # conexiones
        self.act_agregar.triggered.connect(self.abrir_formulario)
        self.act_editar.triggered.connect(self.editar_producto)
        self.act_eliminar.triggered.connect(self.eliminar_producto)
        self.act_vender.triggered.connect(self.abrir_pos)
        self.act_importar.triggered.connect(self.importar_excel)
        self.act_exportar.triggered.connect(self.exportar_excel)
        self.act_reporte.triggered.connect(self.generar_reporte_ventas)
        self.act_bajo_stock.triggered.connect(self.imprimir_bajo_stock)
        self.act_reembolsos.triggered.connect(self.abrir_reembolsos)
        self.act_clientes.triggered.connect(self.abrir_clientes)
        self.act_pendientes.triggered.connect(self.abrir_pendientes)
        self.act_backup.triggered.connect(self.backup_manual)

        self.input_buscar.textChanged.connect(self.aplicar_filtros)
        self.chk_bajo_stock.toggled.connect(self.aplicar_filtros)
        
        self.act_gastos = QAction("💵 Gastos", self)
        toolbar.addAction(self.act_gastos)
        self.act_gastos.triggered.connect(self.abrir_gastos)

        
        

        # atajos
        self.act_agregar.setShortcut(QKeySequence("F1"))
        self.act_vender.setShortcut(QKeySequence("F2"))
        self.act_editar.setShortcut(QKeySequence("F3"))
        self.act_eliminar.setShortcut(QKeySequence("Delete"))

        # --- SCANNER ---
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._procesar_scanner)
        # cuando cambia el texto, reiniciamos el timer
        self.input_buscar.textChanged.connect(self._on_scanner_text_changed)

    # -------------------------
    # SCANNER
    # -------------------------
    def _on_scanner_text_changed(self, texto):
        if texto.strip():
            # esperamos un poquito a que el lector termine de "escribir"
            self._scan_timer.start(250)

    def _procesar_scanner(self):
        codigo = self.input_buscar.text().strip()
        if not codigo:
            return
        self.input_buscar.clear()
        self.input_buscar.setFocus()
        self.escanear_codigo(codigo)
                   
    def escanear_codigo(self, codigo):
        # Buscar producto por barcode o código interno
        prod = database.obtener_producto_por_barcode(codigo)
        if not prod:
            for p in database.obtener_productos():
                pid, cod, nombre, cantidad, costo, sector, precio, codigo_barras, movs = p
                if str(cod).strip().lower() == codigo.lower():
                    prod = p
                    break

        if prod:
            if not self._pos_dialog or not self._pos_dialog.isVisible():
                # Abrir POS en modo no bloqueante
                self._pos_dialog = FormularioPOS(self, producto_preseleccionado=prod)

                # cuando se cierre el POS, refrescar todo y resetear variable
                self._pos_dialog.finished.connect(lambda _: (
                    self.actualizar_tabla(),
                    self.actualizar_historial(),
                    self.aplicar_filtros(),
                    self.input_buscar.setFocus(),
                    self.status.showMessage("🛒 Venta registrada", 5000),
                    setattr(self, "_pos_dialog", None)   # 👈 importante
                ))

                self._pos_dialog.open()

                # aseguramos que el POS tome foco y reciba el escaneo
                QTimer.singleShot(0, lambda: (
                    self._pos_dialog.activateWindow(),
                    self._pos_dialog.raise_(),
                    self._pos_dialog.input_buscar.setFocus()
                ))
            else:
                # Ya hay un POS abierto → agregar directo al carrito
                self._pos_dialog.agregar_producto_externo(prod)
        else:
            # Producto no existe → abrir formulario de alta
            form = FormularioProducto(self, codigo_barras=codigo)
            if form.exec():
                self.actualizar_tabla()
                self.actualizar_historial()
                self.aplicar_filtros()
                self.status.showMessage("➕ Producto nuevo agregado", 4000)




    # -------------------------
    # tabla productos (igual que antes)
    # -------------------------
    def _cargar_productos(self):
        self._productos_cache = database.obtener_productos()
        return self._productos_cache

    def actualizar_tabla(self):
        productos = self._cargar_productos()
        self._pintar_tabla(productos)

    def _pintar_tabla(self, productos):
        headers = ["ID", "Código", "Nombre", "Cantidad", "Costo", "Sector", "Precio", "Código Barras", "Movs"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(productos))

        for r, prod in enumerate(productos):
            for c, val in enumerate(prod):
                item = QTableWidgetItem(str(val))
                if c == 3:
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
        movs = database.obtener_movimientos(300)
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
    # POS / ventas
    # -------------------------
    def abrir_pos(self):
        dialog = FormularioPOS(self)
        if dialog.exec():
            # recargar todo
            self.actualizar_tabla()
            self.actualizar_historial()
            self.aplicar_filtros()
            self.status.showMessage("🛒 Venta registrada", 5000)

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
            self.formatear_hoja_excel(writer, "Stock", df)
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

                if sector_nombre not in sector_map:
                    database.agregar_sector(sector_nombre, 0.30)
                    sectores = database.obtener_sectores()
                    sector_map = {s[1]: s[0] for s in sectores}

                sector_id = sector_map.get(sector_nombre)
                database.agregar_o_actualizar_producto(codigo, nombre, cantidad, costo, sector_id, codigo_barras)

            self.actualizar_tabla()
            self.actualizar_historial()
            self.status.showMessage("📥 Importación finalizada", 4000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar: {e}")

    # -------------------------
    # Helper Excel (formato tabla: encabezado gris, bordes, autoancho)
    # -------------------------
    def formatear_hoja_excel(self, writer, sheet_name, df):
        ws = writer.sheets[sheet_name]
        wb = writer.book
        header_fmt = wb.add_format({"bold": True, "bg_color": "#DDDDDD", "border": 1})
        cell_fmt = wb.add_format({"border": 1})
        for c, col in enumerate(df.columns):
            try:
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            except Exception:
                max_len = len(col) + 2
            ws.set_column(c, c, max_len)
            ws.write(0, c, col, header_fmt)
        for r in range(1, len(df) + 1):
            for c in range(len(df.columns)):
                ws.write(r, c, df.iloc[r - 1, c], cell_fmt)

    # -------------------------
    # Reportes - ventas agrupadas por tipo de pago (formato mejorado)
    # -------------------------
    def generar_reporte_ventas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Generar reporte de ventas")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Desde:"))
        date_ini = QDateEdit(QDate.currentDate().addDays(-30))
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
            ventas = database.obtener_ventas_con_detalles()
            ventas = [v for v in ventas if fi <= v["fecha"][:10] <= ff]

            if not ventas:
                self.status.showMessage("ℹ️ No se encontraron ventas en el rango", 4000)
                return

            ventas.sort(key=lambda v: v["tipo_pago"])
            ruta, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", "reporte_ventas.xlsx", "Excel Files (*.xlsx)")
            if not ruta:
                return

            with pd.ExcelWriter(ruta, engine="xlsxwriter") as writer:
                wb = writer.book
                ws = wb.add_worksheet("Ventas")
                writer.sheets["Ventas"] = ws

                bold = wb.add_format({"bold": True})
                header_fmt = wb.add_format({"bold": True, "bg_color": "#DDDDDD", "border": 1})
                cell_fmt = wb.add_format({"border": 1})
                money = wb.add_format({"num_format": "$#,##0.00", "border": 1})

                row = 0
                total_general = 0
                max_lens = [0,0,0,0,0]

                for tipo in sorted(set(v["tipo_pago"] for v in ventas)):
                    ws.write(row, 0, f"Tipo de pago: {tipo}", bold)
                    row += 1
                    headers = ["Fecha/Hora", "Producto", "Cantidad", "Precio Unitario", "Subtotal"]
                    for i, h in enumerate(headers):
                        ws.write(row, i, h, header_fmt)
                        max_lens[i] = max(max_lens[i], len(str(h)))
                    row += 1

                    total_tipo = 0
                    for v in [x for x in ventas if x["tipo_pago"] == tipo]:
                        for item in v["items"]:
                            values = [v["fecha"], item["nombre"], item["cantidad"], item["precio"], item["subtotal"]]
                            for i, val in enumerate(values):
                                txt = str(val)
                                max_lens[i] = max(max_lens[i], len(txt))

                            ws.write(row, 0, v["fecha"], cell_fmt)
                            ws.write(row, 1, item["nombre"], cell_fmt)
                            ws.write(row, 2, item["cantidad"], cell_fmt)
                            ws.write_number(row, 3, item["precio"], money)
                            ws.write_number(row, 4, item["subtotal"], money)
                            total_tipo += item["subtotal"]
                            row += 1

                    ws.write(row, 3, "TOTAL " + tipo, header_fmt)
                    ws.write_number(row, 4, total_tipo, money)
                    row += 2
                    total_general += total_tipo

                ws.write(row, 3, "TOTAL GENERAL", header_fmt)
                ws.write_number(row, 4, total_general, money)

                for i, width in enumerate(max_lens):
                    ws.set_column(i, i, width + 2)

            self.status.showMessage(f"📊 Reporte guardado en {ruta}", 5000)

    # -------------------------
    # Reembolsos
    # -------------------------
    def abrir_reembolsos(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Gestión de Reembolsos")
        dlg.resize(900, 600)
        layout = QVBoxLayout(dlg)

        # Tabla de ventas
        table_ventas = QTableWidget()
        table_ventas.setColumnCount(5)
        table_ventas.setHorizontalHeaderLabels(["Venta ID", "Fecha", "Pago", "Estado", "Total ($)"])
        layout.addWidget(table_ventas)

        # Tabla de items
        table_items = QTableWidget()
        table_items.setColumnCount(5)
        table_items.setHorizontalHeaderLabels(["Item ID", "Producto", "Cantidad", "Precio Unitario ($)", "Subtotal ($)"])
        layout.addWidget(table_items)

        # Botones
        btn_layout = QHBoxLayout()
        btn_reembolsar_total = QPushButton("↩️ Reembolsar toda la venta")
        btn_reembolsar_parcial = QPushButton("↩️ Reembolsar ítem seleccionado")
        btn_cerrar = QPushButton("❌ Cerrar")

        btn_reembolsar_total.setStyleSheet("background-color:#d9534f;color:white;font-weight:bold;")
        btn_reembolsar_parcial.setStyleSheet("background-color:#0275d8;color:white;font-weight:bold;")
        btn_cerrar.setStyleSheet("background-color:#5bc0de;color:black;")

        btn_layout.addWidget(btn_reembolsar_total)
        btn_layout.addWidget(btn_reembolsar_parcial)
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

        # Cargar ventas
        ventas = database.obtener_ventas_con_detalles()
        table_ventas.setRowCount(len(ventas))
        for r, v in enumerate(ventas):
            table_ventas.setItem(r, 0, QTableWidgetItem(str(v["id"])))
            table_ventas.setItem(r, 1, QTableWidgetItem(str(v["fecha"])))
            table_ventas.setItem(r, 2, QTableWidgetItem(v["tipo_pago"]))
            table_ventas.setItem(r, 3, QTableWidgetItem(v["estado"]))

            item_total = QTableWidgetItem(f"${v['total']:.2f}")
            item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table_ventas.setItem(r, 4, item_total)

            # Colorear ventas reembolsadas
            if v["estado"] == "REEMBOLSADO":
                for col in range(5):
                    table_ventas.item(r, col).setBackground(QColor("#f0f0f0"))

        # Mostrar items de la venta seleccionada
        def mostrar_items():
            row = table_ventas.currentRow()
            if row < 0:
                return
            venta_id = int(table_ventas.item(row, 0).text())
            venta = next((x for x in ventas if x["id"] == venta_id), None)
            if not venta:
                return

            table_items.setRowCount(len(venta["items"]))
            for i, it in enumerate(venta["items"]):
                # Usamos el ID real del item en la DB
                table_items.setItem(i, 0, QTableWidgetItem(str(it["id"])))
                table_items.setItem(i, 1, QTableWidgetItem(it["nombre"]))

                item_cant = QTableWidgetItem(str(it["cantidad"]))
                item_cant.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table_items.setItem(i, 2, item_cant)

                item_precio = QTableWidgetItem(f"${it['precio']:.2f}")
                item_precio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table_items.setItem(i, 3, item_precio)

                item_sub = QTableWidgetItem(f"${it['subtotal']:.2f}")
                item_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table_items.setItem(i, 4, item_sub)

        table_ventas.itemSelectionChanged.connect(mostrar_items)
        if ventas:
            table_ventas.selectRow(0)
            mostrar_items()

        # Reembolso total
        def reembolsar_total():
            row = table_ventas.currentRow()
            if row < 0:
                QMessageBox.warning(dlg, "Error", "Seleccione una venta para reembolsar.")
                return

            venta_id = int(table_ventas.item(row, 0).text())

            reply = QMessageBox.question(
                dlg, "Confirmar reembolso",
                f"¿Seguro que desea reembolsar COMPLETAMENTE la venta {venta_id}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            ok, msg = database.reembolsar_venta(venta_id)
            if ok:
                QMessageBox.information(dlg, "Reembolso realizado", msg)
                self.actualizar_tabla()       #  refresca la tabla de productos
                self.actualizar_historial()   # refresca historial de movimientos
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "Error en reembolso", msg)

        # Reembolso parcial
        def reembolsar_parcial():
            row_v = table_ventas.currentRow()
            row_i = table_items.currentRow()

            if row_v < 0 or row_i < 0:
                QMessageBox.warning(dlg, "Error", "Seleccione una venta y un ítem para reembolsar.")
                return

            venta_id = int(table_ventas.item(row_v, 0).text())
            item_id = int(table_items.item(row_i, 0).text())  # Ahora es el ID real

            reply = QMessageBox.question(
                dlg, "Confirmar reembolso parcial",
                f"¿Seguro que desea reembolsar el ítem {item_id} de la venta {venta_id}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            ok, msg = database.reembolsar_venta(venta_id, [item_id])
            if ok:
                QMessageBox.information(dlg, "Reembolso parcial realizado", msg)
                self.actualizar_tabla()
                self.actualizar_historial()
                dlg.accept()
            else:
                QMessageBox.warning(dlg, "Error en reembolso", msg)

        # Conectar botones
        btn_reembolsar_total.clicked.connect(reembolsar_total)
        btn_reembolsar_parcial.clicked.connect(reembolsar_parcial)
        btn_cerrar.clicked.connect(dlg.reject)

        dlg.exec()


    # -------------------------
    # Bajo stock (usa helper de Excel)
    # -------------------------
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
                self.formatear_hoja_excel(writer, "BajoStock", df)
            self.status.showMessage(f"🖨 Guardado: {ruta}", 4000)

    # -------------------------
    # NUEVO: Backup manual de la base de datos
    # -------------------------
    def backup_manual(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar backup", "almacen_backup.db", "Database Files (*.db)")
        if not ruta:
            return
        if not os.path.exists("almacen.db"):
            QMessageBox.warning(self, "Backup", "No existe el archivo almacen.db")
            return
        try:
            shutil.copy("almacen.db", ruta)
            QMessageBox.information(self, "Backup", f"Backup guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Backup", str(e))

    # -------------------------
    # CLIENTES - ABM (NUEVO)
    # -------------------------
    def abrir_clientes(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Clientes")
        vbox = QVBoxLayout(dlg)
        table = QTableWidget()
        clientes = database.obtener_clientes()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono", "Dirección", "Notas"])
        table.setRowCount(len(clientes))
        for r, c in enumerate(clientes):
            table.setItem(r,0, QTableWidgetItem(str(c[0])))
            table.setItem(r,1, QTableWidgetItem(str(c[1])))
            table.setItem(r,2, QTableWidgetItem(str(c[2] or "")))
            table.setItem(r,3, QTableWidgetItem(str(c[3] or "")))
            table.setItem(r,4, QTableWidgetItem(str(c[4] or "")))
        vbox.addWidget(table)

        btns = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar")
        btn_edit = QPushButton("✏️ Editar")
        btn_del = QPushButton("🗑 Eliminar")
        btn_close = QPushButton("Cerrar")
        btns.addWidget(btn_add); btns.addWidget(btn_edit); btns.addWidget(btn_del); btns.addWidget(btn_close)
        vbox.addLayout(btns)

        def agregar_cliente():
            d = QDialog(self)
            d.setWindowTitle("Agregar Cliente")
            f = QFormLayout(d)
            inp_nombre = QLineEdit()
            inp_tel = QLineEdit()
            inp_dir = QLineEdit()
            inp_not = QLineEdit()
            f.addRow("Nombre:", inp_nombre)
            f.addRow("Teléfono:", inp_tel)
            f.addRow("Dirección:", inp_dir)
            f.addRow("Notas:", inp_not)
            ok = QPushButton("Crear")
            canc = QPushButton("Cancelar")
            row = QHBoxLayout()
            row.addWidget(ok); row.addWidget(canc)
            f.addRow(row)
            ok.clicked.connect(d.accept)
            canc.clicked.connect(d.reject)
            if d.exec():
                nombre = inp_nombre.text().strip()
                if not nombre:
                    QMessageBox.warning(self, "Cliente", "Nombre requerido")
                    return
                telefono = inp_tel.text().strip()
                direccion = inp_dir.text().strip()
                notas = inp_not.text().strip()
                database.agregar_cliente(nombre, telefono, direccion, notas)
                QMessageBox.information(self, "Clientes", "Cliente agregado")
                dlg.accept()
                self.actualizar_historial()
                self.actualizar_tabla()
                self.abrir_clientes()

        def editar_cliente():
            r = table.currentRow()
            if r < 0:
                QMessageBox.warning(self, "Seleccionar", "Seleccioná un cliente")
                return
            cid = int(table.item(r,0).text())
            d = QDialog(self)
            d.setWindowTitle("Editar Cliente")
            f = QFormLayout(d)
            inp_nombre = QLineEdit(table.item(r,1).text())
            inp_tel = QLineEdit(table.item(r,2).text())
            inp_dir = QLineEdit(table.item(r,3).text())
            inp_not = QLineEdit(table.item(r,4).text())
            f.addRow("Nombre:", inp_nombre)
            f.addRow("Teléfono:", inp_tel)
            f.addRow("Dirección:", inp_dir)
            f.addRow("Notas:", inp_not)
            ok = QPushButton("Guardar")
            canc = QPushButton("Cancelar")
            row = QHBoxLayout()
            row.addWidget(ok); row.addWidget(canc)
            f.addRow(row)
            ok.clicked.connect(d.accept)
            canc.clicked.connect(d.reject)
            if d.exec():
                database.editar_cliente(cid, inp_nombre.text().strip(), inp_tel.text().strip(), inp_dir.text().strip(), inp_not.text().strip())
                QMessageBox.information(self, "Clientes", "Cliente editado")
                dlg.accept()
                self.abrir_clientes()

        def eliminar_cliente():
            r = table.currentRow()
            if r < 0:
                QMessageBox.warning(self, "Seleccionar", "Seleccioná un cliente")
                return
            cid = int(table.item(r,0).text())
            confirm = QMessageBox.question(self, "Confirmar", "¿Eliminar cliente seleccionado?")
            if confirm == QMessageBox.Yes:
                database.eliminar_cliente(cid)
                QMessageBox.information(self, "Clientes", "Cliente eliminado")
                dlg.accept()
                self.abrir_clientes()

        btn_add.clicked.connect(agregar_cliente)
        btn_edit.clicked.connect(editar_cliente)
        btn_del.clicked.connect(eliminar_cliente)
        btn_close.clicked.connect(dlg.reject)

        dlg.exec()

    # -------------------------
    # PENDIENTES (ventas a cuenta) - NUEVO
    # -------------------------
    def abrir_pendientes(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ventas Pendientes / Deudores")
        vbox = QVBoxLayout(dlg)

        # lista de ventas pendientes
        ventas = database.obtener_ventas(estado="PENDIENTE")
        # agrupar por cliente
        agrup = {}
        for v in ventas:
            venta_id, fecha, tipo, estado, total, recibido, vuelto, cliente = v
            key = cliente or "(Sin cliente)"
            agrup.setdefault(key, []).append((venta_id, fecha, total))

        # tabla por cliente
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Cliente", "Ventas pendientes", "Total adeudado"])
        table.setRowCount(len(agrup))
        for r, (cliente, ventas_cliente) in enumerate(agrup.items()):
            suma = sum(v[2] for v in ventas_cliente)
            table.setItem(r, 0, QTableWidgetItem(str(cliente)))
            table.setItem(r, 1, QTableWidgetItem(str(len(ventas_cliente))))
            table.setItem(r, 2, QTableWidgetItem(f"${suma:,.2f}"))
        vbox.addWidget(table)

        btns = QHBoxLayout()
        btn_ver = QPushButton("🔎 Ver ventas del cliente")
        btn_cobrar = QPushButton("💰 Cobrar venta seleccionada")
        btn_close = QPushButton("Cerrar")
        btns.addWidget(btn_ver); btns.addWidget(btn_cobrar); btns.addWidget(btn_close)
        vbox.addLayout(btns)

        def ver_ventas():
            r = table.currentRow()
            if r < 0:
                QMessageBox.warning(self, "Seleccionar", "Seleccioná un cliente")
                return
            cliente = table.item(r,0).text()
            # mostrar detalle de ventas de ese cliente
            sub = QDialog(self)
            sub.setWindowTitle(f"Ventas pendientes - {cliente}")
            sv = QVBoxLayout(sub)
            sub_table = QTableWidget()
            sub_table.setColumnCount(4)
            sub_table.setHorizontalHeaderLabels(["Venta ID", "Fecha", "Total", "Detalle"])
            # buscar ventas con ese cliente
            rows = []
            for v in ventas:
                if (v[7] or "(Sin cliente)") == cliente:
                    rows.append(v)
            sub_table.setRowCount(len(rows))
            for rr, vv in enumerate(rows):
                sub_table.setItem(rr,0, QTableWidgetItem(str(vv[0])))
                sub_table.setItem(rr,1, QTableWidgetItem(str(vv[1])))
                sub_table.setItem(rr,2, QTableWidgetItem(f"${vv[4]:,.2f}"))
                # detalle (cargar items)
                items = database.obtener_items_venta(vv[0])
                detalle = ", ".join([f"{it[2]} x{it[3]}" for it in items])
                sub_table.setItem(rr,3, QTableWidgetItem(detalle))
            sv.addWidget(sub_table)
            btn_ok = QPushButton("Cerrar")
            sv.addWidget(btn_ok)
            btn_ok.clicked.connect(sub.reject)
            sub.exec()

        def cobrar():
            # pedimos selección de cliente y luego selección de venta (simplificamos: pedimos ID manual)
            r = table.currentRow()
            if r < 0:
                QMessageBox.warning(self, "Seleccionar", "Seleccioná un cliente")
                return
            cliente = table.item(r,0).text()
            # list ventas para ese cliente
            ventas_cliente = [v for v in ventas if (v[7] or "(Sin cliente)") == cliente]
            if not ventas_cliente:
                QMessageBox.information(self, "Cobrar", "No hay ventas para este cliente")
                return
            # pedir al usuario qué venta cobrar (si hay varias) - simple: mostrar ids
            opciones = [f"ID {v[0]} - {v[1]} - ${v[4]:,.2f}" for v in ventas_cliente]
            from PySide6.QtWidgets import QInputDialog  # import local
            sel, ok = QInputDialog.getItem(self, "Seleccionar venta", "Ventas pendientes:", opciones, 0, False)
            if not ok:
                return
            idx = opciones.index(sel)
            venta_id = ventas_cliente[idx][0]
            total = ventas_cliente[idx][4]

            # diálogo cobro
            d = QDialog(self)
            d.setWindowTitle(f"Cobrar Venta {venta_id}")
            f = QFormLayout(d)
            combo = QComboBox()
            combo.addItems(["Efectivo", "Transferencia", "QR"])
            f.addRow("Tipo de pago:", combo)
            inp_rec = QLineEdit()
            inp_rec.setPlaceholderText("0.00 (si efectivo)")
            f.addRow("Monto recibido:", inp_rec)
            btn_ok = QPushButton("Cobrar")
            btn_cancel = QPushButton("Cancelar")
            row = QHBoxLayout()
            row.addWidget(btn_ok); row.addWidget(btn_cancel)
            f.addRow(row)
            btn_ok.clicked.connect(d.accept)
            btn_cancel.clicked.connect(d.reject)
            if d.exec():
                tipo = combo.currentText()
                recibido = None
                try:
                    recibido = float(inp_rec.text()) if inp_rec.text().strip() != "" else None
                except:
                    QMessageBox.warning(self, "Monto", "Monto inválido")
                    return
                ok2, msg = database.marcar_venta_pagada(venta_id, tipo, recibido)
                if ok2:
                    QMessageBox.information(self, "Cobro", "Venta cobrada correctamente")
                    self.actualizar_tabla()
                    self.actualizar_historial()
                    dlg.accept()
                else:
                    QMessageBox.critical(self, "Error", msg)

        btn_ver.clicked.connect(ver_ventas)
        btn_cobrar.clicked.connect(cobrar)
        btn_close.clicked.connect(dlg.reject)
        dlg.exec()
    
    def abrir_gastos(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Gestión de Gastos")
        layout = QVBoxLayout(dlg)

        # --- Selector de tipo ---
        tipo_layout = QHBoxLayout()
        tipo_layout.addWidget(QLabel("Tipo de gasto:"))
        combo_tipo = QComboBox()
        combo_tipo.addItems(["almacen", "personal"])
        tipo_layout.addWidget(combo_tipo)
        layout.addLayout(tipo_layout)

        # --- Formulario de gasto ---
        form_layout = QHBoxLayout()
        combo_cat = QComboBox()
        combo_cat.addItems(["Proveedores", "Sueldos", "Alquiler", "Luz",
                            "Impuestos", "Contador", "Agua", "Otros"])
        form_layout.addWidget(combo_cat)

        inp_monto = QLineEdit()
        inp_monto.setPlaceholderText("Monto")
        form_layout.addWidget(inp_monto)

        inp_detalle = QLineEdit()
        inp_detalle.setPlaceholderText("Detalle (opcional)")
        form_layout.addWidget(inp_detalle)

        btn_add = QPushButton("➕ Agregar")
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        # --- Selector de fechas ---
        fechas_layout = QHBoxLayout()
        fechas_layout.addWidget(QLabel("Desde:"))
        date_inicio = QDateEdit()
        date_inicio.setCalendarPopup(True)
        date_inicio.setDisplayFormat("yyyy-MM-dd")
        # Primer día del mes actual
        hoy = QDate.currentDate()
        primer_dia_mes = QDate(hoy.year(), hoy.month(), 1)
        date_inicio.setDate(primer_dia_mes)
        fechas_layout.addWidget(date_inicio)

        fechas_layout.addWidget(QLabel("Hasta:"))
        date_fin = QDateEdit()
        date_fin.setCalendarPopup(True)
        date_fin.setDisplayFormat("yyyy-MM-dd")
        # Fecha actual
        date_fin.setDate(hoy)
        fechas_layout.addWidget(date_fin)

        layout.addLayout(fechas_layout)
        
        # --- Tabla de gastos ---
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Fecha", "Categoría", "Monto", "Detalle"])
        layout.addWidget(table)
        # --- Botones ---
        btns = QHBoxLayout()
        btn_del = QPushButton("🗑️ Eliminar seleccionado")
        btn_export = QPushButton("📊 Exportar a Excel")
        btns.addWidget(btn_del)
        btns.addWidget(btn_export)
        layout.addLayout(btns)

        # --- Funciones internas ---
        def cargar():
            gastos = database.obtener_gastos(combo_tipo.currentText())
            table.setRowCount(len(gastos))
            for i, g in enumerate(gastos):
                gid, fecha, cat, monto, detalle = g
                table.setItem(i, 0, QTableWidgetItem(fecha))
                table.setItem(i, 1, QTableWidgetItem(cat))
                table.setItem(i, 2, QTableWidgetItem(f"${monto:.2f}"))
                table.setItem(i, 3, QTableWidgetItem(detalle or ""))

        def agregar():
            try:
                categoria = combo_cat.currentText()
                monto = float(inp_monto.text())
                detalle = inp_detalle.text().strip()
                database.agregar_gasto(categoria, monto, detalle, combo_tipo.currentText())
                cargar()
                inp_monto.clear()
                inp_detalle.clear()
            except Exception as e:
                QMessageBox.critical(dlg, "Error", f"No se pudo agregar gasto:\n{e}")

        def eliminar():
            row = table.currentRow()
            if row < 0:
                return
            gid = database.obtener_gastos(combo_tipo.currentText())[row][0]
            database.eliminar_gasto(gid)
            cargar()

        def exportar():
            from datetime import datetime
            tipo = combo_tipo.currentText()
            f1 = date_inicio.date().toString("yyyy-MM-dd") if date_inicio.date().isValid() else None
            f2 = date_fin.date().toString("yyyy-MM-dd") if date_fin.date().isValid() else None

            # Nombre automático del archivo
            fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
            rango_txt = ""
            if f1 and f2:
                rango_txt = f"_{f1}_a_{f2}"
            elif f1:
                rango_txt = f"_desde_{f1}"
            elif f2:
                rango_txt = f"_hasta_{f2}"

            default_name = f"gastos_{tipo}{rango_txt}_{fecha_actual}.xlsx"

            filename, _ = QFileDialog.getSaveFileName(dlg, "Guardar Excel", default_name, "Excel (*.xlsx)")
            if filename:
                path = database.exportar_gastos_excel(tipo, filename, fecha_inicio=f1, fecha_fin=f2)
                QMessageBox.information(dlg, "Exportación exitosa", f"Archivo generado:\n{path}")

        combo_tipo.currentIndexChanged.connect(cargar)
        btn_add.clicked.connect(agregar)
        btn_del.clicked.connect(eliminar)
        btn_export.clicked.connect(exportar)

        cargar()
        dlg.exec()
