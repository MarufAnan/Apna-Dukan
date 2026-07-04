"""
modules/billing_manager.py
Cart + checkout logic. A Cart is built in-memory during billing; checkout()
persists the bill + bill_items atomically, reduces stock, updates customer
history, and returns the bill_id + invoice_number for PDF generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.db_manager import db
from modules.product_manager import products
from modules.customer_manager import customers
from utils.config_manager import config
from utils.logger import get_logger

logger = get_logger("billing")


@dataclass
class CartItem:
    product_id: int | None
    name: str
    quantity: float
    unit_price: float
    gst_percent: float
    discount: float = 0.0

    @property
    def line_total(self) -> float:
        base = self.quantity * self.unit_price
        base -= self.discount
        gst_amt = base * (self.gst_percent / 100)
        return round(base + gst_amt, 2)


@dataclass
class Cart:
    items: list[CartItem] = field(default_factory=list)
    customer_id: int | None = None
    overall_discount: float = 0.0
    payment_method: str = "Cash"
    price_mode: str = "retail"

    def add_item(self, item: CartItem) -> None:
        for existing in self.items:
            if existing.product_id == item.product_id and item.product_id is not None:
                existing.quantity += item.quantity
                return
        self.items.append(item)

    def remove_item(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def update_quantity(self, index: int, quantity: float) -> None:
        if 0 <= index < len(self.items):
            self.items[index].quantity = quantity

    def clear(self) -> None:
        self.items.clear()
        self.customer_id = None
        self.overall_discount = 0.0

    @property
    def subtotal(self) -> float:
        return round(sum(i.quantity * i.unit_price for i in self.items), 2)

    @property
    def gst_total(self) -> float:
        total = 0.0
        for i in self.items:
            base = i.quantity * i.unit_price - i.discount
            total += base * (i.gst_percent / 100)
        return round(total, 2)

    @property
    def grand_total(self) -> float:
        total = sum(i.line_total for i in self.items) - self.overall_discount
        return round(max(total, 0), 2)


class BillingManager:
    def generate_invoice_number(self) -> str:
        prefix = config.get("invoice_prefix", "INV")
        today = datetime.now().strftime("%Y%m%d")
        row = db.fetchone(
            "SELECT COUNT(*) AS c FROM bills WHERE invoice_number LIKE ?",
            (f"{prefix}-{today}-%",),
        )
        seq = (row["c"] or 0) + 1
        return f"{prefix}-{today}-{seq:04d}"

    def checkout(self, cart: Cart, created_by: int | None = None) -> dict:
        if not cart.items:
            raise ValueError("Cannot checkout an empty cart")

        invoice_number = self.generate_invoice_number()
        subtotal = cart.subtotal
        gst_amount = cart.gst_total
        grand_total = cart.grand_total

        cur = db.execute(
            """INSERT INTO bills (invoice_number, customer_id, subtotal, discount,
                                   gst_amount, grand_total, payment_method, price_mode, created_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (invoice_number, cart.customer_id, subtotal, cart.overall_discount,
             gst_amount, grand_total, cart.payment_method, cart.price_mode, created_by),
        )
        bill_id = cur.lastrowid

        rows = [
            (bill_id, i.product_id, i.name, i.quantity, i.unit_price,
             i.gst_percent, i.discount, i.line_total)
            for i in cart.items
        ]
        db.executemany(
            """INSERT INTO bill_items
               (bill_id, product_id, product_name, quantity, unit_price, gst_percent, discount, line_total)
               VALUES (?,?,?,?,?,?,?,?)""",
            rows,
        )

        for item in cart.items:
            if item.product_id is not None:
                products.adjust_stock(item.product_id, -int(item.quantity), "sale", invoice_number)

        if cart.customer_id is not None:
            due = grand_total if cart.payment_method.lower() == "credit" else 0.0
            customers.record_visit(cart.customer_id, due)

        logger.info("Checkout complete: %s total=%.2f items=%d", invoice_number, grand_total, len(cart.items))
        return {
            "bill_id": bill_id,
            "invoice_number": invoice_number,
            "subtotal": subtotal,
            "discount": cart.overall_discount,
            "gst_amount": gst_amount,
            "grand_total": grand_total,
        }

    def cancel_bill(self, bill_id: int, restock: bool = True) -> None:
        items = db.fetchall("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,))
        if restock:
            for it in items:
                if it["product_id"] is not None:
                    products.adjust_stock(it["product_id"], int(it["quantity"]), "return", f"cancel-bill-{bill_id}")
        db.execute("UPDATE bills SET is_cancelled = 1 WHERE id = ?", (bill_id,))
        logger.info("Bill %s cancelled (restock=%s)", bill_id, restock)

    def get_bill(self, bill_id: int) -> dict | None:
        bill = db.fetchone("SELECT * FROM bills WHERE id = ?", (bill_id,))
        if not bill:
            return None
        items = db.fetchall("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,))
        result = dict(bill)
        result["items"] = [dict(i) for i in items]
        return result

    def recent_bills(self, limit: int = 20) -> list[dict]:
        rows = db.fetchall(
            """SELECT b.id, b.invoice_number, b.bill_date, b.grand_total, b.payment_method,
                      COALESCE(c.name, 'Walk-in') AS customer_name
               FROM bills b LEFT JOIN customers c ON c.id = b.customer_id
               WHERE b.is_cancelled = 0 ORDER BY b.id DESC LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]


billing = BillingManager()
