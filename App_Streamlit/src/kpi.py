"""Semua rumus KPI dihitung di sini (query ke Star Schema).

Query berat (total, approval, wilayah, kategori, kartu, bulanan, RFM, aktivitas
merchant) langsung ke FACT + dimensi yang dibutuhkan saja, dengan agregasi per
merchant_key (INT) sebelum mengambil nama merchant. Ini menekan memory grant di
SQL Server Express. Query yang butuh kolom view (trx_time, nama_hari,
transaction_key) tetap lewat dbo.VW_TRANSAKSI.

Semua tabel dibaca dengan WITH (NOLOCK) supaya dashboard tidak tertahan oleh
transaksi lain (mis. ETL yang sedang berjalan). Catatan: NOLOCK = dirty read,
jadi jangan membaca angka dashboard saat Proses ETL sedang berlangsung.
"""
from datetime import date
from typing import NamedTuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text

from src import config
from src.db import get_engine

V = "dbo.VW_TRANSAKSI"
FACT = "dbo.FACT_TRANSAKSI_EDC"
NL = "WITH (NOLOCK)"
TTL = 1800                       # cache juga dikosongkan otomatis oleh db.sync_cache()
_HINT = " OPTION (MAXDOP 2, MAX_GRANT_PERCENT = 10)"   # batasi paralelisme DAN ukuran memory grant per query


class F(NamedTuple):
    d1: date
    d2: date
    wilayah: Optional[str] = None
    kartu: Optional[str] = None


def _where(f: F):
    """Filter untuk query yang masih memakai view."""
    sql, p = "tanggal BETWEEN :d1 AND :d2", {"d1": f.d1, "d2": f.d2}
    if f.wilayah:
        sql += " AND regional_performance = :w"; p["w"] = f.wilayah
    if f.kartu:
        sql += " AND card_type = :k"; p["k"] = f.kartu
    return sql, p


def _fact(f: F, approved_only: bool = True, need_card: bool = False, need_merchant: bool = False):
    """JOIN + WHERE langsung ke fact. Alias: f=fact, w=waktu, c=kartu, m=merchant.
    Dimensi hanya di-JOIN bila benar-benar dipakai (filter atau GROUP BY)."""
    joins = f" JOIN dbo.DIM_WAKTU w {NL} ON w.date_key = f.date_key"
    where = ["w.tanggal BETWEEN :d1 AND :d2"]
    p = {"d1": f.d1, "d2": f.d2}
    if approved_only:
        where.append("f.status_trx = 'Approved'")
    if need_card or f.kartu:
        joins += f" JOIN dbo.DIM_KARTU c {NL} ON c.card_key = f.card_key"
    if f.kartu:
        where.append("c.card_type = :k"); p["k"] = f.kartu
    if need_merchant or f.wilayah:
        joins += f" JOIN dbo.DIM_MERCHANT m {NL} ON m.merchant_key = f.merchant_key"
    if f.wilayah:
        where.append("m.regional_performance = :w"); p["w"] = f.wilayah
    return joins, " AND ".join(where), p


