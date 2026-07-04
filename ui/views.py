"""
ui/views.py (part 1 of module) - Products, Customers, Billing, Reports,
Settings views. Split as classes in one file to keep the ui/ package small;
each class is self-contained and only talks to its corresponding manager.
"""
from __future__ import annotations

import os
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from modules.product_manager import products, Product
from modules.customer_manager import customers, Customer
from modules.billing_manager import billing, Cart, CartItem
from modules.invoice_generator import invoice_generator
from modules.excel_manager import excel_manager
from modules.report_manager import reports
from modules.backup_manager import backup_manager
from modules.auth_manager import auth
from utils.config_manager import config


def _style_treeview():
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", rowheight=28, font=("Segoe UI", 10), borderwidth=0)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.map("Treeview", background=[("selected", "#2f6fed")])


# ---------------------------------------------------------------------- #
# PRODUCTS
# ---------------------------------------------------------------------- #
class ProductsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        _style_treeview()
        self.selected_id = None
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(top, text="Products", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="right")
        ctk.CTkButton(btns, text="Import Excel", width=110, command=self._import_excel).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Export Excel", width=110, command=self._export_excel).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="+ Add Product", width=120, command=self._open_form).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", padx=20)
        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Search by name, barcode, or brand...", width=350)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh())
        ctk.CTkButton(search_row, text="Low Stock Only", width=130, command=self._toggle_low_stock).pack(side="left", padx=8)
        self.low_stock_only = False

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("barcode", "name", "category", "retail", "wholesale", "stock", "min_stock")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headers = ["Barcode", "Name", "Category", "Retail Price", "Wholesale Price", "Stock", "Min Stock"]
        widths = [110, 220, 120, 100, 110, 70, 80]
        for col, head, w in zip(columns, headers, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="center" if col != "name" else "w")
        self.tree.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda e: self._open_form(edit=True))

        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(action_row, text="Edit Selected", width=120, command=lambda: self._open_form(edit=True)).pack(side="left", padx=4)
        ctk.CTkButton(action_row, text="Delete Selected", width=120, fg_color="#a83232", hover_color="#832020",
                      command=self._delete_selected).pack(side="left", padx=4)

    def _refresh(self):
        term = self.search_entry.get().strip()
        rows = products.low_stock() if self.low_stock_only else products.search(term)
        self.tree.delete(*self.tree.get_children())
        for p in rows:
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["barcode"] or "-", p["name"], p["category"] or "-",
                f"{p['retail_price']:.2f}", f"{p['wholesale_price']:.2f}", p["stock"], p["min_stock"],
            ))

    def _toggle_low_stock(self):
        self.low_stock_only = not self.low_stock_only
        self._refresh()

    def _selected_product_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _delete_selected(self):
        pid = self._selected_product_id()
        if not pid:
            messagebox.showinfo("No Selection", "Please select a product first.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this product?"):
            products.delete_product(pid)
            self._refresh()

    def _import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return
        try:
            count = excel_manager.import_products(path)
            messagebox.showinfo("Import Complete", f"Imported/updated {count} products.")
            self._refresh()
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

    def _export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Products.xlsx")
        if not path:
            return
        try:
            excel_manager.export_products(path)
            messagebox.showinfo("Export Complete", f"Products exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _open_form(self, edit: bool = False):
        product = None
        if edit:
            pid = self._selected_product_id()
            if not pid:
                messagebox.showinfo("No Selection", "Please select a product first.")
                return
            product = products.get_by_id(pid)
        ProductFormDialog(self, product, on_saved=self._refresh)


class ProductFormDialog(ctk.CTkToplevel):
    def __init__(self, master, product: dict | None, on_saved):
        super().__init__(master)
        self.product = product
        self.on_saved = on_saved
        self.title("Edit Product" if product else "Add Product")
        self.geometry("420x620")
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        fields = [
            ("barcode", "Barcode"), ("name", "Product Name *"), ("category", "Category"),
            ("brand", "Brand"), ("purchase_price", "Purchase Price"), ("retail_price", "Retail Price *"),
            ("wholesale_price", "Wholesale Price"), ("gst_percent", "GST %"),
            ("stock", "Stock"), ("min_stock", "Minimum Stock"), ("rack_location", "Rack Location"),
            ("remarks", "Remarks"),
        ]
        self.entries = {}
        scroll = ctk.CTkScrollableFrame(self, width=380, height=540)
        scroll.pack(padx=16, pady=16, fill="both", expand=True)
        for key, label in fields:
            ctk.CTkLabel(scroll, text=label, anchor="w").pack(fill="x", pady=(6, 2))
            entry = ctk.CTkEntry(scroll)
            entry.pack(fill="x")
            if self.product and key in self.product and self.product[key] is not None:
                entry.insert(0, str(self.product[key]))
            self.entries[key] = entry

        ctk.CTkButton(self, text="Save", height=40, command=self._save).pack(pady=10, padx=16, fill="x")

    def _save(self):
        try:
            name = self.entries["name"].get().strip()
            if not name:
                messagebox.showerror("Missing Field", "Product name is required.")
                return
            p = Product(
                id=self.product["id"] if self.product else None,
                barcode=self.entries["barcode"].get().strip(),
                name=name,
                category=self.entries["category"].get().strip(),
                brand=self.entries["brand"].get().strip(),
                purchase_price=_f(self.entries["purchase_price"].get()),
                retail_price=_f(self.entries["retail_price"].get()),
                wholesale_price=_f(self.entries["wholesale_price"].get()),
                gst_percent=_f(self.entries["gst_percent"].get()),
                stock=int(_f(self.entries["stock"].get())),
                min_stock=int(_f(self.entries["min_stock"].get()) or 5),
                rack_location=self.entries["rack_location"].get().strip(),
                remarks=self.entries["remarks"].get().strip(),
            )
            if self.product:
                products.update_product(
                    p.id, barcode=p.barcode or None, name=p.name, category=p.category,
                    brand=p.brand, purchase_price=p.purchase_price, retail_price=p.retail_price,
                    wholesale_price=p.wholesale_price, gst_percent=p.gst_percent,
                    min_stock=p.min_stock, rack_location=p.rack_location, remarks=p.remarks,
                )
            else:
                products.add_product(p)
            self.on_saved()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))


