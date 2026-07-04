"""
ui/recovery.py
Shown when database/shop.db is missing. If prior backups exist (e.g. the
.db file was deleted but backups/ still has snapshots), offers Recovery
Mode (restore backup or re-import Excel) instead of forcing a brand-new
setup wizard.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from modules.backup_manager import backup_manager
from database.db_manager import db
from utils.logger import get_logger

logger = get_logger("recovery")


class RecoveryOrSetupScreen(ctk.CTkFrame):
    def __init__(self, master, on_ready):
        super().__init__(master, fg_color="transparent")
        self.master_window = master
        self.on_ready = on_ready
        self.pack(fill="both", expand=True)

        backups = backup_manager.list_backups()
        if backups:
            self._build_recovery_ui(backups)
        else:
            self._launch_setup_wizard()

    def _build_recovery_ui(self, backups: list[str]):
        container = ctk.CTkFrame(self, width=460, height=320, corner_radius=16)
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        ctk.CTkLabel(container, text="Database Not Found", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(30, 6))
        ctk.CTkLabel(container, text="We found previous backups. What would you like to do?",
                     text_color="gray", wraplength=380, justify="center").pack(pady=(0, 20))

        ctk.CTkButton(container, text="Restore Latest Backup", width=280, height=42,
                      command=lambda: self._restore(backups[0])).pack(pady=6)
        ctk.CTkButton(container, text="Import from Excel (Fresh Setup)", width=280, height=42,
                      fg_color="transparent", border_width=1,
                      command=self._launch_setup_wizard).pack(pady=6)

    def _restore(self, backup_name: str):
        try:
            db.connect()
            db.initialize()
            if backup_manager.restore_backup(backup_name):
                messagebox.showinfo("Restored", f"Database restored from backup: {backup_name}")
                for w in self.master_window.winfo_children():
                    w.destroy()
                self.on_ready()
            else:
                messagebox.showerror("Restore Failed", "Could not restore the selected backup.")
        except Exception as exc:
            logger.exception("Restore failed")
            messagebox.showerror("Restore Failed", str(exc))

    def _launch_setup_wizard(self):
        for w in self.winfo_children():
            w.destroy()
        from ui.setup_wizard import SetupWizard

        def _complete():
            for w in self.master_window.winfo_children():
                w.destroy()
            self.on_ready()

        SetupWizard(self.master_window, on_complete=_complete)
