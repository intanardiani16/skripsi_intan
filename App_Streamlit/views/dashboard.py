"""Halaman Dashboard: tampilan dimuat malas (lazy), query ter-cache, peta interaktif."""
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src import config, db, kpi, ui

BLUE, RED = "#2563eb", "#dc2626"
GROWTH_YEARS = config.GROWTH_YEARS
PLOT_CFG = {"displayModeBar": False}
MAP_CFG = {"displayModeBar": False, "scrollZoom": True}
TABLE_LIMIT = 500          # batas baris yang dikirim ke browser
NAV = ["Overview", "RFM Merchant", "Perbandingan Sales Harian", "Sales Growth Analysis"]
INDONESIA_CENTER = {"lat": -2.5, "lon": 118.0}


# ------------------------------------------------------------------ helpers UI
def _kpi_css():
    st.markdown("""
    <style>
    .kpi-card{background:#fff;border-radius:12px;padding:14px 16px;height:128px;
              box-shadow:0 1px 3px rgba(15,23,42,.10);display:flex;flex-direction:column;
              justify-content:space-between;box-sizing:border-box;overflow:hidden}
    .kpi-label{font-size:11px;font-weight:700;color:#2563eb;line-height:1.2}
    .kpi-label.red{color:#dc2626}
    .kpi-value{font-size:26px;font-weight:700;color:#0f172a;line-height:1.1;white-space:nowrap}
    .kpi-sub{font-size:11px;color:#64748b;line-height:1.25;min-height:28px}
    </style>""", unsafe_allow_html=True)


def _kpi(label, value, sub="", red=False):
    st.markdown(
        f"<div class='kpi-card'><div class='kpi-label{' red' if red else ''}'>{label}</div>"
        f"<div class='kpi-value'>{value}</div><div class='kpi-sub'>{sub}</div></div>",
        unsafe_allow_html=True)


def _box(title):
    c = st.container(border=True)
    c.markdown(f"<div class='chart-title'>{title}</div>", unsafe_allow_html=True)
    return c


def _year_filter(y, w, k):
    return kpi.F(date(y, 1, 1), date(y, 12, 31), w, k)


def _growth_pct(cur: pd.Series, base: pd.Series) -> pd.Series:
    """Sales Growth Rate = (Sales_t - Sales_(t-1)) / Sales_(t-1) x 100%   [Rumus 1]"""
    return (cur - base) / base.where(base > 0, np.nan) * 100


def _monthly_table(fb, fc, base, cur) -> pd.DataFrame:
    m = pd.DataFrame({"bulan_no": range(1, 13)})
    for col, f in ((f"Sales {base}", fb), (f"Sales {cur}", fc)):
        m = m.merge(kpi.monthly_sales(f).rename(columns={"sales": col}), on="bulan_no", how="left")
    m = m.fillna(0)
    m["Bulan"] = m["bulan_no"].map(lambda i: kpi.BULAN_SHORT[i - 1])
    m["Growth (%)"] = _growth_pct(m[f"Sales {cur}"], m[f"Sales {base}"])
    return m


def _regional_table(fb, fc, base, cur) -> pd.DataFrame:
    rb = kpi.regional_contribution(fb)[["region", "sales"]].rename(columns={"sales": f"Sales {base}"})
    rc = kpi.regional_contribution(fc)[["region", "sales"]].rename(columns={"sales": f"Sales {cur}"})
    r = rb.merge(rc, on="region", how="outer").fillna(0)
    r["Growth (%)"] = _growth_pct(r[f"Sales {cur}"], r[f"Sales {base}"])
    return r.sort_values(f"Sales {cur}", ascending=False)


