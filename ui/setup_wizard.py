"""
ui/setup_wizard.py
First-run Setup Wizard: collects shop details + optional Excel imports,
then creates and initializes the database. Shown only when shop.db does
not exist (see main.py).
"""
from __future__ import annotations

import os
import shutil
from tkinter import filedialog, messagebox

import customtkinter as ctk

from database.db_manager import db
from modules.auth_manager import auth
from modules.excel_manager import excel_manager
from utils.config_manager import config
from utils.logger import get_logger

logger = get_logger("setup_wizard")


class SetupWizard(ctk.CTkToplevel):
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete = on_complete
        self.title("ShopEase POS - Setup Wizard")
        self.geometry("640x680")
        self.resizable(False, False)
        self.grab_set()

        self.product_excel_path = ""
        self.customer_excel_path = ""
        self.logo_path = ""

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkLabel(self, text="Welcome to ShopEase POS",
                               font=ctk.CTkFont(size=22, weight="bold"))
        header.pack(pady=(24, 4))
        sub = ctk.CTkLabel(self, text="Let's set up your shop in a minute.",
                            font=ctk.CTkFont(size=13), text_color="gray")
        sub.pack(pady=(0, 16))

        form = ctk.CTkScrollableFrame(self, width=580, height=420)
        form.pack(padx=20, pady=10, fill="both", expand=True)

        self.entries = {}
        fields = [
            ("shop_name", "Shop Name *"),
            ("owner_name", "Owner Name *"),
            ("phone", "Phone Number *"),
            ("address", "Address"),
            ("gst_number", "GST Number (optional)"),
        ]
        for key, label in fields:
            ctk.CTkLabel(form, text=label, anchor="w").pack(fill="x", pady=(8, 2))
            entry = ctk.CTkEntry(form, height=36)
            entry.pack(fill="x")
            self.entries[key] = entry

        ctk.CTkLabel(form, text="Shop Logo (optional)", anchor="w").pack(fill="x", pady=(12, 2))
        logo_row = ctk.CTkFrame(form, fg_color="transparent")
        logo_row.pack(fill="x")
        self.logo_label = ctk.CTkLabel(logo_row, text="No file selected", text_color="gray")
        self.logo_label.pack(side="left", padx=(0, 10))
        ctk.CTkButton(logo_row, text="Browse...", width=100, command=self._pick_logo).pack(side="left")

        ctk.CTkLabel(form, text="Login Credentials (Admin)", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(16, 2))
        ctk.CTkLabel(form, text="Admin Username *", anchor="w").pack(fill="x", pady=(6, 2))
        self.entries["admin_username"] = ctk.CTkEntry(form, height=36)
        self.entries["admin_username"].pack(fill="x")
        ctk.CTkLabel(form, text="Admin Password *", anchor="w").pack(fill="x", pady=(6, 2))
        self.entries["admin_password"] = ctk.CTkEntry(form, height=36, show="*")
        self.entries["admin_password"].pack(fill="x")

        ctk.CTkLabel(form, text="Import Existing Data (optional)", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(16, 2))

        prod_row = ctk.CTkFrame(form, fg_color="transparent")
        prod_row.pack(fill="x", pady=4)
        self.product_file_label = ctk.CTkLabel(prod_row, text="No product Excel selected", text_color="gray")
        self.product_file_label.pack(side="left", padx=(0, 10))
        ctk.CTkButton(prod_row, text="Select Product Excel", width=170,
                      command=self._pick_product_excel).pack(side="left")

        cust_row = ctk.CTkFrame(form, fg_color="transparent")
        cust_row.pack(fill="x", pady=4)
        self.customer_file_label = ctk.CTkLabel(cust_row, text="No customer Excel selected", text_color="gray")
        self.customer_file_label.pack(side="left", padx=(0, 10))
        ctk.CTkButton(cust_row, text="Select Customer Excel", width=170,
                      command=self._pick_customer_excel).pack(side="left")

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack(pady=(4, 0))

        ctk.CTkButton(self, text="Finish Setup", height=42, font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._finish_setup).pack(pady=16)

    def _pick_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.logo_path = path
            self.logo_label.configure(text=os.path.basename(path))

    def _pick_product_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if path:
            self.product_excel_path = path
            self.product_file_label.configure(text=os.path.basename(path))

    def _pick_customer_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if path:
            self.customer_excel_path = path
            self.customer_file_label.configure(text=os.path.basename(path))

    def _finish_setup(self):
        shop_name = self.entries["shop_name"].get().strip()
        owner_name = self.entries["owner_name"].get().strip()
        phone = self.entries["phone"].get().strip()
        admin_username = self.entries["admin_username"].get().strip()
        admin_password = self.entries["admin_password"].get().strip()

        if not shop_name or not owner_name or not phone:
            messagebox.showerror("Missing Information", "Shop Name, Owner Name and Phone are required.")
            return
        if not admin_username or not admin_password:
            messagebox.showerror("Missing Information", "Admin username and password are required.")
            return
        if len(admin_password) < 4:
            messagebox.showerror("Weak Password", "Password should be at least 4 characters.")
            return

        try:
            self.status_label.configure(text="Creating database...")
            self.update_idletasks()
            db.initialize()

            logo_dest = ""
            if self.logo_path:
                assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
                os.makedirs(assets_dir, exist_ok=True)
                logo_dest = os.path.join(assets_dir, "logo" + os.path.splitext(self.logo_path)[1])
                shutil.copy2(self.logo_path, logo_dest)

            config.update({
                "shop_name": shop_name,
                "owner_name": owner_name,
                "phone": phone,
                "address": self.entries["address"].get().strip(),
                "gst_number": self.entries["gst_number"].get().strip(),
                "logo_path": logo_dest,
                "first_run_complete": True,
            })

            self.status_label.configure(text="Creating admin account...")
            self.update_idletasks()
            auth.create_default_admin(admin_username, admin_password, owner_name)

            if self.product_excel_path:
                self.status_label.configure(text="Importing products...")
                self.update_idletasks()
                excel_manager.import_products(self.product_excel_path)

            if self.customer_excel_path:
                self.status_label.configure(text="Importing customers...")
                self.update_idletasks()
                excel_manager.import_customers(self.customer_excel_path)

            self.status_label.configure(text="Setup complete!")
            messagebox.showinfo("Setup Complete", "ShopEase POS is ready to use!")
            self.grab_release()
            self.destroy()
            self.on_complete()
        except Exception as exc:
            logger.exception("Setup failed")
            messagebox.showerror("Setup Failed", f"An error occurred during setup:\n{exc}")
            self.status_label.configure(text="Setup failed. Please try again.")
