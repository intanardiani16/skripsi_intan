import pandas as pd
import streamlit as st
from sqlalchemy import text

from src import ui
from src.db import get_engine


def render():
    ui.header("Data Management", "View Raw Data")
    with st.container(border=True):
        st.subheader("Raw Log Transaksi EDC")
        st.caption("Data sebelum proses cleansing dan transformasi (maks. 1.000 baris).")
        q = st.text_input("Cari merchant ...", label_visibility="collapsed", placeholder="Cari merchant ...")
        sql = ("SELECT TOP 1000 OFFCL_MER_NM, CARD_NO, TID, trx_date, trx_time, sales_volume, "
               "respone_code, ONOFF FROM dbo.RAW_HISTORY_MERCHANT")
        p = {}
        if q:
            sql += " WHERE OFFCL_MER_NM LIKE :q"; p["q"] = f"%{q}%"
        try:
            with get_engine().connect() as c:
                st.dataframe(pd.read_sql(text(sql), c, params=p), use_container_width=True, hide_index=True)
        except Exception as e:
            st.info(f"Raw data belum tersedia. Upload file terlebih dahulu. ({type(e).__name__})")
