from datetime import date

import streamlit as st
from fpdf import FPDF

from src import kpi, ui


def _pdf(title, rows) -> bytes:
    p = FPDF(); p.add_page()
    p.set_font("Helvetica", "B", 16); p.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", size=11)
    for k, v in rows:
        p.cell(80, 8, k); p.cell(0, 8, v, new_x="LMARGIN", new_y="NEXT")
    return bytes(p.output())


def render():
    ui.header("Reporting", "Laporan KPI")
    with st.container(border=True):
        st.subheader("Export Laporan")
        c1, c2, c3 = st.columns(3)
        d1 = c1.date_input("Periode awal", date(2025, 1, 1))
        d2 = c2.date_input("Periode akhir", date(2025, 12, 31))
        try:
            regs = kpi.regions()
        except Exception:
            regs = []
        wil = c3.selectbox("Wilayah", ["Semua Wilayah"] + regs)
        w = None if wil == "Semua Wilayah" else wil

    try:
        f = kpi.F(d1, d2, w)
        prev = kpi.F(date(d1.year - 1, d1.month, min(d1.day, 28)), date(d2.year - 1, d2.month, min(d2.day, 28)), w)
        sales, appr = kpi.total_sales(f), kpi.approval_rate(f)
        g = kpi.sales_growth(sales, kpi.total_sales(prev))
        trx = int(kpi.card_distribution(f)["n"].sum())
    except Exception:
        st.info("Data Mart belum tersedia."); return

    rows = [("Total Transaksi", f"{trx:,}"), ("Total Sales Volume", ui.rupiah_short(sales)),
            ("Approval Rate", "n/a" if appr is None else f"{appr:.1f}%"),
            ("Sales Growth (YoY)", "n/a" if g is None else f"{g:+.1f}%")]
    with st.container(border=True):
        st.markdown(f"**Business Intelligence Report** — {d1} s/d {d2}")
        for col, (k, v) in zip(st.columns(4), rows):
            col.metric(k, v)
    st.download_button("⭳ Download PDF", _pdf(f"Business Intelligence Report {d1} - {d2}", rows),
                       "laporan_bi.pdf", "application/pdf", type="primary")