# ------------------------------------------------------------------------ peta
def _region_map(reg: pd.DataFrame):
    """Peta interaktif (zoom/geser, responsif) memakai tile Carto, tanpa API key.
    Ukuran bubble = sales, warna = kontribusi %."""
    geo = reg.dropna(subset=["lat", "lon"]).copy()
    if geo.empty:
        st.info("Koordinat wilayah belum tersedia untuk filter ini.")
        return
    geo["sales"] = geo["sales"].astype(float)
    geo["pct"] = geo["pct"].astype(float)
    geo["_size"] = geo["sales"].clip(lower=1)

    if len(geo) == 1:
        center = {"lat": float(geo.iloc[0]["lat"]), "lon": float(geo.iloc[0]["lon"])}
        zoom = 6
    else:
        center, zoom = INDONESIA_CENTER, 3.3

    common = dict(
        lat="lat", lon="lon", size="_size", color="pct", hover_name="region",
        hover_data={"pct": ":.1f", "sales": ":,.0f", "_size": False, "lat": False, "lon": False},
        # skala hangat supaya kontras di atas citra satelit
        color_continuous_scale=["#fde047", "#f97316", "#dc2626"],
        size_max=46, opacity=0.88, center=center, zoom=zoom, height=380,
        labels={"pct": "Kontribusi %", "sales": "Sales"},
    )
    # Mode satelit saja: tanpa basemap OSM/Carto, hanya citra Esri + label wilayah transparan
    sat_layers = [
        {"below": "traces", "sourcetype": "raster", "sourceattribution": "Esri, Maxar, Earthstar Geographics",
         "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]},
        {"below": "traces", "sourcetype": "raster", "sourceattribution": "Esri",
         "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"]},
    ]
    if hasattr(px, "scatter_map"):                      # plotly >= 5.24
        fig = px.scatter_map(geo, map_style="white-bg", **common)
        fig.update_layout(map_layers=sat_layers)
    else:                                               # plotly lama
        fig = px.scatter_mapbox(geo, mapbox_style="white-bg", **common)
        fig.update_layout(mapbox_layers=sat_layers)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                      coloraxis_colorbar=dict(title="%", thickness=10, len=0.7))
    st.plotly_chart(fig, use_container_width=True, config=MAP_CFG)


# ------------------------------------------------------------- Sales Growth tab
def _growth_tab(yrs, w, k):
    cur = st.selectbox("Tahun analisis (t)", GROWTH_YEARS, index=len(GROWTH_YEARS) - 1)
    base = cur - 1                                   # pembanding otomatis t-1
    st.markdown(f"### Sales Growth Analysis {base}–{cur}")
    st.caption(f"Pertumbuhan {cur} dibandingkan {base} (mengikuti filter Wilayah dan Kartu di atas). "
               f"Tahun analisis diatur di GROWTH_YEARS pada src/config.py.")
    both = f"{base}-{cur}"
    drill = st.radio("Drill down", [both, str(base), str(cur)], horizontal=True)
    st.caption("Tahun yang tersedia di Data Mart: " + (", ".join(map(str, yrs)) or "-"))

    needed = [base, cur] if drill == both else [int(drill)]
    missing = [y for y in needed if y not in yrs]
    if missing:
        st.warning(f"Data transaksi {', '.join(map(str, missing))} belum ada di Data Mart. "
                   f"Upload raw data tahun tersebut lalu jalankan Proses ETL.")
        return

    fb, fc = _year_filter(base, w, k), _year_filter(cur, w, k)
    sb, sc = kpi.total_sales(fb), kpi.total_sales(fc)

    if drill == both:
        g = kpi.sales_growth(sc, sb)
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Sales {base}", ui.rupiah_short(sb))
        m2.metric(f"Sales {cur}", ui.rupiah_short(sc))
        m3.metric("Sales Growth", "n/a" if g is None else f"{g:+,.2f}%")
        st.divider()

        st.markdown("#### Monthly Sales Comparison")
        mon = _monthly_table(fb, fc, base, cur)
        fig = px.line(mon, x="Bulan", y=[f"Sales {base}", f"Sales {cur}"], markers=True,
                      color_discrete_sequence=[RED, BLUE],
                      labels={"value": "Sales Volume", "variable": "Tahun"})
        fig.update_layout(height=380, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)
        st.dataframe(mon[["Bulan", f"Sales {base}", f"Sales {cur}", "Growth (%)"]],
                     hide_index=True, use_container_width=True)
        st.divider()

        st.markdown("#### Regional Sales Comparison")
        reg = _regional_table(fb, fc, base, cur)
        fig = px.bar(reg, x="region", y=[f"Sales {base}", f"Sales {cur}"], barmode="group",
                     color_discrete_sequence=[RED, BLUE],
                     labels={"value": "Sales Volume", "variable": "Tahun", "region": "Wilayah"})
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)
        st.dataframe(reg.rename(columns={"region": "Wilayah"}), hide_index=True, use_container_width=True)
        st.caption(f"Growth = (Sales {cur} − Sales {base}) / Sales {base} × 100%  [Rumus 1]")
        return

    y = int(drill)
    f, s = (fb, sb) if y == base else (fc, sc)
    reg = kpi.regional_contribution(f)           # kolom pct = Rumus 2
    appr = kpi.approval_rate(f)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Total Sales {y}", ui.rupiah_short(s))
    m2.metric("Approval Rate", "n/a" if appr is None else f"{appr:.1f}%")
    m3.metric("Wilayah Teratas", "n/a" if reg.empty else f"{reg.iloc[0]['region']} ({reg.iloc[0]['pct']:.1f}%)")
    st.divider()

    st.markdown(f"#### Monthly Sales {y}")
    mon = kpi.monthly_sales(f)
    mon["Bulan"] = mon["bulan_no"].map(lambda i: kpi.BULAN_SHORT[i - 1])
    fig = px.bar(mon, x="Bulan", y="sales", color_discrete_sequence=[RED if y == base else BLUE],
                 labels={"sales": "Sales Volume"})
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)

    st.markdown(f"#### Regional Sales {y}")
    fig = px.bar(reg, x="region", y="sales", color_discrete_sequence=[RED if y == base else BLUE],
                 labels={"region": "Wilayah", "sales": "Sales Volume"})
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)
    st.dataframe(reg[["region", "sales", "pct"]].rename(
        columns={"region": "Wilayah", "sales": "Sales", "pct": "Kontribusi %"}),
        hide_index=True, use_container_width=True)
    st.caption("Kontribusi % = Regional Sales Volume / Total Sales Volume × 100%  [Rumus 2]")


