"""
FinAnálisis: plataforma educativa de inversión por sectores.

Páginas: Inicio · Sectores (ETFs) · Academia (30 vídeos) · Interés compuesto · Sobre
         + Administración (solo con el modo edición activado).

Ejecutar en local:  streamlit run streamlit_app.py
"""
import streamlit as st

from services import auth
from vistas import academia, admin, inicio, interes, nav, sectores, sobre, ui

st.set_page_config(page_title="FinAnálisis", page_icon=":material/insights:", layout="wide",
                   initial_sidebar_state="collapsed")
ui.inject_css()

# ------------------------------------------------------------------ páginas
PAGES = {
    "inicio": st.Page(inicio.render, title="Inicio", icon=":material/home:", url_path="inicio", default=True),
    "sectores": st.Page(sectores.render, title="Sectores", icon=":material/monitoring:", url_path="sectores"),
    "academia": st.Page(academia.render, title="Academia", icon=":material/school:", url_path="academia"),
    "interes": st.Page(interes.render, title="Interés compuesto", icon=":material/calculate:", url_path="interes"),
    "sobre": st.Page(sobre.render, title="Sobre", icon=":material/info:", url_path="sobre"),
}
nav.PAGES.update(PAGES)
pages = list(PAGES.values())
if auth.is_admin():
    pages.append(st.Page(admin.render, title="Administración", icon=":material/edit:", url_path="admin"))

try:
    current = st.navigation(pages, position="top")
except TypeError:   # versiones antiguas de Streamlit sin menú superior
    current = st.navigation(pages)
current.run()

# ------------------------------------------------------------------ pie + acceso discreto
st.divider()
left, right = st.columns([5, 1])
left.caption("FinAnálisis · contenido educativo, no es asesoramiento financiero.")
with right:
    if auth.is_admin():
        if st.button("Salir de edición", icon=":material/lock:", use_container_width=True):
            auth.logout()
            st.rerun()
    else:
        with st.popover("Acceso", icon=":material/lock:", use_container_width=True):
            st.caption("Solo para el administrador.")
            with st.form("login", clear_on_submit=True, border=False):
                pin = st.text_input("Clave", type="password", label_visibility="collapsed",
                                    placeholder="Clave de administrador")
                if st.form_submit_button("Entrar", use_container_width=True):
                    ok, msg = auth.login(pin)
                    if ok:
                        st.rerun()
                    st.error(msg)
