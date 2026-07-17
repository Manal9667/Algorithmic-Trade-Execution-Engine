"""
SQLite database setup. Kept intentionally simple (no ORM) to minimize
memory footprint on Render's free tier.
"""
import sqlite3
from config import Config


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            account_name TEXT NOT NULL,
            profile_url TEXT,
            risk_category TEXT,
            confidence INTEGER,
            last_checked TEXT,
            UNIQUE(platform, account_name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            post_url TEXT,
            post_text TEXT,
            reason TEXT,
            category TEXT,
            confidence INTEGER,
            timestamp TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            platform TEXT,
            status TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
