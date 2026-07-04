"""
modules/customer_manager.py
Business logic for customers: CRUD, search, purchase history / ledger,
and pending-amount tracking (for credit sales).
"""
from __future__ import annotations

from dataclasses import dataclass

from database.db_manager import db
from utils.logger import get_logger

logger = get_logger("customers")


@dataclass
class Customer:
    id: int | None
    name: str
    phone: str
    email: str = ""
    address: str = ""
    gst_number: str = ""


class CustomerManager:
    def add_customer(self, c: Customer) -> int:
        cur = db.execute(
            "INSERT INTO customers (name, phone, email, address, gst_number) VALUES (?,?,?,?,?)",
            (c.name, c.phone or None, c.email, c.address, c.gst_number),
        )
        logger.info("Customer added: %s (id=%s)", c.name, cur.lastrowid)
        return cur.lastrowid

    def update_customer(self, customer_id: int, **fields) -> None:
        if not fields:
            return
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [customer_id]
        db.execute(f"UPDATE customers SET {columns} WHERE id = ?", values)

    def delete_customer(self, customer_id: int) -> None:
        db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

    def get_by_id(self, customer_id: int) -> dict | None:
        row = db.fetchone("SELECT * FROM customers WHERE id = ?", (customer_id,))
        return dict(row) if row else None

    def get_by_phone(self, phone: str) -> dict | None:
        row = db.fetchone("SELECT * FROM customers WHERE phone = ?", (phone,))
        return dict(row) if row else None

    def search(self, term: str = "", limit: int = 200) -> list[dict]:
        if term:
            like = f"%{term}%"
            rows = db.fetchall(
                "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT ?",
                (like, like, limit),
            )
        else:
            rows = db.fetchall("SELECT * FROM customers ORDER BY name LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def record_visit(self, customer_id: int, amount_due: float = 0.0) -> None:
        db.execute(
            "UPDATE customers SET last_visit = datetime('now'), pending_amount = pending_amount + ? WHERE id = ?",
            (amount_due, customer_id),
        )

    def get_ledger(self, customer_id: int) -> list[dict]:
        rows = db.fetchall(
            """SELECT invoice_number, bill_date, grand_total, payment_method
               FROM bills WHERE customer_id = ? AND is_cancelled = 0
               ORDER BY bill_date DESC""",
            (customer_id,),
        )
        return [dict(r) for r in rows]

    def total_customers(self) -> int:
        row = db.fetchone("SELECT COUNT(*) AS c FROM customers")
        return row["c"]

    def top_customers(self, limit: int = 10) -> list[dict]:
        rows = db.fetchall(
            """SELECT c.id, c.name, c.phone, COUNT(b.id) AS bill_count,
                      COALESCE(SUM(b.grand_total), 0) AS total_spent
               FROM customers c JOIN bills b ON b.customer_id = c.id AND b.is_cancelled = 0
               GROUP BY c.id ORDER BY total_spent DESC LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]


customers = CustomerManager()
