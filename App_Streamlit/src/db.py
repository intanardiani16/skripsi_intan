"""Koneksi SQL Server, helper query ber-cache, inisialisasi skema."""
import re
import urllib.parse

import pandas as pd
import pyodbc
import streamlit as st
from sqlalchemy import create_engine, text

from src import config

# --- SESUAIKAN dengan sql/schema.sql milikmu ---
FACT_TABLE = "dbo.FACT_TRANSAKSI_EDC"
FACT_ID_COL = "transaction_key"


def _driver() -> str:
    installed = pyodbc.drivers()
    for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
        if d in installed:
            return d
    raise RuntimeError("ODBC Driver untuk SQL Server belum terpasang.")


@st.cache_resource
def get_engine():
    conn = (
        f"DRIVER={{{_driver()}}};SERVER={config.SERVER};DATABASE={config.DATABASE};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"   # Windows Authentication
    )
    return create_engine(
        "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conn),
        fast_executemany=True,
        pool_size=5,          # koneksi dipakai ulang, tidak bikin koneksi baru tiap query
        max_overflow=5,
        pool_pre_ping=True,   # buang koneksi mati otomatis
        pool_recycle=1800,
    )


def ensure_schema() -> None:
    """Jalankan sql/schema.sql (idempotent)."""
    sql = config.SCHEMA_FILE.read_text(encoding="utf-8")
    batches = [b.strip() for b in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if b.strip()]
    with get_engine().begin() as conn:
        for b in batches:
            conn.execute(text(b))


@st.cache_resource(show_spinner=False)
def ensure_schema_once() -> bool:
    """Skema cukup dicek SEKALI per proses server, bukan di setiap rerun Streamlit.
    Di app.py ganti pemanggilan ensure_schema() dengan ensure_schema_once()."""
    ensure_schema()
    return True


# ---------------------------------------------------------------------------
# Query ber-cache + jaminan data selalu sama dengan isi database
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Pakai ini di kpi.py untuk query langsung (hasil di-cache per sql+params)."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


@st.cache_data(ttl=15, show_spinner=False)
def data_version() -> str:
    """'Sidik jari' murah dari fact table: jumlah baris + ID terbesar.
    Berubah setiap kali ETL memuat/menghapus data.
    WITH (NOLOCK) agar pengecekan ini tidak tertahan oleh ETL yang sedang berjalan."""
    sql = f"""
        SELECT CONCAT(
            (SELECT ISNULL(SUM(row_count), 0) FROM sys.dm_db_partition_stats
              WHERE object_id = OBJECT_ID('{FACT_TABLE}') AND index_id IN (0, 1)),
            '-',
            (SELECT ISNULL(MAX({FACT_ID_COL}), 0) FROM {FACT_TABLE} WITH (NOLOCK)))
    """
    try:
        with get_engine().connect() as conn:
            return str(conn.execute(text(sql)).scalar())
    except Exception:
        return ""   # gagal baca versi -> cache hanya kedaluwarsa lewat TTL


@st.cache_resource
def _version_holder() -> dict:
    return {"v": None}


def sync_cache() -> str:
    """Panggil di awal render dashboard. Bila isi DB berubah (mis. setelah ETL),
    seluruh cache data dikosongkan sehingga angka di layar = angka di database."""
    v = data_version()
    holder = _version_holder()
    if v and holder["v"] != v:
        if holder["v"] is not None:
            st.cache_data.clear()
        holder["v"] = v
    return v