# ------------------------------------------------------------------- Overview
def _overview(ft):
    l, r = st.columns(2)
    with l, _box("REGIONAL PERFORMANCE (Kontribusi Wilayah %)"):
        reg = kpi.regional_contribution(ft)
        _region_map(reg)
        st.dataframe(reg[["region", "sales", "pct"]].head(5).rename(
            columns={"region": "Wilayah", "sales": "Sales", "pct": "Kontribusi %"}),
            hide_index=True, use_container_width=True)
    with r, _box("TOP MERCHANT CATEGORIES BY SALES VOLUME"):
        fig = px.bar(kpi.category_sales(ft), x="sales", y="merchant_type", orientation="h",
                     color_discrete_sequence=[BLUE])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=470,
                          xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)

    l, r = st.columns([1, 1.6])
    with l, _box("PAYMENT CARD DISTRIBUTION (DEBIT & CREDIT CARD)"):
        fig = px.pie(kpi.card_distribution(ft), names="card_type", values="n", hole=.6,
                     color_discrete_sequence=[RED, BLUE])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=260)
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)
    with r, _box("LATEST TRANSACTION DETAILS"):
        lt = kpi.latest_transactions(ft)
        lt["sales_volume"] = lt["sales_volume"].astype(float).map(ui.rupiah)
        st.dataframe(lt.rename(columns={
            "transaction_key": "Transaction ID", "waktu": "Date & Time",
            "merchant_name_alz": "Merchant Name", "regional_performance": "Regional Area",
            "card_type": "Card Type", "sales_volume": "Amount (Rp)", "status_trx": "Status"}),
            hide_index=True, use_container_width=True)


# ------------------------------------------------------------------ RFM
def _rfm(ft):
    st.caption("Recency = hari sejak transaksi terakhir, Frequency = jumlah transaksi, "
               "Monetary = total sales. Batas skor diatur di src/config.py.")
    df = kpi.rfm(ft)
    if df.empty:
        st.info("Tidak ada data untuk filter ini.")
        return
    x, y = st.columns([1, 2])
    x.dataframe(df["segmen"].value_counts().reset_index(), hide_index=True, use_container_width=True)
    top = df.sort_values("monetary", ascending=False).head(TABLE_LIMIT)
    y.dataframe(top[["MID", "merchant_name_alz", "recency", "frequency", "monetary",
                     "R", "F", "M", "segmen"]],
                hide_index=True, use_container_width=True, height=300)
    y.caption(f"Menampilkan {len(top):,} merchant dengan monetary tertinggi dari {len(df):,} merchant.")


