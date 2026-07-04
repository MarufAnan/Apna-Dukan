"""
modules/backup_manager.py
Creates timestamped SQLite backups + fresh Excel exports (Products/Customers/Bills)
on every app exit, and supports restoring from a backup file. Also implements
Recovery Mode helpers used when shop.db is missing at startup.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from database.db_manager import db, DB_PATH
from modules.excel_manager import excel_manager
from utils.logger import get_logger

logger = get_logger("backup")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


class BackupManager:
    def create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = os.path.join(BACKUP_DIR, timestamp)
        os.makedirs(backup_subdir, exist_ok=True)

        db_backup_path = os.path.join(backup_subdir, "shop.db")
        try:
            if db.conn is not None:
                # Use SQLite's online backup API for a consistent snapshot
                import sqlite3
                dest = sqlite3.connect(db_backup_path)
                db.conn.backup(dest)
                dest.close()
            else:
                shutil.copy2(DB_PATH, db_backup_path)
        except Exception as exc:
            logger.error("Database backup failed: %s", exc)

        try:
            excel_manager.export_products(os.path.join(backup_subdir, "Products.xlsx"))
            excel_manager.export_customers(os.path.join(backup_subdir, "Customers.xlsx"))
            excel_manager.export_bills(os.path.join(backup_subdir, "Bills.xlsx"))
        except Exception as exc:
            logger.error("Excel export during backup failed: %s", exc)

        logger.info("Backup created at %s", backup_subdir)
        self._prune_old_backups(keep=20)
        return backup_subdir

    def _prune_old_backups(self, keep: int = 20) -> None:
        try:
            entries = sorted(
                (d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))),
                reverse=True,
            )
            for old in entries[keep:]:
                shutil.rmtree(os.path.join(BACKUP_DIR, old), ignore_errors=True)
        except OSError as exc:
            logger.warning("Backup pruning failed: %s", exc)

    def list_backups(self) -> list[str]:
        if not os.path.exists(BACKUP_DIR):
            return []
        return sorted(
            (d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))),
            reverse=True,
        )

    def restore_backup(self, backup_name: str) -> bool:
        src = os.path.join(BACKUP_DIR, backup_name, "shop.db")
        if not os.path.exists(src):
            logger.error("Backup database not found: %s", src)
            return False
        db.close()
        shutil.copy2(src, DB_PATH)
        db.connect()
        logger.info("Database restored from backup %s", backup_name)
        return True


backup_manager = BackupManager()
