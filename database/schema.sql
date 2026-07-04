-- database/schema.sql
-- ShopEase POS full schema. Applied once on first run (see db_manager.initialize()).
-- Foreign keys + indexes included for performance at 100k+ row scale.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('admin', 'staff')),
    full_name       TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_login      TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key             TEXT PRIMARY KEY,
    value           TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT,
    email           TEXT,
    address         TEXT,
    gst_number      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode         TEXT UNIQUE,
    name            TEXT NOT NULL,
    category        TEXT,
    brand           TEXT,
    purchase_price  REAL NOT NULL DEFAULT 0,
    retail_price    REAL NOT NULL DEFAULT 0,
    wholesale_price REAL NOT NULL DEFAULT 0,
    gst_percent     REAL NOT NULL DEFAULT 0,
    stock           INTEGER NOT NULL DEFAULT 0,
    min_stock       INTEGER NOT NULL DEFAULT 5,
    rack_location   TEXT,
    remarks         TEXT,
    supplier_id     INTEGER,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT UNIQUE,
    email           TEXT,
    address         TEXT,
    gst_number      TEXT,
    pending_amount  REAL NOT NULL DEFAULT 0,
    last_visit      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

CREATE TABLE IF NOT EXISTS bills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT NOT NULL UNIQUE,
    customer_id     INTEGER,
    bill_date       TEXT NOT NULL DEFAULT (datetime('now')),
    subtotal        REAL NOT NULL DEFAULT 0,
    discount        REAL NOT NULL DEFAULT 0,
    gst_amount      REAL NOT NULL DEFAULT 0,
    grand_total     REAL NOT NULL DEFAULT 0,
    payment_method  TEXT NOT NULL DEFAULT 'Cash',
    price_mode      TEXT NOT NULL DEFAULT 'retail',
    pdf_path        TEXT,
    created_by      INTEGER,
    is_cancelled    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_bills_date ON bills(bill_date);
CREATE INDEX IF NOT EXISTS idx_bills_customer ON bills(customer_id);

CREATE TABLE IF NOT EXISTS bill_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         INTEGER NOT NULL,
    product_id      INTEGER,
    product_name    TEXT NOT NULL,
    quantity        REAL NOT NULL,
    unit_price      REAL NOT NULL,
    gst_percent     REAL NOT NULL DEFAULT 0,
    discount        REAL NOT NULL DEFAULT 0,
    line_total      REAL NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_bill_items_bill ON bill_items(bill_id);

CREATE TABLE IF NOT EXISTS stock_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    change_type     TEXT NOT NULL CHECK(change_type IN ('sale','purchase','adjustment','return')),
    quantity_change INTEGER NOT NULL,
    reference       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_stock_history_product ON stock_history(product_id);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    category        TEXT,
    amount          REAL NOT NULL,
    expense_date    TEXT NOT NULL DEFAULT (datetime('now')),
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS invoice_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         INTEGER NOT NULL,
    pdf_path        TEXT NOT NULL,
    generated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    action          TEXT NOT NULL,
    details         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
