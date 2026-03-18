"""
database.py — SQLite Connection & Schema Setup

Provides:
  - get_connection()      → cached SQLite connection to data/expenses.db
  - init_db()             → creates tables and seeds default categories
  - get_db_path()         → resolved absolute path to the database file
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = _DB_DIR / "expenses.db"


def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return _DB_PATH


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Return a reusable SQLite connection (created on first call).

    The connection is configured with:
      - Row factory  → sqlite3.Row  (dict-like access)
      - WAL journal mode for better concurrent-read performance
    """
    global _connection
    if _connection is None:
        # Ensure the data/ directory exists
        _DB_DIR.mkdir(parents=True, exist_ok=True)

        _connection = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL;")
        _connection.execute("PRAGMA foreign_keys=ON;")
    return _connection


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL UNIQUE,
    icon  TEXT    NOT NULL DEFAULT '',
    color TEXT    NOT NULL DEFAULT '#AAAAAA'
);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    amount          REAL    NOT NULL,
    category        TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    date            TEXT    NOT NULL,            -- ISO format YYYY-MM-DD
    payment_method  TEXT    NOT NULL DEFAULT 'Cash',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    category       TEXT    NOT NULL,
    monthly_limit  REAL    NOT NULL,
    month          TEXT    NOT NULL,             -- YYYY-MM
    UNIQUE(category, month)
);
"""

# ---------------------------------------------------------------------------
# Default categories
# ---------------------------------------------------------------------------

DEFAULT_CATEGORIES = [
    ("Food",          "🍕", "#FF6B6B"),
    ("Transport",     "🚗", "#4ECDC4"),
    ("Shopping",      "🛍️", "#45B7D1"),
    ("Entertainment", "🎬", "#96CEB4"),
    ("Health",        "💊", "#FFEAA7"),
    ("Utilities",     "🔌", "#DDA0DD"),
    ("Education",     "📚", "#98D8C8"),
    ("Travel",        "✈️", "#F7DC6F"),
    ("Sports",        "🏋️", "#82E0AA"),
    ("Others",        "💰", "#AED6F1"),
]


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables (if they don't exist) and seed default categories.

    Safe to call multiple times — uses INSERT OR IGNORE so existing rows
    are never duplicated.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript(_SCHEMA_SQL)

    # Seed categories
    cursor.executemany(
        "INSERT OR IGNORE INTO categories (name, icon, color) VALUES (?, ?, ?);",
        DEFAULT_CATEGORIES,
    )

    conn.commit()


# Auto-initialize when the module is first imported
init_db()
