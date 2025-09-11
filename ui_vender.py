#ui_vender.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QLineEdit, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem,
    QFormLayout, QDialogButtonBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
import database
import os

class FormularioPOS(QDialog):
    def __init__(self, parent=None, producto_preseleccionado=None):
        super().__init__(parent)
        self.setWindowTitle("Punto de Venta - Registrar Venta")
        self.resize(780, 520)

        self.cart = []

        layout = QVBoxLayout()

        # Cliente selector
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        cliente_layout.addWidget(self.combo_cliente)
        self.btn_nuevo_cliente = QPushButton("➕ Nuevo")
        cliente_layout.addWidget(self.btn_nuevo_cliente)
        layout.addLayout(cliente_layout)
        self.btn_nuevo_cliente.clicked.connect(self._crear_cliente_rapido)
        self._cargar_clientes()
        
        self._venta_confirmada = False
        self._recupero_carrito_este_sesion = False
        QTimer.singleShot(0, self._intentar_recuperar_carrito)

        # Buscador por código, nombre o barcode
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar (Código / Nombre / Barcode):"))
        self.input_buscar = QLineEdit()
        search_layout.addWidget(self.input_buscar)
        self.btn_buscar = QPushButton("Buscar")
        search_layout.addWidget(self.btn_buscar)
        layout.addLayout(search_layout)

        # Conexiones búsqueda (scanner + botón)
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._buscar_producto)
        self.btn_buscar.clicked.connect(self._buscar_producto)
        self.input_buscar.returnPressed.connect(self._buscar_producto)
        self.input_buscar.textChanged.connect(self._on_text_changed)

        # Tabla carrito
        self.table_cart = QTableWidget()
        self.table_cart.setColumnCount(5)
        self.table_cart.setHorizontalHeaderLabels(["Producto ID", "Código", "Nombre", "Cantidad", "Precio Unit."])
        layout.addWidget(self.table_cart)

        # Agregar manualmente cantidad
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Cantidad a agregar:"))
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 10000)
        self.spin_cant.setValue(1)
        add_layout.addWidget(self.spin_cant)
        self.btn_agregar = QPushButton("➕ Agregar al carrito")
        add_layout.addWidget(self.btn_agregar)
        layout.addLayout(add_layout)
        self.btn_agregar.clicked.connect(self._agregar_al_carrito)

        # Tipo de pago
        pay_layout = QHBoxLayout()
        pay_layout.addWidget(QLabel("Tipo de pago:"))
        self.combo_pago = QComboBox()
        for t in ["Efectivo", "Transferencia", "QR", "Pendiente"]:
            self.combo_pago.addItem(t)
        pay_layout.addWidget(self.combo_pago)

        pay_layout.addWidget(QLabel("Monto recibido (si efectivo):"))
        self.input_recibido = QLineEdit()
        self.input_recibido.setPlaceholderText("0.00")
        pay_layout.addWidget(self.input_recibido)

        layout.addLayout(pay_layout)

        # Totales y botones
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        bottom.addWidget(self.lbl_total)
        self.btn_confirm = QPushButton("✅ Confirmar Venta")
        self.btn_confirm.setShortcut(QKeySequence("F10"))
        bottom.addWidget(self.btn_confirm)
        self.btn_cancel = QPushButton("❌ Cancelar")
        bottom.addWidget(self.btn_cancel)
        layout.addLayout(bottom)

        self.setLayout(layout)

        # Conexiones principales
        self.btn_confirm.clicked.connect(self._confirmar_venta)
        self.btn_cancel.clicked.connect(self.reject)
        self.combo_pago.currentIndexChanged.connect(self._on_pago_change)
        self.input_recibido.textChanged.connect(self._calcular_vuelto)

        self._ultimo_producto = None

        # 🔧 FIX: evitar que Enter dispare botones por defecto
        self.btn_nuevo_cliente.setAutoDefault(False)
        self.btn_buscar.setAutoDefault(False)
        self.btn_agregar.setAutoDefault(False)
        self.btn_confirm.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)

        # Producto preseleccionado (primer escaneo desde ui_main)
        if producto_preseleccionado:
            try:
                pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = producto_preseleccionado
                if int(cantidad) > 0:
                    self._ultimo_producto = {
                        "id": pid, "codigo": codigo, "nombre": nombre,
                        "stock": int(cantidad), "precio": float(precio)
                    }
                    self._agregar_al_carrito(cant_override=1, clear_search=False)
            except Exception:
                pass
        
        QTimer.singleShot(0, self.input_buscar.setFocus)

    # ---------------- Clientes ----------------
    def _cargar_clientes(self):
        self.combo_cliente.clear()
        self.combo_cliente.addItem("(Sin cliente)", None)
        for c in database.obtener_clientes():
            self.combo_cliente.addItem(c[1], c[0])

    def _crear_cliente_rapido(self):
        d = QDialog(self)
        d.setWindowTitle("Crear cliente")
        form = QFormLayout(d)
        inp_nombre = QLineEdit()
        inp_telefono = QLineEdit()
        inp_direccion = QLineEdit()
        inp_notas = QLineEdit()
        form.addRow("Nombre:", inp_nombre)
        form.addRow("Teléfono:", inp_telefono)
        form.addRow("Dirección:", inp_direccion)
        form.addRow("Notas:", inp_notas)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        form.addRow(buttons)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        if d.exec():
            nombre = inp_nombre.text().strip()
            if not nombre:
                QMessageBox.warning(self, "Cliente", "El nombre es obligatorio")
                return
            telefono = inp_telefono.text().strip()
            direccion = inp_direccion.text().strip()
            notas = inp_notas.text().strip()
            cid = database.agregar_cliente(nombre, telefono, direccion, notas)
            self._cargar_clientes()
            idx = self.combo_cliente.findData(cid)
            if idx >= 0:
                self.combo_cliente.setCurrentIndex(idx)

    # ---------------- Scanner / Búsqueda ----------------
    def _on_text_changed(self, texto):
        # Evitar buscar con 1 sola letra; esperar al menos 2 caracteres
        texto = (texto or "").strip()
        if texto and len(texto) >= 2:
            self._scan_timer.start(250)
            
    def _buscar_producto(self):
        q = (self.input_buscar.text() or "").strip()
        if len(q) < 2:
            return

        try:
            encontrados = database.buscar_productos(q, limit=100)
        except Exception as e:
            QMessageBox.critical(self, "Buscar", f"Error al buscar:\n{e}")
            return

        # 0 resultados → flujo de alta rápida (igual que antes)
        if not encontrados:
            QApplication.beep(); QApplication.beep()
            self._alta_rapida_producto(codigo_barras=q)
            prod = database.obtener_producto_por_barcode(q)
            if prod:
                self._ultimo_producto = {
                    "id": prod[0], "codigo": prod[1], "nombre": prod[2],
                    "stock": int(prod[3]), "precio": float(prod[6]) if len(prod) > 6 else 0.0
                }
                self._agregar_al_carrito(cant_override=1, clear_search=True)
            else:
                QMessageBox.information(self, "Alta rápida",
                                        "Producto creado, pero no se pudo recuperar. Vuelva a escanear.")
            self.input_buscar.clear()
            self.input_buscar.setFocus()
            return

        # 1 resultado → agregar directo (match exacto o único resultado)
        if len(encontrados) == 1:
            p = encontrados[0]
            self._ultimo_producto = {
                "id": p[0], "codigo": p[1], "nombre": p[2],
                "stock": int(p[3]), "precio": float(p[6])
            }
            self._agregar_al_carrito(cant_override=1, clear_search=True)
            self.input_buscar.clear()
            self.input_buscar.setFocus()
            return

        # Varios → mostrar selector para que el usuario elija
        elegido = self._mostrar_selector_productos(encontrados)
        if elegido:
            self._ultimo_producto = {
                "id": elegido[0], "codigo": elegido[1], "nombre": elegido[2],
                "stock": int(elegido[3]), "precio": float(elegido[6])
            }
            self._agregar_al_carrito(cant_override=1, clear_search=True)

        self.input_buscar.clear()
        self.input_buscar.setFocus()
    
    def _mostrar_selector_productos(self, filas):
        dlg = QDialog(self)
        dlg.setWindowTitle("Seleccionar producto")
        v = QVBoxLayout(dlg)

        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Stock", "Precio"])
        tabla.setRowCount(len(filas))
        for r, p in enumerate(filas):
            tabla.setItem(r, 0, QTableWidgetItem(str(p[0])))
            tabla.setItem(r, 1, QTableWidgetItem(str(p[1] or "")))
            tabla.setItem(r, 2, QTableWidgetItem(str(p[2] or "")))
            tabla.setItem(r, 3, QTableWidgetItem(str(p[3] or 0)))
            tabla.setItem(r, 4, QTableWidgetItem(str(p[6] or 0.0)))
        tabla.resizeColumnsToContents()
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(tabla)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(botones)
        botones.accepted.connect(dlg.accept)
        botones.rejected.connect(dlg.reject)

        # doble click = aceptar
        tabla.itemDoubleClicked.connect(lambda _item: dlg.accept())

        if dlg.exec() == QDialog.Accepted:
            row = tabla.currentRow()
            if row >= 0:
                return filas[row]
        return None

    # ---------------- Alta rápida ----------------
    def _alta_rapida_producto(self, codigo_barras=""):
        
        
        d = QDialog(self)
        d.setWindowTitle("Alta rápida de producto")
        form = QFormLayout(d)

        # Campos
        inp_codigo = QLineEdit()
        inp_codigo.setText(codigo_barras)
        inp_nombre = QLineEdit()
        inp_cantidad = QSpinBox()
        inp_cantidad.setRange(0, 100000)
        inp_cantidad.setValue(1)
        inp_costo = QLineEdit()

        # Combo de sectores
        sectores = database.obtener_sectores()
        combo_sector = QComboBox()
        for s in sectores:
            combo_sector.addItem(s[1], s[0])

        # Agregar al formulario
        form.addRow("Código (barcode):", inp_codigo)
        form.addRow("Nombre:", inp_nombre)
        form.addRow("Cantidad inicial:", inp_cantidad)
        form.addRow("Costo:", inp_costo)
        form.addRow("Sector:", combo_sector)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        form.addRow(buttons)

        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)

        if d.exec():
            codigo = inp_codigo.text().strip()
            nombre = inp_nombre.text().strip()
            cantidad = int(inp_cantidad.value())

            try:
                costo = float(inp_costo.text()) if inp_costo.text().strip() != "" else 0.0
            except ValueError:
                QMessageBox.warning(self, "Costo inválido", "Por favor ingrese un costo válido.")
                return

            sector_id = combo_sector.currentData() if combo_sector.currentIndex() >= 0 else None

            if not codigo or not nombre:
                QMessageBox.warning(self, "Datos incompletos", "Código y nombre son obligatorios.")
                return

            # Guardar en la base de datos
            try:
                database.agregar_o_actualizar_producto(
                    codigo=codigo,
                    nombre=nombre,
                    cantidad=cantidad,
                    costo=costo,
                    sector_id=sector_id,
                    codigo_barras=codigo
                )
                QMessageBox.information(self, "Producto agregado", f"✅ Producto '{nombre}' agregado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo agregar el producto: {e}")


    # ---------------- Carrito ----------------
    def _agregar_al_carrito(self, cant_override=None, clear_search=False):
        if not self._ultimo_producto:
            QMessageBox.warning(self, "Agregar", "Primero buscá un producto")
            return
        cant = int(self.spin_cant.value()) if cant_override is None else int(cant_override)
        if cant <= 0:
            QMessageBox.warning(self, "Cantidad", "Cantidad inválida")
            return
        if cant > self._ultimo_producto["stock"]:
            QMessageBox.warning(self, "Stock", f"Stock insuficiente ({self._ultimo_producto['stock']})")
            return
        for it in self.cart:
            if it["producto_id"] == self._ultimo_producto["id"]:
                it["cantidad"] += cant
                break
        else:
            self.cart.append({
                "producto_id": self._ultimo_producto["id"],
                "codigo": self._ultimo_producto["codigo"],
                "nombre": self._ultimo_producto["nombre"],
                "cantidad": cant,
                "precio_unitario": self._ultimo_producto.get("precio", 0)
            })
        QApplication.beep()
        self._refrescar_carrito()
        database.guardar_carrito_temporal(self.cart)
        if clear_search:
            self.input_buscar.clear()
            # 👇 no resetear self._ultimo_producto, así se puede usar en próximos escaneos

    def _refrescar_carrito(self):
        self.table_cart.setRowCount(len(self.cart))
        for r, it in enumerate(self.cart):
            self.table_cart.setItem(r, 0, QTableWidgetItem(str(it["producto_id"])))
            self.table_cart.setItem(r, 1, QTableWidgetItem(it["codigo"]))
            self.table_cart.setItem(r, 2, QTableWidgetItem(it["nombre"]))
            self.table_cart.setItem(r, 3, QTableWidgetItem(str(it["cantidad"])))
            self.table_cart.setItem(r, 4, QTableWidgetItem(f"{it['precio_unitario']:.2f}"))
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
        self.lbl_total.setText(f"Total: ${total:,.2f}")
        self._calcular_vuelto()

    # ---------------- Pago ----------------
    def _on_pago_change(self):
        tipo = self.combo_pago.currentText()
        if tipo == "Efectivo":
            self.input_recibido.setEnabled(True)
            self.input_recibido.setFocus()
        else:
            self.input_recibido.setEnabled(False)
            self.input_recibido.clear()
        self._calcular_vuelto()

    def _calcular_vuelto(self):
        try:
            recibido = float(self.input_recibido.text()) if self.input_recibido.text().strip() != "" else None
        except:
            recibido = None
        total = sum(it["cantidad"] * it["precio_unitario"] for it in self.cart)
        if recibido is not None:
            vuelto = recibido - total
            if vuelto < 0:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Falta: ${abs(vuelto):,.2f}")
                self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: red;")
            else:
                self.lbl_total.setText(f"Total: ${total:,.2f} — Vuelto: ${vuelto:,.2f}")
                self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: green;")
        else:
            self.lbl_total.setText(f"Total: ${total:,.2f}")
            self.lbl_total.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")

    def _confirmar_venta(self):
        # 1) Validar que haya ítems en el carrito/tabla
        filas = self.table_cart.rowCount()
        if filas == 0:
            QMessageBox.warning(self, "Carrito vacío", "No hay productos en el carrito.")
            return

        # 2) Construir items desde la tabla de carrito
        items = []
        total = 0.0
        for r in range(filas):
            try:
                pid = int(self.table_cart.item(r, 0).text())
                cant = int(self.table_cart.item(r, 3).text())
                precio = float(str(self.table_cart.item(r, 4).text()).replace(",", "."))
            except Exception:
                QMessageBox.warning(self, "Datos inválidos", "Hay valores no numéricos en el carrito.")
                return
            if cant <= 0:
                QMessageBox.warning(self, "Cantidad inválida", "Las cantidades deben ser mayores a cero.")
                return
            items.append({"producto_id": pid, "cantidad": cant, "precio_unitario": precio})
            total += cant * precio

        # 3) Tipo de pago y validaciones específicas
        tipo_pago = self.combo_pago.currentText()
        recibido = None
        vuelto = None

        if tipo_pago == "Efectivo":
            # Parsear aceptando coma o punto
            try:
                recibido = float((self.input_recibido.text() or "0").replace(",", "."))
            except ValueError:
                QMessageBox.warning(self, "Pago en efectivo", "Monto recibido inválido.")
                return
            if recibido < total:
                QMessageBox.warning(self, "Pago en efectivo", "El monto recibido es menor que el total.")
                return
            vuelto = round(recibido - total, 2)
        elif tipo_pago in ("Transferencia", "QR", "Pendiente"):
            recibido = None
            vuelto = None
        else:
            QMessageBox.warning(self, "Tipo de pago", "Seleccioná un tipo de pago válido.")
            return

        # 4) Cliente (puede ser None)
        cliente_id = self.combo_cliente.currentData()

        # 5) Confirmación final
        resumen = f"Total: ${total:.2f}\nPago: {tipo_pago}"
        if tipo_pago == "Efectivo":
            resumen += f"\nRecibido: ${recibido:.2f}\nVuelto: ${vuelto:.2f}"
        if cliente_id:
            cliente_nombre = self.combo_cliente.currentText()
            resumen += f"\nCliente: {cliente_nombre}"

        if QMessageBox.question(self, "Confirmar venta", f"{resumen}\n\n¿Registrar la venta?") != QMessageBox.Yes:
            return

        # 6) Registrar venta en la base
        try:
            ok, info = database.registrar_venta(
                items=items,
                tipo_pago=tipo_pago,
                cliente=cliente_id,
                efectivo_recibido=recibido if tipo_pago == "Efectivo" else None
            )
            if not ok:
                raise Exception(info)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta:\n{e}")
            return

        # 7) Limpieza de UI, marcar flag y limpiar carrito temporal
        self.cart.clear()
        self.table_cart.setRowCount(0)
        self.lbl_total.setText("Total: $0.00")
        self.input_recibido.clear()

        # >>> clave: marcar venta confirmada y limpiar temporal
        self._venta_confirmada = True
        try:
            database.limpiar_carrito_temporal()
        except Exception:
            pass

        QMessageBox.information(self, "Venta", "✅ Venta registrada correctamente.")
        self.accept()

        

    def obtener_carrito(self):
        return self.cart

    def _buscar_si_completo(self, texto: str):
        texto = texto.strip()
        if len(texto) >= 6:
            self._buscar_producto()
    
    def agregar_producto_externo(self, prod):
        """
        Permite que MainWindow agregue un producto al carrito cuando ya hay un POS abierto.
        'prod' es la tupla del producto que viene de database.obtener_productos().
        """
        try:
            pid, codigo, nombre, cantidad, costo, sector, precio, codigo_barras, movs = prod
            if int(cantidad) <= 0:
                QMessageBox.warning(self, "Stock", f"Stock insuficiente para {nombre}")
                return

            self._ultimo_producto = {
                "id": pid,
                "codigo": codigo,
                "nombre": nombre,
                "stock": int(cantidad),
                "precio": float(precio)
            }
            # Agregamos al carrito directamente (1 unidad)
            self._agregar_al_carrito(cant_override=1, clear_search=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar producto externo:\n{e}")
    
    def _intentar_recuperar_carrito(self):
        if self._recupero_carrito_este_sesion:
            return
        try:
            data = database.obtener_carrito_temporal()
        except Exception:
            data = []

        if not data:
            return

        resp = QMessageBox.question(
            self, "Carrito anterior encontrado",
            "Se encontró un carrito sin confirmar.\n¿Querés recuperarlo?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            # Cargar el carrito guardado
            self.cart = []
            for (row) in data:
                # data ya viene como dicts desde database.obtener_carrito_temporal()
                self.cart.append({
                    "producto_id": row["producto_id"],
                    "codigo": row["codigo"] or "",
                    "nombre": row["nombre"] or "",
                    "cantidad": int(row["cantidad"] or 0),
                    "precio_unitario": float(row["precio_unitario"] or 0.0),
                })
            self._refrescar_carrito()
            self._recupero_carrito_este_sesion = True
        else:
            # Si NO quiere recuperar, limpiamos el temporal para que no vuelva a preguntar
            try:
                database.limpiar_carrito_temporal()
            except Exception:
                pass
    
    def closeEvent(self, event):
        try:
            if not getattr(self, "_venta_confirmada", False):
                # Guardar carrito temporal si hay items
                items = []
                for it in self.cart:
                    items.append({
                        "producto_id": it["producto_id"],
                        "codigo": it["codigo"],
                        "nombre": it["nombre"],
                        "cantidad": it["cantidad"],
                        "precio_unitario": it["precio_unitario"],
                    })
                if items:
                    database.guardar_carrito_temporal(items)
                else:
                    database.limpiar_carrito_temporal()
            else:
                # Si hubo venta, aseguramos limpiar
                database.limpiar_carrito_temporal()
        except Exception:
            pass
        super().closeEvent(event)

