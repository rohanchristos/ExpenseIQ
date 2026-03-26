"""
login_page.py — Simple Login Page for ExpenseIQ

Renders a centered login card with hardcoded admin/admin credentials.
"""

from __future__ import annotations

import streamlit as st


def render_login() -> None:
    """Render a simple, styled login page."""

    # Hide the sidebar on the login page
    st.markdown(
        "<style>"
        "[data-testid='stSidebar'] { display: none !important; }"
        "[data-testid='stSidebarCollapsedControl'] { display: none !important; }"
        "</style>",
        unsafe_allow_html=True,
    )

    # ── Centered card via columns ──────────────────────────────
    _spacer_top, col_center, _spacer_bottom = st.columns([1, 1.5, 1])

    with col_center:
        st.markdown("<br><br><br>", unsafe_allow_html=True)

        # Card wrapper open
        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        # Logo + Title
        st.markdown(
            "<div style='text-align:center;'>"
            "  <span style='font-size:3rem;'>💰</span>"
            "  <h1 style='"
            "    font-family: Space Mono, monospace;"
            "    color: #00D4AA;"
            "    font-size: 2.2rem;"
            "    margin: 8px 0 0 0;"
            "    text-shadow: 0 0 25px rgba(0,212,170,0.3);"
            "  '>ExpenseIQ</h1>"
            "  <p style='color:#8B949E; font-size:0.9rem; margin-top:4px;'>"
            "    Track smarter. Spend better."
            "  </p>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if username == "admin" and password == "admin":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        # Hint
        st.markdown(
            "<p style='text-align:center; color:#555; font-size:0.75rem; margin-top:16px;'>"
            "Default: <span style='color:#00D4AA;'>admin</span> / "
            "<span style='color:#00D4AA;'>admin</span>"
            "</p>",
            unsafe_allow_html=True,
        )

        # Card wrapper close
        st.markdown("</div>", unsafe_allow_html=True)
