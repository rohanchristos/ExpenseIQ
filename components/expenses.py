"""
expenses.py — Add / Edit / Delete Expense Page

Provides:
  render_expenses()  — full expense management with:
    1. Add expense form (st.form)
    2. Filter bar (date range, category, payment, search)
    3. Expenses table with inline edit & delete
    4. Bulk actions (CSV export, summary stats)
    5. CSV import with validation & preview
"""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db.database import DEFAULT_CATEGORIES, get_connection
from db.queries import (
    add_expense,
    delete_expense,
    get_all_expenses,
    update_expense,
)
from utils.helpers import format_currency


# ───────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────

_CATEGORY_NAMES = [c[0] for c in DEFAULT_CATEGORIES]
_CATEGORY_ICONS = {c[0]: c[1] for c in DEFAULT_CATEGORIES}
_CATEGORY_DISPLAY = [f"{c[1]} {c[0]}" for c in DEFAULT_CATEGORIES]
_DISPLAY_TO_NAME = {f"{c[1]} {c[0]}": c[0] for c in DEFAULT_CATEGORIES}
_PAYMENT_METHODS = ["Cash", "UPI", "Card", "Net Banking", "Wallet", "Other"]
_REQUIRED_CSV_COLS = {"amount", "category", "description", "date"}


# ───────────────────────────────────────────────────────────────
# Main render
# ───────────────────────────────────────────────────────────────


def render_expenses() -> None:
    """Render the full expense management page."""

    st.markdown("## 💸 Expenses")

    # ── 1. Add Expense Form ───────────────────────────────────
    _render_add_form()

    st.markdown("---")

    # ── 2. Filter Bar ─────────────────────────────────────────
    filters = _render_filter_bar()

    # ── 3. Load & display data ────────────────────────────────
    with st.spinner("Loading expenses…"):
        df = _fetch_filtered(filters)

    if df.empty:
        st.info("📭 No expenses match your filters. Try adjusting or add some!")
        return

    # ── 4. Expenses Table + Actions ───────────────────────────
    _render_expenses_table(df)

    st.markdown("---")

    # ── 5. Bulk Actions ───────────────────────────────────────
    _render_bulk_actions(df)

    st.markdown("---")

    # ── 6. CSV Import ─────────────────────────────────────────
    _render_csv_import()


# ═══════════════════════════════════════════════════════════════
# 1. Add Expense Form
# ═══════════════════════════════════════════════════════════════


def _render_add_form() -> None:
    """Add-expense form wrapped in st.form to prevent premature reruns."""

    with st.form("add_expense_form", clear_on_submit=True):
        st.markdown("### ➕ Add New Expense")

        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input(
                "Amount (₹)", min_value=0.01, step=0.01, value=0.01,
                format="%.2f",
            )
            category_display = st.selectbox("Category", _CATEGORY_DISPLAY)
            expense_date = st.date_input("Date", value=date.today())

        with c2:
            description = st.text_input(
                "Description", placeholder="e.g. Coffee at Starbucks",
            )
            pay_method = st.radio(
                "Payment Method", _PAYMENT_METHODS, horizontal=True,
            )

        submitted = st.form_submit_button(
            "💾 Save Expense", use_container_width=True,
        )

        if submitted:
            if amount <= 0:
                st.warning("⚠️ Amount must be greater than zero.")
                return
            if expense_date > date.today():
                st.warning("⚠️ Date cannot be in the future.")
                return

            category = _DISPLAY_TO_NAME.get(category_display, category_display)

            try:
                new_id = add_expense(
                    amount=float(amount),
                    category=category,
                    description=description,
                    date_=str(expense_date),
                    payment_method=pay_method,
                )

                icon = _CATEGORY_ICONS.get(category, "✅")
                st.toast(f"{icon} Added {format_currency(amount)} to {category}")

                # First expense celebration
                total_count = len(get_all_expenses())
                if total_count == 1:
                    st.balloons()
                    st.info("🎉 Your first expense! Keep tracking to see insights.")

                st.rerun()
            except Exception as exc:
                st.error(f"❌ Failed to add expense: {exc}")


# ═══════════════════════════════════════════════════════════════
# 2. Filter Bar
# ═══════════════════════════════════════════════════════════════


