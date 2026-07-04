"""
ui/login_window.py
Login screen shown every time the app starts (after setup is complete).
Verifies credentials via AuthManager and hands off to the Dashboard.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from modules.auth_manager import auth
from utils.config_manager import config


class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success
        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, width=380, height=420, corner_radius=16)
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        ctk.CTkLabel(container, text="ShopEase POS", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(36, 4))
        shop_name = config.get("shop_name", "")
        if shop_name:
            ctk.CTkLabel(container, text=shop_name, text_color="gray").pack(pady=(0, 20))
        else:
            ctk.CTkLabel(container, text="").pack(pady=(0, 20))

        self.username_entry = ctk.CTkEntry(container, placeholder_text="Username", width=280, height=40)
        self.username_entry.pack(pady=8)
        self.password_entry = ctk.CTkEntry(container, placeholder_text="Password", show="*", width=280, height=40)
        self.password_entry.pack(pady=8)
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        self.error_label = ctk.CTkLabel(container, text="", text_color="#e05555")
        self.error_label.pack(pady=(4, 0))

        ctk.CTkButton(container, text="Login", width=280, height=40,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._attempt_login).pack(pady=16)

        self.username_entry.focus_set()

    def _attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            self.error_label.configure(text="Please enter username and password.")
            return
        user = auth.login(username, password)
        if user:
            self.destroy()
            self.on_login_success(user)
        else:
            self.error_label.configure(text="Invalid username or password.")
            self.password_entry.delete(0, "end")
