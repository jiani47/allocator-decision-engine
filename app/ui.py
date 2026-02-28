import streamlit as st

st.set_page_config(
    page_title="Equi — Allocator Decision Engine",
    page_icon=":",
    layout="wide",
)

st.title("Equi")
st.subheader("Allocator Decision Engine")

st.markdown(
    "Turn messy manager data into normalized, validated, "
    "and defendable investment decisions."
)

uploaded = st.file_uploader("Upload fund universe CSV", type=["csv"])

if uploaded:
    st.success(f"Uploaded: {uploaded.name}")
    st.info("Pipeline coming soon — ingestion, normalization, metrics, ranking, memo.")