def _q(sql: str, p: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as c:
        return pd.read_sql(text(sql), c, params=p or {})


# ---------------- referensi filter ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def years() -> list[int]:
    return _q(f"SELECT DISTINCT tahun FROM dbo.DIM_WAKTU {NL} ORDER BY tahun")["tahun"].tolist()


@st.cache_data(ttl=TTL, show_spinner=False)
def regions() -> list[str]:
    return _q(f"SELECT DISTINCT regional_performance r FROM dbo.DIM_MERCHANT {NL} ORDER BY r{_HINT}")["r"].tolist()


@st.cache_data(ttl=TTL, show_spinner=False)
def merchants() -> pd.DataFrame:
    df = _q(f"SELECT MID, merchant_name_alz FROM dbo.DIM_MERCHANT {NL} ORDER BY merchant_name_alz")
    df["label"] = df["merchant_name_alz"] + " (" + df["MID"] + ")"
    return df


@st.cache_data(ttl=TTL, show_spinner="Memuat daftar merchant...")
def merchants_aktif(d1: date, d2: date, limit: int = 1000) -> pd.DataFrame:
    """Hanya merchant yang punya transaksi Approved pada rentang tanggal d1-d2."""
    df = _q(f"""
        WITH agg AS (
            SELECT f.merchant_key,
                   COUNT(DISTINCT f.date_key)          AS hari_aktif,
                   COUNT_BIG(*)                        AS n,
                   CAST(SUM(f.sales_volume) AS FLOAT)  AS total_sales
            FROM {FACT} f {NL}
            JOIN dbo.DIM_WAKTU w {NL} ON w.date_key = f.date_key
            WHERE w.tanggal BETWEEN :d1 AND :d2 AND f.status_trx = 'Approved'
            GROUP BY f.merchant_key)
        SELECT TOP {int(limit)} dm.MID, dm.merchant_name_alz, a.hari_aktif, a.n, a.total_sales
        FROM agg a
        JOIN dbo.DIM_MERCHANT dm {NL} ON dm.merchant_key = a.merchant_key
        ORDER BY a.hari_aktif DESC, a.n DESC{_HINT}""",
        {"d1": d1, "d2": d2})
    df["label"] = (df["merchant_name_alz"] + " (" + df["MID"] + ") - "
                   + df["hari_aktif"].astype(str) + " hari, " + df["n"].astype(str) + " trx")
    return df


# ---------------- Rumus 1: Sales Growth ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def total_sales(f: F) -> float:
    j, w, p = _fact(f)
    return float(_q(f"SELECT CAST(COALESCE(SUM(f.sales_volume),0) AS FLOAT) s "
                    f"FROM {FACT} f {NL}{j} WHERE {w}{_HINT}", p)["s"][0])


def sales_growth(sales_t: float, sales_prev: float) -> Optional[float]:
    """Sales Growth Rate = (Sales_t - Sales_(t-1)) / Sales_(t-1) x 100%   [Rumus 1]"""
    return None if not sales_prev else (sales_t - sales_prev) / sales_prev * 100


# ---------------- Rumus 2: Kontribusi Wilayah ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def regional_contribution(f: F) -> pd.DataFrame:
    j, w, p = _fact(F(f.d1, f.d2, None, f.kartu), need_merchant=True)
    df = _q(f"SELECT m.regional_performance region, CAST(SUM(f.sales_volume) AS FLOAT) sales "
            f"FROM {FACT} f {NL}{j} WHERE {w} GROUP BY m.regional_performance{_HINT}", p)
    total = df["sales"].sum()
    # Regional Sales Contribution (%) = Regional Sales Volume / Total Sales Volume x 100%   [Rumus 2]
    df["pct"] = df["sales"] / total * 100 if total else 0.0
    df["lat"] = df["region"].map(lambda r: config.PROVINCE_COORDS.get(r, (None, None))[0])
    df["lon"] = df["region"].map(lambda r: config.PROVINCE_COORDS.get(r, (None, None))[1])
    return df.sort_values("sales", ascending=False)


# ---------------- Rumus 3: Approval Rate ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def approval_rate(f: F) -> Optional[float]:
    j, w, p = _fact(f, approved_only=False)
    r = _q(f"SELECT COUNT_BIG(*) total, "
           f"COALESCE(SUM(CASE WHEN f.status_trx='Approved' THEN 1 ELSE 0 END),0) ok "
           f"FROM {FACT} f {NL}{j} WHERE {w}{_HINT}", p).iloc[0]
    # Approval Rate (%) = Approved Transaction / Total Transaction x 100%   [Rumus 3]
    return float(r["ok"]) / float(r["total"]) * 100 if r["total"] else None


# ---------------- Grafik pendukung ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def category_sales(f: F) -> pd.DataFrame:
    j, w, p = _fact(f, need_merchant=True)
    return _q(f"SELECT TOP 10 m.merchant_type, CAST(SUM(f.sales_volume) AS FLOAT) sales "
              f"FROM {FACT} f {NL}{j} WHERE {w} GROUP BY m.merchant_type ORDER BY sales DESC{_HINT}", p
              ).sort_values("sales")


@st.cache_data(ttl=TTL, show_spinner=False)
def card_distribution(f: F) -> pd.DataFrame:
    j, w, p = _fact(f, approved_only=False, need_card=True)
    return _q(f"SELECT c.card_type, COUNT_BIG(*) n FROM {FACT} f {NL}{j} WHERE {w} "
              f"GROUP BY c.card_type{_HINT}", p)


@st.cache_data(ttl=TTL, show_spinner=False)
def latest_transactions(f: F) -> pd.DataFrame:
    w, p = _where(f)
    return _q(f"SELECT TOP 5 transaction_key, CONVERT(VARCHAR(10),tanggal,120)+' '+trx_time AS waktu, "
              f"merchant_name_alz, regional_performance, card_type, sales_volume, status_trx FROM {V} {NL} "
              f"WHERE {w} ORDER BY tanggal DESC, trx_time DESC{_HINT}", p)


# ---------------- RFM ----------------
def _score_r(v): return 3 if v <= config.R_BINS[0] else 2 if v <= config.R_BINS[1] else 1
def _score_hi(v, b): return 3 if v >= b[1] else 2 if v >= b[0] else 1


def _segment(total: int) -> str:
    return "Champion" if total >= 8 else "Loyal" if total >= 6 else "Potensial" if total >= 4 else "Dormant"


@st.cache_data(ttl=TTL, show_spinner=False)
def rfm(f: F) -> pd.DataFrame:
    """R = hari sejak transaksi terakhir, F = jumlah transaksi, M = total sales volume."""
    j, w, p = _fact(f)
    df = _q(f"""
        WITH agg AS (
            SELECT f.merchant_key,
                   MAX(w.tanggal)                     AS last_trx,
                   COUNT_BIG(*)                       AS frequency,
                   SUM(CAST(f.sales_volume AS FLOAT)) AS monetary
            FROM {FACT} f {NL}{j}
            WHERE {w}
            GROUP BY f.merchant_key)
        SELECT dm.MID, dm.merchant_name_alz,
               MAX(a.last_trx)  AS last_trx,
               SUM(a.frequency) AS frequency,
               SUM(a.monetary)  AS monetary
        FROM agg a
        JOIN dbo.DIM_MERCHANT dm {NL} ON dm.merchant_key = a.merchant_key
        GROUP BY dm.MID, dm.merchant_name_alz{_HINT}""", p)
    if df.empty:
        return df
    df["last_trx"] = pd.to_datetime(df["last_trx"])
    df["recency"] = (df["last_trx"].max() - df["last_trx"]).dt.days
    rb, fb, mb = config.R_BINS, config.F_BINS, config.M_BINS
    df["R"] = np.select([df["recency"] <= rb[0], df["recency"] <= rb[1]], [3, 2], default=1)
    df["F"] = np.select([df["frequency"] >= fb[1], df["frequency"] >= fb[0]], [3, 2], default=1)
    df["M"] = np.select([df["monetary"] >= mb[1], df["monetary"] >= mb[0]], [3, 2], default=1)
    tot = df["R"] + df["F"] + df["M"]
    df["segmen"] = np.select([tot >= 8, tot >= 6, tot >= 4],
                             ["Champion", "Loyal", "Potensial"], default="Dormant")
    return df.sort_values("monetary", ascending=False)


@st.cache_data(ttl=TTL, show_spinner=False)
def merchant_activity(f: F) -> tuple[int, int]:
    """(aktif, tidak aktif): aktif bila Recency <= ACTIVE_DAYS.
    Dihitung langsung di SQL (tanpa menarik seluruh tabel RFM ke Python)."""
    sql, p = f"SELECT COUNT(*) n FROM dbo.DIM_MERCHANT {NL}", {}
    if f.wilayah:
        sql += " WHERE regional_performance=:w"; p["w"] = f.wilayah
    total = int(_q(sql, p)["n"][0])

    j, w, pf = _fact(f)
    pf["ad"] = int(config.ACTIVE_DAYS)
    active = int(_q(f"""
        WITH agg AS (
            SELECT f.merchant_key, MAX(w.tanggal) AS last_trx
            FROM {FACT} f {NL}{j}
            WHERE {w}
            GROUP BY f.merchant_key)
        SELECT COALESCE(SUM(CASE WHEN DATEDIFF(day, x.last_trx, x.mx) <= :ad THEN 1 ELSE 0 END), 0) AS active
        FROM (SELECT last_trx, MAX(last_trx) OVER () AS mx FROM agg) x{_HINT}""", pf)["active"][0])
    return active, max(total - active, 0)


# ---------------- Same-Day Merchant Comparison ----------------
@st.cache_data(ttl=TTL, show_spinner=False)
def daily_sales(mids: tuple, d1: date, d2: date) -> pd.DataFrame:
    """Sales volume harian beberapa merchant, disejajarkan pada tanggal (T) dan hari (H) yang sama."""
    ph = ",".join(f":m{i}" for i in range(len(mids)))
    p = {f"m{i}": m for i, m in enumerate(mids)}
    p.update({"d1": d1, "d2": d2})
    return _q(f"SELECT tanggal, nama_hari, MID, merchant_name_alz, CAST(SUM(sales_volume) AS FLOAT) sales "
              f"FROM {V} {NL} WHERE MID IN ({ph}) AND tanggal BETWEEN :d1 AND :d2 AND status_trx='Approved' "
              f"GROUP BY tanggal, nama_hari, MID, merchant_name_alz ORDER BY tanggal{_HINT}", p)


@st.cache_data(ttl=60, show_spinner=False)
def table_counts() -> dict:
    out = {}
    for t in ("RAW_HISTORY_MERCHANT", "DIM_MERCHANT", "DIM_WAKTU", "DIM_KARTU", "DIM_JENIS_TRANSAKSI", "FACT_TRANSAKSI_EDC"):
        try:
            out[t] = int(_q(f"SELECT COUNT_BIG(*) n FROM dbo.{t} {NL}")["n"][0])
        except Exception:
            out[t] = 0
    return out


BULAN_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


@st.cache_data(ttl=TTL, show_spinner=False)
def monthly_sales(f: F) -> pd.DataFrame:
    """Total sales volume approved per bulan (bulan_no 1-12) untuk drill down growth."""
    j, w, p = _fact(f)
    return _q(f"SELECT MONTH(w.tanggal) bulan_no, CAST(SUM(f.sales_volume) AS FLOAT) sales "
              f"FROM {FACT} f {NL}{j} WHERE {w} GROUP BY MONTH(w.tanggal) ORDER BY bulan_no{_HINT}", p)