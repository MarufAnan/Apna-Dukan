"""
modules/report_manager.py
Aggregation queries backing the Dashboard and Reports screens: sales by
period, profit, GST collected, top products/customers, inventory value,
and expense totals. Pure data layer - charts are built in ui/views.py
using matplotlib from the dicts/lists returned here.
"""
from __future__ import annotations

from database.db_manager import db


class ReportManager:
    def sales_summary(self, period: str = "today") -> dict:
        """period: today | week | month | year"""
        date_filter = {
            "today": "date(bill_date) = date('now')",
            "week": "bill_date >= date('now', '-7 days')",
            "month": "strftime('%Y-%m', bill_date) = strftime('%Y-%m', 'now')",
            "year": "strftime('%Y', bill_date) = strftime('%Y', 'now')",
        }.get(period, "date(bill_date) = date('now')")

        row = db.fetchone(
            f"""SELECT COALESCE(SUM(grand_total), 0) AS total_sales,
                       COALESCE(SUM(gst_amount), 0) AS total_gst,
                       COUNT(*) AS bill_count
                FROM bills WHERE is_cancelled = 0 AND {date_filter}"""
        )
        return dict(row)

    def profit_report(self, period: str = "month") -> dict:
        date_filter = {
            "today": "date(b.bill_date) = date('now')",
            "week": "b.bill_date >= date('now', '-7 days')",
            "month": "strftime('%Y-%m', b.bill_date) = strftime('%Y-%m', 'now')",
            "year": "strftime('%Y', b.bill_date) = strftime('%Y', 'now')",
        }.get(period, "strftime('%Y-%m', b.bill_date) = strftime('%Y-%m', 'now')")

        row = db.fetchone(
            f"""SELECT
                    COALESCE(SUM(bi.line_total), 0) AS revenue,
                    COALESCE(SUM(bi.quantity * p.purchase_price), 0) AS cost
                FROM bill_items bi
                JOIN bills b ON b.id = bi.bill_id AND b.is_cancelled = 0
                LEFT JOIN products p ON p.id = bi.product_id
                WHERE {date_filter}"""
        )
        result = dict(row)
        result["profit"] = round(result["revenue"] - result["cost"], 2)
        return result

    def daily_sales_series(self, days: int = 30) -> list[dict]:
        rows = db.fetchall(
            f"""SELECT date(bill_date) AS day, SUM(grand_total) AS total
                FROM bills WHERE is_cancelled = 0 AND bill_date >= date('now', ?)
                GROUP BY day ORDER BY day""",
            (f"-{days} days",),
        )
        return [dict(r) for r in rows]

    def top_products(self, limit: int = 10, period: str = "month") -> list[dict]:
        date_filter = {
            "today": "date(b.bill_date) = date('now')",
            "week": "b.bill_date >= date('now', '-7 days')",
            "month": "strftime('%Y-%m', b.bill_date) = strftime('%Y-%m', 'now')",
            "year": "strftime('%Y', b.bill_date) = strftime('%Y', 'now')",
            "all": "1=1",
        }.get(period, "1=1")
        rows = db.fetchall(
            f"""SELECT bi.product_name, SUM(bi.quantity) AS qty_sold,
                       SUM(bi.line_total) AS revenue
                FROM bill_items bi JOIN bills b ON b.id = bi.bill_id AND b.is_cancelled = 0
                WHERE {date_filter}
                GROUP BY bi.product_name ORDER BY qty_sold DESC LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]

    def gst_report(self, period: str = "month") -> dict:
        return self.sales_summary(period)

    def expense_summary(self, period: str = "month") -> dict:
        date_filter = {
            "today": "date(expense_date) = date('now')",
            "week": "expense_date >= date('now', '-7 days')",
            "month": "strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')",
            "year": "strftime('%Y', expense_date) = strftime('%Y', 'now')",
        }.get(period, "strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')")
        row = db.fetchone(
            f"SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE {date_filter}"
        )
        return dict(row)

    def add_expense(self, title: str, amount: float, category: str = "", notes: str = "") -> int:
        cur = db.execute(
            "INSERT INTO expenses (title, category, amount, notes) VALUES (?,?,?,?)",
            (title, category, amount, notes),
        )
        return cur.lastrowid

    def list_expenses(self, limit: int = 100) -> list[dict]:
        rows = db.fetchall("SELECT * FROM expenses ORDER BY expense_date DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]


reports = ReportManager()
