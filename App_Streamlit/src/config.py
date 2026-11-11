"""Konfigurasi aplikasi."""
import hashlib
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"

SERVER = "db79247.public.databaseasp.net"
DATABASE = "db79247"
DB_USER = "db79247"
DB_PASS = "Qb7@6+fBS4=e"
RAW_TABLE = "dbo.RAW_HISTORY_MERCHANT"


# ---- Koneksi SQL Server (SQL Server Authentication) ----
def _get(key: str, default: str = "") -> str:
    """Urutan: environment variable -> st.secrets -> default."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(key, default))
    except Exception:          # secrets.toml belum ada / di luar Streamlit
        return default


SERVER   = _get("DB_SERVER")                       # db79247.public.databaseasp.net
DATABASE = _get("DB_NAME", "HISTORY_MERCHANT")     # di hosting biasanya = nama login (db79247)
DB_USER  = _get("DB_USER")
DB_PASS  = _get("DB_PASSWORD")
RAW_TABLE = "dbo.RAW_HISTORY_MERCHANT"

# ... RAW_COLUMNS, REQUIRED_COLUMNS, dst. tetap sama ...