# ----------------------------------------------------- Perbandingan sales harian
def _harian(t):
    dr = st.date_input("Rentang tanggal", (date(t, 1, 1), date(t, 12, 31)), key="rng_harian")
    rentang_ok = isinstance(dr, (tuple, list)) and len(dr) == 2

    m = pd.DataFrame(columns=["MID", "merchant_name_alz", "label"])
    if rentang_ok:
        try:
            with st.spinner("Memuat daftar merchant yang punya transaksi..."):
                m = kpi.merchants_aktif(dr[0], dr[1])
        except Exception as e:
            st.error(f"Gagal memuat daftar merchant: {e}")
    else:
        st.info("Pilih tanggal awal dan tanggal akhir.")

    if rentang_ok and m.empty:
        st.warning("Tidak ada merchant dengan transaksi pada rentang ini. Ubah rentang tanggal.")
    elif rentang_ok:
        st.caption(f"{len(m):,} merchant punya transaksi Approved pada rentang ini "
                   f"(diurutkan dari hari aktif terbanyak, maksimal 1.000 teratas).")

    pick = st.multiselect("Pilih 2–5 merchant", m["label"].tolist(), max_selections=5,
                          key=f"pick_{dr[0] if rentang_ok else 'x'}_{dr[1] if rentang_ok else 'x'}")

    if rentang_ok and not m.empty:
        if len(pick) < 2:
            st.info("Pilih minimal dua merchant untuk dibandingkan.")
            return
        mids = tuple(m.loc[m["label"].isin(pick), "MID"])
        ds = kpi.daily_sales(mids, dr[0], dr[1])
        if ds.empty:
            st.info("Tidak ada transaksi pada rentang ini.")
            return
        fig = px.bar(ds, x="tanggal", y="sales", color="merchant_name_alz", barmode="group",
                     labels={"sales": "Sales Volume", "tanggal": "Tanggal",
                             "merchant_name_alz": "Merchant"})
        fig.update_layout(height=420, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)

        pv = ds.pivot_table(index=["tanggal", "nama_hari"], columns="merchant_name_alz",
                            values="sales", fill_value=0)
        pv["Dominan"] = pv.idxmax(axis=1)
        st.dataframe(pv, use_container_width=True)


# --------------------------------------------------------------------- render
def render():
    ui.header("Business Intelligence", "Dashboard KPI")
    db.sync_cache()      # cache otomatis dikosongkan bila isi DB berubah (setelah ETL)

    try:
        yrs = kpi.years()
    except Exception as e:
        st.error(f"Tidak dapat membaca Data Mart: {e}")
        return
    if not yrs:
        st.info("Data Mart masih kosong. Upload raw data lalu jalankan Proses ETL.")
        return

    h1, h2 = st.columns([6, 1])
    h1.markdown("### Dashboard Monitoring Transaksi EDC MTI Success Rate")
    if h2.button("↻ Muat ulang", help="Ambil ulang data terbaru dari database"):
        st.cache_data.clear()
        st.rerun()

    c1, c2, c3 = st.columns(3)
    t = c1.selectbox("Tahun Dashboard", yrs, index=len(yrs) - 1)
    wil = c2.selectbox("Wilayah", ["All Indonesia"] + kpi.regions())
    kar = c3.selectbox("Kartu", ["Kredit & Debit", "Credit", "Debit"])
    w = None if wil == "All Indonesia" else wil
    k = None if kar == "Kredit & Debit" else kar

    with st.spinner("Memuat KPI..."):
        ft = _year_filter(t, w, k)
        s_t = kpi.total_sales(ft)
        appr = kpi.approval_rate(ft)
        act, inact = kpi.merchant_activity(ft)

        growth, g_sub = None, "Analisis growth tersedia untuk " + ", ".join(map(str, GROWTH_YEARS))
        if t in GROWTH_YEARS:
            if (t - 1) in yrs:
                growth = kpi.sales_growth(s_t, kpi.total_sales(_year_filter(t - 1, w, k)))
                g_sub = f"{t - 1} → {t}" if growth is not None else f"Tidak ada penjualan approved di {t - 1}"
            else:
                g_sub = f"Data {t - 1} belum ada di Data Mart"

    _kpi_css()
    a, b, c, d, e = st.columns(5)
    with a: _kpi("Total Sales Volume", ui.rupiah_short(s_t), f"Transaksi approved {t}")
    with b: _kpi("YoY Sales Growth", "n/a" if growth is None else f"{growth:+,.1f}%", g_sub)
    with c: _kpi("Transaction Approval Rate", "n/a" if appr is None else f"{appr:.1f}%", "Approved / Total")
    with d: _kpi("Merchant Aktif", f"{act:,}", f"Transaksi dalam {config.ACTIVE_DAYS} hari terakhir")
    with e: _kpi("Merchant Tidak Aktif", f"{inact:,}",
                 f"Tanpa transaksi {config.ACTIVE_DAYS} hari terakhir", red=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # LAZY: hanya tampilan yang dipilih yang dihitung (st.tabs menjalankan SEMUA tab tiap rerun)
    view = st.radio("Tampilan", NAV, horizontal=True, label_visibility="collapsed", key="dash_view")
    if view == NAV[0]:
        _overview(ft)
    elif view == NAV[1]:
        _rfm(ft)
    elif view == NAV[2]:
        _harian(t)
    else:
        _growth_tab(yrs, w, k)