"""Execute: streamlit run iniciar_cad.py"""
import streamlit as st
from contorno_cad.i18n import t, set_language
set_language(st.session_state.get("language", "en"))
from scripts.preparar_casadi import verificar_instalacao

try:
    verificar_instalacao()
except Exception as exc:
    st.error(t(str(exc)))
    st.code("python scripts/preparar_casadi.py")
    st.stop()

from contorno_cad.ui import run
run()
