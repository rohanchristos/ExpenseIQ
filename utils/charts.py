"""
charts.py — Plotly Chart Factory Functions

Provides six reusable, dark-themed, interactive chart builders:
  1. donut_chart          – spending by category (donut / pie)
  2. monthly_bar_chart    – monthly totals with gradient bars + trend line
  3. budget_gauge_chart   – single-category gauge indicator
  4. calendar_heatmap     – day-of-week × week spending intensity
  5. category_trend_lines – per-category area lines over months
  6. payment_method_pie   – payment method distribution
"""

from __future__ import annotations

import calendar as _cal
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ───────────────────────────────────────────────────────────────────────────
# Shared defaults
# ───────────────────────────────────────────────────────────────────────────

_FONT_FAMILY = "JetBrains Mono, IBM Plex Mono, monospace"

_COMMON_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=_FONT_FAMILY, size=12),
    margin=dict(t=40, b=20, l=20, r=20),
)

# Default colour sequence (matches seeded category palette)
_DEFAULT_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#82E0AA", "#AED6F1",
]


def _fmt_currency(value: float, symbol: str = "₹") -> str:
    """Format a number as a currency string."""
    if abs(value) >= 1_000:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"


def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    """Convert a hex colour (e.g. '#FF6B6B') to an rgba() string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _apply_common(fig: go.Figure) -> go.Figure:
    """Apply shared layout settings to any figure."""
    fig.update_layout(**_COMMON_LAYOUT)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 1. Donut chart — spending by category
# ═══════════════════════════════════════════════════════════════════════════


def donut_chart(
    df: pd.DataFrame,
    title: str = "Spending by Category",
    color_map: Optional[dict[str, str]] = None,
) -> go.Figure:
    """Return a donut chart of spending per category.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``category`` and ``total``.
    title : str
        Chart title.
    color_map : dict or None
        ``{category_name: hex_color}``.  Falls back to the default
        palette when not provided.

    Returns
    -------
    go.Figure
    """
    df = df.sort_values("total", ascending=False).reset_index(drop=True)

    # Determine per-slice colours
    if color_map:
        colors = [color_map.get(c, "#AED6F1") for c in df["category"]]
    else:
        colors = _DEFAULT_COLORS[: len(df)]

    # Pull the largest slice out slightly
    pull = [0.06 if i == 0 else 0 for i in range(len(df))]

    grand_total = df["total"].sum()

    fig = go.Figure(
        go.Pie(
            labels=df["category"],
            values=df["total"],
            hole=0.55,
            pull=pull,
            marker=dict(colors=colors, line=dict(color="#1a1a2e", width=2)),
            textinfo="percent+label",
            textposition="outside",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Amount: ₹%{value:,.0f}<br>"
                "Share: %{percent}<extra></extra>"
            ),
        )
    )

    # Centered annotation showing total
    fig.add_annotation(
        text=f"<b>{_fmt_currency(grand_total)}</b><br><span style='font-size:11px'>Total</span>",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=18, family=_FONT_FAMILY, color="#EAEAEA"),
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        showlegend=False,
    )
    return _apply_common(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Monthly bar chart with trend line
# ═══════════════════════════════════════════════════════════════════════════


def monthly_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Return a bar chart of monthly spending with a trend overlay.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``month`` (``YYYY-MM``) and ``total``.

    Returns
    -------
    go.Figure
    """
    df = df.sort_values("month").reset_index(drop=True)

    # Normalise values to 0-1 for colorscale mapping
    vmin, vmax = df["total"].min(), df["total"].max()
    if vmax == vmin:
        normed = [0.5] * len(df)
    else:
        normed = ((df["total"] - vmin) / (vmax - vmin)).tolist()

    # Build gradient bar colours using a teal→coral ramp
    bar_colors = [
        f"rgb({int(78 + n * 177)}, {int(205 - n * 100)}, {int(196 - n * 89)})"
        for n in normed
    ]

    fig = go.Figure()

    # Bars
    fig.add_trace(
        go.Bar(
            x=df["month"],
            y=df["total"],
            marker=dict(color=bar_colors, line=dict(color="#1a1a2e", width=1)),
            text=[_fmt_currency(v) for v in df["total"]],
            textposition="outside",
            textfont=dict(size=10, family=_FONT_FAMILY),
            hovertemplate="<b>%{x}</b><br>Total: ₹%{y:,.0f}<extra></extra>",
            name="Monthly Total",
        )
    )

    # Trend line overlay
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["total"],
            mode="lines+markers",
            line=dict(color="#FFEAA7", width=2, dash="dot"),
            marker=dict(size=6, color="#FFEAA7"),
            hoverinfo="skip",
            name="Trend",
        )
    )

    fig.update_layout(
        title=dict(text="Monthly Spending Trend", font=dict(size=16)),
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        showlegend=False,
        bargap=0.3,
    )
    return _apply_common(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Budget gauge chart
# ═══════════════════════════════════════════════════════════════════════════


def budget_gauge_chart(
    category: str, spent: float, budget: float
) -> go.Figure:
    """Return a gauge indicator for one category's budget usage.

    Parameters
    ----------
    category : str
        Category name (used in the title).
    spent : float
        Amount spent so far.
    budget : float
        Budget ceiling for the period.

    Returns
    -------
    go.Figure
    """
    pct = (spent / budget * 100) if budget > 0 else 0

    # Threshold colours
    if pct < 70:
        bar_color = "#82E0AA"   # green
    elif pct < 90:
        bar_color = "#F7DC6F"   # yellow
    else:
        bar_color = "#FF6B6B"   # red

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=spent,
            number=dict(
                prefix="₹",
                font=dict(size=22, family=_FONT_FAMILY),
            ),
            delta=dict(
                reference=budget,
                relative=False,
                increasing=dict(color="#FF6B6B"),
                decreasing=dict(color="#82E0AA"),
                font=dict(size=13),
            ),
            title=dict(
                text=(
                    f"<b>{category}</b><br>"
                    f"<span style='font-size:11px'>"
                    f"{_fmt_currency(spent)} / {_fmt_currency(budget)}  •  {pct:.0f}%"
                    f"</span>"
                ),
                font=dict(size=14, family=_FONT_FAMILY),
            ),
            gauge=dict(
                axis=dict(range=[0, budget * 1.15], tickprefix="₹"),
                bar=dict(color=bar_color, thickness=0.75),
                bgcolor="rgba(255,255,255,0.05)",
                borderwidth=0,
                steps=[
                    dict(range=[0, budget * 0.7], color="rgba(130,224,170,0.15)"),
                    dict(range=[budget * 0.7, budget * 0.9], color="rgba(247,220,111,0.15)"),
                    dict(range=[budget * 0.9, budget * 1.15], color="rgba(255,107,107,0.15)"),
                ],
                threshold=dict(
                    line=dict(color="#EAEAEA", width=2),
                    thickness=0.8,
                    value=budget,
                ),
            ),
        )
    )

    fig.update_layout(height=260)
    return _apply_common(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Calendar heatmap
# ═══════════════════════════════════════════════════════════════════════════


def calendar_heatmap(df: pd.DataFrame) -> go.Figure:
    """Return a day-of-week × week heatmap for spending intensity.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``date`` (``YYYY-MM-DD``) and ``amount``.
        Typically filtered to a single month before calling.

    Returns
    -------
    go.Figure
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate by date in case of multiple expenses per day
    daily = df.groupby("date")["amount"].sum().reset_index()
    daily["dow"] = daily["date"].dt.dayofweek          # 0=Mon … 6=Sun
    daily["week"] = daily["date"].dt.isocalendar().week.astype(int)

    # Build a full grid so empty days show as well
    all_dates = pd.date_range(daily["date"].min(), daily["date"].max())
    grid = pd.DataFrame({"date": all_dates})
    grid["dow"] = grid["date"].dt.dayofweek
    grid["week"] = grid["date"].dt.isocalendar().week.astype(int)
    grid = grid.merge(daily[["date", "amount"]], on="date", how="left").fillna(0)

    # Rebase week numbers to 0-indexed starting from the first week
    min_week = grid["week"].min()
    grid["week_idx"] = grid["week"] - min_week

    # Pivot for heatmap: rows = day-of-week, cols = week index
    pivot = grid.pivot_table(
        index="dow", columns="week_idx", values="amount", aggfunc="sum"
    ).fillna(0)

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Custom hover text
    hover_text = []
    for dow in range(7):
        row_texts = []
        for wk in pivot.columns:
            val = pivot.loc[dow, wk] if dow in pivot.index else 0
            matching = grid[(grid["dow"] == dow) & (grid["week_idx"] == wk)]
            date_str = matching["date"].dt.strftime("%b %d").values[0] if len(matching) > 0 else ""
            row_texts.append(f"{date_str}<br>{_fmt_currency(val)}")
        hover_text.append(row_texts)

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[f"W{int(c) + 1}" for c in pivot.columns],
            y=day_labels[: pivot.shape[0]],
            hovertext=hover_text,
            hovertemplate="%{hovertext}<extra></extra>",
            colorscale=[
                [0.0, "rgba(30,30,60,0.4)"],
                [0.25, "#4ECDC4"],
                [0.5, "#45B7D1"],
                [0.75, "#FFEAA7"],
                [1.0, "#FF6B6B"],
            ],
            showscale=True,
            colorbar=dict(title="₹", tickprefix="₹"),
        )
    )

    fig.update_layout(
        title=dict(text="Daily Spending Heatmap", font=dict(size=16)),
        xaxis_title="Week",
        yaxis=dict(autorange="reversed"),
    )
    return _apply_common(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Category trend lines (area)
# ═══════════════════════════════════════════════════════════════════════════


def category_trend_lines(
    df: pd.DataFrame,
    color_map: Optional[dict[str, str]] = None,
) -> go.Figure:
    """Return an area-line chart with one line per category.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``month``, ``category``, ``total``.
    color_map : dict or None
        ``{category_name: hex_color}``.

    Returns
    -------
    go.Figure
    """
    fig = go.Figure()

    categories = df["category"].unique()
    fallback = {c: _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)] for i, c in enumerate(categories)}
    cmap = color_map or fallback

    for cat in categories:
        sub = df[df["category"] == cat].sort_values("month")
        color = cmap.get(cat, "#AED6F1")
        fig.add_trace(
            go.Scatter(
                x=sub["month"],
                y=sub["total"],
                name=cat,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
                fill="tozeroy",
                fillcolor=_hex_to_rgba(color, 0.12),
                hovertemplate=(
                    f"<b>{cat}</b><br>"
                    "Month: %{x}<br>"
                    "Total: ₹%{y:,.0f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text="Category Trends", font=dict(size=16)),
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font=dict(size=10),
        ),
    )
    return _apply_common(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Payment method pie
# ═══════════════════════════════════════════════════════════════════════════


def payment_method_pie(df: pd.DataFrame) -> go.Figure:
    """Return a pie chart of totals by payment method.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``payment_method`` and ``total``.

    Returns
    -------
    go.Figure
    """
    method_colors = [
        "#4ECDC4", "#FF6B6B", "#FFEAA7", "#45B7D1",
        "#96CEB4", "#DDA0DD", "#82E0AA", "#AED6F1",
    ]

    fig = go.Figure(
        go.Pie(
            labels=df["payment_method"],
            values=df["total"],
            marker=dict(
                colors=method_colors[: len(df)],
                line=dict(color="#1a1a2e", width=2),
            ),
            textinfo="label+percent",
            textposition="outside",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Amount: ₹%{value:,.0f}<br>"
                "Share: %{percent}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(text="Payment Methods", font=dict(size=16)),
        showlegend=False,
    )
    return _apply_common(fig)
