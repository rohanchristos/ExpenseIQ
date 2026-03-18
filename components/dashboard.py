"""
dashboard.py — Overview Page

Renders the main dashboard with:
  - 4 KPI metric cards (total, biggest category, daily avg, remaining budget)
  - Monthly bar chart + donut chart
  - Top 5 expenses table + calendar heatmap
  - Budget gauge grid
  - Quick-add expense expander
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from db.database import DEFAULT_CATEGORIES, get_connection
from db.queries import (
    add_expense,
    get_all_expenses,
    get_budgets,
    get_category_colors,
    get_monthly_summary,
    get_spending_trend,
    get_top_expenses,
)
from utils.charts import (
    budget_gauge_chart,
    calendar_heatmap,
    donut_chart,
    monthly_bar_chart,
)
from utils.helpers import format_currency, get_current_month


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────

_CATEGORY_NAMES = [c[0] for c in DEFAULT_CATEGORIES]
_CATEGORY_ICONS = {c[0]: c[1] for c in DEFAULT_CATEGORIES}
_PAYMENT_METHODS = ["Cash", "Card", "UPI", "Net Banking", "Wallet", "Other"]


def _prev_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the previous month."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


# ───────────────────────────────────────────────────────────────
# Main render
# ───────────────────────────────────────────────────────────────


def render_dashboard() -> None:
    """Render the full dashboard page."""

    st.markdown("## 📊 Dashboard")

    today = date.today()

    # Read the active month from the sidebar selector
    active_month = st.session_state.get("global_month", get_current_month())
    parts = active_month.split("-")
    cur_year, cur_month = int(parts[0]), int(parts[1])
    cur_month_str = active_month
    prev_y, prev_m = _prev_month(cur_year, cur_month)
    is_current = active_month == get_current_month()

    # ── Quick Add Expander (only for current month) ───────────
    if is_current:
        _render_quick_add(cur_month_str)
    else:
        st.info(f"📅 Viewing **{active_month}** — switch to current month to add expenses.")

    # ── Fetch data with spinner ───────────────────────────────
    try:
        with st.spinner("Loading dashboard…"):
            summary = get_monthly_summary(cur_year, cur_month)
            prev_summary = get_monthly_summary(prev_y, prev_m)
            trend_df = get_spending_trend(months=6)
            top_df = get_top_expenses(n=5, month=cur_month_str)
            budgets_df = get_budgets(cur_month_str)
            color_map = get_category_colors()
            all_expenses = get_all_expenses(
                start_date=f"{cur_year}-{cur_month:02d}-01",
                end_date=f"{cur_year}-{cur_month:02d}-31",
            )
    except Exception as exc:
        st.error(f"⚠️ Failed to load dashboard data: {exc}")
        return

    # ── KPI Metrics ───────────────────────────────────────────
    days_ref = today.day if is_current else 30
    _render_kpis(summary, prev_summary, budgets_df, days_ref)

    st.markdown("---")

    # ── Charts Row ────────────────────────────────────────────
    _render_charts_row(trend_df, summary, color_map)

    st.markdown("---")

    # ── Bottom Row: Top Expenses + Heatmap ────────────────────
    _render_bottom_row(top_df, all_expenses, color_map)

    st.markdown("---")

    # ── Budget Gauges ─────────────────────────────────────────
    _render_budget_gauges(budgets_df, summary)


# ───────────────────────────────────────────────────────────────
# Section renderers
# ───────────────────────────────────────────────────────────────


def _render_quick_add(current_month: str) -> None:
    """Inline form to add an expense without navigating away."""

    with st.expander("⚡ Quick Add Expense", expanded=False):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            amount = st.number_input(
                "Amount (₹)", min_value=0.01, step=0.50, value=0.01,
                key="qa_amount",
            )
        with c2:
            category = st.selectbox(
                "Category", _CATEGORY_NAMES, key="qa_category",
            )
        with c3:
            pay_method = st.selectbox(
                "Payment", _PAYMENT_METHODS, key="qa_payment",
            )

        c4, c5 = st.columns([3, 3])
        with c4:
            expense_date = st.date_input(
                "Date", value=date.today(), key="qa_date",
            )
        with c5:
            description = st.text_input(
                "Description", placeholder="e.g. Lunch at Domino's",
                key="qa_desc",
            )

        if st.button("➕ Add Expense", key="qa_submit", use_container_width=True):
            if amount <= 0:
                st.warning("Amount must be greater than zero.")
            elif expense_date > date.today():
                st.warning("⚠️ Date cannot be in the future.")
            else:
                try:
                    add_expense(
                        amount=float(amount),
                        category=category,
                        description=description,
                        date_=str(expense_date),
                        payment_method=pay_method,
                    )
                    st.toast(f"✅ Added {format_currency(amount)} to {category}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Failed to add expense: {exc}")

        st.caption("💡 *Tip: Use the **Expenses** page for full editing, CSV import & more.*")


def _render_kpis(
    summary: pd.DataFrame,
    prev_summary: pd.DataFrame,
    budgets_df: pd.DataFrame,
    days_elapsed: int,
) -> None:
    """Render the 4 KPI metric cards."""

    total_this = summary["total"].sum() if not summary.empty else 0
    total_prev = prev_summary["total"].sum() if not prev_summary.empty else 0
    delta = total_this - total_prev

    # Biggest category
    if not summary.empty:
        top_row = summary.iloc[0]
        biggest_cat = f"{_CATEGORY_ICONS.get(top_row['category'], '')} {top_row['category']}"
        biggest_amt = top_row["total"]
    else:
        biggest_cat = "—"
        biggest_amt = 0

    # Daily average
    daily_avg = total_this / days_elapsed if days_elapsed > 0 else 0

    # Remaining budget
    total_budget = budgets_df["monthly_limit"].sum() if not budgets_df.empty else 0
    remaining = total_budget - total_this

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric(
            label="Total This Month",
            value=format_currency(total_this),
            delta=f"{format_currency(abs(delta))} {'↑' if delta >= 0 else '↓'}",
            delta_color="inverse",
        )
    with k2:
        st.metric(
            label="Biggest Category",
            value=biggest_cat,
            delta=format_currency(biggest_amt) if biggest_amt else None,
            delta_color="off",
        )
    with k3:
        st.metric(
            label="Daily Average",
            value=format_currency(daily_avg),
            delta=f"{days_elapsed} days elapsed",
            delta_color="off",
        )
    with k4:
        if total_budget > 0:
            st.metric(
                label="Remaining Budget",
                value=format_currency(remaining),
                delta="Over budget!" if remaining < 0 else "On track",
                delta_color="inverse" if remaining < 0 else "normal",
            )
        else:
            st.metric(
                label="Remaining Budget",
                value="—",
                delta="No budgets set",
                delta_color="off",
            )


def _render_charts_row(
    trend_df: pd.DataFrame,
    summary: pd.DataFrame,
    color_map: dict,
) -> None:
    """Render the monthly bar chart and donut chart side by side."""

    col_left, col_right = st.columns([3, 2])

    with col_left:
        if trend_df.empty:
            st.info("📈 No spending data yet — add some expenses to see trends!")
        else:
            fig = monthly_bar_chart(trend_df)
            st.plotly_chart(fig, use_container_width=True, key="dash_bar")

    with col_right:
        if summary.empty:
            st.info("🍩 Add expenses this month to see the category breakdown!")
        else:
            fig = donut_chart(summary, color_map=color_map)
            st.plotly_chart(fig, use_container_width=True, key="dash_donut")


def _render_bottom_row(
    top_df: pd.DataFrame,
    all_expenses: pd.DataFrame,
    color_map: dict,
) -> None:
    """Render top expenses table and calendar heatmap."""

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### 🏆 Top 5 Expenses")
        if top_df.empty:
            st.info("💸 No expenses recorded this month yet.")
        else:
            display_df = top_df[["date", "category", "description", "amount", "payment_method"]].copy()
            display_df["amount"] = display_df["amount"].apply(lambda v: format_currency(v))
            display_df["category"] = display_df["category"].apply(
                lambda c: f"{_CATEGORY_ICONS.get(c, '')} {c}"
            )
            display_df.columns = ["Date", "Category", "Description", "Amount", "Payment"]
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

    with col_right:
        st.markdown("### 🗓️ Spending Heatmap")
        if all_expenses.empty:
            st.info("📅 No data for the heatmap — start logging expenses!")
        else:
            heatmap_df = all_expenses[["date", "amount"]].copy()
            fig = calendar_heatmap(heatmap_df)
            st.plotly_chart(fig, use_container_width=True, key="dash_heatmap")


def _render_budget_gauges(
    budgets_df: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    """Render budget gauge charts in a 3-column grid."""

    st.markdown("### 🎯 Budget Progress")

    if budgets_df.empty:
        st.info(
            "💡 No budgets set for this month. "
            "Head over to the **Budget** page to set spending limits!"
        )
        return

    # Build a lookup: category → spent
    spent_map: dict[str, float] = {}
    if not summary.empty:
        for _, row in summary.iterrows():
            spent_map[row["category"]] = row["total"]

    # Render gauges in rows of 3
    budget_rows = budgets_df.to_dict("records")
    for i in range(0, len(budget_rows), 3):
        chunk = budget_rows[i : i + 3]
        cols = st.columns(3)
        for j, record in enumerate(chunk):
            cat = record["category"]
            limit = record["monthly_limit"]
            spent = spent_map.get(cat, 0)
            with cols[j]:
                fig = budget_gauge_chart(cat, spent, limit)
                st.plotly_chart(fig, use_container_width=True, key=f"gauge_{cat}")
