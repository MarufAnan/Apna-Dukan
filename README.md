# Apna Dukan

Offline Billing & Inventory Management Software for small shops (mobile accessories, electronics, sewing accessories, general retail). 100% local: SQLite database, no internet required, Excel used only for import/export.

---

## Features implemented in this build

* First-run Setup Wizard (shop details, admin login, optional Excel import)
* Login system with Admin/Staff roles and activity logging
* Dashboard with live KPIs, recent bills, low-stock alerts
* Product management: add/edit/delete, search, barcode lookup, low-stock view, Excel import/export
* Customer management: add/edit/delete, search, purchase ledger, Excel export
* Billing: fast search, barcode entry, cart, quantity/discount editing, retail/wholesale pricing, multiple payment methods, automatic stock deduction
* Automatic professional PDF invoice generation (saved to `invoices/`)
* Reports: sales (today/week/month/year), profit, GST, top products, top customers, inventory value, expense tracking, Excel export
* Settings: shop details, theme, import/export, backup & restore
* Automatic backup (SQLite snapshot + Excel exports) on every app exit, with Recovery Mode if the database is missing but backups exist

---

## 1. Requirements

* Windows 10/11 (recommended) — also runs on macOS/Linux for development (except silent printing which is Windows-only)
* Python 3.12+ (only needed if running from source; not required for packaged `.exe`)

---

## 2. Setup (running from source)

```bash
cd ApnaDukan

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# or dependency-safe launcher
python launcher.py
```

On first launch (no `database/shop.db` present), the **Setup Wizard** opens automatically:

1. Enter Shop Name, Owner Name, Phone (required), Address & GST (optional)
2. Optionally choose shop logo
3. Create Admin username & password
4. Optionally import Excel files:

   * Products: `Barcode, Product Name, Category, Brand, Purchase Price, Retail Price, Wholesale Price, GST, Stock, Minimum Stock, Rack Location, Remarks`
   * Customers: `Name, Phone, Email, Address, GST, Pending Amount`
5. Click **Finish Setup**

---

## 3. Everyday use

* **Billing tab**: scan barcode or search product → add to cart → adjust qty/price → apply discount → choose payment → generate invoice
* **Products / Customers**: manage master data + Excel import/export
* **Reports**: sales, profit, GST, top products/customers, inventory value, expenses
* **Settings (Admin only)**: shop config, theme, backups, restore

---

## 4. Backups & recovery

Automatic backup runs on every exit:

* SQLite database snapshot
* Excel exports (products, customers, bills)
* Stored in `backups/`

If database is missing at startup:

* Restore latest backup OR
* Start fresh setup wizard

---

## 5. Building a Windows executable (packaging)

```bash
pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed --name ApnaDukan ^
    --add-data "config;config" ^
    --add-data "database/schema.sql;database" ^
    main.py
```

Output:

```
dist/ApnaDukan/
```

Run:

```
ApnaDukan.exe
```

For full installer (Start Menu + Desktop shortcut), use **Inno Setup** on the `dist/ApnaDukan` folder.

---

## 6. Project structure

```
ApnaDukan/
  main.py
  launcher.py
  requirements.txt

  database/
    db_manager.py
    schema.sql

  modules/
    auth_manager.py
    product_manager.py
    customer_manager.py
    billing_manager.py
    invoice_generator.py
    excel_manager.py
    backup_manager.py
    report_manager.py

  ui/
    setup_wizard.py
    login_window.py
    dashboard.py
    views.py
    recovery.py

  utils/
    logger.py
    config_manager.py

  assets/
  exports/
  imports/
  invoices/
  backups/
  logs/
  temp/
  config/
```

---

## 7. Notes on scope

This version covers full core functionality of **Apna Dukan** with a clean modular architecture (UI separated from business logic).

Future extensions can include:

* WhatsApp/SMS invoices
* Cloud backup
* Multi-shop support
* Loyalty program
* Multi-language support
* Auto-updates
* Thermal printer & barcode scanner integration

