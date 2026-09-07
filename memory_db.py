"""
memory_db.py
Handles all storage and retrieval of conversation memory using SQLite.

Core idea:
- Every message (user + assistant) gets stored with a timestamp.
- Every conversation can have "extracted facts" — short, durable pieces
  of information about the user (e.g. "user is learning C++ DSA").
- When a new conversation starts, we pull the most recent facts and
  recent messages to give the LLM context — instead of starting blank.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory.db"


def get_connection():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create tables if they don't already exist. Safe to run every time."""
    conn = get_connection()
    cursor = conn.cursor()

    # Stores every single message exchanged
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,              -- 'user' or 'assistant'
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Stores durable facts extracted about the user over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_message(role: str, content: str):
    """Save a single message to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = 10):
    """Fetch the last N messages, oldest first, for context."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    # reverse so oldest comes first (natural conversation order)
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def save_fact(fact: str):
    """Save a new extracted fact about the user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO facts (fact, created_at) VALUES (?, ?)",
        (fact, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_facts():
    """Fetch all stored facts about the user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fact FROM facts ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r["fact"] for r in rows]