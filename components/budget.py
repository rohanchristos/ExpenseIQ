"""
budget.py — Budget Management Page

Provides:
  render_budget()  — full budget management with:
    1. Month selector (current + past months read-only)
    2. Budget setup grid (number inputs per category)
    3. Budget status dashboard (gauge charts + progress bars)
    4. Budget recommendations based on historical averages
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from db.database import DEFAULT_CATEGORIES
from db.queries import (
    get_all_expenses,
    get_budgets,
    get_category_colors,
    get_monthly_summary,
    set_budget,
)
from utils.charts import budget_gauge_chart
from utils.helpers import format_currency, get_current_month, get_month_options


# ───────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────

_CATEGORY_NAMES = [c[0] for c in DEFAULT_CATEGORIES]
_CATEGORY_ICONS = {c[0]: c[1] for c in DEFAULT_CATEGORIES}


# ───────────────────────────────────────────────────────────────
# Main render
# ───────────────────────────────────────────────────────────────


def render_budget() -> None:
    """Render the full budget management page."""

    st.markdown("## 🎯 Budget Manager")

    # ── Month selector ────────────────────────────────────────
    current_month = get_current_month()
    months = get_month_options(n=12)

    # Default to the sidebar's active month
    global_month = st.session_state.get("global_month", current_month)
    default_idx = months.index(global_month) if global_month in months else 0

    selected_month = st.selectbox(
        "Select Month", months, index=default_idx, key="budget_month",
    )

    is_current = selected_month == current_month
    if not is_current:
        st.info(f"📅 Viewing **{selected_month}** (read-only for past months)")

    st.markdown("---")

    # ── Load data ─────────────────────────────────────────────
    try:
        with st.spinner("Loading budgets…"):
            budgets_df = get_budgets(selected_month)

            # Parse year/month for summary
            parts = selected_month.split("-")
            year, month = int(parts[0]), int(parts[1])
            summary = get_monthly_summary(year, month)
            color_map = get_category_colors()
    except Exception as exc:
        st.error(f"⚠️ Failed to load budget data: {exc}")
        return

    # Build lookup dicts
    budget_map: dict[str, float] = {}
    if not budgets_df.empty:
        for _, row in budgets_df.iterrows():
            budget_map[row["category"]] = row["monthly_limit"]

    spent_map: dict[str, float] = {}
    if not summary.empty:
        for _, row in summary.iterrows():
            spent_map[row["category"]] = row["total"]

    # ── Budget Status Dashboard ───────────────────────────────
    if budget_map:
        _render_status_dashboard(budget_map, spent_map, color_map)
        st.markdown("---")

    # ── Budget Setup (editable only for current month) ────────
    if is_current:
        _render_budget_setup(budget_map, selected_month)
        st.markdown("---")
        _render_recommendations(selected_month, budget_map)
    else:
        _render_past_month_summary(budget_map, spent_map)


# ═══════════════════════════════════════════════════════════════
# Budget Status Dashboard
# ═══════════════════════════════════════════════════════════════


def _render_status_dashboard(
    budget_map: dict[str, float],
    spent_map: dict[str, float],
    color_map: dict[str, str],
) -> None:
    """Gauge charts + progress bars, sorted by most overspent first."""

    st.markdown("### 📊 Budget Status")

    # Build list and sort by overspent percentage descending
    items: list[dict] = []
    for cat, limit in budget_map.items():
        spent = spent_map.get(cat, 0)
        pct = (spent / limit * 100) if limit > 0 else 0
        items.append({
            "category": cat,
            "limit": limit,
            "spent": spent,
            "remaining": limit - spent,
            "pct": pct,
        })

    items.sort(key=lambda x: x["pct"], reverse=True)

    # Render in rows of 3
    for i in range(0, len(items), 3):
        chunk = items[i : i + 3]
        cols = st.columns(3)

        for j, item in enumerate(chunk):
            cat = item["category"]
            spent = item["spent"]
            limit = item["limit"]
            remaining = item["remaining"]
            pct = item["pct"]
            icon = _CATEGORY_ICONS.get(cat, "📌")

            with cols[j]:
                # Gauge chart
                fig = budget_gauge_chart(f"{icon} {cat}", spent, limit)
                st.plotly_chart(fig, use_container_width=True, key=f"bg_{cat}")

                # Progress bar
                bar_pct = min(pct / 100, 1.0)
                st.progress(bar_pct)

                # Status text
                if remaining < 0:
                    st.markdown(
                        f"<span style='color:#FF4757;font-weight:700'>"
                        f"⚠️ Over by {format_currency(abs(remaining))}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"💚 {format_currency(remaining)} remaining")

    if not items:
        st.info("No budgets set. Use the form below to set budgets for categories.")


# ═══════════════════════════════════════════════════════════════
# Budget Setup Grid
# ═══════════════════════════════════════════════════════════════


def _render_budget_setup(budget_map: dict[str, float], month: str) -> None:
    """Grid of number inputs for setting budgets per category."""

    st.markdown("### ⚙️ Set Monthly Budgets")
    st.caption("Set a monthly spending limit for each category. Leave 0 to skip.")

    new_budgets: dict[str, float] = {}

    # 3-column grid
    for i in range(0, len(_CATEGORY_NAMES), 3):
        chunk = _CATEGORY_NAMES[i : i + 3]
        cols = st.columns(3)

        for j, cat in enumerate(chunk):
            icon = _CATEGORY_ICONS.get(cat, "📌")
            current = budget_map.get(cat, 0.0)

            with cols[j]:
                val = st.number_input(
                    f"{icon} {cat}",
                    min_value=0.0,
                    step=500.0,
                    value=float(current),
                    format="%.0f",
                    key=f"budget_input_{cat}",
                )
                new_budgets[cat] = val

    # Save button
    if st.button("💾 Save All Budgets", use_container_width=True, key="save_budgets"):
        saved = 0
        try:
            for cat, limit in new_budgets.items():
                if limit > 0:
                    set_budget(cat, limit, month)
                    saved += 1

            if saved > 0:
                st.toast(f"✅ Saved budgets for {saved} categories")
                st.rerun()
            else:
                st.warning("No budgets to save — set at least one value above 0.")
        except Exception as exc:
            st.error(f"❌ Failed to save budgets: {exc}")


# ═══════════════════════════════════════════════════════════════
# Budget Recommendations
# ═══════════════════════════════════════════════════════════════


def _render_recommendations(month: str, current_budgets: dict[str, float]) -> None:
    """Suggest budgets based on last 3 months average spending."""

    st.markdown("### 🤖 Smart Recommendations")
    st.caption("Based on your average spending over the last 3 months")

    today = date.today()
    suggestions: dict[str, float] = {}

    # Compute 3-month average per category
    for offset in range(1, 4):
        y = today.year
        m = today.month - offset
        while m <= 0:
            m += 12
            y -= 1
        month_summary = get_monthly_summary(y, m)
        if not month_summary.empty:
            for _, row in month_summary.iterrows():
                cat = row["category"]
                suggestions[cat] = suggestions.get(cat, 0) + row["total"]

    # Average over 3 months, round up to nearest 500
    for cat in suggestions:
        avg = suggestions[cat] / 3
        suggestions[cat] = _round_up(avg, 500)

    if not suggestions:
        st.info("📊 Not enough historical data to generate recommendations yet.")
        return

    # Display suggestions
    cols_header = st.columns([3, 2, 2, 2])
    cols_header[0].markdown("**Category**")
    cols_header[1].markdown("**3-Month Avg**")
    cols_header[2].markdown("**Suggested**")
    cols_header[3].markdown("**Current**")

    for cat, suggested in sorted(suggestions.items()):
        icon = _CATEGORY_ICONS.get(cat, "📌")
        current = current_budgets.get(cat, 0)
        avg_raw = suggested  # already rounded

        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.markdown(f"{icon} **{cat}**")
        c2.markdown(format_currency(avg_raw))
        c3.markdown(f"**{format_currency(suggested)}**")
        c4.markdown(
            format_currency(current) if current > 0 else "—"
        )

    if st.button(
        "✨ Apply All Suggestions", use_container_width=True,
        key="apply_suggestions",
    ):
        try:
            applied = 0
            for cat, suggested in suggestions.items():
                set_budget(cat, suggested, month)
                applied += 1
            st.toast(f"✅ Applied budgets for {applied} categories")
            st.rerun()
        except Exception as exc:
            st.error(f"❌ Failed to apply suggestions: {exc}")


# ═══════════════════════════════════════════════════════════════
# Past Month Read-Only View
# ═══════════════════════════════════════════════════════════════


def _render_past_month_summary(
    budget_map: dict[str, float],
    spent_map: dict[str, float],
) -> None:
    """Read-only summary of budgets for a past month."""

    st.markdown("### 📋 Budget Summary (Read-Only)")

    if not budget_map:
        st.info("No budgets were set for this month.")
        return

    rows = []
    for cat, limit in sorted(budget_map.items()):
        spent = spent_map.get(cat, 0)
        remaining = limit - spent
        pct = (spent / limit * 100) if limit > 0 else 0
        icon = _CATEGORY_ICONS.get(cat, "📌")
        status = "🔴 Over" if remaining < 0 else "🟢 OK"
        rows.append({
            "Category": f"{icon} {cat}",
            "Budget": format_currency(limit),
            "Spent": format_currency(spent),
            "Remaining": format_currency(remaining),
            "Used %": f"{pct:.0f}%",
            "Status": status,
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────


def _round_up(value: float, step: float) -> float:
    """Round *value* up to the nearest *step*."""
    import math
    return math.ceil(value / step) * step
