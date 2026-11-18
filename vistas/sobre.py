"""Página informativa (texto editable por el administrador)."""
import streamlit as st

from . import ui


def render():
    content = ui.get_content()
    st.markdown('<div class="kicker">Información</div>', unsafe_allow_html=True)
    st.markdown(content["textos"].get("sobre_md", ""))
    st.divider()
    st.caption(content["textos"].get("aviso_legal", ""))
