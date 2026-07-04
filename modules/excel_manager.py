"""
modules/excel_manager.py
All Excel I/O goes through here (openpyxl/pandas). Used by the setup wizard
(initial import), settings screen (ongoing import/export), and backup manager
(automatic export on exit).
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd

from database.db_manager import db
from utils.logger import get_logger

logger = get_logger("excel")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

PRODUCT_COLUMNS = {
    "barcode": "Barcode", "name": "Product Name", "category": "Category",
    "brand": "Brand", "purchase_price": "Purchase Price", "retail_price": "Retail Price",
    "wholesale_price": "Wholesale Price", "gst_percent": "GST", "stock": "Stock",
    "min_stock": "Minimum Stock", "rack_location": "Rack Location", "remarks": "Remarks",
}
CUSTOMER_COLUMNS = {
    "name": "Name", "phone": "Phone", "email": "Email", "address": "Address",
    "gst_number": "GST", "pending_amount": "Pending Amount",
}


class ExcelManager:
    # ------------------------------------------------------------------ #
    # Import
    # ------------------------------------------------------------------ #
    def import_products(self, file_path: str) -> int:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        reverse_map = {v: k for k, v in PRODUCT_COLUMNS.items()}
        df = df.rename(columns=reverse_map)

        count = 0
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            if not name or name.lower() == "nan":
                continue
            barcode = str(row.get("barcode", "")).strip()
            barcode = None if barcode.lower() in ("", "nan") else barcode
            try:
                db.execute(
                    """INSERT INTO products
                       (barcode, name, category, brand, purchase_price, retail_price,
                        wholesale_price, gst_percent, stock, min_stock, rack_location, remarks)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(barcode) DO UPDATE SET
                          name=excluded.name, category=excluded.category, brand=excluded.brand,
                          purchase_price=excluded.purchase_price, retail_price=excluded.retail_price,
                          wholesale_price=excluded.wholesale_price, gst_percent=excluded.gst_percent,
                          stock=excluded.stock, min_stock=excluded.min_stock,
                          rack_location=excluded.rack_location, remarks=excluded.remarks""",
                    (
                        barcode, name,
                        _clean(row.get("category")), _clean(row.get("brand")),
                        _num(row.get("purchase_price")), _num(row.get("retail_price")),
                        _num(row.get("wholesale_price")), _num(row.get("gst_percent")),
                        int(_num(row.get("stock"))), int(_num(row.get("min_stock", 5)) or 5),
                        _clean(row.get("rack_location")), _clean(row.get("remarks")),
                    ),
                )
                count += 1
            except Exception as exc:
                logger.warning("Skipping product row (%s): %s", name, exc)
        logger.info("Imported %d products from %s", count, file_path)
        return count

    def import_customers(self, file_path: str) -> int:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        reverse_map = {v: k for k, v in CUSTOMER_COLUMNS.items()}
        df = df.rename(columns=reverse_map)

        count = 0
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            if not name or name.lower() == "nan":
                continue
            phone = str(row.get("phone", "")).strip()
            phone = None if phone.lower() in ("", "nan") else phone
            try:
                db.execute(
                    """INSERT INTO customers (name, phone, email, address, gst_number, pending_amount)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(phone) DO UPDATE SET
                          name=excluded.name, email=excluded.email, address=excluded.address,
                          gst_number=excluded.gst_number""",
                    (name, phone, _clean(row.get("email")), _clean(row.get("address")),
                     _clean(row.get("gst_number")), _num(row.get("pending_amount"))),
                )
                count += 1
            except Exception as exc:
                logger.warning("Skipping customer row (%s): %s", name, exc)
        logger.info("Imported %d customers from %s", count, file_path)
        return count

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def export_products(self, file_path: str | None = None) -> str:
        rows = db.fetchall("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
        df = pd.DataFrame([dict(r) for r in rows])
        if not df.empty:
            df = df[[c for c in PRODUCT_COLUMNS if c in df.columns]]
            df = df.rename(columns=PRODUCT_COLUMNS)
        path = file_path or os.path.join(EXPORT_DIR, "Products.xlsx")
        df.to_excel(path, index=False)
        logger.info("Exported %d products to %s", len(df), path)
        return path

    def export_customers(self, file_path: str | None = None) -> str:
        rows = db.fetchall("SELECT * FROM customers ORDER BY name")
        df = pd.DataFrame([dict(r) for r in rows])
        if not df.empty:
            df = df[[c for c in CUSTOMER_COLUMNS if c in df.columns]]
            df = df.rename(columns=CUSTOMER_COLUMNS)
        path = file_path or os.path.join(EXPORT_DIR, "Customers.xlsx")
        df.to_excel(path, index=False)
        logger.info("Exported %d customers to %s", len(df), path)
        return path

    def export_bills(self, file_path: str | None = None) -> str:
        rows = db.fetchall(
            """SELECT b.invoice_number AS "Invoice", b.bill_date AS "Date",
                      COALESCE(c.name, 'Walk-in') AS "Customer", b.subtotal AS "Subtotal",
                      b.discount AS "Discount", b.gst_amount AS "GST", b.grand_total AS "Total",
                      b.payment_method AS "Payment Method"
               FROM bills b LEFT JOIN customers c ON c.id = b.customer_id
               WHERE b.is_cancelled = 0 ORDER BY b.bill_date DESC"""
        )
        df = pd.DataFrame([dict(r) for r in rows])
        path = file_path or os.path.join(EXPORT_DIR, "Bills.xlsx")
        df.to_excel(path, index=False)
        logger.info("Exported %d bills to %s", len(df), path)
        return path


def _clean(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def _num(val) -> float:
    try:
        f = float(val)
        return 0.0 if f != f else f  # NaN check
    except (TypeError, ValueError):
        return 0.0


excel_manager = ExcelManager()
