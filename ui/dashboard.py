"""
ui/dashboard.py
Main application shell after login: sidebar navigation + a content area that
swaps between Home/Products/Customers/Billing/Reports/Settings frames.
"""
from __future__ import annotations

import customtkinter as ctk

from modules.auth_manager import auth
from modules.backup_manager import backup_manager
from modules.customer_manager import customers
from modules.product_manager import products
from modules.billing_manager import billing
from modules.report_manager import reports
from utils.config_manager import config


class HomeView(ctk.CTkFrame):
    """Dashboard landing page: KPI cards + recent bills + low stock list."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", padx=24, pady=(20, 10))

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=24, pady=8)

        today = reports.sales_summary("today")
        month = reports.sales_summary("month")
        profit_today = reports.profit_report("today")

        card_data = [
            ("Today's Sales", f"{config.get('currency_symbol')}{today['total_sales']:.2f}"),
            ("Today's Profit", f"{config.get('currency_symbol')}{profit_today['profit']:.2f}"),
            ("Monthly Sales", f"{config.get('currency_symbol')}{month['total_sales']:.2f}"),
            ("Total Customers", str(customers.total_customers())),
            ("Total Products", str(products.count())),
            ("Low Stock Items", str(len(products.low_stock()))),
        ]
        for i, (title, value) in enumerate(card_data):
            card = ctk.CTkFrame(cards_frame, corner_radius=12, height=90)
            card.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            cards_frame.grid_columnconfigure(i % 3, weight=1)
            ctk.CTkLabel(card, text=title, text_color="gray", font=ctk.CTkFont(size=12)).pack(
                anchor="w", padx=16, pady=(14, 0))
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold")).pack(
                anchor="w", padx=16, pady=(2, 14))

        lists_frame = ctk.CTkFrame(self, fg_color="transparent")
        lists_frame.pack(fill="both", expand=True, padx=24, pady=(12, 20))
        lists_frame.grid_columnconfigure(0, weight=1)
        lists_frame.grid_columnconfigure(1, weight=1)

        recent_box = ctk.CTkFrame(lists_frame, corner_radius=12)
        recent_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(recent_box, text="Recent Bills", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=16, pady=(12, 6))
        recent = billing.recent_bills(8)
        if not recent:
            ctk.CTkLabel(recent_box, text="No bills yet.", text_color="gray").pack(padx=16, pady=8)
        for b in recent:
            row = ctk.CTkFrame(recent_box, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=f"{b['invoice_number']}  •  {b['customer_name']}", anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"{config.get('currency_symbol')}{b['grand_total']:.2f}").pack(side="right")

        low_stock_box = ctk.CTkFrame(lists_frame, corner_radius=12)
        low_stock_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(low_stock_box, text="Low Stock Products", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=16, pady=(12, 6))
        low = products.low_stock()[:8]
        if not low:
            ctk.CTkLabel(low_stock_box, text="All stock levels healthy.", text_color="gray").pack(padx=16, pady=8)
        for p in low:
            row = ctk.CTkFrame(low_stock_box, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=p["name"], anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"Stock: {p['stock']}", text_color="#e0a020").pack(side="right")


class Dashboard(ctk.CTkFrame):
    NAV_ITEMS = [
        ("Dashboard", "home"),
        ("Billing", "billing"),
        ("Products", "products"),
        ("Customers", "customers"),
        ("Reports", "reports"),
        ("Settings", "settings"),
    ]

    def __init__(self, master, user, on_logout):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.on_logout = on_logout
        self.pack(fill="both", expand=True)
        self.current_frame = None
        self.frame_cache: dict = {}
        self._build_ui()
        self.show("home")

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="ShopEase", font=ctk.CTkFont(size=20, weight="bold")).pack(
            pady=(24, 4))
        ctk.CTkLabel(sidebar, text=config.get("shop_name", "POS"), text_color="gray",
                     font=ctk.CTkFont(size=11)).pack(pady=(0, 20))

        self.nav_buttons = {}
        for label, key in self.NAV_ITEMS:
            if key == "settings" and self.user.role != "admin":
                continue
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w", height=40, corner_radius=8,
                fg_color="transparent", hover_color=("gray80", "gray25"),
                command=lambda k=key: self.show(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        ctk.CTkLabel(sidebar, text=f"{self.user.username} ({self.user.role})",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 4))
        ctk.CTkButton(sidebar, text="Logout", fg_color="#a83232", hover_color="#832020",
                      height=34, command=self._logout).pack(fill="x", padx=12, pady=(0, 16))

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")

    def show(self, key: str):
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if k == key else "transparent")

        if self.current_frame is not None:
            self.current_frame.pack_forget()

        if key not in self.frame_cache:
            self.frame_cache[key] = self._build_frame(key)
        self.current_frame = self.frame_cache[key]
        self.current_frame.pack(fill="both", expand=True)

        if key == "home" and "home" in self.frame_cache:
            # Rebuild home each time so KPI numbers stay fresh
            self.frame_cache["home"].destroy()
            self.frame_cache["home"] = HomeView(self.content)
            self.current_frame = self.frame_cache["home"]
            self.current_frame.pack(fill="both", expand=True)

    def _build_frame(self, key: str):
        if key == "home":
            return HomeView(self.content)
        elif key == "billing":
            from ui.views import BillingView
            return BillingView(self.content, self.user)
        elif key == "products":
            from ui.views import ProductsView
            return ProductsView(self.content)
        elif key == "customers":
            from ui.views import CustomersView
            return CustomersView(self.content)
        elif key == "reports":
            from ui.views import ReportsView
            return ReportsView(self.content)
        elif key == "settings":
            from ui.views import SettingsView
            return SettingsView(self.content)
        raise ValueError(f"Unknown nav key: {key}")

    def _logout(self):
        auth.logout()
        backup_manager.create_backup()
        self.destroy()
        self.on_logout()