def _render_filter_bar() -> dict:
    """Render filter controls and return the active filters."""

    st.markdown("### 🔍 Filter Expenses")

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

    with c1:
        start_date = st.date_input(
            "From",
            value=date.today().replace(day=1),
            key="filter_start",
        )
    with c2:
        end_date = st.date_input(
            "To",
            value=date.today(),
            key="filter_end",
        )
    with c3:
        cat_filter = st.multiselect(
            "Categories", _CATEGORY_NAMES, default=[], key="filter_cats",
        )
    with c4:
        pay_filter = st.multiselect(
            "Payment", _PAYMENT_METHODS, default=[], key="filter_pay",
        )

    search = st.text_input(
        "🔎 Search description…", key="filter_search",
        placeholder="Type keywords to search",
    )

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "categories": cat_filter,
        "payments": pay_filter,
        "search": search.strip().lower(),
    }


def _fetch_filtered(filters: dict) -> pd.DataFrame:
    """Fetch expenses and apply all active filters."""

    try:
        df = get_all_expenses(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )
    except Exception as exc:
        st.error(f"⚠️ Failed to load expenses: {exc}")
        return pd.DataFrame()

    if df.empty:
        return df

    if filters["categories"]:
        df = df[df["category"].isin(filters["categories"])]

    if filters["payments"]:
        df = df[df["payment_method"].isin(filters["payments"])]

    if filters["search"]:
        mask = df["description"].str.lower().str.contains(
            filters["search"], na=False,
        )
        df = df[mask]

    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# 3. Expenses Table
# ═══════════════════════════════════════════════════════════════


def _render_expenses_table(df: pd.DataFrame) -> None:
    """Render the expenses table with edit and delete support."""

    st.markdown("### 📋 Expense Records")
    st.caption(f"Showing **{len(df)}** expenses")

    # Prepare display copy
    display = df[["id", "date", "category", "description", "amount",
                   "payment_method"]].copy()

    # Add category icons
    display["category"] = display["category"].apply(
        lambda c: f"{_CATEGORY_ICONS.get(c, '')} {c}"
    )

    # Rename columns for display
    display.columns = ["ID", "Date", "Category", "Description", "Amount", "Payment"]

    # Color-code amounts using pandas Styler
    def _color_amount(val):
        if val >= 5000:
            return "color: #FF4757; font-weight: 700;"
        elif val >= 1000:
            return "color: #FFA502; font-weight: 600;"
        return "color: #E8EDF2;"

    styled = (
        display.style
        .applymap(_color_amount, subset=["Amount"])
        .format({"Amount": "₹{:,.2f}"})
    )

    st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

    # ── Edit / Delete Section ─────────────────────────────────
    st.markdown("---")
    _render_edit_delete(df)


def _render_edit_delete(df: pd.DataFrame) -> None:
    """Render edit and delete controls for individual expenses."""

    with st.expander("✏️ Edit or 🗑️ Delete an Expense"):
        if df.empty:
            st.info("No expenses to edit.")
            return

        # Build options list
        options = {
            row["id"]: (
                f"#{row['id']}  |  {row['date']}  |  "
                f"{_CATEGORY_ICONS.get(row['category'], '')} {row['category']}  |  "
                f"{format_currency(row['amount'])}  |  {row['description'][:30]}"
            )
            for _, row in df.iterrows()
        }

        selected_label = st.selectbox(
            "Select expense", list(options.values()), key="edit_select",
        )

        # Reverse-lookup the id
        selected_id = None
        for eid, label in options.items():
            if label == selected_label:
                selected_id = eid
                break

        if selected_id is None:
            return

        row = df[df["id"] == selected_id].iloc[0]

        st.markdown("#### Edit Fields")

        ec1, ec2 = st.columns(2)
        with ec1:
            new_amount = st.number_input(
                "Amount", value=float(row["amount"]),
                min_value=0.01, step=0.01, key="edit_amount",
            )
            cat_idx = _CATEGORY_NAMES.index(row["category"]) if row["category"] in _CATEGORY_NAMES else 0
            new_cat_display = st.selectbox(
                "Category", _CATEGORY_DISPLAY, index=cat_idx, key="edit_cat",
            )
            new_date = st.date_input(
                "Date", value=date.fromisoformat(row["date"]), key="edit_date",
            )

        with ec2:
            new_desc = st.text_input(
                "Description", value=row["description"], key="edit_desc",
            )
            pay_idx = _PAYMENT_METHODS.index(row["payment_method"]) if row["payment_method"] in _PAYMENT_METHODS else 0
            new_pay = st.selectbox(
                "Payment", _PAYMENT_METHODS, index=pay_idx, key="edit_pay",
            )

        bc1, bc2 = st.columns(2)

        with bc1:
            if st.button("💾 Save Changes", key="edit_save", use_container_width=True):
                try:
                    new_cat = _DISPLAY_TO_NAME.get(new_cat_display, new_cat_display)
                    updated = update_expense(
                        selected_id,
                        amount=float(new_amount),
                        category=new_cat,
                        description=new_desc,
                        date=str(new_date),
                        payment_method=new_pay,
                    )
                    if updated:
                        st.toast("✅ Expense updated!")
                        st.rerun()
                    else:
                        st.error("❌ Update failed — expense not found.")
                except Exception as exc:
                    st.error(f"❌ Update error: {exc}")

        with bc2:
            # Two-step delete: first click sets a session flag, second confirms
            delete_key = f"confirm_delete_{selected_id}"
            if st.session_state.get(delete_key, False):
                st.warning(f"⚠️ Are you sure you want to delete #{selected_id}?")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("✅ Yes, delete", key=f"del_yes_{selected_id}"):
                        try:
                            delete_expense(selected_id)
                            st.session_state.pop(delete_key, None)
                            st.toast("🗑️ Expense deleted")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"❌ Delete error: {exc}")
                with dc2:
                    if st.button("❌ Cancel", key=f"del_no_{selected_id}"):
                        st.session_state.pop(delete_key, None)
                        st.rerun()
            else:
                if st.button(
                    "🗑️ Delete Expense", key="edit_delete",
                    use_container_width=True,
                ):
                    st.session_state[delete_key] = True
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# 4. Bulk Actions
# ═══════════════════════════════════════════════════════════════


