
"""Proses ETL: RAW_HISTORY_MERCHANT -> pandas -> Star Schema."""

import pandas as pd
from sqlalchemy import text

from src import config
from src.db import ensure_schema, get_engine


BULAN = [
    "Januari", "Februari", "Maret", "April",
    "Mei", "Juni", "Juli", "Agustus",
    "September", "Oktober", "November", "Desember"
]

HARI = [
    "Senin", "Selasa", "Rabu", "Kamis",
    "Jumat", "Sabtu", "Minggu"
]


# ============================================================
# EXTRACT
# ============================================================

def extract() -> pd.DataFrame:
    """Mengambil data mentah dari tabel RAW."""

    with get_engine().connect() as conn:
        return pd.read_sql(
            text(f"SELECT * FROM {config.RAW_TABLE}"),
            conn
        )


# ============================================================
# HELPER
# ============================================================

def _title_wilayah(s: pd.Series) -> pd.Series:
    out = s.str.strip().str.title()

    out = out.str.replace(
        r"^Dki\b", "DKI", regex=True
    )

    out = out.str.replace(
        r"^Di\b", "DI", regex=True
    )

    return out


def parse_trx_date(s: pd.Series) -> pd.Series:
    """
    Membaca beberapa format tanggal:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - Excel serial number
    """

    s = s.astype("string").str.strip()

    out = pd.Series(
        pd.NaT,
        index=s.index,
        dtype="datetime64[ns]"
    )

    iso = s.str.match(
        r"^\d{4}-\d{1,2}-\d{1,2}",
        na=False
    )

    dmy = s.str.match(
        r"^\d{1,2}/\d{1,2}/\d{4}",
        na=False
    )

    serial = s.str.match(
        r"^\d{5}(\.\d+)?$",
        na=False
    )

    if iso.any():
        out.loc[iso] = pd.to_datetime(
            s.loc[iso].str.extract(
                r"^(\d{4}-\d{1,2}-\d{1,2})"
            )[0],
            format="%Y-%m-%d",
            errors="coerce"
        )

    if dmy.any():
        out.loc[dmy] = pd.to_datetime(
            s.loc[dmy].str.extract(
                r"^(\d{1,2}/\d{1,2}/\d{4})"
            )[0],
            format="%d/%m/%Y",
            errors="coerce"
        )

    if serial.any():
        out.loc[serial] = pd.to_datetime(
            pd.to_numeric(s.loc[serial]),
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )

    return out


# ============================================================
# TRANSFORM
# ============================================================

