"""
database/db_manager.py
Single point of access to the SQLite database (database/shop.db).

Design notes:
- One shared connection with WAL journal mode for good concurrent read
  performance and check_same_thread=False so the Tkinter main thread and any
  background worker threads can share it safely (writes are still serialized
  by SQLite itself).
- Row factory returns sqlite3.Row so callers can access columns by name.
- initialize() applies schema.sql idempotently (CREATE TABLE IF NOT EXISTS).
- All higher-level modules (ProductManager, CustomerManager, ...) go through
  this class instead of opening their own connections.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

from utils.logger import get_logger

logger = get_logger("database")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "shop.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


class DatabaseManager:
    """Wraps a single SQLite connection and exposes safe query helpers."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls, *args, **kwargs):
        # Simple singleton so every module shares one connection/db file.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = DB_PATH):
        if getattr(self, "_initialized", False):
            return
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._initialized = True

    # ---------------------------------------------------------------- #
    # Connection lifecycle
    # ---------------------------------------------------------------- #
    def database_exists(self) -> bool:
        return os.path.exists(self.db_path)

    def connect(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        logger.info("Connected to database at %s", self.db_path)

    def initialize(self) -> None:
        """Create the connection (if needed) and apply the schema."""
        if self.conn is None:
            self.connect()
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        self.conn.executescript(schema_sql)
        self.conn.commit()
        logger.info("Schema applied/verified successfully.")

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    # ---------------------------------------------------------------- #
    # Generic helpers used by manager classes
    # ---------------------------------------------------------------- #
    def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE and commit. Returns the cursor
        (use .lastrowid for inserts)."""
        try:
            with self.cursor() as cur:
                cur.execute(query, params)
                self.conn.commit()
                return cur
        except sqlite3.Error as exc:
            logger.error("execute failed: %s | query=%s | params=%s", exc, query, params)
            raise

    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
        try:
            with self.cursor() as cur:
                cur.executemany(query, seq_of_params)
                self.conn.commit()
        except sqlite3.Error as exc:
            logger.error("executemany failed: %s | query=%s", exc, query)
            raise

    def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        try:
            with self.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        except sqlite3.Error as exc:
            logger.error("fetchone failed: %s | query=%s | params=%s", exc, query, params)
            raise

    def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        try:
            with self.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except sqlite3.Error as exc:
            logger.error("fetchall failed: %s | query=%s | params=%s", exc, query, params)
            raise


# Module-level singleton used throughout the app.
db = DatabaseManager()
