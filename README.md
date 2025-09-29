# Epica Almacén — Gestor de Stock (Fase 2)

<!-- Badges -->
![Estado CI](https://github.com/gasparswidzinski/app-Epika-almacen/actions/workflows/ci.yml/badge.svg)
![Último commit](https://img.shields.io/github/last-commit/gasparswidzinski/app-Epika-almacen)
![Issues](https://img.shields.io/github/issues/gasparswidzinski/app-Epika-almacen)
![PRs](https://img.shields.io/github/issues-pr/gasparswidzinski/app-Epika-almacen)
![Tamaño del repo](https://img.shields.io/github/repo-size/gasparswidzinski/app-Epika-almacen)
![Licencia](https://img.shields.io/github/license/gasparswidzinski/app-Epika-almacen)
![Estrellas](https://img.shields.io/github/stars/gasparswidzinski/app-Epika-almacen?style=social)

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Plataformas](https://img.shields.io/badge/Plataformas-Windows%20%7C%20Linux-informational)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)


Sistema de **gestión de stock y ventas para almacenes** (chicos/medianos), con **login y roles**, **punto de venta (POS)** con lector de códigos, **importación/exportación a Excel**, **historial de movimientos**, **clientes**, **gastos**, y **backup automático**. Interfaz de escritorio hecha en **Python + PySide6 (Qt)** y persistencia en **SQLite**.

> Proyecto educativo y de uso real. Ideal para kioscos/almacenes que necesitan un control simple, rápido y local.

---

##  Funcionalidades clave

- **Login con roles (admin/user/developer)** y gestión de usuarios desde la UI.  
- **Panel principal** con búsqueda rápida, filtro de **bajo stock** y **historial de movimientos** en tiempo real.  
- **ABM de productos** (código interno y **código de barras**), sectores con **márgenes** y **precio** autocalculado.  
- **POS (ventas)** con carrito, **tipos de pago** (Efectivo/Transferencia/QR/Pendiente), clientes, y cálculo de **vuelto**.  
- **Importar / Exportar** stock a **Excel/CSV** (mapeo flexible de columnas y formateo de planilla al exportar).  
- **Reportes de ventas** y **listado de bajo stock** desde la barra superior.  
- **Clientes**: alta/edición rápida desde POS y módulo dedicado.  
- **Gastos**: categorías para almacén/personal (estructura lista para panel financiero).  
- **Scanner** de códigos (teclado/USB): flujo optimizado para alta/venta en pocos pasos.  
- **Backups diarios automáticos** del archivo SQLite en carpeta de datos de la app.  

---


##  Arquitectura (módulos principales)

- `main.py` — punto de arranque; inicializa DB, **login**, crea **backup automático** del día y abre la `MainWindow`.
- `ui_main.py` — **ventana principal** (toolbar, tabla de productos, historial, import/export, reportes, scanner, backup).
- `ui_formulario.py` — **alta/edición** de productos (código interno, nombre, cantidad, costo, **sector**, **código de barras**).
- `ui_vender.py` — **POS**: búsqueda/escaneo, carrito, cliente, método de pago, cálculo de totales/vuelto.
- `ui_login.py` — diálogo de **inicio de sesión** (estilizado) con verificación contra DB.
- `ui_usuarios.py` — **gestión de usuarios** (crear/editar/borrar con rol).
- `database.py` — **capa de datos**: creación/migración de tablas, CRUD de productos/ventas/clientes/usuarios, movimientos, utilidades.

---

##  Estructura sugerida del repo

```
app-Epika-almacen/
├─ main.py
├─ database.py
├─ ui_main.py
├─ ui_login.py
├─ ui_formulario.py
├─ ui_vender.py
├─ ui_usuarios.py
├─ requerimientos.txt
├─ docs/
│  └─ img/ (capturas para el README)
└─ .github/
   └─ workflows/
      └─ ci.yml
```

---

##  Requisitos

- **Python** 3.10 o superior (Windows o Linux).
- Dependencias en `requerimientos.txt` (PySide6, pandas, openpyxl, pyinstaller, PyQt5/pyqt5-tools, matplotlib, reportlab, requests).

> Instalación rápida:
```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Linux
# source .venv/bin/activate

pip install -r requerimientos.txt
```

---

##  Configuración y primer arranque

1. **Clonar** el repo y crear el **entorno virtual**.
2. Instalar dependencias.
3. Ejecutar:
   ```bash
   python main.py
   ```
4. **Usuarios iniciales**: se crean `admin/admin` y `developer/developer`. En el **primer inicio como admin**, la app **obliga a crear** un **usuario administrador propio** antes de continuar (flujo guiado).  
5. Se crea/usa una **DB SQLite** en la **carpeta de datos del sistema** (ver sección _Datos & Backups_).

---

##  Uso rápido

- **Buscar** por código/nombre/barcode.
- **F1**: agregar producto. **F2**: abrir POS. **F3**: editar. **Del**: eliminar.
- **POS** (ventas): buscá/escaneá, ajustá **cantidades**, elegí **tipo de pago** y **confirmá** la venta.
- **Importar** Excel/CSV (mapeo de columnas flexible). **Exportar** stock con formato de tabla.
- **Historial**: ver últimos movimientos etiquetados (Ingreso/Venta/Editar/Eliminar/Reembolso).

---

##  Datos & Backups

- La **DB** (SQLite) se guarda en una **carpeta de datos persistente del sistema** (Windows: `ProgramData\GestorDeStock`).  
- En cada inicio se realiza un **backup automático** diario en `.../backups/almacen_YYYY-MM-DD.db`.  
- Para **backup manual**, basta con **cerrar la app** y copiar el `.db`.

> Si migrás desde instalaciones viejas, la app intenta **migrar** tu `almacen.db` automáticamente a la nueva ruta segura.

---

##  Importar /  Exportar

- **Exportar**: genera `stock_exportado.xlsx` con **formato** (encabezados, bordes, autoancho).  
- **Importar**: admite **Excel/CSV**; reconoce alias típicos (`codigo`, `sku`, `nombre`, `stock`, `costo`, `sector`, `codigo_barras`).  
- Crea sectores faltantes **on the fly** con margen por defecto (**30%**) y recalcula **precio**.  
- Hace **upsert** por **código de barras** (si existe) o por **código interno**. Muestra conteo de **insertados/actualizados/errores**.

---

##  Seguridad de acceso

- Usuarios con **roles** (`admin`, `user`, `developer`).  
- Contraseñas almacenadas con **hash**.  
- UI para **crear/editar/eliminar** usuarios (protecciones básicas, ejemplo: no borrar `admin`).

> Para uso productivo, se recomienda endurecer políticas (logs de auditoría, complejidad de claves, bloqueo por intentos, etc.).

---

##  Modelo de datos (resumen)

- `sectores(id, nombre, margen)`  
- `productos(id, codigo, nombre, cantidad, costo, sector_id, precio, codigo_barras, movimientos)` + índice **único** en `codigo_barras` **no nulo**  
- `movimientos(id, producto_id, tipo, cambio, precio_unitario, fecha, detalles)`  
- `ventas(id, fecha, tipo_pago, estado, total, efectivo_recibido, vuelto, cliente, cliente_id)`  
- `venta_items(id, venta_id, producto_id, cantidad, precio_unitario, subtotal)`  
- `clientes(id, nombre, telefono, direccion, notas)`  
- `gastos(id, fecha, categoria, monto, detalle, tipo)` y `categorias_gasto(...)`  
- `carrito_temporal(...)` (para recuperar carrito en POS si se cerró).  
- `usuarios(id, usuario, password_hash, rol)`

---

## ⌨ Atajos útiles

- **F1** agregar producto  
- **F2** abrir POS  
- **F3** editar producto  
- **Del** eliminar producto  

---


---

##  Empaquetado (PyInstaller, opcional)

Para generar un ejecutable local:

```bash
pyinstaller --noconfirm --onefile --name "EpikaAlmacen" main.py
```

> Podés sumar un `.spec` y recursos (iconos) para dejarlo profesional.

---

##  Contribuciones

- Abrí un **Issue** con mejoras/bugs y, si podés, un **PR**.  
- Para cambios grandes, explicá el caso de uso y sumá capturas/GIF.

---

##  Licencia

MIT

---

##  Créditos

**Gaspar Swidzinski** — Diseño, desarrollo y pruebas con datos reales.
