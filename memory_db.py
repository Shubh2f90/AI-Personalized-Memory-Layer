"""
memory_db.py
Handles all storage and retrieval of conversation memory using SQLite.

Wrapped everything into a MemoryStore class so the connection handling
and table setup live in one place. Makes it easier to swap SQLite for
something else later without changing how the rest of the app calls it.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory.db"


class MemoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Open a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # lets us access columns by name
        return conn

    def init_db(self):
        """Create tables if they don't already exist. Safe to run every time."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def save_message(self, role: str, content: str):
        """Save a single message to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_recent_messages(self, limit: int = 10):
        """Fetch the last N messages, oldest first, for context."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def save_fact(self, fact: str):
        """Save a new extracted fact about the user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO facts (fact, created_at) VALUES (?, ?)",
            (fact, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_all_facts(self):
        """Fetch all stored facts about the user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT fact FROM facts ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [r["fact"] for r in rows]

# --- Module-level shortcuts -------------------------------------------------
# chat_engine.py and main.py call plain functions (db.save_message(...)).
# These thin wrappers forward each call to one shared MemoryStore, so the
# rest of the app doesn't care that storage is now a class.
_store = MemoryStore()


def init_db():
    """Create tables if missing. Kept so older callers keep working."""
    _store.init_db()


def save_message(role: str, content: str):
    """Forward to MemoryStore.save_message."""
    _store.save_message(role, content)


def get_recent_messages(limit: int = 10):
    """Forward to MemoryStore.get_recent_messages."""
    return _store.get_recent_messages(limit)


def save_fact(fact: str):
    """Forward to MemoryStore.save_fact."""
    _store.save_fact(fact)


def get_all_facts():
    """Forward to MemoryStore.get_all_facts."""
    return _store.get_all_facts()