def _render_bulk_actions(df: pd.DataFrame) -> None:
    """Export CSV + summary stats."""

    st.markdown("### 📦 Bulk Actions")

    c1, c2, c3, c4 = st.columns(4)

    total = df["amount"].sum()
    avg = df["amount"].mean()
    max_val = df["amount"].max()
    count = len(df)

    with c1:
        st.metric("Total Rows", f"{count}")
    with c2:
        st.metric("Sum", format_currency(total))
    with c3:
        st.metric("Average", format_currency(avg))
    with c4:
        st.metric("Largest", format_currency(max_val))

    # CSV export
    csv_data = df[["date", "category", "description", "amount",
                    "payment_method"]].to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Export as CSV",
        data=csv_data,
        file_name="expenses_export.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════
# 5. CSV Import
# ═══════════════════════════════════════════════════════════════


def _render_csv_import() -> None:
    """Upload and import expenses from a CSV file."""

    with st.expander("📤 Import Expenses from CSV"):
        st.markdown(
            "Upload a CSV with columns: "
            "**amount**, **category**, **description**, **date** "
            "(and optionally **payment_method**)."
        )

        uploaded = st.file_uploader(
            "Choose CSV file", type=["csv"], key="csv_upload",
        )

        if uploaded is not None:
            try:
                import_df = pd.read_csv(uploaded)
            except Exception as e:
                st.error(f"❌ Could not read file: {e}")
                return

            # Validate columns
            cols = set(import_df.columns.str.lower().str.strip())
            missing = _REQUIRED_CSV_COLS - cols
            if missing:
                st.error(
                    f"❌ Missing required columns: **{', '.join(missing)}**. "
                    f"Found: {', '.join(import_df.columns)}"
                )
                return

            # Normalise column names
            import_df.columns = import_df.columns.str.lower().str.strip()

            st.markdown("#### Preview")
            st.dataframe(import_df.head(10), use_container_width=True, hide_index=True)
            st.caption(f"{len(import_df)} rows total")

            if st.button(
                f"✅ Import {len(import_df)} Expenses",
                key="csv_import_btn",
                use_container_width=True,
            ):
                success = 0
                errors = 0

                progress = st.progress(0, text="Importing…")

                for idx, row in import_df.iterrows():
                    try:
                        add_expense(
                            amount=float(row["amount"]),
                            category=str(row["category"]).strip(),
                            description=str(row.get("description", "")),
                            date_=str(row["date"]).strip(),
                            payment_method=str(
                                row.get("payment_method", "Cash")
                            ).strip(),
                        )
                        success += 1
                    except Exception:
                        errors += 1

                    progress.progress(
                        (idx + 1) / len(import_df),
                        text=f"Row {idx + 1}/{len(import_df)}",
                    )

                progress.empty()

                if errors == 0:
                    st.success(f"🎉 All **{success}** expenses imported successfully!")
                else:
                    st.warning(
                        f"Imported **{success}** expenses. "
                        f"**{errors}** rows had errors and were skipped."
                    )

                st.rerun()
