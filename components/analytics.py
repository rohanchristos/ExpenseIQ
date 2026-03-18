"""
analytics.py — Charts & Insights Page

Provides:
  render_analytics()    — deep insights with 4 tabs
  generate_insights(df) — automatic insight strings from expense data
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db.database import DEFAULT_CATEGORIES
from db.queries import (
    get_all_expenses,
    get_category_colors,
    get_monthly_summary,
    get_spending_trend,
)
from utils.charts import (
    category_trend_lines,
    monthly_bar_chart,
    payment_method_pie,
    _apply_common,
    _FONT_FAMILY,
)
from utils.helpers import format_currency, format_date


# ───────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────

_CATEGORY_NAMES = [c[0] for c in DEFAULT_CATEGORIES]
_CATEGORY_ICONS = {c[0]: c[1] for c in DEFAULT_CATEGORIES}

_PERIOD_OPTIONS = {
    "Last 30 days": 30,
    "Last 3 months": 90,
    "Last 6 months": 180,
    "Last 1 year": 365,
    "Custom": None,
}


# ───────────────────────────────────────────────────────────────
# Main render
# ───────────────────────────────────────────────────────────────


def render_analytics() -> None:
    """Render the analytics / insights page."""

    st.markdown("## 📈 Analytics")

    # ── Date range selector ───────────────────────────────────
    start_date, end_date = _render_date_selector()

    # ── Load data ─────────────────────────────────────────────
    with st.spinner("Crunching numbers…"):
        df = get_all_expenses(start_date=str(start_date), end_date=str(end_date))
        color_map = get_category_colors()

    if df.empty:
        st.info("📊 No expense data for this period. Add some expenses first!")
        return

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Spending Overview",
        "🔍 Category Deep Dive",
        "💡 Insights",
        "📅 Yearly Summary",
    ])

    with tab1:
        _render_spending_overview(df, color_map)
    with tab2:
        _render_category_dive(df, color_map, start_date, end_date)
    with tab3:
        _render_insights(df)
    with tab4:
        _render_yearly_summary(df, color_map)


# ═══════════════════════════════════════════════════════════════
# Date range selector
# ═══════════════════════════════════════════════════════════════


def _render_date_selector() -> tuple[date, date]:
    """Render period selector and return (start_date, end_date)."""

    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        period = st.selectbox(
            "Period", list(_PERIOD_OPTIONS.keys()), index=2, key="ana_period",
        )

    today = date.today()
    days = _PERIOD_OPTIONS[period]

    if days is not None:
        start = today - timedelta(days=days)
        end = today
    else:
        with c2:
            start = st.date_input("From", value=today - timedelta(days=180), key="ana_start")
        with c3:
            end = st.date_input("To", value=today, key="ana_end")

    return start, end


# ═══════════════════════════════════════════════════════════════
# Tab 1 — Spending Overview
# ═══════════════════════════════════════════════════════════════


def _render_spending_overview(df: pd.DataFrame, color_map: dict) -> None:
    """Category trends, monthly bar, and payment pie."""

    # --- Category trend lines ---
    st.markdown("### Category Trends")
    cat_monthly = (
        df.assign(month=pd.to_datetime(df["date"]).dt.to_period("M").astype(str))
        .groupby(["month", "category"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    if not cat_monthly.empty:
        fig = category_trend_lines(cat_monthly, color_map=color_map)
        st.plotly_chart(fig, use_container_width=True, key="ana_trends")
    else:
        st.info("Not enough data for trend lines.")

    st.markdown("---")

    # --- Monthly bar + Payment pie side by side ---
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("### Monthly Totals")
        monthly = (
            df.assign(month=pd.to_datetime(df["date"]).dt.to_period("M").astype(str))
            .groupby("month")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "total"})
        )
        if not monthly.empty:
            fig = monthly_bar_chart(monthly)
            st.plotly_chart(fig, use_container_width=True, key="ana_bar")
        else:
            st.info("No monthly data.")

    with col_r:
        st.markdown("### Payment Methods")
        pay_totals = (
            df.groupby("payment_method")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "total"})
        )
        if not pay_totals.empty:
            fig = payment_method_pie(pay_totals)
            st.plotly_chart(fig, use_container_width=True, key="ana_pie")
        else:
            st.info("No payment data.")


# ═══════════════════════════════════════════════════════════════
# Tab 2 — Category Deep Dive
# ═══════════════════════════════════════════════════════════════


def _render_category_dive(
    df: pd.DataFrame,
    color_map: dict,
    start_date: date,
    end_date: date,
) -> None:
    """Deep dive into a single category."""

    available_cats = sorted(df["category"].unique().tolist())
    if not available_cats:
        st.info("No categories with spending in this period.")
        return

    display_opts = [f"{_CATEGORY_ICONS.get(c, '')} {c}" for c in available_cats]
    selected_display = st.selectbox("Pick a category", display_opts, key="ana_cat_sel")
    selected_cat = selected_display.split(" ", 1)[-1].strip()

    cat_df = df[df["category"] == selected_cat].copy()

    if cat_df.empty:
        st.info(f"No expenses in **{selected_cat}** for this period.")
        return

    # --- KPI cards ---
    total = cat_df["amount"].sum()
    count = len(cat_df)
    avg = cat_df["amount"].mean()
    max_val = cat_df["amount"].max()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Spent", format_currency(total))
    with k2:
        st.metric("Transactions", f"{count}")
    with k3:
        st.metric("Avg / Transaction", format_currency(avg))
    with k4:
        st.metric("Largest Expense", format_currency(max_val))

    st.markdown("---")

    # --- Line chart over time ---
    st.markdown(f"### {_CATEGORY_ICONS.get(selected_cat, '')} {selected_cat} Over Time")

    daily = (
        cat_df.groupby("date")["amount"]
        .sum()
        .reset_index()
        .sort_values("date")
    )

    color = color_map.get(selected_cat, "#00D4AA")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["amount"],
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.10)",
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT_FAMILY, size=12),
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis_title="Date",
        yaxis_title="Amount (₹)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="ana_cat_line")

    # --- Transaction list ---
    with st.expander(f"📋 All {count} transactions in {selected_cat}"):
        show_df = cat_df[["date", "description", "amount", "payment_method"]].copy()
        show_df["amount"] = show_df["amount"].apply(format_currency)
        show_df.columns = ["Date", "Description", "Amount", "Payment"]
        st.dataframe(show_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# Tab 3 — Automatic Insights
# ═══════════════════════════════════════════════════════════════


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Analyse *df* and return a list of human-readable insight strings.

    Parameters
    ----------
    df : pd.DataFrame
        Expense records with columns: date, category, amount,
        payment_method, description.

    Returns
    -------
    list[str]
        Each item is a single-line insight prefixed with an emoji.
    """
    insights: list[str] = []
    if df.empty:
        return insights

    today = date.today()
    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"])
    df["_month"] = df["_date"].dt.to_period("M")

    cur_period = pd.Period(today, freq="M")
    prev_period = cur_period - 1

    cur_df = df[df["_month"] == cur_period]
    prev_df = df[df["_month"] == prev_period]

    # ── Category month-over-month ──────────────────────────────
    if not cur_df.empty and not prev_df.empty:
        cur_by_cat = cur_df.groupby("category")["amount"].sum()
        prev_by_cat = prev_df.groupby("category")["amount"].sum()

        for cat in cur_by_cat.index:
            cur_val = cur_by_cat[cat]
            prev_val = prev_by_cat.get(cat, 0)
            if prev_val > 0:
                pct = ((cur_val - prev_val) / prev_val) * 100
                icon = _CATEGORY_ICONS.get(cat, "📌")
                if pct > 0:
                    insights.append(
                        f"📈 You spent **{pct:.0f}% more** on {icon} **{cat}** "
                        f"this month vs last month "
                        f"({format_currency(cur_val)} vs {format_currency(prev_val)})"
                    )
                elif pct < -10:
                    insights.append(
                        f"📉 Great! You spent **{abs(pct):.0f}% less** on {icon} **{cat}** "
                        f"this month ({format_currency(cur_val)} vs {format_currency(prev_val)})"
                    )

    # ── Highest spending day ───────────────────────────────────
    daily_totals = df.groupby("date")["amount"].sum()
    if not daily_totals.empty:
        top_day = daily_totals.idxmax()
        top_amt = daily_totals.max()
        insights.append(
            f"🔥 Your highest spending day was **{format_date(str(top_day))}** "
            f"with **{format_currency(top_amt)}**"
        )

    # ── Projected monthly spending ─────────────────────────────
    if not cur_df.empty:
        days_elapsed = today.day
        total_so_far = cur_df["amount"].sum()
        if days_elapsed > 0:
            import calendar
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            projected = (total_so_far / days_elapsed) * days_in_month
            insights.append(
                f"🎯 At your current pace, you'll spend roughly "
                f"**{format_currency(projected)}** this month "
                f"(spent {format_currency(total_so_far)} in {days_elapsed} days)"
            )

    # ── Most used payment method ───────────────────────────────
    if not df.empty:
        pay_counts = df["payment_method"].value_counts()
        top_pay = pay_counts.index[0]
        top_pct = (pay_counts.iloc[0] / len(df)) * 100
        insights.append(
            f"💳 **{top_pay}** is your most used payment method "
            f"(**{top_pct:.0f}%** of {len(df)} transactions)"
        )

    # ── Biggest single expense ─────────────────────────────────
    if not df.empty:
        idx_max = df["amount"].idxmax()
        row = df.loc[idx_max]
        insights.append(
            f"💰 Your biggest single expense: **{format_currency(row['amount'])}** "
            f"on {_CATEGORY_ICONS.get(row['category'], '')} {row['category']} "
            f"— \"{row['description']}\" ({format_date(str(row['date']))})"
        )

    # ── Average daily spending ─────────────────────────────────
    if not df.empty:
        unique_days = df["date"].nunique()
        total_all = df["amount"].sum()
        if unique_days > 0:
            avg_daily = total_all / unique_days
            insights.append(
                f"📊 You spend an average of **{format_currency(avg_daily)}/day** "
                f"across {unique_days} active days"
            )

    return insights


