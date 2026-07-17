"""
Data access helpers. Keeps SQL out of app.py so routes stay readable.
"""
from datetime import datetime, timezone
from database import get_connection


def upsert_account(platform, account_name, profile_url, risk_category, confidence):
    """Insert an account, or update its risk info if it already exists
    and the new confidence is higher than what's stored."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cur.execute(
        "SELECT id, confidence FROM accounts WHERE platform=? AND account_name=?",
        (platform, account_name),
    )
    row = cur.fetchone()

    if row is None:
        cur.execute(
            """INSERT INTO accounts
               (platform, account_name, profile_url, risk_category, confidence, last_checked)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (platform, account_name, profile_url, risk_category, confidence, now),
        )
        account_id = cur.lastrowid
    else:
        account_id = row["id"]
        if confidence > (row["confidence"] or 0):
            cur.execute(
                """UPDATE accounts SET risk_category=?, confidence=?, last_checked=?
                   WHERE id=?""",
                (risk_category, confidence, now, account_id),
            )
        else:
            cur.execute("UPDATE accounts SET last_checked=? WHERE id=?", (now, account_id))

    conn.commit()
    conn.close()
    return account_id


def add_violation(account_id, post_url, post_text, reason, category, confidence, timestamp):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO violations
           (account_id, post_url, post_text, reason, category, confidence, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (account_id, post_url, post_text, reason, category, confidence, timestamp),
    )
    conn.commit()
    conn.close()


def get_flagged_accounts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM accounts
           WHERE risk_category IS NOT NULL
           ORDER BY confidence DESC, last_checked DESC"""
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_account(account_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (account_id,))
    account = cur.fetchone()
    account = dict(account) if account else None

    violations = []
    if account:
        cur.execute(
            "SELECT * FROM violations WHERE account_id=? ORDER BY confidence DESC",
            (account_id,),
        )
        violations = [dict(r) for r in cur.fetchall()]

    conn.close()
    return account, violations


def log_search(keyword, platform, status, message=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO search_log (keyword, platform, status, message) VALUES (?, ?, ?, ?)",
        (keyword, platform, status, message),
    )
    conn.commit()
    conn.close()
