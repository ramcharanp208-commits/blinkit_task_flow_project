"""One-time migration: add hashed_password to users, status to tasks."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "backend", "taskflow.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# --- users: hashed_password ---
cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
if "hashed_password" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT")
    print("Added hashed_password to users")
else:
    print("hashed_password already exists")

# --- tasks: status ---
cols = [r[1] for r in cur.execute("PRAGMA table_info(tasks)").fetchall()]
if "status" not in cols:
    cur.execute("ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'")
    print("Added status to tasks")
else:
    print("status already exists")

conn.commit()
conn.close()
print("Migration complete.")
