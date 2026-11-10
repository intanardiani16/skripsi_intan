import hashlib
import hmac

import streamlit as st

from src import config, db

_HIDE_SIDEBAR = ("<style>[data-testid='stSidebar'],"
                 "[data-testid='stSidebarCollapsedControl']{display:none}</style>")


def _check(email: str, pw: str):
    """Return role jika kredensial valid, None jika salah."""
    user = config.USERS.get(email.strip().lower())
    if not user:
        return None
    given = hashlib.sha256(pw.strip().encode()).hexdigest()
    return user["role"] if hmac.compare_digest(user["hash"], given) else None


def login_page():
    st.markdown(_HIDE_SIDEBAR, unsafe_allow_html=True)
    slot = st.empty()          # seluruh kartu login hidup di dalam slot ini
    ok, email, role = False, "", None

    with slot.container():
        st.write("")
        _, c, _ = st.columns([1.2, 1, 1.2])
        with c.container(border=True):
            st.markdown("<div style='text-align:center'><div class='logo'>BI</div>"
                        "<h3 style='margin:.5rem 0 0'>Business Intelligence</h3>"
                        "<p class='muted'>Dashboard Transaksi EDC MTI</p></div>",
                        unsafe_allow_html=True)
            with st.form("login"):
                email = st.text_input("Email", placeholder="admin@bankx.co.id")
                pw = st.text_input("Password", type="password")
                ok = st.form_submit_button("Login", type="primary", use_container_width=True)
            role = _check(email, pw) if ok else None
            if ok and not role:
                st.error("Email atau password salah.")
            st.caption("Demo: admin@bankx.co.id / admin123  |  "
                       "headoffice@bankx.co.id / head123 (ubah di src/config.py)")

    if ok and role:
        slot.empty()                                   # hapus kartu login SEKARANG juga
        with st.spinner("Memuat dashboard..."):
            st.session_state.update(auth=True, user=email.strip().lower(),
                                    role=role, page="Dashboard")
            db.ensure_schema_once()                    # sekali per server
            db.sync_cache()
        st.rerun()