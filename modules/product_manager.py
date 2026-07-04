"""
modules/product_manager.py
Business logic for products: CRUD, search, barcode lookup, stock updates,
and low-stock alerts. UI code (ui/views.py) calls into this class only -
it never touches SQL directly, keeping business logic and presentation separate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from database.db_manager import db
from utils.logger import get_logger

logger = get_logger("products")


@dataclass
class Product:
    id: int | None
    barcode: str
    name: str
    category: str
    brand: str
    purchase_price: float
    retail_price: float
    wholesale_price: float
    gst_percent: float
    stock: int
    min_stock: int
    rack_location: str = ""
    remarks: str = ""
    supplier_id: int | None = None


class ProductManager:
    def add_product(self, p: Product) -> int:
        cur = db.execute(
            """INSERT INTO products
               (barcode, name, category, brand, purchase_price, retail_price,
                wholesale_price, gst_percent, stock, min_stock, rack_location,
                remarks, supplier_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p.barcode or None, p.name, p.category, p.brand, p.purchase_price,
             p.retail_price, p.wholesale_price, p.gst_percent, p.stock,
             p.min_stock, p.rack_location, p.remarks, p.supplier_id),
        )
        product_id = cur.lastrowid
        if p.stock:
            self._log_stock_change(product_id, "purchase", p.stock, "Initial stock")
        logger.info("Product added: %s (id=%s)", p.name, product_id)
        return product_id

    def update_product(self, product_id: int, **fields) -> None:
        if not fields:
            return
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [product_id]
        db.execute(
            f"UPDATE products SET {columns}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        logger.info("Product %s updated: %s", product_id, list(fields.keys()))

    def delete_product(self, product_id: int) -> None:
        db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        logger.info("Product %s soft-deleted", product_id)

    def get_by_id(self, product_id: int) -> dict | None:
        row = db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        return dict(row) if row else None

    def get_by_barcode(self, barcode: str) -> dict | None:
        row = db.fetchone(
            "SELECT * FROM products WHERE barcode = ? AND is_active = 1", (barcode,)
        )
        return dict(row) if row else None

    def search(self, term: str = "", category: str = "", limit: int = 200) -> list[dict]:
        query = "SELECT * FROM products WHERE is_active = 1"
        params: list = []
        if term:
            query += " AND (name LIKE ? OR barcode LIKE ? OR brand LIKE ?)"
            like = f"%{term}%"
            params += [like, like, like]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY name LIMIT ?"
        params.append(limit)
        rows = db.fetchall(query, params)
        return [dict(r) for r in rows]

    def list_categories(self) -> list[str]:
        rows = db.fetchall(
            "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        return [r["category"] for r in rows]

    def low_stock(self) -> list[dict]:
        rows = db.fetchall(
            "SELECT * FROM products WHERE is_active = 1 AND stock <= min_stock ORDER BY stock ASC"
        )
        return [dict(r) for r in rows]

    def adjust_stock(self, product_id: int, delta: int, change_type: str, reference: str = "") -> None:
        """delta is positive for increases (purchase/return), negative for sales."""
        db.execute("UPDATE products SET stock = stock + ?, updated_at = datetime('now') WHERE id = ?",
                   (delta, product_id))
        self._log_stock_change(product_id, change_type, delta, reference)

    def _log_stock_change(self, product_id: int, change_type: str, delta: int, reference: str) -> None:
        db.execute(
            "INSERT INTO stock_history (product_id, change_type, quantity_change, reference) VALUES (?,?,?,?)",
            (product_id, change_type, delta, reference),
        )

    def stock_value(self) -> dict:
        row = db.fetchone(
            """SELECT COALESCE(SUM(stock * purchase_price), 0) AS cost_value,
                      COALESCE(SUM(stock * retail_price), 0) AS retail_value,
                      COALESCE(SUM(stock), 0) AS total_units
               FROM products WHERE is_active = 1"""
        )
        return dict(row)

    def count(self) -> int:
        row = db.fetchone("SELECT COUNT(*) AS c FROM products WHERE is_active = 1")
        return row["c"]


products = ProductManager()
