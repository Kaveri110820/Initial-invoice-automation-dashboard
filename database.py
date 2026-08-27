import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "invoices.db"

VALID_STATUSES = ("Pending", "Approved", "Rejected")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number  TEXT,
                vendor_name     TEXT NOT NULL,
                invoice_date    TEXT,
                due_date        TEXT,
                subtotal        REAL DEFAULT 0,
                tax             REAL DEFAULT 0,
                total_amount    REAL DEFAULT 0,
                currency        TEXT DEFAULT 'USD',
                status          TEXT DEFAULT 'Pending'
                                  CHECK(status IN ('Pending', 'Approved', 'Rejected')),
                file_name       TEXT NOT NULL,
                extracted_text  TEXT DEFAULT '',
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_invoice(data: dict) -> int:
    sql = """
        INSERT INTO invoices
            (invoice_number, vendor_name, invoice_date, due_date,
             subtotal, tax, total_amount, currency,
             status, file_name, extracted_text)
        VALUES
            (:invoice_number, :vendor_name, :invoice_date, :due_date,
             :subtotal, :tax, :total_amount, :currency,
             :status, :file_name, :extracted_text)
    """
    defaults = {
        "invoice_number": "",
        "vendor_name": "",
        "invoice_date": "",
        "due_date": "",
        "subtotal": 0.0,
        "tax": 0.0,
        "total_amount": 0.0,
        "currency": "USD",
        "status": "Pending",
        "file_name": "",
        "extracted_text": "",
    }
    defaults.update(data)

    with _get_connection() as conn:
        cursor = conn.execute(sql, defaults)
        return cursor.lastrowid


def get_all_invoices(status: str | None = None) -> list[dict]:
    conn = _get_connection()
    try:
        if status and status in VALID_STATUSES:
            sql = "SELECT * FROM invoices WHERE status = ? ORDER BY created_at DESC"
            rows = conn.execute(sql, (status,)).fetchall()
        else:
            sql = "SELECT * FROM invoices ORDER BY created_at DESC"
            rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_invoice_by_id(invoice_id: int) -> dict | None:
    conn = _get_connection()
    try:
        sql = "SELECT * FROM invoices WHERE id = ?"
        row = conn.execute(sql, (invoice_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_invoice_status(
    invoice_id: int, status: str, notes: str = ""
) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

    sql = """
        UPDATE invoices
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    with _get_connection() as conn:
        cursor = conn.execute(sql, (status, invoice_id))
        return cursor.rowcount > 0


def find_duplicate(invoice_number: str, vendor_name: str, total_amount: float) -> dict | None:
    if not invoice_number:
        return None
    conn = _get_connection()
    try:
        sql = """
            SELECT * FROM invoices
            WHERE invoice_number = ? AND vendor_name = ? AND total_amount = ?
            LIMIT 1
        """
        row = conn.execute(sql, (invoice_number, vendor_name, total_amount)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_invoice(invoice_id: int) -> bool:
    sql = "DELETE FROM invoices WHERE id = ?"
    with _get_connection() as conn:
        cursor = conn.execute(sql, (invoice_id,))
        return cursor.rowcount > 0
