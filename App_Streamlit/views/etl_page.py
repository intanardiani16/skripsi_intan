import streamlit as st

from src import etl, ui


def render():
    ui.header("Data Processing", "Proses ETL")
    with st.container(border=True):
        st.subheader("ETL Pipeline")
        st.caption("Jalankan proses Extract, Transform, dan Load terhadap raw log.")
        c = st.columns(3)
        for col, (n, t, d) in zip(c, [("01", "Extract", "Ambil raw log dari staging (SELECT *)"),
                                      ("02", "Transform", "Cleansing, standarisasi tipe, surrogate key"),
                                      ("03", "Load", "Muat dimensi lalu fakta ke Data Mart")]):
            col.markdown(f"<div class='step'><span>{n}</span><b>{t}</b><span>{d}</span></div>", unsafe_allow_html=True)
        st.write("")
        if st.button("▶ Jalankan Proses ETL", type="primary"):
            with st.status("Menjalankan ETL ...", expanded=True) as s:
                try:
                    res = etl.run(log=st.write)
                    s.update(label="ETL berhasil", state="complete")
                    st.cache_data.clear()
                    st.session_state["etl_result"] = res
                except Exception as e:
                    s.update(label="ETL gagal", state="error")
                    st.error(f"{type(e).__name__}: {e}")
        if "etl_result" in st.session_state:
            st.json(st.session_state["etl_result"])
