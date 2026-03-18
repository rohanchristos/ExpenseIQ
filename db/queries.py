"""
queries.py — All SQL CRUD Operations

Every public function in this module operates on the shared SQLite
connection from database.py and returns either a scalar, a bool,
or a pandas DataFrame.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, Optional

import pandas as pd

from db.database import get_connection


# ═══════════════════════════════════════════════════════════════════════════
#  Expense CRUD
# ═══════════════════════════════════════════════════════════════════════════


def add_expense(
    amount: float,
    category: str,
    description: str,
    date_: str,
    payment_method: str = "Cash",
) -> int:
    """Insert a new expense and return its row id.

    Parameters
    ----------
    amount : float
        Expense amount (must be > 0).
    category : str
        Category name (should match a row in the categories table).
    description : str
        Free-text note for the expense.
    date_ : str
        Date in ISO format ``YYYY-MM-DD``.
    payment_method : str, optional
        Payment method label, by default ``"Cash"``.

    Returns
    -------
    int
        The ``id`` of the newly created expense row.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO expenses (amount, category, description, date, payment_method)
        VALUES (?, ?, ?, ?, ?)
        """,
        (amount, category, description, date_, payment_method),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
) -> pd.DataFrame:
    """Return expenses as a DataFrame, optionally filtered.

    Parameters
    ----------
    start_date : str or None
        Include expenses on or after this date (``YYYY-MM-DD``).
    end_date : str or None
        Include expenses on or before this date (``YYYY-MM-DD``).
    category : str or None
        Filter to a single category name.

    Returns
    -------
    pd.DataFrame
        Columns: id, amount, category, description, date,
        payment_method, created_at.  Ordered by date descending.
    """
    query = "SELECT * FROM expenses WHERE 1=1"
    params: list[Any] = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, id DESC"
    return pd.read_sql_query(query, get_connection(), params=params)


def update_expense(expense_id: int, **kwargs: Any) -> bool:
    """Update one or more fields of an existing expense.

    Parameters
    ----------
    expense_id : int
        Primary key of the expense to update.
    **kwargs
        Column-value pairs to update.  Valid keys:
        ``amount``, ``category``, ``description``, ``date``,
        ``payment_method``.

    Returns
    -------
    bool
        ``True`` if a row was updated, ``False`` if ``expense_id``
        was not found.
    """
    allowed = {"amount", "category", "description", "date", "payment_method"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [expense_id]

    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE expenses SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by its id.

    Parameters
    ----------
    expense_id : int
        Primary key of the expense to remove.

    Returns
    -------
    bool
        ``True`` if a row was deleted, ``False`` otherwise.
    """
    conn = get_connection()
    cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════
#  Aggregations / Reports
# ═══════════════════════════════════════════════════════════════════════════


def get_monthly_summary(year: int, month: int) -> pd.DataFrame:
    """Return per-category totals for a given month.

    Parameters
    ----------
    year : int
        Four-digit year, e.g. ``2026``.
    month : int
        Month number (1–12).

    Returns
    -------
    pd.DataFrame
        Columns: ``category``, ``total``, ``count``.
    """
    month_str = f"{year}-{month:02d}"
    query = """
        SELECT category,
               SUM(amount)   AS total,
               COUNT(*)      AS count
        FROM   expenses
        WHERE  strftime('%Y-%m', date) = ?
        GROUP  BY category
        ORDER  BY total DESC
    """
    return pd.read_sql_query(query, get_connection(), params=[month_str])


def get_spending_trend(months: int = 6) -> pd.DataFrame:
    """Return total spending per month for the last *n* months.

    Parameters
    ----------
    months : int, optional
        How many months of history to include, by default ``6``.

    Returns
    -------
    pd.DataFrame
        Columns: ``month`` (``YYYY-MM``), ``total``.
    """
    query = """
        SELECT strftime('%Y-%m', date) AS month,
               SUM(amount)             AS total
        FROM   expenses
        WHERE  date >= date('now', ? || ' months')
        GROUP  BY month
        ORDER  BY month ASC
    """
    return pd.read_sql_query(
        query, get_connection(), params=[f"-{months}"]
    )


def get_top_expenses(n: int = 5, month: Optional[str] = None) -> pd.DataFrame:
    """Return the *n* largest expenses, optionally filtered to a month.

    Parameters
    ----------
    n : int, optional
        Number of rows to return, by default ``5``.
    month : str or None
        If provided, filter to this month (``YYYY-MM``).

    Returns
    -------
    pd.DataFrame
        Columns: id, amount, category, description, date,
        payment_method, created_at.
    """
    query = "SELECT * FROM expenses"
    params: list[Any] = []

    if month:
        query += " WHERE strftime('%Y-%m', date) = ?"
        params.append(month)

    query += " ORDER BY amount DESC LIMIT ?"
    params.append(n)

    return pd.read_sql_query(query, get_connection(), params=params)


# ═══════════════════════════════════════════════════════════════════════════
#  Budget CRUD
# ═══════════════════════════════════════════════════════════════════════════


def set_budget(category: str, monthly_limit: float, month: str) -> None:
    """Create or update a budget for a category + month pair.

    Parameters
    ----------
    category : str
        Category name.
    monthly_limit : float
        Maximum spending allowed for this category in the given month.
    month : str
        Target month in ``YYYY-MM`` format.
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO budgets (category, monthly_limit, month)
        VALUES (?, ?, ?)
        ON CONFLICT(category, month)
        DO UPDATE SET monthly_limit = excluded.monthly_limit
        """,
        (category, monthly_limit, month),
    )
    conn.commit()


def get_budgets(month: str) -> pd.DataFrame:
    """Return all budgets for a given month.

    Parameters
    ----------
    month : str
        Target month in ``YYYY-MM`` format.

    Returns
    -------
    pd.DataFrame
        Columns: id, category, monthly_limit, month.
    """
    query = "SELECT * FROM budgets WHERE month = ? ORDER BY category"
    return pd.read_sql_query(query, get_connection(), params=[month])


# ═══════════════════════════════════════════════════════════════════════════
#  Category helpers
# ═══════════════════════════════════════════════════════════════════════════


def get_category_colors() -> Dict[str, str]:
    """Return a mapping of category name → hex color.

    Returns
    -------
    dict[str, str]
        e.g. ``{"Food": "#FF6B6B", "Transport": "#4ECDC4", …}``
    """
    conn = get_connection()
    rows = conn.execute("SELECT name, color FROM categories").fetchall()
    return {row["name"]: row["color"] for row in rows}
