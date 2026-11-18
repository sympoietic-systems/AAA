"""Durable daily review email delivery leases and receipts."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_email_deliveries (
        date TEXT NOT NULL, recipient TEXT NOT NULL, lease_until REAL NOT NULL,
        sent_at REAL, PRIMARY KEY (date, recipient)
    )""")
