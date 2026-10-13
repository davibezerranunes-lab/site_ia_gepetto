"""Rota raiz: encaminha cada visitante para a página correta."""

import streamlit as st
from gepetto_core import inicializar_runtime

inicializar_runtime()

if str(st.session_state.get("usuario", "")).strip():
    st.switch_page("views/chat.py")
else:
    st.switch_page("views/login.py")

st.stop()
