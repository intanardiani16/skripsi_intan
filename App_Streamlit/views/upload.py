import pandas as pd
import streamlit as st
from sqlalchemy import text

from src import config, ui
from src.db import ensure_schema, get_engine


LANGKAH = [
    ("Raw File", "Upload file .xlsx / .csv"),
    ("Validasi", "Cek kolom dan format data"),
    ("Staging Area", "Simpan ke tabel RAW"),
    ("Proses ETL", "Bersihkan dan bentuk Star Schema"),
]


def _alur_sistem(langkah=LANGKAH):
    """Alur sistem versi ringkas: satu baris, lingkaran bernomor dengan garis penghubung."""
    css = """<style>
.alur-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 16px 14px;margin-top:8px}
.alur-title{font-size:12px;font-weight:700;color:#2563eb;letter-spacing:.04em;text-transform:uppercase;margin-bottom:10px}
.alur-row{display:flex;align-items:flex-start;gap:0}
.alur-step{flex:1;display:flex;flex-direction:column;align-items:center;text-align:center;position:relative;padding:0 6px}
.alur-step:not(:last-child)::after{content:"";position:absolute;top:13px;left:calc(50% + 18px);right:calc(-50% + 18px);height:2px;background:#cbd5e1}
.alur-num{width:26px;height:26px;border-radius:50%;background:#2563eb;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;position:relative;z-index:1}
.alur-name{font-size:13px;font-weight:700;color:#0f172a;margin-top:6px;line-height:1.2}
.alur-desc{font-size:11px;color:#64748b;margin-top:2px;line-height:1.25}
@media (max-width:640px){.alur-row{flex-direction:column;gap:10px}.alur-step{flex-direction:row;text-align:left;gap:10px}.alur-step::after{display:none}}
</style>"""
    items = "".join(
        f"<div class='alur-step'><div class='alur-num'>{i}</div>"
        f"<div><div class='alur-name'>{nama}</div><div class='alur-desc'>{ket}</div></div></div>"
        for i, (nama, ket) in enumerate(langkah, 1)
    )
    html = (f"{css}<div class='alur-wrap'><div class='alur-title'>Alur Sistem</div>"
            f"<div class='alur-row'>{items}</div></div>")
    st.markdown(html, unsafe_allow_html=True)


def render():
    ui.header("Data Management", "Upload Raw Log EDC MTI")

    with st.container(border=True):
        st.subheader("Upload File")
        st.caption(
            "Pilih file transaksi mentah dalam format .xlsx atau .csv."
        )

        f = st.file_uploader(
            "Drag & drop file di sini",
            type=["xlsx", "csv"]
        )

        replace = st.checkbox(
            "Kosongkan raw data lama sebelum upload",
            value=False
        )

        if st.button(
            "Upload File",
            type="primary",
            disabled=f is None
        ):
            try:
                with st.status(
                    "Memproses file ...",
                    expanded=True
                ) as s:

                    # 1. Membaca file
                    if f.name.lower().endswith(".csv"):
                        df = pd.read_csv(
                            f,
                            dtype=str,
                            sep=None,
                            engine="python"
                        )
                    else:
                        df = pd.read_excel(
                            f,
                            dtype=str
                        )

                    # 2. Membersihkan nama kolom
                    df.columns = [
                        str(c).strip() for c in df.columns
                    ]

                    st.write("### Pemeriksaan File")
                    st.write("Nama file:", f.name)
                    st.write(
                        f"Jumlah baris file: {len(df):,}"
                    )

                    # 3. Validasi kolom wajib
                    miss = [
                        c for c in config.REQUIRED_COLUMNS
                        if c not in df.columns
                    ]

                    if miss:
                        s.update(
                            label="Validasi gagal",
                            state="error"
                        )
                        st.error(
                            "Kolom wajib tidak ditemukan: "
                            + ", ".join(miss)
                        )
                        return

                    # 4. Pemeriksaan kolom tanggal
                    date_col = next(
                        (
                            c for c in [
                                "TRX_DATE",
                                "trx_date"
                            ]
                            if c in df.columns
                        ),
                        None
                    )

                    if date_col:
                        tanggal = df[date_col].astype(str).str.strip()

                        st.write(
                            "Contoh tanggal:",
                            tanggal.head(10).tolist()
                        )

                        st.write(
                            "Jumlah tanggal 2024:",
                            tanggal.str.contains(
                                "2024",
                                na=False
                            ).sum()
                        )

                        st.write(
                            "Jumlah tanggal 2025:",
                            tanggal.str.contains(
                                "2025",
                                na=False
                            ).sum()
                        )

                        if tanggal.str.contains(
                            "2025",
                            na=False
                        ).sum() == 0:
                            st.warning(
                                "Tidak ditemukan tanggal tahun 2025 "
                                "pada file yang dibaca."
                            )

                    else:
                        st.warning(
                            "Kolom tanggal TRX_DATE tidak ditemukan. "
                            "Periksa nama kolom tanggal pada file."
                        )

                    # 5. Melengkapi kolom RAW
                    for c in config.RAW_COLUMNS:
                        if c not in df.columns:
                            df[c] = None

                    df = df[config.RAW_COLUMNS]

                    # Mengubah NaN menjadi None
                    df = df.astype(object).where(
                        pd.notna(df),
                        None
                    )

                    st.write(
                        f"Data siap disimpan: {len(df):,} baris"
                    )

                    # 6. Memastikan tabel tersedia
                    ensure_schema()

                    engine = get_engine()

                    # 7. Menghapus data lama hanya jika dipilih
                    if replace:
                        with engine.begin() as conn:
                            conn.execute(
                                text(
                                    f"DELETE FROM {config.RAW_TABLE}"
                                )
                            )

                    # 8. Menambahkan data ke SQL Server
                    df.to_sql(
                        "RAW_HISTORY_MERCHANT",
                        engine,
                        schema="dbo",
                        if_exists="append",
                        index=False,
                        chunksize=5000
                    )

                    # 9. Memeriksa data setelah upload
                    with engine.connect() as conn:
                        result = conn.execute(
                            text("""
                                SELECT
                                    COUNT(*) AS total_data,
                                    SUM(
                                        CASE
                                            WHEN trx_date LIKE '%2024%'
                                            THEN 1 ELSE 0
                                        END
                                    ) AS data_2024,
                                    SUM(
                                        CASE
                                            WHEN trx_date LIKE '%2025%'
                                            THEN 1 ELSE 0
                                        END
                                    ) AS data_2025
                                FROM dbo.RAW_HISTORY_MERCHANT
                            """)
                        ).mappings().first()

                    s.update(
                        label="Upload berhasil!",
                        state="complete"
                    )

                    st.success(
                        f"{len(df):,} baris berhasil ditambahkan."
                    )

                    st.write("### Ringkasan RAW Database")

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Total Data",
                        f"{result['total_data']:,}"
                    )

                    col2.metric(
                        "Data 2024",
                        f"{result['data_2024'] or 0:,}"
                    )

                    col3.metric(
                        "Data 2025",
                        f"{result['data_2025'] or 0:,}"
                    )

                    if not result["data_2025"]:
                        st.warning(
                            "Data 2025 belum terdeteksi di database. "
                            "Periksa hasil pemeriksaan tanggal file."
                        )

                st.cache_data.clear()

            except Exception as e:
                st.error(
                    f"Terjadi kesalahan saat upload: {str(e)}"
                )

    # 10. Alur Sistem (versi ringkas)
    _alur_sistem()