"""
modules/invoice_generator.py
Generates a professional PDF invoice using reportlab, saves it under
invoices/<invoice_number>.pdf, and records it in invoice_history.
Also provides an optional Windows print via pywin32 (no-op on other OSes).
"""
from __future__ import annotations

import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                 Spacer, Image)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from database.db_manager import db
from utils.config_manager import config
from utils.logger import get_logger

logger = get_logger("invoice")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVOICE_DIR = os.path.join(BASE_DIR, "invoices")
os.makedirs(INVOICE_DIR, exist_ok=True)


class InvoiceGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name="ShopTitle", fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=2))
        self.styles.add(ParagraphStyle(
            name="ShopSub", fontSize=8.5, leading=11, alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(
            name="InvoiceMeta", fontSize=8.5, leading=12))
        self.styles.add(ParagraphStyle(
            name="RightBold", fontSize=10, alignment=TA_RIGHT, fontName="Helvetica-Bold"))

    def generate(self, bill: dict, customer: dict | None) -> str:
        """bill: result of BillingManager.get_bill(). Returns the PDF path."""
        invoice_number = bill["invoice_number"]
        pdf_path = os.path.join(INVOICE_DIR, f"{invoice_number}.pdf")
        currency = config.get("currency_symbol", "Rs.")

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A5,
            topMargin=10 * mm, bottomMargin=10 * mm,
            leftMargin=10 * mm, rightMargin=10 * mm,
        )
        story = []

        logo_path = config.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            try:
                story.append(Image(logo_path, width=25 * mm, height=25 * mm))
            except Exception as exc:
                logger.warning("Could not embed logo: %s", exc)

        story.append(Paragraph(config.get("shop_name", "My Shop"), self.styles["ShopTitle"]))
        sub_lines = [config.get("address", ""), f"Phone: {config.get('phone', '')}"]
        if config.get("gst_number"):
            sub_lines.append(f"GSTIN: {config.get('gst_number')}")
        story.append(Paragraph(" | ".join([s for s in sub_lines if s]), self.styles["ShopSub"]))
        story.append(Spacer(1, 6))

        meta_table = Table(
            [
                [Paragraph(f"<b>Invoice #:</b> {invoice_number}", self.styles["InvoiceMeta"]),
                 Paragraph(f"<b>Date:</b> {bill['bill_date']}", self.styles["InvoiceMeta"])],
                [Paragraph(f"<b>Customer:</b> {customer['name'] if customer else 'Walk-in'}", self.styles["InvoiceMeta"]),
                 Paragraph(f"<b>Phone:</b> {customer['phone'] if customer else '-'}", self.styles["InvoiceMeta"])],
                [Paragraph(f"<b>Payment:</b> {bill['payment_method']}", self.styles["InvoiceMeta"]),
                 Paragraph(f"<b>Price Mode:</b> {bill['price_mode'].title()}", self.styles["InvoiceMeta"])],
            ],
            colWidths=[65 * mm, 65 * mm],
        )
        story.append(meta_table)
        story.append(Spacer(1, 8))

        item_rows = [["#", "Item", "Qty", "Price", "GST%", "Disc.", "Total"]]
        for idx, item in enumerate(bill["items"], start=1):
            item_rows.append([
                str(idx), item["product_name"], f"{item['quantity']:g}",
                f"{currency}{item['unit_price']:.2f}", f"{item['gst_percent']:g}",
                f"{currency}{item['discount']:.2f}", f"{currency}{item['line_total']:.2f}",
            ])
        items_table = Table(item_rows, colWidths=[8*mm, 40*mm, 12*mm, 18*mm, 12*mm, 15*mm, 20*mm])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b2b2b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 8))

        totals_rows = [
            ["Subtotal", f"{currency}{bill['subtotal']:.2f}"],
            ["Discount", f"{currency}{bill['discount']:.2f}"],
            ["GST", f"{currency}{bill['gst_amount']:.2f}"],
            ["Grand Total", f"{currency}{bill['grand_total']:.2f}"],
        ]
        totals_table = Table(totals_rows, colWidths=[100 * mm, 25 * mm])
        totals_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
            ("LINEABOVE", (0, 3), (-1, 3), 0.6, colors.black),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 14))
        story.append(Paragraph("Thank you for shopping with us!", self.styles["ShopSub"]))

        doc.build(story)

        db.execute(
            "INSERT INTO invoice_history (bill_id, pdf_path) VALUES (?, ?)",
            (bill["id"], pdf_path),
        )
        db.execute("UPDATE bills SET pdf_path = ? WHERE id = ?", (pdf_path, bill["id"]))
        logger.info("Invoice PDF generated: %s", pdf_path)
        return pdf_path

    def print_pdf(self, pdf_path: str, printer_name: str | None = None) -> bool:
        """Best-effort silent print on Windows via the default PDF handler."""
        if sys.platform != "win32":
            logger.warning("Printing is only supported on Windows in this build.")
            return False
        try:
            import win32api  # type: ignore
            win32api.ShellExecute(0, "print", pdf_path, f'"{printer_name}"' if printer_name else None, ".", 0)
            return True
        except Exception as exc:
            logger.error("Print failed: %s", exc)
            return False


invoice_generator = InvoiceGenerator()
