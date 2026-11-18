"""Página Academia: biblioteca de los 30 vídeos del reto, organizada por módulos."""
import streamlit as st

from services import content as content_svc

from . import ui

COLS = 3


@st.dialog("Reproduciendo", width="large")
def player(video: dict):
    src = content_svc.playable_source(video)
    st.markdown(f"### {ui.esc(video['titulo'])}")
    if src:
        st.video(src)
    st.markdown(f"**{ui.esc(video.get('gancho', ''))}**")
    st.markdown(ui.esc(video.get("descripcion", "")))
    st.caption(video.get("modulo", ""))


def card_html(v: dict, available: bool) -> str:
    dark, light = ui.module_colors(v.get("modulo", ""))
    yid = content_svc.youtube_id(v.get("url", ""))
    if yid:
        bg = (f"background-image:linear-gradient(180deg,rgba(0,0,0,.05),rgba(0,0,0,.65)),"
              f"url('https://img.youtube.com/vi/{yid}/hqdefault.jpg')")
    else:
        bg = f"background:linear-gradient(135deg,{dark},{light})"
    num = f"{v['dia']:02d}" if v.get("dia") else "+"
    label = f"Día {v['dia']}" if v.get("dia") else "Extra"
    soon = "" if available else "<span class='soon'>Próximamente</span>"
    return (f"<div class='vcard'><div class='thumb' style=\"{bg}\"><span class='lbl'>{label}</span>{soon}"
            f"<span class='day'>{num}</span></div><div class='vbody'><b>{ui.esc(v['titulo'])}</b>"
            f"<span>{ui.esc(v.get('gancho', ''))}</span></div></div>")


def render():
    content = ui.get_content()
    videos = content["videos"]
    available = {v["id"]: content_svc.playable_source(v) is not None for v in videos}
    n_ok = sum(available[v["id"]] for v in videos if v.get("dia"))
    n_total = sum(1 for v in videos if v.get("dia"))

    st.markdown('<div class="kicker">Academia</div>', unsafe_allow_html=True)
    st.title("Aprende a invertir en 30 clases")
    st.markdown("Un vídeo corto al día, de lo más básico a la libertad financiera. "
                "Cada clase dura menos de dos minutos.")
    st.progress(n_ok / n_total if n_total else 0, text=f"{n_ok} de {n_total} clases publicadas")

    modules = list(dict.fromkeys(v.get("modulo", "") for v in videos))
    f1, f2 = st.columns([3, 1.2])
    picked = f1.pills("Módulo", ["Todos"] + modules, default="Todos", label_visibility="collapsed") or "Todos"
    query = f2.text_input("Buscar", placeholder="Buscar clase…", label_visibility="collapsed").strip().lower()

    shown = [v for v in videos
             if (picked == "Todos" or v.get("modulo") == picked)
             and (not query or query in f"{v['titulo']} {v.get('gancho', '')} {v.get('descripcion', '')}".lower())]
    if not shown:
        st.info("No hay clases que coincidan con la búsqueda.")
        return

    for modulo in dict.fromkeys(v.get("modulo", "") for v in shown):
        group = [v for v in shown if v.get("modulo") == modulo]
        st.markdown(f"#### {ui.esc(modulo)}")
        for i in range(0, len(group), COLS):
            cols = st.columns(COLS, gap="medium")
            for col, v in zip(cols, group[i:i + COLS]):
                with col:
                    st.markdown(card_html(v, available[v["id"]]), unsafe_allow_html=True)
                    if available[v["id"]]:
                        if st.button("Ver clase", key=f"play_{v['id']}", icon=":material/play_arrow:",
                                     use_container_width=True):
                            player(v)
                    else:
                        st.button("Próximamente", key=f"soon_{v['id']}", disabled=True,
                                  use_container_width=True)
