"""Komponen tampilan bersama (tema sesuai desain)."""
import streamlit as st

from src import config

MENU = [("Dashboard", "▦"), ("Upload Raw Data", "⇪"), ("View Raw Data", "☰"),
        ("Proses ETL", "⚙"), ("Processed Data", "✓"), ("Laporan", "▤")]

CSS = """
<style>
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2rem;max-width:1280px}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"]{background:#0f172a}
[data-testid="stSidebar"][aria-expanded="true"]{width:270px !important;min-width:270px !important;
  max-width:270px !important}
[data-testid="stSidebar"] *{color:#cbd5e1}
[data-testid="stSidebarUserContent"]{padding:.5rem .8rem 1rem}

/* isi sidebar dibuat setinggi layar, Logout otomatis turun ke bawah */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.55rem;min-height:calc(100vh - 8.5rem)}
[data-testid="stSidebar"] .stButton{margin:0}
.st-key-nav_logout{margin-top:auto !important;padding-top:.8rem;border-top:1px solid #1e293b}

/* tombol menu */
[data-testid="stSidebar"] .stButton>button{justify-content:flex-start !important;text-align:left !important;
  border:0;background:transparent;color:#cbd5e1;padding:.35rem .9rem;font-size:.92rem;
  min-height:2.6rem;height:2.6rem;line-height:1.2;border-radius:8px}
[data-testid="stSidebar"] .stButton>button>div,
[data-testid="stSidebar"] .stButton>button [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] .stButton>button p{width:100%;justify-content:flex-start !important;
  text-align:left !important;margin:0;font-size:.92rem}
[data-testid="stSidebar"] .stButton>button:hover{background:#1e293b;color:#fff}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:#1e3a8a;color:#fff;
  min-height:2.6rem;height:2.6rem;padding:.35rem .9rem;border-radius:8px}

/* ===== PANAH BUKA/TUTUP: selalu terlihat ===== */
/* panah di dalam sidebar (latar gelap) -> warna TERANG */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] button{opacity:1 !important;visibility:visible !important}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] button *,
[data-testid="stSidebarHeader"] button *{color:#f1f5f9 !important;fill:#f1f5f9 !important}
[data-testid="stSidebarCollapseButton"] button:hover{background:#1e293b}

/* panah saat sidebar ditutup / layar penuh (latar terang) -> warna GELAP */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"]{opacity:1 !important;visibility:visible !important}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button{opacity:1 !important;visibility:visible !important}
[data-testid="stSidebarCollapsedControl"] *,
[data-testid="stExpandSidebarButton"] *{color:#0f172a !important;fill:#0f172a !important}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stExpandSidebarButton"]:hover{background:#e2e8f0}

/* ===== KOMPONEN LAIN ===== */
.brand{display:flex;gap:.7rem;align-items:center;padding:.4rem .2rem 3rem}
.brand b{color:#fff;font-size:.88rem;white-space:nowrap;display:block;line-height:1.25}
.brand small{display:block;color:#64748b;white-space:nowrap}
.brand>div:last-child{min-width:0}
.logo{display:inline-flex;width:40px;height:40px;border-radius:10px;background:#2563eb;color:#fff;
  font-weight:700;align-items:center;justify-content:center}
.muted{color:#64748b;font-size:.8rem}
.eyebrow{font-size:.68rem;letter-spacing:.08em;color:#2563eb;font-weight:600;text-transform:uppercase}
.ptitle{font-size:1.45rem;font-weight:700;margin:0 0 1rem}
.kpi{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:.9rem 1rem;
  box-shadow:0 1px 3px rgba(15,23,42,.08);margin-bottom:.5rem}
.kpi .t{font-size:.72rem;font-weight:700;color:#1d4ed8}.kpi .v{font-size:1.9rem;font-weight:700;margin-top:.2rem}
.kpi.red .t{color:#dc2626}.kpi .s{font-size:.7rem;color:#64748b}
.kpi .v.small{
    font-size:1.45rem;
    font-weight:700;
    white-space:nowrap;
}
.chart-title{font-size:.78rem;font-weight:700;color:#1d4ed8;margin-bottom:.2rem}
.badge{background:#dcfce7;color:#15803d;padding:.1rem .6rem;border-radius:99px;font-size:.7rem;font-weight:600}
.step{border:1px solid #e2e8f0;border-radius:10px;padding:.9rem;background:#f8fafc;height:100%}
.step b{display:block;font-size:1rem}.step span{color:#64748b;font-size:.78rem}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(eyebrow: str, title: str):
    st.markdown(f"<div class='eyebrow'>{eyebrow}</div><div class='ptitle'>{title}</div>", unsafe_allow_html=True)


def kpi_card(title: str, value: str, sub: str = "", red: bool = False):
    st.markdown(f"<div class='kpi {'red' if red else ''}'><div class='t'>{title}</div>"
                f"<div class='v'>{value}</div><div class='s'>{sub}</div></div>", unsafe_allow_html=True)


def rupiah_short(x: float) -> str:
    for div, suf in ((1e12, "T"), (1e9, "M"), (1e6, "Jt")):
        if abs(x) >= div:
            return f"Rp {x / div:,.2f} {suf}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Rp {x:,.0f}".replace(",", ".")


def rupiah(x: float) -> str:
    return f"Rp {x:,.0f}".replace(",", ".")


@st.dialog("Konfirmasi logout")
def _logout_dialog():
    st.write("Apakah Anda yakin ingin logout?")
    a, b = st.columns(2)
    if a.button("OK", type="primary", use_container_width=True):
        st.session_state.clear(); st.rerun()
    if b.button("Cancel", use_container_width=True):
        st.rerun()


def sidebar():
    allowed = config.ROLE_PAGES.get(st.session_state.get("role"), [])
    with st.sidebar:
        st.markdown("<div class='brand'><div class='logo'>BI</div><div><b>Business Intelligence</b>"
                    "<small>Bank X</small></div></div>", unsafe_allow_html=True)
        for name, icon in MENU:
            if name not in allowed:          # sembunyikan menu di luar hak akses role
                continue
            if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True,
                         type="primary" if st.session_state.page == name else "secondary"):
                st.session_state.page = name; st.rerun()
        # Logout otomatis menempel di bawah lewat CSS (.st-key-nav_logout)
        if st.button("↪  Logout", key="nav_logout", use_container_width=True):
            _logout_dialog()