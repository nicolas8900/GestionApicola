import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import tempfile
from datetime import datetime
import json
import textwrap
from fpdf import FPDF


def init_db():
    conn = sqlite3.connect("gestion_apicola.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT,
        cuit_dni TEXT, telefono TEXT, provincia TEXT, localidad TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT,
        cuit_dni TEXT, telefono TEXT, provincia TEXT, localidad TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_nombre TEXT,
        fecha TEXT, total REAL, detalle TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT, proveedor_nombre TEXT,
        fecha TEXT, total REAL, detalle TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock (
        nombre TEXT PRIMARY KEY, cantidad REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_nombre TEXT,
        fecha TEXT, monto REAL, observaciones TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS presupuestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_info TEXT,
        fecha TEXT, total REAL, detalle TEXT)''')

    try:
        cursor.execute("ALTER TABLE ventas ADD COLUMN con_iva INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_db_connection():
    return sqlite3.connect("gestion_apicola.db")


class AppApicola:
    def __init__(self, root):
        self.root = root
        self.root.title("Software de Gestión Apícola v11.0")
        self.root.geometry("1200x850")

        self.cliente_actual_info = "Consumidor Final"
        self.proveedor_actual_info = "Proveedor Genérico"
        self.id_clie_edit = None
        self.id_prov_edit = None

        self.lista_materiales = [
            "Alzas Standard 1ª cal", "Alzas Standard 2ª cal", "Alzas Standard 3ª cal",
            "Alzas de 3/4' 1ª cal", "Alzas de 3/4' 2ª cal", "Alzas de 3/4' 3ª cal",
            "Alzas de 1/2' 1ª cal", "Alzas de 1/2' 2ª cal", "Alzas de 1/2' 3ª cal",
            "Marcos Standard 1ª cal", "Marcos Standard 2ª cal", "Marcos de 3/4' 1ª cal",
            "Marcos de 1/2' 1ª cal", "Pisos 1ª cal", "Pisos 2ª cal", "Pisos 3ª cal",
            "Techos Standard 1ª cal", "Techos Standard 2ª cal", "Techos Standard 3ª cal",
            "Techos americanos 1ª cal", "Techos americanos 2ª cal", "Techos americanos 3ª cal",
            "Núcleros de 4 marcos", "Núcleros de 5 marcos", "Alimentadores de marco"
        ]

        init_db()
        os.makedirs("pdf", exist_ok=True)
        os.makedirs("presupuestos", exist_ok=True)

        with get_db_connection() as conn:
            c = conn.cursor()
            for mat in self.lista_materiales:
                c.execute("INSERT OR IGNORE INTO stock (nombre, cantidad) VALUES (?, ?)", (mat, 0.0))
            conn.commit()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both")

        self.tab_clie = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_clie, text="Clientes")

        self.tab_prov = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_prov, text="Proveedores")

        self.tab_vent = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_vent, text="Ventas")

        self.tab_comp = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_comp, text="Compras")

        self.tab_hven = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_hven, text="Historial Ventas")

        self.tab_hcom = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_hcom, text="Historial Compras")

        self.tab_bal = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bal, text="Balance")

        self.tab_stk = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stk, text="Stock de materiales")

        self.tab_cc = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cc, text="Cuenta Corriente")

        self.tab_deud = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_deud, text="Deudores")

        self.tab_pres = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pres, text="Presupuestos")

        self.setup_entidad(self.tab_clie, "Cliente", "clientes", self.guardar_cliente, self.modificar_cliente, self.eliminar_cliente, self.limpiar_clie)
        self.setup_entidad(self.tab_prov, "Proveedor", "proveedores", self.guardar_proveedor, self.modificar_proveedor, self.eliminar_proveedor, self.limpiar_prov)

        self.setup_ventas()
        self.setup_compras()
        self.setup_historiales()
        self.setup_balance()
        self.setup_stock()
        self.setup_cuenta_corriente()
        self.setup_deudores()
        self.setup_presupuestos()
        self.actualizar_tablas()

    def formato_moneda(self, valor):
        try:
            return "{:,.2f}".format(float(valor)).replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "0,00"

    def abrir_archivo(self, path):
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                if sys.platform == "darwin":
                    subprocess.run(['open', path], check=False)
                else:
                    subprocess.run(['xdg-open', path], check=False)
        except Exception as e:
            print(f"Error al abrir archivo {path}: {e}")

    def setup_entidad(self, tab, nombre_entidad, tabla_db, cmd_guardar, cmd_modificar, cmd_eliminar, cmd_limpiar):
        f_busq = ttk.LabelFrame(tab, text=f"Buscar {nombre_entidad}")
        f_busq.pack(padx=10, pady=5, fill="x")

        ent_busq = ttk.Entry(f_busq)
        ent_busq.pack(padx=10, pady=5, fill="x")
        ent_busq.bind("<KeyRelease>", lambda e: self.actualizar_tablas())

        if tabla_db == "clientes":
            self.ent_busq_clie = ent_busq
            self.ent_clie = {}
            ent_dict = self.ent_clie
        else:
            self.ent_busq_prov = ent_busq
            self.ent_prov = {}
            ent_dict = self.ent_prov

        cols = ["ID", "Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]
        display_cols = ["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]

        f_form = ttk.LabelFrame(tab, text=f"Datos del {nombre_entidad}")
        f_form.pack(padx=10, pady=5, fill="x")

        for i, col in enumerate(cols[1:]):
            ttk.Label(f_form, text=col).grid(row=i // 3, column=(i % 3) * 2, padx=5, pady=5)
            ent_dict[col] = ttk.Entry(f_form)
            ent_dict[col].grid(row=i // 3, column=(i % 3) * 2 + 1, padx=5, pady=5)

        btn_f = ttk.Frame(tab)
        btn_f.pack(pady=5)

        btn_guardar = ttk.Button(btn_f, text="Guardar", command=cmd_guardar)
        btn_guardar.pack(side="left", padx=5)

        ttk.Button(btn_f, text="Modificar", command=cmd_modificar).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Eliminar", command=cmd_eliminar).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Limpiar", command=cmd_limpiar).pack(side="left", padx=5)

        tree = ttk.Treeview(tab, columns=cols, displaycolumns=display_cols, show='headings', height=8)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        if tabla_db == "clientes":
            self.btn_guardar_clie = btn_guardar
            self.tree_clie = tree
            self.tree_clie.bind("<Double-1>", self.cargar_clie)
        else:
            self.btn_guardar_prov = btn_guardar
            self.tree_prov = tree
            self.tree_prov.bind("<Double-1>", self.cargar_prov)

    # --- CLIENTES ---
    def guardar_cliente(self):
        d = [self.ent_clie[c].get().strip() for c in ["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]]
        cuit_dni = d[2]

        with get_db_connection() as conn:
            c = conn.cursor()
            if cuit_dni:
                c.execute("SELECT id FROM clientes WHERE cuit_dni = ?", (cuit_dni,))
                if c.fetchone():
                    return messagebox.showwarning("Error", "Ya existe un cliente con ese CUIT/DNI.")
            c.execute("INSERT INTO clientes (nombre, apellido, cuit_dni, telefono, provincia, localidad) VALUES (?,?,?,?,?,?)", d)
            conn.commit()
        messagebox.showinfo("Éxito", "Cliente guardado")
        self.limpiar_clie()

    def modificar_cliente(self):
        if self.id_clie_edit is None:
            return
        d = [self.ent_clie[c].get().strip() for c in ["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]]
        cuit_dni = d[2]

        with get_db_connection() as conn:
            c = conn.cursor()
            if cuit_dni:
                c.execute("SELECT id FROM clientes WHERE cuit_dni = ? AND id != ?", (cuit_dni, self.id_clie_edit[0]))
                if c.fetchone():
                    return messagebox.showwarning("Error", "Ya existe otro cliente con ese CUIT/DNI.")
            c.execute("UPDATE clientes SET nombre=?, apellido=?, cuit_dni=?, telefono=?, provincia=?, localidad=? WHERE id=?", (*d, self.id_clie_edit[0]))
            conn.commit()
        messagebox.showinfo("Éxito", "Cliente modificado")
        self.limpiar_clie()

    def cargar_clie(self, event):
        sel = self.tree_clie.selection()
        if not sel:
            return
        v = self.tree_clie.item(sel)['values']
        self.id_clie_edit = v
        self.btn_guardar_clie.config(state="disabled")
        for i, col in enumerate(["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]):
            self.ent_clie[col].delete(0, tk.END)
            self.ent_clie[col].insert(0, v[i + 1])

    def eliminar_cliente(self):
        sel = self.tree_clie.selection()
        if sel and messagebox.askyesno("Confirmar", "¿Desea eliminar este registro?"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM clientes WHERE id=?", (self.tree_clie.item(sel)['values'][0],))
                conn.commit()
            self.actualizar_tablas()
            self.limpiar_clie()

    def limpiar_clie(self):
        for e in self.ent_clie.values():
            e.delete(0, tk.END)
        self.ent_busq_clie.delete(0, tk.END)
        self.id_clie_edit = None
        self.btn_guardar_clie.config(state="normal")
        self.actualizar_tablas()

    # --- PROVEEDORES ---
    def guardar_proveedor(self):
        d = [self.ent_prov[c].get().strip() for c in ["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]]
        cuit_dni = d[2]

        with get_db_connection() as conn:
            c = conn.cursor()
            if cuit_dni:
                c.execute("SELECT id FROM proveedores WHERE cuit_dni = ?", (cuit_dni,))
                if c.fetchone():
                    return messagebox.showwarning("Error", "Ya existe un proveedor con ese CUIT/DNI.")
            c.execute("INSERT INTO proveedores (nombre, apellido, cuit_dni, telefono, provincia, localidad) VALUES (?,?,?,?,?,?)", d)
            conn.commit()
        messagebox.showinfo("Éxito", "Proveedor guardado")
        self.limpiar_prov()

    def modificar_proveedor(self):
        if self.id_prov_edit is None:
            return
        d = [self.ent_prov[c].get().strip() for c in ["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]]
        cuit_dni = d[2]

        with get_db_connection() as conn:
            c = conn.cursor()
            if cuit_dni:
                c.execute("SELECT id FROM proveedores WHERE cuit_dni = ? AND id != ?", (cuit_dni, self.id_prov_edit[0]))
                if c.fetchone():
                    return messagebox.showwarning("Error", "Ya existe otro proveedor con ese CUIT/DNI.")
            c.execute("UPDATE proveedores SET nombre=?, apellido=?, cuit_dni=?, telefono=?, provincia=?, localidad=? WHERE id=?", (*d, self.id_prov_edit[0]))
            conn.commit()
        messagebox.showinfo("Éxito", "Proveedor modificado")
        self.limpiar_prov()

    def cargar_prov(self, event):
        sel = self.tree_prov.selection()
        if not sel:
            return
        v = self.tree_prov.item(sel)['values']
        self.id_prov_edit = v
        self.btn_guardar_prov.config(state="disabled")
        for i, col in enumerate(["Nombre", "Apellido", "CUIT/DNI", "Teléfono", "Provincia", "Localidad"]):
            self.ent_prov[col].delete(0, tk.END)
            self.ent_prov[col].insert(0, v[i + 1])

    def eliminar_proveedor(self):
        sel = self.tree_prov.selection()
        if sel and messagebox.askyesno("Confirmar", "¿Desea eliminar este registro?"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM proveedores WHERE id=?", (self.tree_prov.item(sel)['values'][0],))
                conn.commit()
            self.actualizar_tablas()
            self.limpiar_prov()

    def limpiar_prov(self):
        for e in self.ent_prov.values():
            e.delete(0, tk.END)
        self.ent_busq_prov.delete(0, tk.END)
        self.id_prov_edit = None
        self.btn_guardar_prov.config(state="normal")
        self.actualizar_tablas()

    # --- STOCK ---
    def setup_stock(self):
        f_stk = ttk.LabelFrame(self.tab_stk, text="Inventario de Materiales")
        f_stk.pack(fill="both", expand=True, padx=10, pady=10)

        self.stk_canvas = tk.Canvas(f_stk)
        self.stk_scrollbar = ttk.Scrollbar(f_stk, orient="vertical", command=self.stk_canvas.yview)
        self.stk_scroll_f = ttk.Frame(self.stk_canvas)

        self.stk_canvas.create_window((0, 0), window=self.stk_scroll_f, anchor="nw")
        self.stk_canvas.configure(yscrollcommand=self.stk_scrollbar.set)
        self.stk_canvas.pack(side="left", fill="both", expand=True)
        self.stk_scrollbar.pack(side="right", fill="y")

        self.stk_scroll_f.bind("<Configure>", lambda e: self.stk_canvas.configure(scrollregion=self.stk_canvas.bbox("all")))

        def _on_wheel_s(event):
            self.stk_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.stk_canvas.bind("<Enter>", lambda e: self.stk_canvas.bind_all("<MouseWheel>", _on_wheel_s))
        self.stk_canvas.bind("<Leave>", lambda e: self.stk_canvas.unbind_all("<MouseWheel>"))

        ttk.Label(self.stk_scroll_f, text="Material", width=40, font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(self.stk_scroll_f, text="Cantidad", width=15, font=("Helvetica", 10, "bold")).grid(row=0, column=1, padx=10, pady=5)

        self.stk_inputs = {}
        for i, mat in enumerate(self.lista_materiales):
            ttk.Label(self.stk_scroll_f, text=mat, width=40).grid(row=i + 1, column=0, padx=10, pady=2, sticky="w")
            ent = ttk.Entry(self.stk_scroll_f, width=15, justify="center")
            ent.grid(row=i + 1, column=1, padx=10, pady=2)
            self.stk_inputs[mat] = ent

        ttk.Button(self.tab_stk, text="MODIFICAR STOCK", command=self.modificar_stock).pack(pady=10)
        self.actualizar_ui_stock()

    def modificar_stock(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            for mat, ent in self.stk_inputs.items():
                val = ent.get().strip()
                if val:
                    try:
                        cant = float(val)
                        c.execute("UPDATE stock SET cantidad = ? WHERE nombre = ?", (cant, mat))
                    except ValueError:
                        pass
            conn.commit()
        messagebox.showinfo("Éxito", "Stock actualizado.")
        self.actualizar_ui_stock()

    def actualizar_ui_stock(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT nombre, cantidad FROM stock")
            for nombre, cantidad in c.fetchall():
                if nombre in self.stk_inputs:
                    self.stk_inputs[nombre].delete(0, tk.END)
                    cant_str = f"{cantidad:.0f}" if cantidad.is_integer() else str(cantidad)
                    self.stk_inputs[nombre].insert(0, cant_str)

    # --- VENTAS ---
    def setup_ventas(self):
        f_clie = ttk.LabelFrame(self.tab_vent, text="1. Seleccionar Cliente")
        f_clie.pack(fill="x", padx=10, pady=5)

        self.v_ent_busq = ttk.Entry(f_clie)
        self.v_ent_busq.pack(fill="x", padx=5, pady=5)
        self.v_ent_busq.bind("<KeyRelease>", lambda e: self.actualizar_tablas())

        self.v_list_clie = tk.Listbox(f_clie, height=4)
        self.v_list_clie.pack(fill="x", padx=5, pady=2)
        self.v_list_clie.bind("<<ListboxSelect>>", self.seleccionar_cliente_venta)

        f_body = ttk.Frame(self.tab_vent)
        f_body.pack(fill="both", expand=True, padx=10, pady=5)

        f_btns = ttk.Frame(f_body)
        f_btns.pack(side="right", fill="y", padx=(15, 5), pady=10)

        ttk.Button(f_btns, text="REGISTRAR VENTA SIN IVA", command=lambda: self.finalizar_venta(con_iva=False, orden_carga=False)).pack(fill="x", pady=8, ipady=8)
        ttk.Button(f_btns, text="REGISTRAR VENTA CON IVA", command=lambda: self.finalizar_venta(con_iva=True, orden_carga=False)).pack(fill="x", pady=8, ipady=8)
        ttk.Button(f_btns, text="REGISTRAR VENTA SIN IVA\n+ ORDEN DE CARGA", command=lambda: self.finalizar_venta(con_iva=False, orden_carga=True)).pack(fill="x", pady=8, ipady=8)
        ttk.Button(f_btns, text="REGISTRAR VENTA CON IVA\n+ ORDEN DE CARGA", command=lambda: self.finalizar_venta(con_iva=True, orden_carga=True)).pack(fill="x", pady=8, ipady=8)
        ttk.Button(f_btns, text="LIMPIAR FORMULARIO", command=self.limpiar_formulario_venta).pack(fill="x", pady=(25, 5), ipady=5)

        f_mat = ttk.LabelFrame(f_body, text="2. Carga de Productos")
        f_mat.pack(side="left", fill="both", expand=True, padx=(0, 5))

        f_head = ttk.Frame(f_mat)
        f_head.pack(fill="x")

        for t, width in [("Cantidad", 10), ("Descripción", 40), ("Precio unitario ($)", 16)]:
            ttk.Label(f_head, text=t, width=width, anchor="center", justify="center").pack(side="left", padx=10)

        self.v_canvas = tk.Canvas(f_mat)
        self.v_scrollbar = ttk.Scrollbar(f_mat, orient="vertical", command=self.v_canvas.yview)
        self.v_scroll_f = ttk.Frame(self.v_canvas)

        self.v_canvas.create_window((0, 0), window=self.v_scroll_f, anchor="nw")
        self.v_canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.v_canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

        self.v_scroll_f.bind("<Configure>", lambda e: self.v_canvas.configure(scrollregion=self.v_canvas.bbox("all")))

        def _on_wheel_v(event):
            self.v_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.v_canvas.bind("<Enter>", lambda e: self.v_canvas.bind_all("<MouseWheel>", _on_wheel_v))
        self.v_canvas.bind("<Leave>", lambda e: self.v_canvas.unbind_all("<MouseWheel>"))

        self.inputs_materiales = []
        for mat in self.lista_materiales:
            self.crear_renglon_vta(mat)
        for _ in range(5):
            self.crear_renglon_vta(None)

    def crear_renglon_vta(self, mat):
        f = ttk.Frame(self.v_scroll_f)
        f.pack(fill="x", pady=1)

        ent_cant = ttk.Entry(f, width=10, justify="center")
        ent_cant.pack(side="left", padx=10)

        if mat:
            ttk.Label(f, text=mat, width=40).pack(side="left", padx=10)
            p_info = mat
        else:
            ent_nom = ttk.Entry(f, width=40, justify="center")
            ent_nom.pack(side="left", padx=10)
            p_info = ent_nom

        ent_prec = ttk.Entry(f, width=15, justify="center")
        ent_prec.pack(side="left", padx=10)

        self.inputs_materiales.append({"prod": p_info, "cant": ent_cant, "prec": ent_prec, "es_extra": mat is None})

    def seleccionar_cliente_venta(self, event):
        sel = self.v_list_clie.curselection()
        if sel:
            self.cliente_actual_info = self.v_list_clie.get(sel)

    def finalizar_venta(self, con_iva=False, orden_carga=False):
        if self.cliente_actual_info == "Consumidor Final" and not self.v_list_clie.curselection():
            if not messagebox.askyesno("Sin cliente seleccionado", "¿Desea guardar la venta como Consumidor Final?"):
                return

        total = 0
        detalle = []
        for item in self.inputs_materiales:
            try:
                c_str = item["cant"].get()
                p_str = item["prec"].get()
                if not c_str or not p_str:
                    continue
                c = float(c_str)
                p = float(p_str)
                if con_iva:
                    p = p * 1.21
                if c > 0:
                    nombre = item["prod"] if not item["es_extra"] else item["prod"].get().strip()
                    if not nombre:
                        continue
                    sub = c * p
                    total += sub
                    detalle.append({"nombre": nombre, "cant": c, "prec": p, "sub": sub, "es_extra": item["es_extra"]})
            except ValueError:
                continue

        if total <= 0:
            return messagebox.showwarning("Error", "Ingrese productos válidos")

        if orden_carga:
            with get_db_connection() as conn:
                c = conn.cursor()
                for p in detalle:
                    if not p["es_extra"]:
                        c.execute("SELECT cantidad FROM stock WHERE nombre = ?", (p["nombre"],))
                        res = c.fetchone()
                        if not res or res[0] < p["cant"]:
                            return messagebox.showwarning("Error de Stock", f"No hay stock suficiente para: {p['nombre']}")

        fecha = datetime.now().strftime("%d-%m-%Y")
        with get_db_connection() as conn:
            c = conn.cursor()
            if orden_carga:
                for p in detalle:
                    if not p["es_extra"]:
                        c.execute("UPDATE stock SET cantidad = cantidad - ? WHERE nombre = ?", (p["cant"], p["nombre"]))
            c.execute("INSERT INTO ventas (cliente_nombre, fecha, total, detalle, con_iva) VALUES (?,?,?,?,?)",
                      (self.cliente_actual_info, fecha, total, json.dumps(detalle), 1 if con_iva else 0))
            conn.commit()
        conn.close()

        self.actualizar_ui_stock()

        pdf_vta, pdf_oc = None, None
        try:
            pdf_vta = self.generar_ticket_pdf(self.cliente_actual_info, fecha, total, detalle, "Cliente", "clientes", con_iva)
            if orden_carga:
                pdf_oc = self.generar_orden_carga(self.cliente_actual_info, fecha, detalle, "clientes")
        except Exception as e:
            messagebox.showerror("Error PDF", f"No se pudieron guardar los archivos PDF.\nError: {e}")

        msg = "Venta registrada correctamente.\n"
        if pdf_vta:
            msg += f"Ticket: {os.path.basename(pdf_vta)}\n"
        if pdf_oc:
            msg += f"Orden: {os.path.basename(pdf_oc)}\n"
        messagebox.showinfo("Éxito", msg)

        if pdf_vta:
            self.abrir_archivo(pdf_vta)
        if pdf_oc:
            self.abrir_archivo(pdf_oc)
        self.limpiar_formulario_venta()
        self.actualizar_tablas()

    def generar_orden_carga(self, persona_info, fecha, productos, tabla_db, preview=False):
        nombre_f = persona_info.split(" (")[0].split(" - CUIT/DNI: ")[0]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT telefono, localidad, provincia FROM {tabla_db} WHERE nombre || ' ' || apellido = ?", (nombre_f,))
            res = c.fetchone()
            tel, loc, prov = (res[0], res[1], res[2]) if res else ("", "", "")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, f"Fecha: {fecha}", ln=True)
        pdf.cell(0, 5, f"Cliente: {nombre_f}", ln=True)
        if loc:
            pdf.cell(0, 5, f"Ubicación: {loc}, {prov}", ln=True)
        if tel:
            pdf.cell(0, 5, f"Teléfono: {tel}", ln=True)
        pdf.ln(5)
        pdf.cell(140, 7, "Producto", border=1, align='C')
        pdf.cell(40, 7, "Cantidad", border=1, align='C', ln=True)
        pdf.set_font("Arial", 'B', 10)
        for p in productos:
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(140, 6, p['nombre'], border=1)
            new_y = pdf.get_y()
            pdf.set_xy(x + 140, y)
            pdf.cell(40, new_y - y, f"{p['cant']:.0f}", border=1, align='R', ln=True)

        if preview:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name
            pdf.output(pdf_path)
            return pdf_path

        nombre_archivo = nombre_f.replace(" ", "_").replace("/", "-")
        pdf_path = os.path.join(os.getcwd(), "pdf", f"OrdenCarga_{nombre_archivo}_{fecha.replace('/', '-')}_{datetime.now().strftime('%H%M%S')}.pdf")
        pdf.output(pdf_path)
        return pdf_path

    # --- PESTAÑA COMPRAS ---
    def setup_compras(self):
        f_prov = ttk.LabelFrame(self.tab_comp, text="1. Seleccionar Proveedor")
        f_prov.pack(fill="x", padx=10, pady=5)
        self.c_ent_busq = ttk.Entry(f_prov)
        self.c_ent_busq.pack(fill="x", padx=5, pady=5)
        self.c_ent_busq.bind("<KeyRelease>", lambda e: self.actualizar_tablas())
        self.c_list_prov = tk.Listbox(f_prov, height=4)
        self.c_list_prov.pack(fill="x", padx=5, pady=2)
        self.c_list_prov.bind("<<ListboxSelect>>", self.seleccionar_prov_compra)
        f_mat = ttk.LabelFrame(self.tab_comp, text="2. Carga Manual de Productos")
        f_mat.pack(fill="both", expand=True, padx=10, pady=5)
        f_head = ttk.Frame(f_mat)
        f_head.pack(fill="x")
        for t, width in [("Cantidad", 10), ("Descripción", 40), ("Precio unitario ($)", 16)]:
            ttk.Label(f_head, text=t, width=width, anchor="center", justify="center").pack(side="left", padx=10)
        self.c_canvas = tk.Canvas(f_mat)
        self.c_scrollbar = ttk.Scrollbar(f_mat, orient="vertical", command=self.c_canvas.yview)
        self.c_scroll_f = ttk.Frame(self.c_canvas)
        self.c_canvas.create_window((0, 0), window=self.c_scroll_f, anchor="nw")
        self.c_canvas.configure(yscrollcommand=self.c_scrollbar.set)
        self.c_canvas.pack(side="left", fill="both", expand=True)
        self.c_scrollbar.pack(side="right", fill="y")
        self.c_scroll_f.bind("<Configure>", lambda e: self.c_canvas.configure(scrollregion=self.c_canvas.bbox("all")))

        def _on_wheel_c(event):
            self.c_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.c_canvas.bind("<Enter>", lambda e: self.c_canvas.bind_all("<MouseWheel>", _on_wheel_c))
        self.c_canvas.bind("<Leave>", lambda e: self.c_canvas.unbind_all("<MouseWheel>"))
        self.inputs_compras = []
        for _ in range(20):
            f = ttk.Frame(self.c_scroll_f)
            f.pack(fill="x", pady=1)
            ent_cant = ttk.Entry(f, width=10, justify="center")
            ent_cant.pack(side="left", padx=10)
            ent_nom = ttk.Entry(f, width=40, justify="center")
            ent_nom.pack(side="left", padx=10)
            ent_prec = ttk.Entry(f, width=15, justify="center")
            ent_prec.pack(side="left", padx=10)
            self.inputs_compras.append({"prod": ent_nom, "cant": ent_cant, "prec": ent_prec})
        ttk.Button(self.tab_comp, text="REGISTRAR COMPRA", command=self.finalizar_compra).pack(fill="x", padx=10, pady=5)

    def seleccionar_prov_compra(self, event):
        sel = self.c_list_prov.curselection()
        if sel:
            self.proveedor_actual_info = self.c_list_prov.get(sel)

    def finalizar_compra(self):
        total, detalle = 0, []
        for item in self.inputs_compras:
            try:
                c, p = float(item["cant"].get()), float(item["prec"].get())
                n = item["prod"].get().strip()
                if not n or c <= 0:
                    continue
                sub = c * p
                total += sub
                detalle.append({"nombre": n, "cant": c, "prec": p, "sub": sub})
            except ValueError:
                continue
        if total <= 0:
            return messagebox.showwarning("Error", "Cargue productos válidos")
        fecha = datetime.now().strftime("%d-%m-%Y")
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO compras (proveedor_nombre, fecha, total, detalle) VALUES (?,?,?,?)", (self.proveedor_actual_info, fecha, total, json.dumps(detalle)))
            conn.commit()

        pdf_path = None
        try:
            pdf_path = self.generar_ticket_pdf(self.proveedor_actual_info, fecha, total, detalle, "Proveedor", "proveedores")
        except Exception as e:
            messagebox.showerror("Error PDF", str(e))

        msg = "Compra registrada.\n"
        if pdf_path:
            msg += f"Archivo: {os.path.basename(pdf_path)}\n"
        messagebox.showinfo("Éxito", msg)

        if pdf_path:
            self.abrir_archivo(pdf_path)

        self.limpiar_formulario_compra()
        self.actualizar_tablas()

    def generar_ticket_pdf(self, persona_info, fecha, total, productos, etiqueta, tabla_db, con_iva=False, preview=False):
        nombre_f = persona_info.split(" (")[0].split(" - CUIT/DNI: ")[0]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT telefono, localidad, provincia FROM {tabla_db} WHERE nombre || ' ' || apellido = ?", (nombre_f,))
            res = c.fetchone()
            tel, loc, prov = (res[0], res[1], res[2]) if res else ("", "", "")
        conn.close()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, f"Fecha: {fecha}", ln=True)
        pdf.cell(0, 5, f"{etiqueta}: {nombre_f}", ln=True)
        if loc:
            pdf.cell(0, 5, f"Ubicación: {loc}, {prov}", ln=True)
        if tel:
            pdf.cell(0, 5, f"Teléfono: {tel}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 7, "Producto", border=1, align='C')
        pdf.cell(20, 7, "Cant", border=1, align='C')
        pdf.cell(30, 7, "P.Unit ($)", border=1, align='C')
        pdf.cell(40, 7, "Subtotal ($)", border=1, align='C', ln=True)
        pdf.set_font("Arial", 'B', 10)
        for p in productos:
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(100, 6, p['nombre'], border=1)
            h = pdf.get_y() - y
            pdf.set_xy(x + 100, y)
            pdf.cell(20, h, f"{p['cant']:.0f}", border=1, align='R')
            pdf.cell(30, h, self.formato_moneda(p['prec']), border=1, align='R')
            pdf.cell(40, h, self.formato_moneda(p['sub']), border=1, align='R', ln=True)
        pdf.ln(5)
        lbl_total = "TOTAL ($):" if etiqueta.lower() == "proveedor" else ("TOTAL CON IVA (21%) ($):" if con_iva else "TOTAL SIN IVA ($):")
        pdf.cell(150, 7, lbl_total, border=0, align='R')
        pdf.cell(40, 7, self.formato_moneda(total), border=1, align='R', ln=True)
        if preview:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name
            pdf.output(pdf_path)
            return pdf_path
        nombre_archivo = nombre_f.replace(" ", "_").replace("/", "-")
        pdf_path = os.path.join(os.getcwd(), "pdf", f"{nombre_archivo}_{fecha.replace('/', '-')}_{datetime.now().strftime('%H%M%S')}.pdf")
        pdf.output(pdf_path)
        return pdf_path

    def setup_historiales(self):
        for tab, ent_attr, tree_attr, cmd_ver, cmd_elim in [
            (self.tab_hven, "ent_busq_hven", "tree_hven", self.ver_ticket_hven, self.eliminar_venta_h),
            (self.tab_hcom, "ent_busq_hcom", "tree_hcom", self.ver_ticket_hcom, self.eliminar_compra_h)
        ]:
            f_busq = ttk.Frame(tab)
            f_busq.pack(fill="x", padx=10, pady=5)
            ttk.Label(f_busq, text="Buscar:").pack(side="left")
            ent = ttk.Entry(f_busq)
            ent.pack(side="left", fill="x", expand=True, padx=5)
            ent.bind("<KeyRelease>", lambda e: self.actualizar_tablas())
            setattr(self, ent_attr, ent)
            ttk.Button(f_busq, text="VER PDF", command=cmd_ver).pack(side="left", padx=5)
            ttk.Button(f_busq, text="ELIMINAR", command=cmd_elim).pack(side="left", padx=5)
            cols = ("ID", "Nombre", "Apellido", "Provincia", "Localidad", "CUIT/DNI", "Fecha")
            tree = ttk.Treeview(tab, columns=cols, show='headings')
            for c in cols:
                tree.heading(c, text=c)
                tree.column(c, width=100, anchor="center")
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            tree.bind("<Double-1>", lambda e, cmd=cmd_ver: cmd())
            setattr(self, tree_attr, tree)

    def eliminar_venta_h(self):
        sel = self.tree_hven.selection()
        if not sel:
            return messagebox.showwarning("Error", "Seleccione una venta")
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este registro de venta?"):
            v_id = self.tree_hven.item(sel)['values'][0]
            with get_db_connection() as conn:
                conn.cursor().execute("DELETE FROM ventas WHERE id=?", (v_id,))
                conn.commit()
            self.actualizar_tablas()

    def eliminar_compra_h(self):
        sel = self.tree_hcom.selection()
        if not sel:
            return messagebox.showwarning("Error", "Seleccione una compra")
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este registro de compra?"):
            c_id = self.tree_hcom.item(sel)['values'][0]
            with get_db_connection() as conn:
                conn.cursor().execute("DELETE FROM compras WHERE id=?", (c_id,))
                conn.commit()
            self.actualizar_tablas()

    def ver_ticket_hven(self):
        sel = self.tree_hven.selection()
        if not sel:
            return
        v_id = self.tree_hven.item(sel)['values'][0]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT cliente_nombre, fecha, total, detalle, con_iva FROM ventas WHERE id=?", (v_id,))
            r = c.fetchone()
        if r:
            self.abrir_archivo(self.generar_ticket_pdf(r[0], r[1], r[2], json.loads(r[3]), "Cliente", "clientes", bool(r[4]), preview=True))

    def ver_ticket_hcom(self):
        sel = self.tree_hcom.selection()
        if not sel:
            return
        c_id = self.tree_hcom.item(sel)['values'][0]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT proveedor_nombre, fecha, total, detalle FROM compras WHERE id=?", (c_id,))
            r = c.fetchone()
        if r:
            self.abrir_archivo(self.generar_ticket_pdf(r[0], r[1], r[2], json.loads(r[3]), "Proveedor", "proveedores", preview=True))

    def setup_balance(self):
        f_bal = ttk.Frame(self.tab_bal)
        f_bal.pack(fill="both", expand=True, padx=10, pady=10)
        f_gen = ttk.LabelFrame(f_bal, text="Balances Generales")
        f_gen.pack(fill="x", pady=5)
        anios = [str(a) for a in range(datetime.now().year, 2020, -1)]
        meses = [f"{i:02d}" for i in range(1, 13)]
        for lbl, t in [("Ventas Periodo:", "ventas"), ("Compras Periodo:", "compras")]:
            f = ttk.Frame(f_gen)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=lbl, width=15).pack(side="left", padx=5)
            m = ttk.Combobox(f, values=meses, width=5)
            m.pack(side="left", padx=2)
            a = ttk.Combobox(f, values=anios, width=7)
            a.pack(side="left", padx=2)
            a.set(anios[0])
            ttk.Button(f, text="Mensual", command=lambda t=t, m=m, a=a: self.gen_bal(t, f"{m.get()}-{a.get()}")).pack(side="left", padx=5)
            ttk.Button(f, text="Anual", command=lambda t=t, a=a: self.gen_bal(t, a.get())).pack(side="left", padx=5)
        f_ent = ttk.LabelFrame(f_bal, text="Balances por Entidad")
        f_ent.pack(fill="x", pady=10)
        for lbl, lst_attr, ent_attr, anio_attr, cmd_todo, cmd_anio in [("Cliente:", "bal_list_clie", "bal_ent_clie", "bal_anio_clie", self.gen_bal_cliente, self.gen_bal_cliente_anio), ("Proveedor:", "bal_list_prov", "bal_ent_prov", "bal_anio_prov", self.gen_bal_proveedor, self.gen_bal_proveedor_anio)]:
            f = ttk.Frame(f_ent)
            f.pack(fill="x", pady=5, padx=10)
            ttk.Label(f, text=f"Buscar {lbl}", width=18).pack(side="left")
            e = ttk.Entry(f, width=25)
            e.pack(side="left", padx=5)
            e.bind("<KeyRelease>", lambda ev: self.actualizar_tablas())
            setattr(self, ent_attr, e)
            l = tk.Listbox(f, height=6)
            l.pack(side="left", fill="x", expand=True, padx=5)
            setattr(self, lst_attr, l)
            fb = ttk.Frame(f)
            fb.pack(side="left", padx=5)
            ttk.Button(fb, text="Todo", width=10, command=cmd_todo).pack(pady=2)
            fa = ttk.Frame(fb)
            fa.pack(pady=2)
            c = ttk.Combobox(fa, values=anios, width=6, state="readonly")
            c.pack(side="left")
            c.set(anios[0])
            setattr(self, anio_attr, c)
            ttk.Button(fa, text="Año", width=5, command=cmd_anio).pack(side="left", padx=2)

    def gen_bal_cliente(self):
        self._gen_bal_e("ventas", "cliente_nombre", self.bal_list_clie, "Cliente")

    def gen_bal_cliente_anio(self):
        self._gen_bal_e("ventas", "cliente_nombre", self.bal_list_clie, "Cliente", self.bal_anio_clie.get())

    def gen_bal_proveedor(self):
        self._gen_bal_e("compras", "proveedor_nombre", self.bal_list_prov, "Proveedor")

    def gen_bal_proveedor_anio(self):
        self._gen_bal_e("compras", "proveedor_nombre", self.bal_list_prov, "Proveedor", self.bal_anio_prov.get())

    def _gen_bal_e(self, tabla, col, lst, tag, anio=None):
        sel = lst.curselection()
        if not sel:
            return messagebox.showwarning("Aviso", "Seleccione una entidad")
        info = lst.get(sel)
        with get_db_connection() as conn:
            c = conn.cursor()
            if anio:
                c.execute(f"SELECT total, detalle FROM {tabla} WHERE {col} = ? AND fecha LIKE ?", (info, f"%{anio}"))
            else:
                c.execute(f"SELECT total, detalle FROM {tabla} WHERE {col} = ?", (info,))
            res = c.fetchall()
        if not res:
            return messagebox.showinfo("Aviso", "Sin datos")
        tot, acc = 0, {}
        for r in res:
            tot += r[0]
            for p in json.loads(r[1]):
                n = p['nombre'].upper()
                acc[n] = acc.get(n, {'cant': 0, 'sub': 0})
                acc[n]['cant'] += p['cant']
                acc[n]['sub'] += p['sub']
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, f"BALANCE - {tag.upper()}", ln=True, align='C')
        pdf.cell(0, 5, f"Entidad: {info}", ln=True)
        if anio:
            pdf.cell(0, 5, f"Año: {anio}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 7, "Producto", border=1, align='C')
        pdf.cell(20, 7, "Cant", border=1, align='C')
        pdf.cell(30, 7, "P.Unit ($)", border=1, align='C')
        pdf.cell(40, 7, "Subtotal ($)", border=1, align='C', ln=True)
        for k, v in acc.items():
            p_p = v['sub'] / v['cant'] if v['cant'] > 0 else 0
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(100, 6, k, border=1)
            h = pdf.get_y() - y
            pdf.set_xy(x + 100, y)
            pdf.cell(20, h, f"{v['cant']:.0f}", border=1, align='R')
            pdf.cell(30, h, self.formato_moneda(p_p), border=1, align='R')
            pdf.cell(40, h, self.formato_moneda(v['sub']), border=1, align='R', ln=True)
        pdf.ln(5)
        pdf.cell(150, 7, "TOTAL ($):", align='R')
        pdf.cell(40, 7, self.formato_moneda(tot), border=1, align='R', ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            t_path = tmp.name
        pdf.output(t_path)
        self.abrir_archivo(t_path)

    def gen_bal(self, tabla, filtro):
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT total, detalle FROM {tabla} WHERE fecha LIKE ?", (f"%{filtro}%",))
            res = c.fetchall()
        if not res:
            return messagebox.showinfo("Aviso", "Sin datos")
        tot, acc = 0, {}
        for r in res:
            tot += r[0]
            for p in json.loads(r[1]):
                n = p['nombre'].upper()
                acc[n] = acc.get(n, {'cant': 0, 'sub': 0})
                acc[n]['cant'] += p['cant']
                acc[n]['sub'] += p['sub']
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, f"BALANCE {tabla.upper()}", ln=True, align='C')
        pdf.cell(0, 5, f"Periodo: {filtro}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 7, "Producto", border=1, align='C')
        pdf.cell(20, 7, "Cant", border=1, align='C')
        pdf.cell(30, 7, "P.Prom ($)", border=1, align='C')
        pdf.cell(40, 7, "Subtotal ($)", border=1, align='C', ln=True)
        for k, v in acc.items():
            p_p = v['sub'] / v['cant'] if v['cant'] > 0 else 0
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(100, 6, k, border=1)
            h = pdf.get_y() - y
            pdf.set_xy(x + 100, y)
            pdf.cell(20, h, f"{v['cant']:.0f}", border=1, align='R')
            pdf.cell(30, h, self.formato_moneda(p_p), border=1, align='R')
            pdf.cell(40, h, self.formato_moneda(v['sub']), border=1, align='R', ln=True)
        pdf.ln(5)
        pdf.cell(150, 7, "TOTAL ($):", align='R')
        pdf.cell(40, 7, self.formato_moneda(tot), border=1, align='R', ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            t_path = tmp.name
        pdf.output(t_path)
        self.abrir_archivo(t_path)

    def setup_cuenta_corriente(self):
        f_clie = ttk.LabelFrame(self.tab_cc, text="1. Seleccionar Cliente")
        f_clie.pack(fill="x", padx=10, pady=5)
        self.cc_ent_busq = ttk.Entry(f_clie)
        self.cc_ent_busq.pack(fill="x", padx=5, pady=5)
        self.cc_ent_busq.bind("<KeyRelease>", lambda e: self.actualizar_tablas())
        self.cc_list_clie = tk.Listbox(f_clie, height=4)
        self.cc_list_clie.pack(fill="x", padx=5, pady=2)
        self.cc_list_clie.bind("<<ListboxSelect>>", self.seleccionar_cliente_cc)
        f_movs = ttk.LabelFrame(self.tab_cc, text="2. Historial de Movimientos")
        f_movs.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ("ID", "Fecha", "Tipo", "Detalle", "Debe", "Haber", "Saldo")
        self.tree_cc = ttk.Treeview(f_movs, columns=cols, show='headings', displaycolumns=("Fecha", "Tipo", "Detalle", "Debe", "Haber", "Saldo"))
        for c in cols:
            self.tree_cc.heading(c, text=c)
            self.tree_cc.column(c, width=100, anchor="center")
        self.tree_cc.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_cc.bind("<Double-1>", self.ver_ticket_desde_cc)
        f_pago = ttk.LabelFrame(self.tab_cc, text="3. Registrar Pago")
        f_pago.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_pago, text="Fecha:").grid(row=0, column=0, padx=5, pady=5)
        self.ent_cc_fecha = ttk.Entry(f_pago)
        self.ent_cc_fecha.grid(row=0, column=1, padx=5, pady=5)
        self.ent_cc_fecha.insert(0, datetime.now().strftime("%d-%m-%Y"))
        ttk.Label(f_pago, text="Monto ($):").grid(row=0, column=2, padx=5, pady=5)
        self.ent_cc_monto = ttk.Entry(f_pago)
        self.ent_cc_monto.grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(f_pago, text="Obs:").grid(row=0, column=4, padx=5, pady=5)
        self.ent_cc_obs = ttk.Entry(f_pago)
        self.ent_cc_obs.grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(f_pago, text="REGISTRAR PAGO", command=self.registrar_pago).grid(row=0, column=6, padx=10, pady=5)
        ttk.Button(f_pago, text="ELIMINAR PAGO", command=self.eliminar_pago).grid(row=0, column=7, padx=10, pady=5)

    def seleccionar_cliente_cc(self, event):
        sel = self.cc_list_clie.curselection()
        if sel:
            self.cliente_cc_info = self.cc_list_clie.get(sel)
            self.cargar_historial_cc()

    def registrar_pago(self):
        if not hasattr(self, 'cliente_cc_info'):
            return messagebox.showwarning("Error", "Seleccione un cliente")
        try:
            monto = float(self.ent_cc_monto.get().strip())
        except ValueError:
            return messagebox.showwarning("Error", "Monto inválido")
        with get_db_connection() as conn:
            conn.cursor().execute("INSERT INTO pagos (cliente_nombre, fecha, monto, observaciones) VALUES (?,?,?,?)",
                                  (self.cliente_cc_info, self.ent_cc_fecha.get().strip(), monto, self.ent_cc_obs.get().strip()))
            conn.commit()
        messagebox.showinfo("Éxito", "Pago registrado")
        self.ent_cc_monto.delete(0, tk.END)
        self.ent_cc_obs.delete(0, tk.END)
        self.cargar_historial_cc()
        self.actualizar_tablas()

    def eliminar_pago(self):
        sel = self.tree_cc.selection()
        if not sel or self.tree_cc.item(sel)['values'][2] != "Pago":
            return messagebox.showwarning("Error", "Seleccione un Pago")
        if messagebox.askyesno("Confirmar", "¿Eliminar pago?"):
            with get_db_connection() as conn:
                conn.cursor().execute("DELETE FROM pagos WHERE id=?", (self.tree_cc.item(sel)['values'][0],))
                conn.commit()
            self.cargar_historial_cc()
            self.actualizar_tablas()

    def ver_ticket_desde_cc(self, event):
        sel = self.tree_cc.selection()
        if not sel or self.tree_cc.item(sel)['values'][2] != "Venta":
            return
        with get_db_connection() as conn:
            r = conn.cursor().execute("SELECT cliente_nombre, fecha, total, detalle, con_iva FROM ventas WHERE id=?",
                                      (self.tree_cc.item(sel)['values'][0],)).fetchone()
        if r:
            self.abrir_archivo(self.generar_ticket_pdf(r[0], r[1], r[2], json.loads(r[3]), "Cliente", "clientes", bool(r[4]), preview=True))

    def cargar_historial_cc(self):
        for i in self.tree_cc.get_children():
            self.tree_cc.delete(i)
        if not hasattr(self, 'cliente_cc_info'):
            return
        movs = []
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, fecha, total FROM ventas WHERE cliente_nombre = ?", (self.cliente_cc_info,))
            for vid, f, t in c.fetchall():
                movs.append({'id': vid, 'fecha': f, 'tipo': 'Venta', 'detalle': 'Venta ticket', 'debe': t, 'haber': 0})
            c.execute("SELECT id, fecha, monto, observaciones FROM pagos WHERE cliente_nombre = ?", (self.cliente_cc_info,))
            for pid, f, m, o in c.fetchall():
                movs.append({'id': pid, 'fecha': f, 'tipo': 'Pago', 'detalle': o, 'debe': 0, 'haber': m})
        try:
            movs.sort(key=lambda x: datetime.strptime(x['fecha'], "%d-%m-%Y"))
        except:
            pass
        saldo = 0
        for m in movs:
            saldo += m['debe'] - m['haber']
            self.tree_cc.insert("", "end", values=(m['id'], m['fecha'], m['tipo'], m['detalle'], self.formato_moneda(m['debe']), self.formato_moneda(m['haber']), self.formato_moneda(saldo)))

    def setup_deudores(self):
        f = ttk.LabelFrame(self.tab_deud, text="Deudores")
        f.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("Nombre", "CUIT/DNI", "Teléfono", "Provincia", "Localidad", "Saldo")
        self.tree_deudores = ttk.Treeview(f, columns=cols, show='headings')
        for c in cols:
            self.tree_deudores.heading(c, text=c)
            self.tree_deudores.column(c, width=120, anchor="center")
        self.tree_deudores.pack(fill="both", expand=True, padx=5, pady=5)
        bf = ttk.Frame(self.tab_deud)
        bf.pack(pady=10)
        ttk.Button(bf, text="PDF DEUDORES", command=self.generar_pdf_deudores).pack(side="left", padx=5)
        ttk.Button(bf, text="ABRIR CARPETA", command=lambda: self.abrir_archivo(os.getcwd())).pack(side="left", padx=5)

    def actualizar_deudores(self):
        for i in self.tree_deudores.get_children():
            self.tree_deudores.delete(i)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT nombre, apellido, cuit_dni, telefono, provincia, localidad FROM clientes")
            for nom, ape, cuit, tel, prov, loc in c.fetchall():
                info = f"{nom} {ape}" + (f" - CUIT/DNI: {cuit}" if cuit else "") + f" ({prov} - {loc})"
                v = conn.execute("SELECT SUM(total) FROM ventas WHERE cliente_nombre = ?", (info,)).fetchone()[0] or 0
                p = conn.execute("SELECT SUM(monto) FROM pagos WHERE cliente_nombre = ?", (info,)).fetchone()[0] or 0
                if v - p > 0.01:
                    self.tree_deudores.insert("", "end", values=(f"{nom} {ape}", cuit, tel, prov, loc, self.formato_moneda(v - p)))
            v_cf = conn.execute("SELECT SUM(total) FROM ventas WHERE cliente_nombre = 'Consumidor Final'").fetchone()[0] or 0
            p_cf = conn.execute("SELECT SUM(monto) FROM pagos WHERE cliente_nombre = 'Consumidor Final'").fetchone()[0] or 0
            if v_cf - p_cf > 0.01:
                self.tree_deudores.insert("", "end", values=("Consumidor Final", "-", "-", "-", "-", self.formato_moneda(v_cf - p_cf)))

    def generar_pdf_deudores(self):
        items = [self.tree_deudores.item(i)['values'] for i in self.tree_deudores.get_children()]
        if not items:
            return messagebox.showinfo("Aviso", "No hay deudores")
        pdf = FPDF(orientation='L')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, "LISTADO DE DEUDORES", ln=True, align='C')
        pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align='R')
        pdf.ln(5)
        cols = ["Nombre", "CUIT/DNI", "Teléfono", "Provincia", "Localidad", "Saldo"]
        ws = [60, 40, 40, 40, 40, 40]
        for i, col in enumerate(cols):
            pdf.cell(ws[i], 10, col, border=1, align='C')
        pdf.ln()
        td = 0
        for item in items:
            for i, val in enumerate(item):
                pdf.cell(ws[i], 10, str(val).encode('latin-1', 'replace').decode('latin-1'), border=1, align='C')
            pdf.ln()
            td += float(str(item[5]).replace(".", "").replace(",", "."))
        pdf.ln(5)
        pdf.cell(150, 7, "DEUDA TOTAL ($):", align='R')
        pdf.cell(40, 7, self.formato_moneda(td), border=1, align='R', ln=True)
        path = os.path.join(os.getcwd(), "pdf", f"Deudores_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        pdf.output(path)
        self.abrir_archivo(path)

    def setup_presupuestos(self):
        pw = ttk.PanedWindow(self.tab_pres, orient="vertical")
        pw.pack(fill="both", expand=True)
        f_n = ttk.Frame(pw)
        f_h = ttk.Frame(pw)
        pw.add(f_n, weight=3)
        pw.add(f_h, weight=2)
        f_t = ttk.Frame(f_n)
        f_t.pack(fill="x", padx=10, pady=5)
        f_c = ttk.LabelFrame(f_t, text="1. Cliente")
        f_c.pack(side="left", fill="both", expand=True, padx=5)
        self.p_ent_busq = ttk.Entry(f_c)
        self.p_ent_busq.pack(fill="x", padx=5, pady=5)
        self.p_ent_busq.bind("<KeyRelease>", lambda e: self.actualizar_tablas())
        self.p_list_clie = tk.Listbox(f_c, height=4)
        self.p_list_clie.pack(fill="x", padx=5, pady=2)
        self.p_list_clie.bind("<<ListboxSelect>>", self.seleccionar_cliente_presupuesto)
        f_ex = ttk.LabelFrame(f_t, text="2. Datos Manuales")
        f_ex.pack(side="left", fill="both", expand=True, padx=5)
        self.p_txt_clie = tk.Text(f_ex, height=4, width=30)
        self.p_txt_clie.pack(fill="both", expand=True, padx=5, pady=5)
        f_f = ttk.LabelFrame(f_t, text="3. Fecha")
        f_f.pack(side="left", fill="y", padx=5)
        self.p_ent_fecha = ttk.Entry(f_f, width=12)
        self.p_ent_fecha.pack(padx=10, pady=10)
        self.p_ent_fecha.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.p_ent_fecha.bind("<KeyRelease>", self.validar_fecha_presupuesto)
        f_b = ttk.Frame(f_n)
        f_b.pack(fill="both", expand=True, padx=10, pady=5)
        f_bt = ttk.Frame(f_b)
        f_bt.pack(side="right", fill="y", padx=(15, 5), pady=5)
        f_m = ttk.LabelFrame(f_b, text="4. Productos")
        f_m.pack(side="left", fill="both", expand=True, padx=(0, 5))
        f_hd = ttk.Frame(f_m)
        f_hd.pack(fill="x")
        for t, w in [("Cantidad", 10), ("Descripción", 40), ("Precio ($)", 16)]:
            ttk.Label(f_hd, text=t, width=w, anchor="center").pack(side="left", padx=10)
        self.p_canvas = tk.Canvas(f_m)
        self.p_scrollbar = ttk.Scrollbar(f_m, command=self.p_canvas.yview)
        self.p_scroll_f = ttk.Frame(self.p_canvas)
        self.p_canvas.create_window((0, 0), window=self.p_scroll_f, anchor="nw")
        self.p_canvas.configure(yscrollcommand=self.p_scrollbar.set)
        self.p_canvas.pack(side="left", fill="both", expand=True)
        self.p_scrollbar.pack(side="right", fill="y")
        self.p_scroll_f.bind("<Configure>", lambda e: self.p_canvas.configure(scrollregion=self.p_canvas.bbox("all")))

        def _on_wheel_p(event):
            self.p_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.p_canvas.bind("<Enter>", lambda e: self.p_canvas.bind_all("<MouseWheel>", _on_wheel_p))
        self.p_canvas.bind("<Leave>", lambda e: self.p_canvas.unbind_all("<MouseWheel>"))

        self.inputs_presupuesto = []
        for mat in self.lista_materiales + [None] * 5:
            f = ttk.Frame(self.p_scroll_f)
            f.pack(fill="x", pady=1)
            c = ttk.Entry(f, width=10, justify="center")
            c.pack(side="left", padx=10)
            c.bind("<KeyRelease>", lambda e: self.actualizar_total_presupuesto())
            if mat:
                ttk.Label(f, text=mat, width=40).pack(side="left", padx=10)
                p_info = mat
            else:
                p_info = ttk.Entry(f, width=40, justify="center")
                p_info.pack(side="left", padx=10)
            p = ttk.Entry(f, width=15, justify="center")
            p.pack(side="left", padx=10)
            p.bind("<KeyRelease>", lambda e: self.actualizar_total_presupuesto())
            self.inputs_presupuesto.append({"prod": p_info, "cant": c, "prec": p, "es_extra": mat is None})
        f_iva = ttk.Frame(f_bt)
        f_iva.pack(fill="x", pady=5)
        self.p_var_iva = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_iva, text="IVA", variable=self.p_var_iva, command=self.actualizar_total_presupuesto).pack(side="left", padx=2)
        self.p_ent_iva_porc = ttk.Entry(f_iva, width=5)
        self.p_ent_iva_porc.pack(side="left", padx=2)
        self.p_ent_iva_porc.insert(0, "21")
        self.p_ent_iva_porc.bind("<KeyRelease>", lambda e: self.actualizar_total_presupuesto())
        self.lbl_p_total = ttk.Label(f_bt, text="TOTAL: $ 0,00", font=("Helvetica", 14, "bold"), foreground="green")
        self.lbl_p_total.pack(pady=8)
        ttk.Button(f_bt, text="GENERAR", command=self.finalizar_presupuesto).pack(fill="x", pady=4, ipady=6)
        ttk.Button(f_bt, text="LIMPIAR", command=self.limpiar_formulario_presupuesto).pack(fill="x", pady=4, ipady=6)
        f_hist = ttk.LabelFrame(f_h, text="Historial")
        f_hist.pack(fill="both", expand=True, padx=10, pady=5)
        f_bh = ttk.Frame(f_hist)
        f_bh.pack(fill="x", padx=5, pady=2)
        self.p_ent_busq_h = ttk.Entry(f_bh)
        self.p_ent_busq_h.pack(side="left", fill="x", expand=True)
        self.p_ent_busq_h.bind("<KeyRelease>", lambda e: self.actualizar_tablas())
        bfh = ttk.Frame(f_hist)
        bfh.pack(pady=5)
        ttk.Button(bfh, text="VER PDF", command=self.reimprimir_presupuesto).pack(side="left", padx=5)
        ttk.Button(bfh, text="ELIMINAR", command=self.eliminar_presupuesto).pack(side="left", padx=5)
        self.tree_hpres = ttk.Treeview(f_hist, columns=("ID", "Cliente", "Fecha", "Total"), show='headings')
        for c in ("ID", "Cliente", "Fecha", "Total"):
            self.tree_hpres.heading(c, text=c)
            self.tree_hpres.column(c, width=150, anchor="center")
        self.tree_hpres.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_hpres.bind("<Double-1>", lambda e: self.reimprimir_presupuesto())

    def validar_fecha_presupuesto(self, event):
        s = ''.join(c for c in self.p_ent_fecha.get().replace("-", "") if c.isdigit())[:8]
        if len(s) >= 4:
            s = f"{s[:2]}-{s[2:4]}-{s[4:]}"
        elif len(s) >= 2:
            s = f"{s[:2]}-{s[2:]}"
        self.p_ent_fecha.delete(0, tk.END)
        self.p_ent_fecha.insert(0, s)

    def actualizar_total_presupuesto(self):
        t, i_en = 0, self.p_var_iva.get()
        try:
            i_p = float(self.p_ent_iva_porc.get()) / 100
        except:
            i_p = 0.21
        for it in self.inputs_presupuesto:
            try:
                c, p = float(it["cant"].get()), float(it["prec"].get())
                if c > 0 and p > 0:
                    sub = c * p
                    t += sub + (sub * i_p if i_en else 0)
            except ValueError:
                continue
        self.lbl_p_total.config(text=f"TOTAL: $ {self.formato_moneda(t)}")

    def seleccionar_cliente_presupuesto(self, event):
        sel = self.p_list_clie.curselection()
        if sel:
            self.cliente_presupuesto_info = self.p_list_clie.get(sel)

    def finalizar_presupuesto(self):
        t_s, det, i_en = 0, [], self.p_var_iva.get()
        try:
            i_p = float(self.p_ent_iva_porc.get())
        except:
            i_p = 21.0
        for it in self.inputs_presupuesto:
            try:
                c, p = float(it["cant"].get()), float(it["prec"].get())
                n = it["prod"] if not it["es_extra"] else it["prod"].get().strip()
                if c > 0 and n:
                    sub = c * p
                    t_s += sub
                    det.append({"nombre": n, "cant": c, "prec": p, "sub": sub})
            except ValueError:
                continue
        if t_s <= 0:
            return messagebox.showwarning("Error", "Ingrese productos")
        t_f = t_s + (t_s * i_p / 100 if i_en else 0)
        cli = f"{getattr(self, 'cliente_presupuesto_info', '')}\n{self.p_txt_clie.get('1.0', tk.END).strip()}".strip()
        if not cli:
            return messagebox.showwarning("Error", "Ingrese cliente")
        with get_db_connection() as conn:
            conn.cursor().execute("INSERT INTO presupuestos (cliente_info, fecha, total, detalle) VALUES (?,?,?,?)",
                                  (cli, self.p_ent_fecha.get().strip(), t_f, json.dumps({"detalle": det, "iva_habilitado": i_en, "porc_iva": i_p, "total_sin_iva": t_s})))
            conn.commit()

        fecha = self.p_ent_fecha.get().strip()
        pdf_path = None
        try:
            pdf_path = self.generar_presupuesto_pdf(cli, fecha, t_f, det, i_en, i_p, t_s)
        except Exception as e:
            messagebox.showerror("Error PDF", str(e))

        msg = "Presupuesto registrado.\n"
        if pdf_path:
            msg += f"Archivo: {os.path.basename(pdf_path)}\n"
        messagebox.showinfo("Éxito", msg)

        if pdf_path:
            self.abrir_archivo(pdf_path)

        self.limpiar_formulario_presupuesto()
        self.actualizar_tablas()

    def limpiar_formulario_presupuesto(self):
        for w in [self.p_ent_busq, self.p_ent_fecha]:
            w.delete(0, tk.END)
        self.p_list_clie.delete(0, tk.END)
        self.p_txt_clie.delete("1.0", tk.END)
        self.p_ent_fecha.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.p_var_iva.set(True)
        self.p_ent_iva_porc.delete(0, tk.END)
        self.p_ent_iva_porc.insert(0, "21")
        self.lbl_p_total.config(text="TOTAL: $ 0,00")
        if hasattr(self, 'cliente_presupuesto_info'):
            del self.cliente_presupuesto_info
        for it in self.inputs_presupuesto:
            it["cant"].delete(0, tk.END)
            it["prec"].delete(0, tk.END)
            if it["es_extra"]:
                it["prod"].delete(0, tk.END)

    def reimprimir_presupuesto(self):
        sel = self.tree_hpres.selection()
        if not sel:
            return
        with get_db_connection() as conn:
            r = conn.cursor().execute("SELECT cliente_info, fecha, total, detalle FROM presupuestos WHERE id=?", (self.tree_hpres.item(sel)['values'][0],)).fetchone()
        if r:
            try:
                d = json.loads(r[3])
                if isinstance(d, dict) and "detalle" in d:
                    path = self.generar_presupuesto_pdf(r[0], r[1], r[2], d["detalle"], d.get("iva_habilitado", False), d.get("porc_iva", 21), d.get("total_sin_iva", r[2]), preview=True)
                else:
                    path = self.generar_presupuesto_pdf(r[0], r[1], r[2], d, preview=True)
                self.abrir_archivo(path)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def eliminar_presupuesto(self):
        sel = self.tree_hpres.selection()
        if sel and messagebox.askyesno("Confirmar", "¿Eliminar?"):
            with get_db_connection() as conn:
                conn.cursor().execute("DELETE FROM presupuestos WHERE id=?", (self.tree_hpres.item(sel)['values'][0],))
                conn.commit()
            self.actualizar_tablas()

    def generar_presupuesto_pdf(self, cli, fecha, total, prods, iva_en=False, iva_p=21.0, t_s=0, preview=False):
        nombre_f_full = cli.split('\n')[0].split(" (")[0].split(" - CUIT/DNI: ")[0]
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT cuit_dni, telefono, localidad, provincia FROM clientes WHERE nombre || ' ' || apellido = ?", (nombre_f_full,))
            res = c.fetchone()
            cuit, tel, loc, prov = (res[0], res[1], res[2], res[3]) if res else ("", "", "", "")
        conn.close()

        pdf = FPDF()
        pdf.add_page()
        logo = next((p for p in ["logo.png", "logo.jpg", "logo.jpeg", "logo apicolavallejos con cuit.png", "logo apicolavallejos con cuit.jpg"] if os.path.exists(p)), None)
        if logo:
            try:
                pdf.image(logo, 10, 8, 60)
            except:
                pass
        pdf.set_font("Arial", 'B', 15)
        pdf.cell(0, 10, 'PRESUPUESTO', ln=True, align='C')
        pdf.ln(35)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, f"Fecha: {fecha}", ln=True, align='R')
        pdf.cell(0, 5, f"Cliente: {nombre_f_full}", ln=True)
        if cuit:
            pdf.cell(0, 5, f"CUIT/DNI: {cuit}", ln=True)
        if loc:
            pdf.cell(0, 5, f"Ubicación: {loc}, {prov}", ln=True)
        if tel:
            pdf.cell(0, 5, f"Teléfono: {tel}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 7, "Producto", border=1, align='C')
        pdf.cell(20, 7, "Cant", border=1, align='C')
        pdf.cell(30, 7, "P.Unit ($)", border=1, align='C')
        pdf.cell(40, 7, "Subtotal ($)", border=1, align='C', ln=True)
        pdf.set_font("Arial", 'B', 10)
        for p in prods:
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(100, 6, p['nombre'], border=1)
            h = pdf.get_y() - y
            pdf.set_xy(x + 100, y)
            pdf.cell(20, h, f"{p['cant']:.0f}", border=1, align='R')
            pdf.cell(30, h, self.formato_moneda(p['prec']), border=1, align='R')
            pdf.cell(40, h, self.formato_moneda(p['sub']), border=1, align='R', ln=True)
        pdf.ln(5)
        if iva_en:
            pdf.cell(150, 6, "SUBTOTAL SIN IVA ($):", align='R')
            pdf.cell(40, 6, self.formato_moneda(t_s), border=1, align='R', ln=True)
            pdf.cell(150, 6, f"IVA ({iva_p}%) ($):", align='R')
            pdf.cell(40, 6, self.formato_moneda(total - t_s), border=1, align='R', ln=True)
            pdf.cell(150, 6, "TOTAL CON IVA ($):", align='R')
        else:
            pdf.cell(150, 6, "TOTAL ($):", align='R')
        pdf.cell(40, 6, self.formato_moneda(total), border=1, align='R', ln=True)

        nombre_f = nombre_f_full.replace(" ", "_")
        if preview:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name
            pdf.output(pdf_path)
            return pdf_path
        os.makedirs("presupuestos", exist_ok=True)
        path = os.path.join("presupuestos", f"Presupuesto_{nombre_f}_{fecha.replace('/', '-')}_{datetime.now().strftime('%H%M%S')}.pdf")
        pdf.output(path)
        return path

    def actualizar_tablas(self):
        with get_db_connection() as conn:
            c = conn.cursor()
            for tree, ent, tbl in [(self.tree_clie, self.ent_busq_clie, "clientes"), (self.tree_prov, self.ent_busq_prov, "proveedores")]:
                for i in tree.get_children():
                    tree.delete(i)
                b = f"%{ent.get()}%"
                c.execute(f"SELECT * FROM {tbl} WHERE nombre LIKE ? OR apellido LIKE ? OR cuit_dni LIKE ? OR telefono LIKE ? OR localidad LIKE ?", (b, b, b, b, b))
                for r in c.fetchall():
                    tree.insert("", "end", values=r)
            for tree, ent_b, tabla, col, ref_table in [(self.tree_hven, self.ent_busq_hven, "ventas", "cliente_nombre", "clientes"), (self.tree_hcom, self.ent_busq_hcom, "compras", "proveedor_nombre", "proveedores")]:
                for i in tree.get_children():
                    tree.delete(i)
                b = f"%{ent_b.get()}%"
                c.execute(f"SELECT id, {col}, fecha FROM {tabla} WHERE {col} LIKE ? OR fecha LIKE ? ORDER BY id DESC", (b, b))
                for r in c.fetchall():
                    pts = r[1].split(" (")
                    nom = pts[0].split(" - CUIT/DNI: ")[0]
                    ref = c.execute(f"SELECT nombre, apellido, cuit_dni FROM {ref_table} WHERE nombre || ' ' || apellido = ?", (nom,)).fetchone()
                    if ref:
                        n, a, cd = ref
                    else:
                        p = nom.split(" ", 1)
                        n, a, cd = p[0], (p[1] if len(p) > 1 else ""), ""
                    ubi = pts[1].replace(")", "") if len(pts) > 1 else ""
                    prov, loc = ubi.split(" - ") if " - " in ubi else (ubi, "")
                    tree.insert("", "end", values=(r[0], n, a, prov, loc, cd, r[2]))
            for lst, ent, tbl in [(self.v_list_clie, self.v_ent_busq, "clientes"), (self.c_list_prov, self.c_ent_busq, "proveedores"), (self.bal_list_clie, self.bal_ent_clie, "clientes"), (self.bal_list_prov, self.bal_ent_prov, "proveedores"), (self.cc_list_clie, self.cc_ent_busq, "clientes"), (self.p_list_clie, self.p_ent_busq, "clientes")]:
                lst.delete(0, tk.END)
                b = f"%{ent.get()}%"
                if tbl == "clientes" and ent.get().lower() in "consumidor final" and c.execute("SELECT 1 FROM ventas WHERE cliente_nombre = 'Consumidor Final'").fetchone():
                    lst.insert(tk.END, "Consumidor Final")
                elif tbl == "proveedores" and ent.get().lower() in "proveedor genérico" and c.execute("SELECT 1 FROM compras WHERE proveedor_nombre = 'Proveedor Genérico'").fetchone():
                    lst.insert(tk.END, "Proveedor Genérico")
                c.execute(f"SELECT nombre, apellido, cuit_dni, provincia, localidad FROM {tbl} WHERE nombre LIKE ? OR apellido LIKE ? OR cuit_dni LIKE ? OR provincia LIKE ? OR localidad LIKE ?", (b, b, b, b, b))
                for n, a, cdni, p, l in c.fetchall():
                    lst.insert(tk.END, f"{n} {a}" + (f" - CUIT/DNI: {cdni}" if cdni else "") + f" ({p} - {l})")
            self.actualizar_deudores()
            if hasattr(self, 'cliente_cc_info'):
                self.cargar_historial_cc()
            for i in self.tree_hpres.get_children():
                self.tree_hpres.delete(i)
            c.execute("SELECT id, cliente_info, fecha, total FROM presupuestos WHERE cliente_info LIKE ? OR fecha LIKE ? ORDER BY id DESC", (f"%{self.p_ent_busq_h.get()}%", f"%{self.p_ent_busq_h.get()}%"))
            for r in c.fetchall():
                self.tree_hpres.insert("", "end", values=(r[0], r[1].split('\n')[0], r[2], self.formato_moneda(r[3])))

    def limpiar_formulario_venta(self):
        for w in [self.v_ent_busq, self.v_list_clie]:
            if hasattr(w, 'delete'):
                w.delete(0, tk.END)
        self.cliente_actual_info = "Consumidor Final"
        for i in self.inputs_materiales:
            i["cant"].delete(0, tk.END)
            i["prec"].delete(0, tk.END)
            if i["es_extra"]:
                i["prod"].delete(0, tk.END)

    def limpiar_formulario_compra(self):
        self.c_ent_busq.delete(0, tk.END)
        self.c_list_prov.delete(0, tk.END)
        self.proveedor_actual_info = "Proveedor Genérico"
        for i in self.inputs_compras:
            i["cant"].delete(0, tk.END)
            i["prec"].delete(0, tk.END)
            i["prod"].delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppApicola(root)
    root.mainloop()