def _f(val: str) -> float:
    try:
        return float(val) if val.strip() else 0.0
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------- #
# CUSTOMERS
# ---------------------------------------------------------------------- #
class CustomersView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        _style_treeview()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(top, text="Customers", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="right")
        ctk.CTkButton(btns, text="Export Excel", width=110, command=self._export_excel).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="+ Add Customer", width=130, command=self._open_form).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", padx=20)
        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Search by name or phone...", width=350)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh())

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("name", "phone", "email", "pending", "last_visit")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headers = ["Name", "Phone", "Email", "Pending Amount", "Last Visit"]
        widths = [200, 120, 200, 120, 160]
        for col, head, w in zip(columns, headers, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="center" if col not in ("name", "email") else "w")
        self.tree.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda e: self._open_form(edit=True))

        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(action_row, text="Edit Selected", width=120, command=lambda: self._open_form(edit=True)).pack(side="left", padx=4)
        ctk.CTkButton(action_row, text="View Ledger", width=120, command=self._view_ledger).pack(side="left", padx=4)
        ctk.CTkButton(action_row, text="Delete Selected", width=120, fg_color="#a83232", hover_color="#832020",
                      command=self._delete_selected).pack(side="left", padx=4)

    def _refresh(self):
        term = self.search_entry.get().strip()
        rows = customers.search(term)
        self.tree.delete(*self.tree.get_children())
        for c in rows:
            self.tree.insert("", "end", iid=str(c["id"]), values=(
                c["name"], c["phone"] or "-", c["email"] or "-",
                f"{config.get('currency_symbol')}{c['pending_amount']:.2f}", c["last_visit"] or "-",
            ))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _delete_selected(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("No Selection", "Please select a customer first.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this customer?"):
            customers.delete_customer(cid)
            self._refresh()

    def _export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Customers.xlsx")
        if not path:
            return
        try:
            excel_manager.export_customers(path)
            messagebox.showinfo("Export Complete", f"Customers exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _open_form(self, edit: bool = False):
        customer = None
        if edit:
            cid = self._selected_id()
            if not cid:
                messagebox.showinfo("No Selection", "Please select a customer first.")
                return
            customer = customers.get_by_id(cid)
        CustomerFormDialog(self, customer, on_saved=self._refresh)

    def _view_ledger(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("No Selection", "Please select a customer first.")
            return
        CustomerLedgerDialog(self, cid)


class CustomerFormDialog(ctk.CTkToplevel):
    def __init__(self, master, customer: dict | None, on_saved):
        super().__init__(master)
        self.customer = customer
        self.on_saved = on_saved
        self.title("Edit Customer" if customer else "Add Customer")
        self.geometry("380x440")
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        fields = [("name", "Name *"), ("phone", "Phone"), ("email", "Email"),
                  ("address", "Address"), ("gst_number", "GST Number")]
        self.entries = {}
        for key, label in fields:
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=16, pady=(8, 2))
            entry = ctk.CTkEntry(self)
            entry.pack(fill="x", padx=16)
            if self.customer and self.customer.get(key):
                entry.insert(0, str(self.customer[key]))
            self.entries[key] = entry
        ctk.CTkButton(self, text="Save", height=40, command=self._save).pack(pady=16, padx=16, fill="x")

    def _save(self):
        name = self.entries["name"].get().strip()
        if not name:
            messagebox.showerror("Missing Field", "Customer name is required.")
            return
        c = Customer(
            id=self.customer["id"] if self.customer else None,
            name=name, phone=self.entries["phone"].get().strip(),
            email=self.entries["email"].get().strip(),
            address=self.entries["address"].get().strip(),
            gst_number=self.entries["gst_number"].get().strip(),
        )
        try:
            if self.customer:
                customers.update_customer(c.id, name=c.name, phone=c.phone or None,
                                           email=c.email, address=c.address, gst_number=c.gst_number)
            else:
                customers.add_customer(c)
            self.on_saved()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))


