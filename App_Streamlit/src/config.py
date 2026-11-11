"""Konfigurasi aplikasi."""
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"

# ---- Koneksi SQL Server (SQL Server Authentication) ----
SERVER = "db79247.public.databaseasp.net"
DATABASE = "db79247"
DB_USER = "db79247"
DB_PASS = "Qb7@6+fBS4=e"
RAW_TABLE = "dbo.RAW_HISTORY_MERCHANT"

RAW_COLUMNS = [
    "RSON_CTNTS_INTN", "RSON_CTNTS_RSPN", "RSON_CTNTS_ISSUR", "ACQ_MB_MID", "merchant_name_alz",
    "MID", "TID", "trx_date", "trx_time", "merchant_type", "regional_performance", "card_type",
    "status_trx", "ACQ_MB_NO", "CARD_NO", "sales_volume", "respone_code", "trx_type", "ONOFF",
    "USER_DECLINE", "OFFCL_MER_NM", "ISSUER_NAME",
]
REQUIRED_COLUMNS = ["MID", "trx_date", "sales_volume", "card_type", "trx_type", "status_trx"]


# ---- Login & hak akses (ganti sesuai kebutuhan) ----
def _h(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# email -> hash password + role
USERS = {
    "admin@bankx.co.id":      {"hash": _h("admin123"), "role": "admin"},
    "headoffice@bankx.co.id": {"hash": _h("head123"),  "role": "head"},
}

ALL_PAGES = ["Dashboard", "Upload Raw Data", "View Raw Data",
             "Proses ETL", "Processed Data", "Laporan"]

ROLE_PAGES = {
    "admin": ALL_PAGES,        # semua menu
    "head":  ["Dashboard"],    # head office hanya dashboard
}

# ---- Batas RFM (ditetapkan bersama unit operasional Bank X; sesuaikan) ----
ACTIVE_DAYS = 30                 # merchant aktif = transaksi terakhir <= 30 hari
R_BINS = (7, 30)                 # hari: <=7 skor 3, <=30 skor 2, selebihnya 1
F_BINS = (50, 200)               # jumlah transaksi: >=200 skor 3, >=50 skor 2
M_BINS = (5_000_000, 50_000_000) # rupiah: >=50jt skor 3, >=5jt skor 2

# ---- Titik koordinat provinsi (peta Regional Performance) ----
PROVINCE_COORDS = {
    "Aceh": (4.7, 96.7), "Sumatera Utara": (2.1, 99.5), "Sumatera Barat": (-0.9, 100.4),
    "Riau": (0.5, 101.4), "Kepulauan Riau": (3.9, 108.1), "Jambi": (-1.6, 103.6),
    "Sumatera Selatan": (-3.3, 104.0), "Bangka Belitung": (-2.7, 106.4), "Bengkulu": (-3.8, 102.3),
    "Lampung": (-4.6, 105.0), "Banten": (-6.4, 106.1), "DKI Jakarta": (-6.2, 106.8),
    "Jawa Barat": (-6.9, 107.6), "Jawa Tengah": (-7.2, 110.2), "DI Yogyakarta": (-7.9, 110.4),
    "Jawa Timur": (-7.5, 112.2), "Bali": (-8.4, 115.2), "Nusa Tenggara Barat": (-8.6, 117.4),
    "Nusa Tenggara Timur": (-9.5, 121.0), "Kalimantan Barat": (0.0, 109.9),
    "Kalimantan Tengah": (-1.7, 113.4), "Kalimantan Selatan": (-3.1, 115.3),
    "Kalimantan Timur": (0.5, 116.4), "Kalimantan Utara": (3.1, 116.0), "Sulawesi Utara": (1.5, 124.8),
    "Gorontalo": (0.7, 122.4), "Sulawesi Tengah": (-1.4, 121.4), "Sulawesi Barat": (-2.5, 119.4),
    "Sulawesi Selatan": (-3.7, 120.0), "Sulawesi Tenggara": (-4.1, 122.1), "Maluku": (-3.2, 129.5),
    "Maluku Utara": (1.6, 127.8), "Papua Barat": (-1.3, 133.2), "Papua": (-4.3, 138.1),
}

# ---- Sales Growth Analysis: tahun t yang boleh dianalisis (pembanding otomatis t-1) ----
GROWTH_YEARS = [2024, 2025]   # contoh: 2025 vs 2024 butuh data 2024 dan 2025 di Data Mart
