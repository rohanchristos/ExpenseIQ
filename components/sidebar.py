"""
sidebar.py — Navigation & Filters Sidebar

Provides:
  render_sidebar() → str   — renders the sidebar and returns the selected page name
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import streamlit as st

from db.database import get_connection, get_db_path
from db.queries import get_all_expenses
from utils.helpers import format_currency, get_current_month, get_month_options


# ───────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────

_NAV_OPTIONS = [
    "📊 Dashboard",
    "💸 Expenses",
    "📈 Analytics",
    "🎯 Budget",
]

_NAV_MAP = {
    "📊 Dashboard": "Dashboard",
    "💸 Expenses": "Expenses",
    "📈 Analytics": "Analytics",
    "🎯 Budget": "Budget",
}


# ───────────────────────────────────────────────────────────────
# Main render
# ───────────────────────────────────────────────────────────────


def render_sidebar() -> str:
    """Render the sidebar and return the selected page name.

    Returns
    -------
    str
        One of ``"Dashboard"``, ``"Expenses"``, ``"Analytics"``,
        ``"Budget"``.
    """

    with st.sidebar:
        # ── Logo / Title ──────────────────────────────────────
        st.markdown(
            "<h1 style='"
            "font-family: Space Mono, monospace; "
            "color: #00D4AA; "
            "font-size: 1.8rem; "
            "text-shadow: 0 0 20px rgba(0,212,170,0.3); "
            "margin-bottom: 0;"
            "'>💰 ExpenseIQ</h1>",
            unsafe_allow_html=True,
        )
        st.caption("Smart Personal Finance Tracker")

        st.markdown("---")

        # ── Navigation ────────────────────────────────────────
        selection = st.radio(
            "Navigate",
            _NAV_OPTIONS,
            index=0,
            key="nav_radio",
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Global Month Filter ───────────────────────────────
        months = get_month_options(n=12)
        if "global_month" not in st.session_state:
            st.session_state["global_month"] = get_current_month()

        st.selectbox(
            "📅 Active Month",
            months,
            index=months.index(st.session_state["global_month"])
            if st.session_state["global_month"] in months
            else 0,
            key="global_month",
        )

        st.markdown("---")

        # ── Quick Stats ───────────────────────────────────────
        _render_quick_stats()

        st.markdown("---")

        # ── Theme Toggle ──────────────────────────────────────
        dark = st.toggle("🌙 Dark Mode", value=True, key="dark_mode")
        if not dark:
            st.markdown(
                "<style>"
                ":root { --bg-primary: #F0F2F6 !important; "
                "--bg-surface: #FFFFFF !important; "
                "--text-primary: #1a1a2e !important; "
                "--text-muted: #555 !important; }"
                "</style>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ── Footer: DB Info ───────────────────────────────────
        _render_db_info()

    return _NAV_MAP.get(selection, "Dashboard")


# ───────────────────────────────────────────────────────────────
# Quick Stats
# ───────────────────────────────────────────────────────────────


def _render_quick_stats() -> None:
    """Show today's and this week's spending as muted text."""

    today_str = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    today_df = get_all_expenses(start_date=today_str, end_date=today_str)
    week_df = get_all_expenses(start_date=week_start, end_date=today_str)

    today_total = today_df["amount"].sum() if not today_df.empty else 0
    week_total = week_df["amount"].sum() if not week_df.empty else 0

    st.markdown(
        f"<p style='color:#8B949E; font-size:0.82rem; margin:0;'>"
        f"📆 Today: <b style='color:#E8EDF2'>{format_currency(today_total)}</b>"
        f"</p>"
        f"<p style='color:#8B949E; font-size:0.82rem; margin:0;'>"
        f"📅 This week: <b style='color:#E8EDF2'>{format_currency(week_total)}</b>"
        f"</p>",
        unsafe_allow_html=True,
    )


# ───────────────────────────────────────────────────────────────
# DB Info Footer
# ───────────────────────────────────────────────────────────────


def _render_db_info() -> None:
    """Show database file size and total record count."""

    db_path = get_db_path()

    # File size
    try:
        size_bytes = os.path.getsize(db_path)
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
    except OSError:
        size_str = "N/A"

    # Record count
    try:
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    except Exception:
        count = 0

    st.markdown(
        f"<p style='color:#8B949E; font-size:0.75rem; margin:0;'>"
        f"🗄️ DB: {size_str} &nbsp;•&nbsp; {count} records"
        f"</p>",
        unsafe_allow_html=True,
    )
