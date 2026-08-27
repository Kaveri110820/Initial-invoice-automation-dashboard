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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'Employee',
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT NOT NULL,
                token_hash  TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                used        INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
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


def add_user(full_name: str, email: str, password_hash: str, role: str = "Employee") -> int | None:
    sql = """
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """
    with _get_connection() as conn:
        try:
            cursor = conn.execute(sql, (full_name, email, password_hash, role))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_user_by_email(email: str) -> dict | None:
    conn = _get_connection()
    try:
        sql = "SELECT id, full_name, email, password_hash, role, created_at FROM users WHERE email = ?"
        row = conn.execute(sql, (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT id, full_name, email, role, created_at FROM users ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_user_role(user_id: int, role: str) -> bool:
    sql = "UPDATE users SET role = ? WHERE id = ?"
    with _get_connection() as conn:
        cursor = conn.execute(sql, (role, user_id))
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    sql = "DELETE FROM users WHERE id = ?"
    with _get_connection() as conn:
        cursor = conn.execute(sql, (user_id,))
        return cursor.rowcount > 0


def update_user_password(user_id: int, password_hash: str) -> bool:
    sql = "UPDATE users SET password_hash = ? WHERE id = ?"
    with _get_connection() as conn:
        cursor = conn.execute(sql, (password_hash, user_id))
        return cursor.rowcount > 0


def create_reset_token(hashed_token: str, email: str, expires_at: str) -> int:
    sql = """
        INSERT INTO password_reset_tokens (email, token_hash, expires_at)
        VALUES (?, ?, ?)
    """
    with _get_connection() as conn:
        cursor = conn.execute(sql, (email, hashed_token, expires_at))
        return cursor.lastrowid


def get_valid_reset_token(hashed_token: str) -> dict | None:
    conn = _get_connection()
    try:
        sql = """
            SELECT * FROM password_reset_tokens
            WHERE token_hash = ? AND used = 0
            ORDER BY id DESC LIMIT 1
        """
        row = conn.execute(sql, (hashed_token,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_reset_token_used(token_id: int) -> None:
    with _get_connection() as conn:
        conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (token_id,))
