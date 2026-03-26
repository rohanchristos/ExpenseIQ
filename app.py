"""
app.py — Streamlit Entry Point for ExpenseIQ

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import streamlit as st

# ── Page config (MUST be the first Streamlit call) ────────────
st.set_page_config(
    page_title="ExpenseIQ",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports (after page config) ───────────────────────────────
from db.database import init_db, DEFAULT_CATEGORIES
from db.queries import add_expense, get_all_expenses, set_budget
from utils.helpers import inject_css

from components.sidebar import render_sidebar
from components.dashboard import render_dashboard
from components.expenses import render_expenses
from components.analytics import render_analytics
from components.budget import render_budget
from components.login_page import render_login


# ───────────────────────────────────────────────────────────────
# Initialization
# ───────────────────────────────────────────────────────────────


def _ensure_db() -> None:
    """Initialize the database (idempotent)."""
    init_db()


def _seed_demo_data() -> None:
    """Seed 5 sample expenses if the database is empty (first run demo)."""

    df = get_all_expenses()
    if not df.empty:
        return  # already has data

    today = date.today()

    samples = [
        (450.00,  "Food",          "Dinner at Italian restaurant",  today - timedelta(days=1),  "Card"),
        (35.50,   "Transport",     "Uber to office",                today - timedelta(days=2),  "UPI"),
        (1299.00, "Shopping",      "New headphones",                today - timedelta(days=3),  "Card"),
        (200.00,  "Entertainment", "Movie tickets — Oppenheimer",   today - timedelta(days=5),  "UPI"),
        (150.00,  "Food",          "Weekly groceries",              today - timedelta(days=7),  "Cash"),
    ]

    for amount, category, desc, d, pay in samples:
        add_expense(
            amount=amount,
            category=category,
            description=desc,
            date_=str(d),
            payment_method=pay,
        )

    # Set a couple of demo budgets for current month
    month_str = today.strftime("%Y-%m")
    set_budget("Food",      3000.0, month_str)
    set_budget("Transport", 2000.0, month_str)
    set_budget("Shopping",  5000.0, month_str)


# ───────────────────────────────────────────────────────────────
# Page router
# ───────────────────────────────────────────────────────────────

_PAGE_RENDERERS = {
    "Dashboard": render_dashboard,
    "Expenses":  render_expenses,
    "Analytics": render_analytics,
    "Budget":    render_budget,
}


def main() -> None:
    """Application entry point."""

    # 1. Inject custom CSS
    inject_css()

    # 2. Initialize login state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # 3. Check Authentication — show login if not logged in
    if not st.session_state["logged_in"]:
        render_login()
        return

    # 4. Initialize DB + seed demo data
    _ensure_db()
    _seed_demo_data()

    # 5. Render sidebar and get page selection
    page = render_sidebar()

    # 6. Route to the selected page
    renderer = _PAGE_RENDERERS.get(page)

    if renderer:
        try:
            renderer()
        except Exception as exc:
            st.error(
                f"⚠️ Something went wrong while loading **{page}**.\n\n"
                f"```\n{exc}\n```"
            )
            st.info("Try refreshing the page. If the problem persists, clear the database.")
    else:
        st.error(f"Unknown page: {page}")


# ───────────────────────────────────────────────────────────────
# Run
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
else:
    # Streamlit runs the file directly, not via __main__
    main()
