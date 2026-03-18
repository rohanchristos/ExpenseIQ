"""
helpers.py — Formatting, Date Utils & Currency Helpers

Provides:
  - inject_css()             → reads assets/style.css and injects it into Streamlit
  - format_currency(amount)  → "₹1,234.50"
  - format_date(date_str)    → "15 Mar 2026"
  - get_month_options(n)     → ["2026-03", "2026-02", …]
"""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Optional

import streamlit as st


# ───────────────────────────────────────────────────────────────
# CSS injection
# ───────────────────────────────────────────────────────────────

_CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style.css"


def inject_css() -> None:
    """Read ``assets/style.css`` and inject it into the Streamlit page.

    Should be called once at the top of ``app.py``::

        from utils.helpers import inject_css
        inject_css()
    """
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────
# Formatting
# ───────────────────────────────────────────────────────────────


def format_currency(amount: float, symbol: str = "₹") -> str:
    """Format *amount* as a currency string.

    Parameters
    ----------
    amount : float
        The numeric value to format.
    symbol : str, optional
        Currency symbol, by default ``"₹"``.

    Returns
    -------
    str
        e.g. ``"₹1,234.50"`` or ``"₹80.00"``.
    """
    return f"{symbol}{amount:,.2f}"


def format_date(date_str: str, fmt: str = "%d %b %Y") -> str:
    """Convert an ISO date string to a human-friendly format.

    Parameters
    ----------
    date_str : str
        Date in ``YYYY-MM-DD`` format.
    fmt : str, optional
        Output format, by default ``"%d %b %Y"`` → ``"15 Mar 2026"``.

    Returns
    -------
    str
        Formatted date string.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").strftime(fmt)


# ───────────────────────────────────────────────────────────────
# Date helpers
# ───────────────────────────────────────────────────────────────


def get_month_options(n: int = 12) -> list[str]:
    """Return a list of ``"YYYY-MM"`` strings for the last *n* months.

    The list starts with the current month and goes backwards.

    Parameters
    ----------
    n : int, optional
        How many months to include, by default ``12``.

    Returns
    -------
    list[str]
        e.g. ``["2026-03", "2026-02", "2026-01", …]``
    """
    today = date.today()
    months: list[str] = []
    for i in range(n):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year}-{month:02d}")
    return months


def get_current_month() -> str:
    """Return the current month as ``YYYY-MM``."""
    return date.today().strftime("%Y-%m")


def get_current_date() -> str:
    """Return today's date as ``YYYY-MM-DD``."""
    return date.today().strftime("%Y-%m-%d")


# ───────────────────────────────────────────────────────────────
# Spending insight helpers
# ───────────────────────────────────────────────────────────────


def get_spending_insight_color(spent: float, budget: float) -> str:
    """Return a CSS color string based on how much of *budget* is used.

    Parameters
    ----------
    spent : float
        Amount spent so far.
    budget : float
        Budget limit.  If zero or negative, returns neutral grey.

    Returns
    -------
    str
        CSS colour — green (<70%), yellow (70–90%), red (>90%).
    """
    if budget <= 0:
        return "#8B949E"  # muted grey

    ratio = spent / budget
    if ratio < 0.70:
        return "#00D4AA"  # accent green
    elif ratio < 0.90:
        return "#FFA502"  # warning yellow
    return "#FF4757"      # danger red


def abbreviate_number(n: float) -> str:
    """Abbreviate *n* using the **Indian number system**.

    Returns
    -------
    str
        ``"1.2K"`` for thousands, ``"3.4L"`` for lakhs,
        ``"1.2Cr"`` for crores.  Values below 1 000 are returned as-is.

    Examples
    --------
    >>> abbreviate_number(1234)
    '1.2K'
    >>> abbreviate_number(345000)
    '3.5L'
    >>> abbreviate_number(12000000)
    '1.2Cr'
    """
    abs_n = abs(n)
    sign = "-" if n < 0 else ""

    if abs_n >= 1_00_00_000:          # 1 crore
        return f"{sign}{abs_n / 1_00_00_000:.1f}Cr"
    elif abs_n >= 1_00_000:           # 1 lakh
        return f"{sign}{abs_n / 1_00_000:.1f}L"
    elif abs_n >= 1_000:              # 1 thousand
        return f"{sign}{abs_n / 1_000:.1f}K"
    return f"{sign}{abs_n:,.0f}"
