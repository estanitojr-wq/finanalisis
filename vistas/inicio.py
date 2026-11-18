"""Página de inicio: resumen del mercado por sectores, últimas clases y noticias."""
import streamlit as st

from services import content as content_svc
from services import news

from . import academia, nav, ui


@st.cache_data(ttl=600, show_spinner=False)
def macro():
    try:
        return news.macro_news(limit=6, ttl=0)
    except Exception:
        return []


def render():
    content = ui.get_content()
    t = content["textos"]
    st.markdown(f"<div class='hero'><div class='kicker'>FinAnálisis</div><h1>{ui.esc(t['hero_titulo'])}</h1>"
                f"<p>{ui.esc(t['hero_subtitulo'])}</p></div>", unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1, 1, 1, 2])
    b1.page_link(nav.PAGES["sectores"], label="Ver sectores", icon=":material/monitoring:")
    b2.page_link(nav.PAGES["academia"], label="Empezar la academia", icon=":material/school:")
    b3.page_link(nav.PAGES["interes"], label="Calculadora", icon=":material/calculate:")

    # ---------------- pulso del mercado
    closes, stats, err = ui.market_safe(content)
    st.subheader("Pulso del mercado · 1 año")
    ui.market_notice(err)
    tiles = []
    for e in sorted(content["etfs"], key=lambda x: -(stats.get(x["ticker"], {}).get("r1y") or -9)):
        r = stats.get(e["ticker"], {}).get("r1y")
        cls = "up" if r and r > 0 else "down" if r and r < 0 else ""
        tiles.append(f"<div class='tile {cls}'><div class='s'>{ui.esc(e['sector'])}</div>"
                     f"<div class='v num'>{ui.pct(r)}</div>"
                     f"<div class='t mono'>{ui.esc(e['ticker'])} · {ui.es(e.get('peso') or 0, 1)} % del índice</div></div>")
    st.markdown(f"<div class='tiles'>{''.join(tiles)}</div>", unsafe_allow_html=True)
    bm = stats.get(content["benchmark"]["ticker"], {})
    if bm.get("r1y") is not None:
        st.caption(f"MSCI World completo en el mismo periodo: {ui.pct(bm['r1y'], color=False)}. "
                   "Rentabilidades en euros con dividendos reinvertidos.")

    # ---------------- últimas clases
    st.subheader("Últimas clases")
    ready = [v for v in content["videos"] if content_svc.playable_source(v)]
    latest = sorted(ready, key=lambda v: v.get("dia") or 0, reverse=True)[:3]
    if latest:
        cols = st.columns(3, gap="medium")
        for col, v in zip(cols, latest):
            with col:
                st.markdown(academia.card_html(v, True), unsafe_allow_html=True)
                if st.button("Ver clase", key=f"home_{v['id']}", icon=":material/play_arrow:",
                             use_container_width=True):
                    academia.player(v)
    else:
        st.caption("Muy pronto: las primeras clases de la academia.")

    # ---------------- noticias
    items = macro()
    if items:
        st.subheader("Contexto económico")
        rows = "".join(
            f"<div style='padding:9px 0;border-bottom:1px solid var(--line)'>"
            f"<a href='{ui.esc(n['link'])}' target='_blank' rel='noopener'>{ui.esc(n['title'])}</a><br>"
            f"<span class='small'>{ui.esc(n['source'])}"
            f"{' · ' + n['published'].strftime('%d/%m %H:%M') if n['published'] else ''}</span></div>"
            for n in items)
        st.markdown(rows, unsafe_allow_html=True)
    st.caption(t.get("aviso_legal", ""))