def _render_insights(df: pd.DataFrame) -> None:
    """Show auto-generated insights as styled cards."""

    st.markdown("### 💡 Smart Insights")

    insights = generate_insights(df)

    if not insights:
        st.info("🤔 Not enough data to generate insights yet. Keep tracking!")
        return

    for insight in insights:
        st.info(insight)


# ═══════════════════════════════════════════════════════════════
# Tab 4 — Yearly Summary
# ═══════════════════════════════════════════════════════════════


def _render_yearly_summary(df: pd.DataFrame, color_map: dict) -> None:
    """12-month × category heatmap + year-over-year comparison."""

    st.markdown("### 📅 Yearly Spending Matrix")

    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"])
    df["month"] = df["_date"].dt.to_period("M").astype(str)
    df["year"] = df["_date"].dt.year

    # --- Heatmap: months × categories ---
    pivot = df.pivot_table(
        index="category", columns="month", values="amount",
        aggfunc="sum", fill_value=0,
    )

    if pivot.empty:
        st.info("Not enough data for a yearly matrix.")
        return

    # Sort columns chronologically
    pivot = pivot[sorted(pivot.columns)]

    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        color_continuous_scale=[
            [0.0, "rgba(30,30,60,0.5)"],
            [0.25, "#4ECDC4"],
            [0.5, "#45B7D1"],
            [0.75, "#FFEAA7"],
            [1.0, "#FF6B6B"],
        ],
        aspect="auto",
        labels=dict(x="Month", y="Category", color="Amount (₹)"),
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT_FAMILY, size=12),
        margin=dict(t=30, b=20, l=20, r=20),
        coloraxis_colorbar=dict(title="₹", tickprefix="₹"),
    )
    st.plotly_chart(fig, use_container_width=True, key="ana_yearly_heatmap")

    # --- Year-over-year comparison ---
    years = sorted(df["year"].unique())
    if len(years) >= 2:
        st.markdown("---")
        st.markdown("### 📊 Year-over-Year Comparison")

        yearly_totals = df.groupby("year")["amount"].sum().reset_index()
        yearly_totals.columns = ["Year", "Total"]

        c1, c2 = st.columns([1, 1])

        with c1:
            for _, row in yearly_totals.iterrows():
                st.metric(
                    label=f"Total in {int(row['Year'])}",
                    value=format_currency(row["Total"]),
                )

        with c2:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=yearly_totals["Year"].astype(str),
                y=yearly_totals["Total"],
                marker=dict(
                    color=["#4ECDC4", "#FF6B6B", "#FFEAA7", "#45B7D1"][:len(years)],
                    line=dict(color="#1a1a2e", width=1),
                ),
                text=[format_currency(v) for v in yearly_totals["Total"]],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=_FONT_FAMILY, size=12),
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False,
                yaxis_title="Amount (₹)",
            )
            st.plotly_chart(fig, use_container_width=True, key="ana_yoy_bar")
    else:
        st.caption("Year-over-year comparison will appear once you have data across multiple years.")
