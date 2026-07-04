"""
modules/auth_manager.py
Handles user accounts, password hashing (PBKDF2, stdlib only - no extra
dependency needed), login verification, role checks and activity logging.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from database.db_manager import db
from utils.logger import get_logger

logger = get_logger("auth")

_ITERATIONS = 200_000


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


@dataclass
class User:
    id: int
    username: str
    role: str
    full_name: str
    is_active: bool


class AuthManager:
    """Manages login, user CRUD, and lightweight audit logging."""

    def __init__(self):
        self.current_user: User | None = None

    def create_default_admin(self, username: str, password: str, full_name: str = "Owner") -> None:
        existing = db.fetchone("SELECT id FROM users WHERE role = 'admin'")
        if existing:
            return
        db.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, 'admin', ?)",
            (username, _hash_password(password), full_name),
        )
        logger.info("Default admin account created: %s", username)

    def add_user(self, username: str, password: str, role: str, full_name: str = "") -> int:
        if role not in ("admin", "staff"):
            raise ValueError("role must be 'admin' or 'staff'")
        cur = db.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            (username, _hash_password(password), role, full_name),
        )
        return cur.lastrowid

    def change_password(self, user_id: int, new_password: str) -> None:
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_id),
        )
        self.log_activity(user_id, "password_change", "User changed password")

    def deactivate_user(self, user_id: int) -> None:
        db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))

    def list_users(self) -> list[dict]:
        rows = db.fetchall("SELECT id, username, role, full_name, is_active, last_login FROM users ORDER BY id")
        return [dict(r) for r in rows]

    def login(self, username: str, password: str) -> User | None:
        row = db.fetchone(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        )
        if row and _verify_password(password, row["password_hash"]):
            db.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (row["id"],))
            user = User(row["id"], row["username"], row["role"], row["full_name"] or "", True)
            self.current_user = user
            self.log_activity(user.id, "login", f"{username} logged in")
            return user
        logger.warning("Failed login attempt for username=%s", username)
        return None

    def logout(self) -> None:
        if self.current_user:
            self.log_activity(self.current_user.id, "logout", f"{self.current_user.username} logged out")
        self.current_user = None

    def log_activity(self, user_id: int | None, action: str, details: str = "") -> None:
        try:
            db.execute(
                "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details),
            )
        except Exception as exc:  # never let logging break the app
            logger.error("Failed to write activity log: %s", exc)

    def get_activity_logs(self, limit: int = 200) -> list[dict]:
        rows = db.fetchall(
            """SELECT al.id, u.username, al.action, al.details, al.created_at
               FROM activity_logs al LEFT JOIN users u ON u.id = al.user_id
               ORDER BY al.id DESC LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]


auth = AuthManager()
