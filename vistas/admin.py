"""
Panel de administración. Solo aparece en el menú con el modo edición activado,
y además cada acción de escritura vuelve a comprobar el permiso (require_admin).
"""
import pandas as pd
import streamlit as st

from services import auth
from services import content as content_svc

from . import ui

ETF_COLS = ["id", "sector", "ticker", "nombre", "ter", "peso", "descripcion"]
VIDEO_COLS = ["id", "dia", "modulo", "titulo", "gancho", "descripcion", "url", "archivo"]


def _secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _publish(data: dict):
    auth.require_admin()
    errors = content_svc.validate(data)
    if errors:
        for e in errors:
            st.error(e)
        return
    content_svc.save_local(data)
    token, repo = _secret("GITHUB_TOKEN"), _secret("GITHUB_REPO")
    if token and repo:
        ok, msg = content_svc.commit_to_github(data, token, repo, _secret("GITHUB_BRANCH", "main"))
        (st.success if ok else st.error)(("Guardado y " if ok else "Guardado en el servidor, pero ") + msg.lower())
        if not ok:
            st.info("Descarga content.json abajo y súbelo a GitHub a mano para no perder los cambios.")
    else:
        st.warning("Guardado en el servidor. Sin GITHUB_TOKEN configurado, los cambios se perderán "
                   "cuando la app se reinicie: descarga content.json y súbelo a GitHub.")
    st.cache_data.clear()


def _records(df: pd.DataFrame, cols) -> list[dict]:
    df = df.reindex(columns=cols)
    out = []
    for rec in df.to_dict("records"):
        clean = {}
        for k, v in rec.items():
            if isinstance(v, float) and pd.isna(v):
                v = None
            if isinstance(v, str):
                v = v.strip()
            clean[k] = v
        out.append(clean)
    return out


def render():
    auth.require_admin()
    data = ui.get_content()

    st.markdown('<span class="badge admin">Modo edición activo</span>', unsafe_allow_html=True)
    st.title("Administración")
    st.caption("Los cambios no se publican hasta que pulses «Guardar y publicar» en cada pestaña.")

    t1, t2, t3, t4 = st.tabs(["Textos", "Vídeos", "ETFs", "Copia de seguridad"])

    with t1:
        tx = data["textos"]
        with st.form("textos"):
            hero_t = st.text_input("Título de la portada", tx.get("hero_titulo", ""))
            hero_s = st.text_area("Subtítulo de la portada", tx.get("hero_subtitulo", ""), height=90)
            sobre = st.text_area("Página «Sobre» (admite Markdown: ## títulos, **negrita**, - listas)",
                                 tx.get("sobre_md", ""), height=320)
            aviso = st.text_area("Aviso legal (aparece al pie de las páginas)", tx.get("aviso_legal", ""), height=90)
            fuente = st.text_input("Fuente de los pesos por sector", data.get("pesos_fuente", ""))
            if st.form_submit_button("Guardar y publicar", type="primary"):
                new = content_svc.clone(data)
                new["textos"].update(hero_titulo=hero_t, hero_subtitulo=hero_s, sobre_md=sobre, aviso_legal=aviso)
                new["pesos_fuente"] = fuente
                _publish(new)

    with t2:
        st.markdown("Para cada clase rellena **url** (enlace de YouTube, también vale un Short) **o** "
                    "**archivo** (nombre del .mp4 subido a la carpeta `videos/` del repositorio). "
                    "Las clases sin ninguno de los dos aparecen como «Próximamente». "
                    "Añade filas al final o bórralas seleccionándolas.")
        vdf = pd.DataFrame(data["videos"]).reindex(columns=VIDEO_COLS)
        edited = st.data_editor(
            vdf, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_videos",
            column_config={
                "id": st.column_config.TextColumn("ID", required=True, width="small"),
                "dia": st.column_config.NumberColumn("Día", min_value=1, max_value=365, step=1, width="small"),
                "modulo": st.column_config.TextColumn("Módulo", required=True),
                "titulo": st.column_config.TextColumn("Título", required=True),
                "gancho": st.column_config.TextColumn("Gancho"),
                "descripcion": st.column_config.TextColumn("Descripción", width="large"),
                "url": st.column_config.LinkColumn("URL (YouTube)"),
                "archivo": st.column_config.TextColumn("Archivo .mp4"),
            })
        if st.button("Guardar y publicar vídeos", type="primary"):
            new = content_svc.clone(data)
            vids = _records(edited, VIDEO_COLS)
            for v in vids:
                v["dia"] = int(v["dia"]) if v.get("dia") is not None else None
                v["url"] = v.get("url") or ""
                v["archivo"] = v.get("archivo") or ""
            new["videos"] = vids
            _publish(new)

    with t3:
        st.markdown("Ticker de Yahoo Finance (bolsa Xetra: termina en `.DE`), TER y peso en %.")
        edf = pd.DataFrame(data["etfs"]).reindex(columns=ETF_COLS)
        edited_e = st.data_editor(
            edf, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_etfs",
            column_config={
                "id": st.column_config.TextColumn("ID", required=True, width="small"),
                "sector": st.column_config.TextColumn("Sector", required=True),
                "ticker": st.column_config.TextColumn("Ticker", required=True, width="small"),
                "nombre": st.column_config.TextColumn("Nombre del ETF"),
                "ter": st.column_config.NumberColumn("TER %", min_value=0.0, max_value=3.0, step=0.01, format="%.2f"),
                "peso": st.column_config.NumberColumn("Peso %", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"),
                "descripcion": st.column_config.TextColumn("Descripción", width="large"),
            })
        b1, b2 = st.columns([1, 2])
        b2.text_input("Ticker de referencia (índice completo)", data["benchmark"]["ticker"], key="bench_t")
        if b1.button("Guardar y publicar ETFs", type="primary"):
            new = content_svc.clone(data)
            etfs = _records(edited_e, ETF_COLS)
            for e in etfs:
                e["ticker"] = (e.get("ticker") or "").upper()
            new["etfs"] = etfs
            new["benchmark"]["ticker"] = st.session_state["bench_t"].strip().upper() or new["benchmark"]["ticker"]
            _publish(new)

    with t4:
        st.markdown("Descarga el contenido actual. Si algún día GitHub no guarda los cambios, "
                    "sube este archivo al repositorio sustituyendo a `content.json`.")
        st.download_button("Descargar content.json", content_svc.to_json(data), "content.json",
                           mime="application/json", icon=":material/download:")
        st.markdown("**Estado de la configuración**")
        st.markdown(f"- Clave de administrador: {'configurada' if auth.is_configured() else 'NO configurada'}\n"
                    f"- Publicación automática en GitHub: "
                    f"{'activada → ' + str(_secret('GITHUB_REPO')) if _secret('GITHUB_TOKEN') else 'desactivada'}")