class CustomerLedgerDialog(ctk.CTkToplevel):
    def __init__(self, master, customer_id: int):
        super().__init__(master)
        self.title("Customer Ledger")
        self.geometry("480x420")
        self.grab_set()
        customer = customers.get_by_id(customer_id)
        ctk.CTkLabel(self, text=f"Ledger: {customer['name']}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=12)
        ledger = customers.get_ledger(customer_id)
        table = ttk.Treeview(self, columns=("invoice", "date", "total", "payment"), show="headings")
        for col, head in zip(("invoice", "date", "total", "payment"), ["Invoice", "Date", "Total", "Payment"]):
            table.heading(col, text=head)
        table.pack(fill="both", expand=True, padx=16, pady=8)
        for entry in ledger:
            table.insert("", "end", values=(entry["invoice_number"], entry["bill_date"],
                                             f"{entry['grand_total']:.2f}", entry["payment_method"]))


# ---------------------------------------------------------------------- #
# BILLING
# ---------------------------------------------------------------------- #
class BillingView(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.cart = Cart()
        self.selected_customer = None
        _style_treeview()
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        ctk.CTkLabel(left, text="Billing", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")

        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x", pady=10)
        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Search product or scan barcode, then Enter...", width=380)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self._search_or_add())
        self.search_entry.bind("<KeyRelease>", lambda e: self._live_search())
        self.price_mode_var = ctk.StringVar(value="retail")
        ctk.CTkOptionMenu(search_row, values=["retail", "wholesale"], variable=self.price_mode_var,
                          width=110).pack(side="left", padx=8)

        self.results_frame = ctk.CTkScrollableFrame(left, height=140)
        self.results_frame.pack(fill="x", pady=(0, 10))

        cart_frame = ctk.CTkFrame(left)
        cart_frame.pack(fill="both", expand=True)
        columns = ("name", "qty", "price", "gst", "total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings")
        for col, head, w in zip(columns, ["Item", "Qty", "Unit Price", "GST%", "Line Total"], [220, 60, 90, 60, 100]):
            self.cart_tree.heading(col, text=head)
            self.cart_tree.column(col, width=w, anchor="center" if col != "name" else "w")
        self.cart_tree.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        scroll.pack(side="right", fill="y")
        self.cart_tree.configure(yscrollcommand=scroll.set)

        cart_actions = ctk.CTkFrame(left, fg_color="transparent")
        cart_actions.pack(fill="x", pady=8)
        ctk.CTkLabel(cart_actions, text="Qty:").pack(side="left")
        self.qty_entry = ctk.CTkEntry(cart_actions, width=60)
        self.qty_entry.insert(0, "1")
        self.qty_entry.pack(side="left", padx=6)
        ctk.CTkButton(cart_actions, text="Update Qty", width=100, command=self._update_qty).pack(side="left", padx=4)
        ctk.CTkButton(cart_actions, text="Remove Item", width=100, fg_color="#a83232", hover_color="#832020",
                      command=self._remove_item).pack(side="left", padx=4)
        ctk.CTkButton(cart_actions, text="Clear Cart", width=100, command=self._clear_cart).pack(side="left", padx=4)

        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)

        ctk.CTkLabel(right, text="Checkout", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16, 8), padx=16, anchor="w")

        cust_row = ctk.CTkFrame(right, fg_color="transparent")
        cust_row.pack(fill="x", padx=16, pady=4)
        self.customer_entry = ctk.CTkEntry(cust_row, placeholder_text="Customer phone (optional)")
        self.customer_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(cust_row, text="Find", width=60, command=self._find_customer).pack(side="left", padx=4)
        self.customer_label = ctk.CTkLabel(right, text="Walk-in Customer", text_color="gray")
        self.customer_label.pack(anchor="w", padx=16)

        ctk.CTkLabel(right, text="Overall Discount", anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.discount_entry = ctk.CTkEntry(right)
        self.discount_entry.insert(0, "0")
        self.discount_entry.pack(fill="x", padx=16)

        ctk.CTkLabel(right, text="Payment Method", anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.payment_var = ctk.StringVar(value="Cash")
        ctk.CTkOptionMenu(right, values=["Cash", "Card", "UPI", "Credit"], variable=self.payment_var).pack(fill="x", padx=16)

        self.totals_label = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=13), justify="left")
        self.totals_label.pack(fill="x", padx=16, pady=16, anchor="w")

        ctk.CTkButton(right, text="Generate Invoice & Checkout", height=46,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._checkout).pack(fill="x", padx=16, pady=(0, 20))

        self._update_totals()

    def _live_search(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        term = self.search_entry.get().strip()
        if not term:
            return
        matches = products.search(term, limit=8)
        for p in matches:
            row = ctk.CTkFrame(self.results_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            label = f"{p['name']}  |  Stock: {p['stock']}  |  {config.get('currency_symbol')}{p['retail_price']:.2f}"
            ctk.CTkButton(row, text=label, anchor="w", fg_color="transparent",
                          hover_color=("gray85", "gray25"),
                          command=lambda pid=p['id']: self._add_product_to_cart(pid)).pack(fill="x")

    def _search_or_add(self):
        term = self.search_entry.get().strip()
        if not term:
            return
        by_barcode = products.get_by_barcode(term)
        if by_barcode:
            self._add_product_to_cart(by_barcode["id"])
            return
        matches = products.search(term, limit=1)
        if matches:
            self._add_product_to_cart(matches[0]["id"])
        else:
            messagebox.showinfo("Not Found", "No matching product found.")

    def _add_product_to_cart(self, product_id: int):
        p = products.get_by_id(product_id)
        if not p:
            return
        if p["stock"] <= 0:
            messagebox.showwarning("Out of Stock", f"{p['name']} has no stock available.")
            return
        price_mode = self.price_mode_var.get()
        unit_price = p["retail_price"] if price_mode == "retail" else p["wholesale_price"]
        self.cart.price_mode = price_mode
        self.cart.add_item(CartItem(
            product_id=p["id"], name=p["name"], quantity=1,
            unit_price=unit_price, gst_percent=p["gst_percent"],
        ))
        self.search_entry.delete(0, "end")
        for w in self.results_frame.winfo_children():
            w.destroy()
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for idx, item in enumerate(self.cart.items):
            self.cart_tree.insert("", "end", iid=str(idx), values=(
                item.name, f"{item.quantity:g}", f"{item.unit_price:.2f}",
                f"{item.gst_percent:g}", f"{item.line_total:.2f}",
            ))
        self._update_totals()

    def _selected_cart_index(self):
        sel = self.cart_tree.selection()
        return int(sel[0]) if sel else None

    def _update_qty(self):
        idx = self._selected_cart_index()
        if idx is None:
            return
        try:
            qty = float(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
            self.cart.update_quantity(idx, qty)
            self._refresh_cart()
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Please enter a valid positive quantity.")

    def _remove_item(self):
        idx = self._selected_cart_index()
        if idx is not None:
            self.cart.remove_item(idx)
            self._refresh_cart()

    def _clear_cart(self):
        self.cart.clear()
        self.selected_customer = None
        self.customer_label.configure(text="Walk-in Customer")
        self._refresh_cart()

    def _find_customer(self):
        phone = self.customer_entry.get().strip()
        if not phone:
            return
        c = customers.get_by_phone(phone)
        if c:
            self.selected_customer = c
            self.cart.customer_id = c["id"]
            self.customer_label.configure(text=f"{c['name']} ({c['phone']})")
        else:
            if messagebox.askyesno("New Customer", "No customer found with this phone. Add as a new customer?"):
                from ui.views import CustomerFormDialog
                CustomerFormDialog(self, {"phone": phone, "id": None, "name": "", "email": "", "address": "", "gst_number": ""},
                                    on_saved=lambda: None)

    def _update_totals(self):
        try:
            self.cart.overall_discount = float(self.discount_entry.get() or 0)
        except ValueError:
            self.cart.overall_discount = 0
        self.cart.payment_method = self.payment_var.get()
        currency = config.get("currency_symbol")
        text = (f"Subtotal: {currency}{self.cart.subtotal:.2f}\n"
                f"GST: {currency}{self.cart.gst_total:.2f}\n"
                f"Discount: {currency}{self.cart.overall_discount:.2f}\n"
                f"Grand Total: {currency}{self.cart.grand_total:.2f}")
        self.totals_label.configure(text=text)
        if self.winfo_exists():
            self.after(300, self._update_totals)

    def _checkout(self):
        if not self.cart.items:
            messagebox.showinfo("Empty Cart", "Add at least one product before checkout.")
            return
        try:
            self.cart.payment_method = self.payment_var.get()
            result = billing.checkout(self.cart, created_by=self.user.id)
            bill = billing.get_bill(result["bill_id"])
            customer = customers.get_by_id(bill["customer_id"]) if bill["customer_id"] else None
            pdf_path = invoice_generator.generate(bill, customer)
            messagebox.showinfo("Sale Complete", f"Invoice {result['invoice_number']} generated:\n{pdf_path}")
            self.cart = Cart()
            self.selected_customer = None
            self.customer_label.configure(text="Walk-in Customer")
            self.discount_entry.delete(0, "end")
            self.discount_entry.insert(0, "0")
            self._refresh_cart()
        except Exception as exc:
            messagebox.showerror("Checkout Failed", str(exc))


# ---------------------------------------------------------------------- #
# REPORTS
# ---------------------------------------------------------------------- #
class ReportsView(ctk.CTkFrame):
    PERIODS = ["today", "week", "month", "year"]

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        _style_treeview()
        self.period_var = ctk.StringVar(value="month")
        self._build_ui()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(top, text="Reports", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(top, values=self.PERIODS, variable=self.period_var,
                          command=lambda _: self._refresh()).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Export Sales (Excel)", width=160, command=self._export_sales).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Add Expense", width=120, command=self._add_expense).pack(side="right", padx=4)

        self.body = ctk.CTkScrollableFrame(self)
        self.body.pack(fill="both", expand=True, padx=20, pady=10)
        self._refresh()

    def _refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        period = self.period_var.get()
        sales = reports.sales_summary(period)
        profit = reports.profit_report(period)
        expense = reports.expense_summary(period)
        currency = config.get("currency_symbol")

        cards = ctk.CTkFrame(self.body, fg_color="transparent")
        cards.pack(fill="x", pady=8)
        for i, (title, value) in enumerate([
            ("Total Sales", f"{currency}{sales['total_sales']:.2f}"),
            ("Bills", str(sales["bill_count"])),
            ("GST Collected", f"{currency}{sales['total_gst']:.2f}"),
            ("Profit", f"{currency}{profit['profit']:.2f}"),
            ("Expenses", f"{currency}{expense['total']:.2f}"),
        ]):
            card = ctk.CTkFrame(cards, corner_radius=10)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            cards.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=title, text_color="gray", font=ctk.CTkFont(size=11)).pack(padx=14, pady=(10, 0))
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=16, weight="bold")).pack(padx=14, pady=(2, 10))

        ctk.CTkLabel(self.body, text="Top Products", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", pady=(16, 6))
        top_products_frame = ctk.CTkFrame(self.body)
        top_products_frame.pack(fill="x")
        table = ttk.Treeview(top_products_frame, columns=("name", "qty", "revenue"), show="headings", height=8)
        for col, head in zip(("name", "qty", "revenue"), ["Product", "Qty Sold", "Revenue"]):
            table.heading(col, text=head)
        table.pack(fill="x")
        for row in reports.top_products(10, period):
            table.insert("", "end", values=(row["product_name"], f"{row['qty_sold']:g}", f"{row['revenue']:.2f}"))

        ctk.CTkLabel(self.body, text="Top Customers", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", pady=(16, 6))
        top_cust_frame = ctk.CTkFrame(self.body)
        top_cust_frame.pack(fill="x")
        table2 = ttk.Treeview(top_cust_frame, columns=("name", "bills", "spent"), show="headings", height=6)
        for col, head in zip(("name", "bills", "spent"), ["Customer", "Bills", "Total Spent"]):
            table2.heading(col, text=head)
        table2.pack(fill="x")
        for row in customers.top_customers(10):
            table2.insert("", "end", values=(row["name"], row["bill_count"], f"{row['total_spent']:.2f}"))

        stock_val = products.stock_value()
        ctk.CTkLabel(self.body,
                     text=f"Inventory Value (Cost): {currency}{stock_val['cost_value']:.2f}   |   "
                          f"Inventory Value (Retail): {currency}{stock_val['retail_value']:.2f}",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(16, 6))

    def _export_sales(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Bills.xlsx")
        if not path:
            return
        try:
            excel_manager.export_bills(path)
            messagebox.showinfo("Export Complete", f"Sales exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _add_expense(self):
        ExpenseDialog(self, on_saved=self._refresh)


class ExpenseDialog(ctk.CTkToplevel):
    def __init__(self, master, on_saved):
        super().__init__(master)
        self.on_saved = on_saved
        self.title("Add Expense")
        self.geometry("340x320")
        self.grab_set()
        for key, label in [("title", "Title *"), ("category", "Category"), ("amount", "Amount *"), ("notes", "Notes")]:
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=16, pady=(8, 2))
            entry = ctk.CTkEntry(self)
            entry.pack(fill="x", padx=16)
            setattr(self, f"{key}_entry", entry)
        ctk.CTkButton(self, text="Save Expense", height=38, command=self._save).pack(pady=16, padx=16, fill="x")

    def _save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Missing Field", "Title is required.")
            return
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid amount.")
            return
        reports.add_expense(title, amount, self.category_entry.get().strip(), self.notes_entry.get().strip())
        self.on_saved()
        self.destroy()


# ---------------------------------------------------------------------- #
# SETTINGS
# ---------------------------------------------------------------------- #
class SettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Settings", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 16))

        # Shop details
        ctk.CTkLabel(scroll, text="Shop Details", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(8, 6))
        self.entries = {}
        for key, label in [("shop_name", "Shop Name"), ("owner_name", "Owner Name"), ("phone", "Phone"),
                            ("address", "Address"), ("gst_number", "GST Number")]:
            ctk.CTkLabel(scroll, text=label, anchor="w").pack(fill="x", pady=(4, 2))
            entry = ctk.CTkEntry(scroll)
            entry.insert(0, config.get(key, ""))
            entry.pack(fill="x")
            self.entries[key] = entry
        ctk.CTkButton(scroll, text="Save Shop Details", command=self._save_shop_details).pack(anchor="w", pady=12)

        # Appearance
        ctk.CTkLabel(scroll, text="Appearance", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(16, 6))
        theme_row = ctk.CTkFrame(scroll, fg_color="transparent")
        theme_row.pack(fill="x")
        ctk.CTkLabel(theme_row, text="Theme:").pack(side="left")
        self.theme_var = ctk.StringVar(value=config.get("theme", "dark"))
        ctk.CTkOptionMenu(theme_row, values=["dark", "light", "system"], variable=self.theme_var,
                          command=self._change_theme).pack(side="left", padx=8)

        # Import / Export
        ctk.CTkLabel(scroll, text="Import / Export", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(20, 6))
        io_row = ctk.CTkFrame(scroll, fg_color="transparent")
        io_row.pack(fill="x")
        ctk.CTkButton(io_row, text="Import Products", command=self._import_products).pack(side="left", padx=4)
        ctk.CTkButton(io_row, text="Import Customers", command=self._import_customers).pack(side="left", padx=4)
        ctk.CTkButton(io_row, text="Export All", command=self._export_all).pack(side="left", padx=4)

        # Backup
        ctk.CTkLabel(scroll, text="Backup & Restore", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(20, 6))
        backup_row = ctk.CTkFrame(scroll, fg_color="transparent")
        backup_row.pack(fill="x")
        ctk.CTkButton(backup_row, text="Backup Now", command=self._backup_now).pack(side="left", padx=4)
        ctk.CTkButton(backup_row, text="Restore from Backup", command=self._restore_backup).pack(side="left", padx=4)

        # Database info
        ctk.CTkLabel(scroll, text="Database Information", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(20, 6))
        info = (f"Products: {products.count()}   |   Customers: {customers.total_customers()}\n"
                f"Database location: database/shop.db")
        ctk.CTkLabel(scroll, text=info, justify="left", text_color="gray").pack(anchor="w")

        # About
        ctk.CTkLabel(scroll, text="About", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(20, 6))
        ctk.CTkLabel(scroll, text="ShopEase POS v1.0 — Offline Billing & Inventory Management",
                     text_color="gray").pack(anchor="w")

    def _save_shop_details(self):
        config.update({k: e.get().strip() for k, e in self.entries.items()})
        messagebox.showinfo("Saved", "Shop details updated.")

    def _change_theme(self, value):
        config.set("theme", value)
        ctk.set_appearance_mode(value)

    def _import_products(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return
        try:
            count = excel_manager.import_products(path)
            messagebox.showinfo("Import Complete", f"Imported/updated {count} products.")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

    def _import_customers(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return
        try:
            count = excel_manager.import_customers(path)
            messagebox.showinfo("Import Complete", f"Imported/updated {count} customers.")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

    def _export_all(self):
        try:
            p1 = excel_manager.export_products()
            p2 = excel_manager.export_customers()
            p3 = excel_manager.export_bills()
            messagebox.showinfo("Export Complete", f"Exported to:\n{p1}\n{p2}\n{p3}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _backup_now(self):
        try:
            path = backup_manager.create_backup()
            messagebox.showinfo("Backup Complete", f"Backup created at:\n{path}")
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc))

    def _restore_backup(self):
        backups = backup_manager.list_backups()
        if not backups:
            messagebox.showinfo("No Backups", "No backups are available yet.")
            return
        dialog = ctk.CTkInputDialog(text=f"Available backups:\n{chr(10).join(backups[:10])}\n\nEnter backup name to restore:",
                                     title="Restore Backup")
        choice = dialog.get_input()
        if choice and choice in backups:
            if messagebox.askyesno("Confirm Restore", "This will overwrite current data. Continue?"):
                if backup_manager.restore_backup(choice):
                    messagebox.showinfo("Restored", "Backup restored successfully. Please restart the application.")
        elif choice:
            messagebox.showerror("Not Found", "Backup name not found.")