def transform(raw: pd.DataFrame) -> dict:

    df = raw.copy()
    total_raw = len(df)

    # 1. Bersihkan data
    for col in df.columns:
        df[col] = df[col].astype("string").str.strip()

    df = df.replace("", pd.NA)

    df = df.dropna(
        subset=config.REQUIRED_COLUMNS
    )

    df = df.drop_duplicates()

    # 2. Konversi tanggal
    df["trx_date"] = parse_trx_date(
        df["trx_date"]
    )

    # 3. Konversi nilai transaksi
    df["sales_volume"] = pd.to_numeric(
        df["sales_volume"].str.replace(
            ",", "", regex=False
        ),
        errors="coerce"
    )

    df = df.dropna(
        subset=["trx_date", "sales_volume"]
    )

    # 4. Standarisasi atribut
    df["regional_performance"] = _title_wilayah(
        df["regional_performance"].fillna(
            "Tidak Diketahui"
        )
    )

    df["merchant_type"] = (
        df["merchant_type"]
        .fillna("OTHERS")
        .str.upper()
    )

    df["merchant_name_alz"] = (
        df["merchant_name_alz"]
        .fillna(df["MID"])
    )

    df["card_type"] = df["card_type"].str.title()
    df["trx_type"] = df["trx_type"].str.title()

    df["status_trx"] = (
        df["status_trx"]
        .str.upper()
        .map(
            lambda x: (
                "Approved"
                if x == "APPROVED"
                else "Declined"
            )
        )
    )

    # 5. Standarisasi waktu transaksi
    df["trx_time"] = (
        df["trx_time"]
        .fillna("000000")
        .str.replace(r"\D", "", regex=True)
        .str.zfill(6)
        .str[:6]
    )

    df["trx_time"] = (
        df["trx_time"].str[:2]
        + ":"
        + df["trx_time"].str[2:4]
        + ":"
        + df["trx_time"].str[4:6]
    )

    # ========================================================
    # DIMENSI
    # Tidak membuat key manual.
    # Key akan dibuat otomatis oleh SQL Server.
    # ========================================================

    dim_merchant = (
        df[
            [
                "MID",
                "merchant_name_alz",
                "merchant_type",
                "regional_performance"
            ]
        ]
        .drop_duplicates(subset=["MID"])
        .reset_index(drop=True)
    )

    # DIM WAKTU
    dim_waktu = (
        df[["trx_date"]]
        .drop_duplicates()
        .sort_values("trx_date")
        .reset_index(drop=True)
    )

    dim_waktu["tanggal"] = dim_waktu["trx_date"].dt.date
    dim_waktu["tahun"] = dim_waktu["trx_date"].dt.year

    dim_waktu["bulan"] = (
        dim_waktu["trx_date"].dt.month
        .map(lambda m: BULAN[m - 1])
    )

    dim_waktu["bulan_no"] = (
        dim_waktu["trx_date"].dt.month
    )

    dim_waktu["nama_hari"] = (
        dim_waktu["trx_date"].dt.dayofweek
        .map(lambda i: HARI[i])
    )

    dim_waktu = dim_waktu[
        [
            "tanggal",
            "tahun",
            "bulan",
            "bulan_no",
            "nama_hari"
        ]
    ]

    # DIM KARTU
    dim_kartu = (
        df[["card_type"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # DIM JENIS TRANSAKSI
    dim_jenis = (
        df[["trx_type"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # FACT sementara, belum memiliki foreign key
    fact_temp = df[
        [
            "MID",
            "trx_date",
            "card_type",
            "trx_type",
            "sales_volume",
            "status_trx",
            "trx_time"
        ]
    ].copy()

    return {
        "DIM_MERCHANT": dim_merchant,
        "DIM_WAKTU": dim_waktu,
        "DIM_KARTU": dim_kartu,
        "DIM_JENIS_TRANSAKSI": dim_jenis,
        "FACT_TEMP": fact_temp,

        "_stats": {
            "raw": total_raw,
            "clean": len(df)
        }
    }


# ============================================================
# LOAD
# ============================================================

def load(tables: dict) -> None:

    engine = get_engine()

    with engine.begin() as conn:

        # 1. Hapus data lama dari tabel fakta dan dimensi
        # RAW_HISTORY_MERCHANT tidak dihapus.

        delete_order = [
            "FACT_TRANSAKSI_EDC",
            "DIM_MERCHANT",
            "DIM_WAKTU",
            "DIM_KARTU",
            "DIM_JENIS_TRANSAKSI"
        ]

        for table_name in delete_order:
            conn.execute(
                text(
                    f"DELETE FROM dbo.{table_name}"
                )
            )

        # 2. Insert seluruh dimensi
        # Kolom IDENTITY tidak dikirimkan.

        tables["DIM_WAKTU"].to_sql(
            "DIM_WAKTU",
            conn,
            schema="dbo",
            if_exists="append",
            index=False,
            chunksize=5000
        )

        tables["DIM_MERCHANT"].to_sql(
            "DIM_MERCHANT",
            conn,
            schema="dbo",
            if_exists="append",
            index=False,
            chunksize=5000
        )

        tables["DIM_KARTU"].to_sql(
            "DIM_KARTU",
            conn,
            schema="dbo",
            if_exists="append",
            index=False
        )

        tables["DIM_JENIS_TRANSAKSI"].to_sql(
            "DIM_JENIS_TRANSAKSI",
            conn,
            schema="dbo",
            if_exists="append",
            index=False
        )

        # 3. Ambil key yang dibuat otomatis oleh SQL Server

        merchant_map = pd.read_sql(
            text("""
                SELECT merchant_key, MID
                FROM dbo.DIM_MERCHANT
            """),
            conn
        )

        waktu_map = pd.read_sql(
            text("""
                SELECT date_key, tanggal
                FROM dbo.DIM_WAKTU
            """),
            conn
        )

        kartu_map = pd.read_sql(
            text("""
                SELECT card_key, card_type
                FROM dbo.DIM_KARTU
            """),
            conn
        )

        jenis_map = pd.read_sql(
            text("""
                SELECT trx_type_key, trx_type
                FROM dbo.DIM_JENIS_TRANSAKSI
            """),
            conn
        )

        # 4. Siapkan tanggal untuk proses mapping

        fact = tables["FACT_TEMP"].copy()

        fact["tanggal"] = (
            fact["trx_date"].dt.date
        )

        waktu_map["tanggal"] = pd.to_datetime(
            waktu_map["tanggal"],
            errors="coerce"
        ).dt.date

        # 5. Hubungkan fact dengan seluruh dimensi

        fact = (
            fact
            .merge(
                merchant_map,
                on="MID",
                how="left",
                validate="many_to_one"
            )
            .merge(
                waktu_map,
                on="tanggal",
                how="left",
                validate="many_to_one"
            )
            .merge(
                kartu_map,
                on="card_type",
                how="left",
                validate="many_to_one"
            )
            .merge(
                jenis_map,
                on="trx_type",
                how="left",
                validate="many_to_one"
            )
        )

        # 6. Validasi foreign key

        key_columns = [
            "merchant_key",
            "date_key",
            "card_key",
            "trx_type_key"
        ]

        if fact[key_columns].isna().any().any():
            raise ValueError(
                "Mapping foreign key gagal. "
                "Periksa data dimensi dan data transaksi."
            )

        # 7. Pilih kolom fact
        # transaction_key dibuat otomatis oleh SQL Server.

        fact = fact[
            [
                "merchant_key",
                "date_key",
                "card_key",
                "trx_type_key",
                "sales_volume",
                "status_trx",
                "trx_time"
            ]
        ]

        # 8. Insert fact

        fact.to_sql(
            "FACT_TRANSAKSI_EDC",
            conn,
            schema="dbo",
            if_exists="append",
            index=False,
            chunksize=5000
        )


# ============================================================
# RUN ETL
# ============================================================

def run(log=print) -> dict:

    ensure_schema()

    log("Extract: membaca RAW_HISTORY_MERCHANT ...")

    raw = extract()

    if raw.empty:
        raise ValueError(
            "Raw data kosong. Silakan upload file terlebih dahulu."
        )

    log(
        f"Extract selesai: {len(raw):,} baris."
    )

    log("Transform: membersihkan dan mengolah data ...")

    tables = transform(raw)

    stats = tables["_stats"]

    log(
        f"Transform selesai: {stats['clean']:,} "
        f"dari {stats['raw']:,} baris lolos pembersihan."
    )

    log("Load: memasukkan data ke tabel dimensi dan fakta ...")

    load(tables)

    log("Load selesai: seluruh dimensi dan fakta berhasil dimuat.")

    return {
        key: len(value)
        for key, value in tables.items()
        if not key.startswith("_")
    } | stats
