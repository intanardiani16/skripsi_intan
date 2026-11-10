"""Entry point:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Business Intelligence | Bank X", page_icon="📊", layout="wide")

from src import auth, config, ui                            # noqa: E402
from views import dashboard, etl_page, processed, raw_data, report, upload   # noqa: E402

ui.inject_css()
if not st.session_state.get("auth"):
    auth.login_page()
    st.stop()

# Hak akses: halaman di luar daftar role otomatis dialihkan ke halaman pertama yang diizinkan
allowed = config.ROLE_PAGES.get(st.session_state.get("role"), [])
if not allowed:                       # role tidak dikenal -> paksa login ulang
    st.session_state.clear()
    st.rerun()
if st.session_state.get("page") not in allowed:
    st.session_state.page = allowed[0]

ui.sidebar()
{"Dashboard": dashboard, "Upload Raw Data": upload, "View Raw Data": raw_data,
 "Proses ETL": etl_page, "Processed Data": processed, "Laporan": report}[st.session_state.page].render()