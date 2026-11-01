"""Hosted entry point: streamlit run online_cad.py --server.address 0.0.0.0"""
import streamlit as st

from contorno_cad.i18n import set_language
from contorno_cad.cloud_runtime import ensure_cloud_runtime

set_language(st.session_state.get("language", "en"))


@st.cache_resource(show_spinner="Preparing and verifying the CAD runtime…")
def prepared_runtime():
    return ensure_cloud_runtime()


try:
    prepared_runtime()
except Exception as exc:
    st.error(f"The hosted CAD runtime could not start: {exc}")
    st.info("The app owner must review the deployment logs. No model was generated.")
    st.stop()

st.caption(
    "Online evaluation demo · Uploaded files are processed on the hosting server. "
    "Project data stays in your browser session's server memory; download JSON "
    "before closing. Please use non-confidential test images."
)

from contorno_cad.ui import run
run()
