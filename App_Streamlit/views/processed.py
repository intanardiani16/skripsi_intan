import pandas as pd
import streamlit as st
from sqlalchemy import text

from src import kpi, ui
from src.db import get_engine


def render():
    ui.header("Data Mart", "Processed Data")
    counts = kpi.table_counts()
    with st.container(border=True):
        a, b = st.columns([4, 1])
        a.subheader("Data Hasil ETL"); a.caption("Data bersih dan terstruktur dari Data Mart (maks. 1.000 baris).")
        if counts["FACT_TRANSAKSI_EDC"]:
            b.markdown("<span class='badge'>ETL Berhasil</span>", unsafe_allow_html=True)
        try:
            with get_engine().connect() as c:
                df = pd.read_sql(text(
                    "SELECT TOP 1000 merchant_name_alz AS Merchant, merchant_type AS [Merchant Type], "
                    "regional_performance AS Provinsi, tanggal AS Tanggal, card_type AS [Card Type], "
                    "sales_volume AS [Sales Volume], status_trx AS Status FROM dbo.VW_TRANSAKSI "
                    "ORDER BY tanggal DESC"), c)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception:
            st.info("Data Mart belum terisi. Jalankan Proses ETL.")
        st.caption("Jumlah baris: " + " | ".join(f"{k}: {v:,}" for k, v in counts.items()))
