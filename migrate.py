"""
migrate.py — TaskFlow DB migrations
Run: python migrate.py
Safe to re-run multiple times.
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")
conn = sqlite3.connect(DB)
cur  = conn.cursor()

def col_exists(table, col):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols

def table_exists(table):
    r = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return r is not None

# ── users ─────────────────────────────────────────────────────────────────────
if not col_exists("users", "hashed_password"):
    cur.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT")
    print("Added users.hashed_password")

if not col_exists("users", "is_admin"):
    cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    print("Added users.is_admin")

# ── tasks ─────────────────────────────────────────────────────────────────────
if not col_exists("tasks", "status"):
    cur.execute("ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'")
    print("Added tasks.status")

# ── otp_tokens ───────────────────────────────────────────────────────────────
if not table_exists("otp_tokens"):
    cur.execute("""
        CREATE TABLE otp_tokens (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            email     TEXT    NOT NULL,
            otp       TEXT    NOT NULL,
            expires_at TEXT   NOT NULL,
            used      INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("Created otp_tokens table")

# ── notifications ─────────────────────────────────────────────────────────────
if not table_exists("notifications"):
    cur.execute("""
        CREATE TABLE notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            message    TEXT    NOT NULL,
            type       TEXT    NOT NULL DEFAULT 'info',
            is_read    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created notifications table")

conn.commit()
conn.close()
print("Migration complete.")
