"""
main.py
Application entry point. Flow:
  1. If database/shop.db doesn't exist -> show Setup Wizard (or Recovery Mode
     if backups/exports are present from a previous install).
  2. Otherwise -> initialize DB connection, show Login screen.
  3. On successful login -> show Dashboard.
On close, automatically creates a backup (per config "backup_on_exit").
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from database.db_manager import db
from modules.backup_manager import backup_manager
from utils.config_manager import config
from utils.logger import get_logger

logger = get_logger("main")

ctk.set_appearance_mode(config.get("theme", "dark"))
ctk.set_default_color_theme(config.get("color_theme", "blue"))


class ShopEaseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ShopEase POS")
        self.geometry("1200x760")
        self.minsize(1024, 640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not db.database_exists():
            self._start_first_run_flow()
        else:
            db.connect()
            self._show_login()

    # ------------------------------------------------------------------ #
    def _start_first_run_flow(self):
        from ui.recovery import RecoveryOrSetupScreen
        RecoveryOrSetupScreen(self, on_ready=self._show_login)

    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()
        db.initialize()  # idempotent; ensures schema is current
        from ui.login_window import LoginWindow
        LoginWindow(self, on_login_success=self._show_dashboard)

    def _show_dashboard(self, user):
        for w in self.winfo_children():
            w.destroy()
        from ui.dashboard import Dashboard
        Dashboard(self, user, on_logout=self._show_login)

    def _on_close(self):
        try:
            if config.get("backup_on_exit", True) and db.conn is not None:
                backup_manager.create_backup()
        except Exception as exc:
            logger.error("Backup on exit failed: %s", exc)
        finally:
            db.close()
            self.destroy()


def main():
    try:
        app = ShopEaseApp()
        app.mainloop()
    except Exception as exc:
        logger.exception("Fatal error")
        try:
            messagebox.showerror("ShopEase POS - Fatal Error", f"An unexpected error occurred:\n{exc}")
        except tk.TclError:
            print(f"Fatal error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
